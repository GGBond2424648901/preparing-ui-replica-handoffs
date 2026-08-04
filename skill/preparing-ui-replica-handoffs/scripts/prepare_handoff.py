from __future__ import annotations

import argparse
import csv
import ctypes
import errno
import hashlib
import io
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import sys
import tempfile

from jsonschema import Draft202012Validator, FormatChecker
from PIL import Image, UnidentifiedImageError


SCHEMA_VERSION = "1.0.0"
SUPPORTED_SUFFIXES = {".gif", ".jpeg", ".jpg", ".png", ".webp"}
FORMAT_DETAILS = {
    "GIF": ("image/gif", ".gif"),
    "JPEG": ("image/jpeg", ".jpg"),
    "PNG": ("image/png", ".png"),
    "WEBP": ("image/webp", ".webp"),
}
CANONICAL_LOCALES = ("zh-CN", "en-US")
DETERMINISTIC_GENERATED_AT = "1970-01-01T00:00:00Z"
AT_FDCWD_LINUX = -100
RENAME_NOREPLACE = 1
RENAME_EXCL = 0x00000004
NO_REPLACE_COLLISION_ERRNOS = frozenset(
    {errno.EEXIST, errno.ENOTEMPTY, errno.ENOTDIR, errno.EISDIR}
)
NO_REPLACE_UNSUPPORTED_ERRNOS = frozenset(
    value
    for value in (
        errno.EINVAL,
        getattr(errno, "ENOSYS", None),
        getattr(errno, "ENOTSUP", None),
        getattr(errno, "EOPNOTSUPP", None),
    )
    if value is not None
)
SKILL_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOT = SKILL_ROOT / "assets" / "templates"
SCHEMA_ROOT = SKILL_ROOT / "assets" / "schemas"
SCHEMA_CONTRACTS = {
    "contracts/asset-manifest.json": "asset-manifest.schema.json",
    "contracts/page-inventory.json": "page-inventory.schema.json",
    "contracts/ui-style-contract.json": "ui-style-contract.schema.json",
    "contracts/component-registry.json": "component-registry.schema.json",
    "contracts/implementation-map.json": "implementation-map.schema.json",
    "contracts/capture-profile.json": "capture-profile.schema.json",
    "contracts/diff-regions.json": "diff-regions.schema.json",
    "contracts/design-lock.json": "design-lock.schema.json",
}


class _AtomicNoReplaceUnavailable(RuntimeError):
    pass


def _load_libc_function(name: str, argtypes: list[type]):
    try:
        library = ctypes.CDLL(None, use_errno=True)
        function = getattr(library, name)
    except (AttributeError, OSError) as error:
        raise _AtomicNoReplaceUnavailable(
            f"atomic no-replace directory move is unsupported: missing {name}"
        ) from error
    function.argtypes = argtypes
    function.restype = ctypes.c_int
    return function


def _call_libc_rename(function, arguments: tuple, destination: Path) -> None:
    ctypes.set_errno(0)
    if function(*arguments) == 0:
        return
    error_number = ctypes.get_errno()
    if error_number == 0:
        raise RuntimeError("atomic no-replace directory move failed without errno")
    raise OSError(error_number, os.strerror(error_number), os.fspath(destination))


def _linux_atomic_no_replace_directory_move(
    source: Path, destination: Path
) -> None:
    renameat2 = _load_libc_function(
        "renameat2",
        [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ],
    )
    _call_libc_rename(
        renameat2,
        (
            AT_FDCWD_LINUX,
            os.fsencode(source),
            AT_FDCWD_LINUX,
            os.fsencode(destination),
            RENAME_NOREPLACE,
        ),
        destination,
    )


def _bsd_atomic_no_replace_directory_move(source: Path, destination: Path) -> None:
    try:
        renamex_np = _load_libc_function(
            "renamex_np", [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
        )
    except _AtomicNoReplaceUnavailable:
        try:
            renameatx_np = _load_libc_function(
                "renameatx_np",
                [
                    ctypes.c_int,
                    ctypes.c_char_p,
                    ctypes.c_int,
                    ctypes.c_char_p,
                    ctypes.c_uint,
                ],
            )
        except _AtomicNoReplaceUnavailable as renameatx_error:
            raise _AtomicNoReplaceUnavailable(
                "atomic no-replace directory move is unsupported: "
                "missing renamex_np and renameatx_np"
            ) from renameatx_error
        _call_libc_rename(
            renameatx_np,
            (
                0,
                os.fsencode(os.path.abspath(source)),
                0,
                os.fsencode(os.path.abspath(destination)),
                RENAME_EXCL,
            ),
            destination,
        )
        return
    _call_libc_rename(
        renamex_np,
        (os.fsencode(source), os.fsencode(destination), RENAME_EXCL),
        destination,
    )


def _atomic_no_replace_directory_move(source: Path, destination: Path) -> None:
    if os.name == "nt":
        os.rename(source, destination)
        return
    if sys.platform.startswith("linux"):
        _linux_atomic_no_replace_directory_move(source, destination)
        return
    if sys.platform == "darwin" or sys.platform.startswith(
        ("freebsd", "openbsd", "netbsd", "dragonfly")
    ):
        _bsd_atomic_no_replace_directory_move(source, destination)
        return
    raise _AtomicNoReplaceUnavailable(
        f"atomic no-replace directory move is unsupported on {sys.platform}"
    )


def _remove_empty_probe_paths(paths: tuple[Path, ...]) -> None:
    # Path-based cleanup cannot prove that a same-owner process did not replace
    # an empty probe directory after the capability check. Preserve probe
    # paths instead of risking deletion of raced-in owner data.
    del paths


def _preflight_atomic_no_replace_directory_move(parent_root: Path) -> None:
    probe_root = Path(
        tempfile.mkdtemp(prefix=".handoff-no-replace-probe-", dir=parent_root)
    )
    source = probe_root / "source"
    destination = probe_root / "destination"
    source.mkdir()
    destination.mkdir()
    try:
        try:
            _atomic_no_replace_directory_move(source, destination)
        except OSError as error:
            if error.errno in NO_REPLACE_COLLISION_ERRNOS:
                if source.is_dir() and destination.is_dir():
                    return
                raise RuntimeError(
                    "atomic no-replace capability probe did not preserve directories"
                ) from error
            if error.errno in NO_REPLACE_UNSUPPORTED_ERRNOS:
                raise _AtomicNoReplaceUnavailable(
                    "atomic no-replace directory move is unsupported by the "
                    "publication filesystem"
                ) from error
            raise
        raise _AtomicNoReplaceUnavailable(
            "atomic no-replace directory move replaced an existing directory"
        )
    finally:
        _remove_empty_probe_paths((source, destination, probe_root))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def collect_images(source_root: Path) -> list[dict]:
    return [
        {key: value for key, value in image.items() if key != "_content"}
        for image in _scan_image_snapshots(source_root)
    ]


def _scan_image_snapshots(source_root: Path) -> list[dict]:
    source_root = Path(source_root)
    if not source_root.exists():
        raise FileNotFoundError(f"source directory does not exist: {source_root}")
    if not source_root.is_dir():
        raise NotADirectoryError(f"source path is not a directory: {source_root}")

    resolved_root = source_root.resolve()
    candidates = [
        path
        for path in source_root.rglob("*")
        if path.is_file() and path.suffix.casefold() in SUPPORTED_SUFFIXES
    ]
    candidates.sort(
        key=lambda path: (
            path.relative_to(source_root).as_posix().casefold(),
            path.relative_to(source_root).as_posix(),
        )
    )
    if not candidates:
        raise ValueError(f"source directory contains no supported image files: {source_root}")

    images = []
    for path in candidates:
        resolved_path = path.resolve()
        if not _is_within(resolved_path, resolved_root):
            raise ValueError(f"source image escapes the source directory: {path}")
        content = path.read_bytes()
        try:
            with Image.open(io.BytesIO(content)) as image:
                image_format = (image.format or "").upper()
                image.load()
                width, height = image.size
        except (OSError, UnidentifiedImageError, ValueError) as error:
            raise ValueError(f"corrupt or invalid image: {path}") from error
        if image_format not in FORMAT_DETAILS:
            raise ValueError(f"invalid supported image format for {path}: {image_format}")
        media_type, canonical_suffix = FORMAT_DETAILS[image_format]
        images.append(
            {
                "sourceRelativePath": path.relative_to(source_root).as_posix(),
                "mediaType": media_type,
                "canonicalSuffix": canonical_suffix,
                "byteSize": len(content),
                "width": width,
                "height": height,
                "sha256": hashlib.sha256(content).hexdigest(),
                "_content": content,
            }
        )
    return images


def _record_set_hash(records: list[tuple[str, str]]) -> str:
    digest = hashlib.sha256()
    for relative_path, file_hash in records:
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_hash.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def _source_set_hash(images: list[dict]) -> str:
    return _record_set_hash(
        [(image["sourceRelativePath"], image["sha256"]) for image in images]
    )


def _validate_inputs(
    source_root: Path,
    output_root: Path,
    design_version: str,
    languages: tuple[str, ...],
) -> tuple[Path, Path]:
    source_root = Path(source_root).resolve()
    output_root = Path(output_root).resolve()
    if source_root == output_root or _is_within(output_root, source_root):
        raise ValueError("output directory must not be nested under the source directory")
    if _is_within(source_root, output_root):
        raise ValueError("source and output directories must not overlap")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", design_version):
        raise ValueError("design_version must be a safe, non-empty path segment")
    if len(languages) != 2 or set(languages) != set(CANONICAL_LOCALES):
        raise ValueError("languages must contain zh-CN and en-US exactly once")
    return source_root, output_root


def _read_schema(schema_name: str) -> dict:
    return json.loads((SCHEMA_ROOT / schema_name).read_text(encoding="utf-8"))


def _contract_is_schema_valid(schema_name: str, document: dict) -> bool:
    return not list(
        Draft202012Validator(
            _read_schema(schema_name), format_checker=FormatChecker()
        ).iter_errors(document)
    )


def _managed_output_snapshot(output_root: Path) -> dict | None:
    documents = {}
    try:
        for relative_path, schema_name in SCHEMA_CONTRACTS.items():
            path = output_root / relative_path
            if path.is_symlink() or not path.is_file():
                return None
            document = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(document, dict) or not _contract_is_schema_valid(
                schema_name, document
            ):
                return None
            documents[relative_path] = document
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None

    lock = documents["contracts/design-lock.json"]
    manifest = documents["contracts/asset-manifest.json"]
    page_inventory = documents["contracts/page-inventory.json"]
    if (
        lock["status"] != "generated"
        or lock["generatedAt"] != DETERMINISTIC_GENERATED_AT
    ):
        return None
    if (
        lock["designVersion"] != manifest["designVersion"]
        or lock["sourceSetHash"] != manifest["sourceSetHash"]
    ):
        return None

    manifest_source_records = [
        (asset["sourceRelativePath"], asset["sha256"])
        for asset in manifest["assets"]
    ]
    if _record_set_hash(manifest_source_records) != manifest["sourceSetHash"]:
        return None
    asset_ids = [asset["assetId"] for asset in manifest["assets"]]
    source_paths = [asset["sourceRelativePath"] for asset in manifest["assets"]]
    delivery_paths = [asset["deliveryRelativePath"] for asset in manifest["assets"]]
    if (
        len(asset_ids) != len(set(asset_ids))
        or len(source_paths) != len(set(source_paths))
        or len(delivery_paths) != len(set(delivery_paths))
    ):
        return None

    referenced_asset_ids = {
        asset_id
        for page in page_inventory["pages"]
        for asset_id in page["sourceAssetIds"]
    }
    if referenced_asset_ids != set(asset_ids):
        return None

    expected_files = {"contracts/design-lock.json"}
    expected_directories = set()
    locked_hashes = {}
    for entry in lock["files"]:
        relative_path = entry["relativePath"]
        expected_hash = entry["sha256"]
        if relative_path in locked_hashes:
            return None
        relative = Path(relative_path)
        if relative.is_absolute() or ".." in relative.parts or "\\" in relative_path:
            return None
        locked_path = output_root / relative
        if locked_path.is_symlink() or not locked_path.is_file():
            return None
        if sha256_file(locked_path) != expected_hash:
            return None
        normalized = relative.as_posix()
        locked_hashes[normalized] = expected_hash
        expected_files.add(normalized)
        parent = relative.parent
        while parent != Path("."):
            expected_directories.add(parent.as_posix())
            parent = parent.parent

    actual_files = set()
    actual_directories = set()
    for path in output_root.rglob("*"):
        if path.is_symlink():
            return None
        relative = path.relative_to(output_root).as_posix()
        if path.is_file():
            actual_files.add(relative)
        elif path.is_dir():
            actual_directories.add(relative)
        else:
            return None
    if actual_files != expected_files or actual_directories != expected_directories:
        return None

    contract_records = [
        (entry["relativePath"], entry["sha256"])
        for entry in lock["files"]
        if entry["relativePath"].startswith("contracts/")
    ]
    if _record_set_hash(contract_records) != lock["contractsHash"]:
        return None
    for asset in manifest["assets"]:
        if locked_hashes.get(asset["deliveryRelativePath"]) != asset["sha256"]:
            return None

    snapshot_files = tuple(
        sorted(
            (relative_path, sha256_file(output_root / relative_path))
            for relative_path in actual_files
        )
    )
    return {
        "files": snapshot_files,
        "directories": tuple(sorted(actual_directories)),
    }


def _authorize_output(output_root: Path, force: bool) -> dict | None:
    if not output_root.exists():
        return None
    if not output_root.is_dir():
        raise FileExistsError(f"output collision with a non-directory path: {output_root}")
    snapshot = _managed_output_snapshot(output_root)
    if snapshot is None:
        raise FileExistsError(f"unmanaged output collision: {output_root}")
    if not force:
        raise FileExistsError(
            f"managed output already exists; pass force=True to replace it: {output_root}"
        )
    return snapshot


def _numbered(prefix: str, number: int, width: int = 3) -> str:
    return f"{prefix}{number:0{width}d}"


def _build_assets(images: list[dict], design_version: str) -> list[dict]:
    duplicate_members: dict[str, list[int]] = {}
    for index, image in enumerate(images):
        duplicate_members.setdefault(image["sha256"], []).append(index)
    duplicate_hashes = sorted(
        (members[0], file_hash)
        for file_hash, members in duplicate_members.items()
        if len(members) > 1
    )
    duplicate_ids = {
        file_hash: _numbered("D", number)
        for number, (_, file_hash) in enumerate(duplicate_hashes, start=1)
    }

    assets = []
    for number, image in enumerate(images, start=1):
        identity = f"P{number:03d}-S01-V01"
        assets.append(
            {
                "assetId": _numbered("A", number),
                "sourceRelativePath": image["sourceRelativePath"],
                "deliveryRelativePath": (
                    f"assets/designs/{design_version}/"
                    f"{identity}-unclassified{image['canonicalSuffix']}"
                ),
                "mediaType": image["mediaType"],
                "byteSize": image["byteSize"],
                "width": image["width"],
                "height": image["height"],
                "sha256": image["sha256"],
                "duplicateGroupId": duplicate_ids.get(image["sha256"]),
                "evidenceLevel": "direct",
                "gapIds": [],
            }
        )
    return assets


def _identity(number: int) -> dict:
    return {
        "pageId": _numbered("P", number),
        "stateId": _numbered("S", 1, width=2),
        "variantId": _numbered("V", 1, width=2),
    }


def _qa_entries(page_number: int) -> list[dict]:
    first = (page_number - 1) * 3 + 1
    return [
        {
            "qaId": _numbered("QA", first + offset),
            "evidenceTypes": [evidence_type],
            "status": "not-run",
        }
        for offset, evidence_type in enumerate(("visual", "structural", "interaction"))
    ]


def _build_page_inventory(assets: list[dict]) -> dict:
    pages = []
    for number, asset in enumerate(assets, start=1):
        identity = _identity(number)
        gap_id = _numbered("G", number)
        pages.append(
            {
                **identity,
                "sourceAssetIds": [asset["assetId"]],
                "route": {
                    "path": None,
                    "evidenceLevel": "unknown",
                    "gapId": gap_id,
                },
                "canvas": {
                    "width": asset["width"],
                    "height": asset["height"],
                    "unit": "px",
                },
                "shell": {
                    "shellId": "unclassified",
                    "evidenceLevel": "unknown",
                    "gapId": gap_id,
                },
                "regions": [
                    {
                        "regionId": "region-canvas",
                        "role": "unknown",
                        "bounds": {
                            "x": 0,
                            "y": 0,
                            "width": asset["width"],
                            "height": asset["height"],
                        },
                        "evidenceLevel": "unknown",
                        "gapIds": [gap_id],
                    }
                ],
                "layoutRelationships": [],
                "copy": [],
                "icons": [],
                "components": [],
                "data": [],
                "interactions": [],
                "responsiveVariants": [
                    {
                        "responsiveVariantId": "baseline-scroll",
                        "mode": "baseline-scroll",
                        "minWidth": asset["width"],
                        "evidenceLevel": "direct",
                        "status": "approved",
                        "gapIds": [],
                    }
                ],
                "acceptanceCriteria": _qa_entries(number),
                "evidenceLevel": "direct",
                "status": "candidate",
                "gapIds": [gap_id],
            }
        )
    return {"schemaVersion": SCHEMA_VERSION, "pages": pages}


def _build_ui_style_contract(global_gap_id: str) -> dict:
    return {
        "schemaVersion": SCHEMA_VERSION,
        "evidenceLevel": "unknown",
        "status": "proposed",
        "tokens": {
            "colors": [],
            "typography": [],
            "spacing": [],
            "radii": [],
            "shadows": [],
        },
        "responsiveVariants": [
            {
                "responsiveVariantId": "baseline-scroll",
                "mode": "baseline-scroll",
                "evidenceLevel": "unknown",
                "status": "proposed",
                "gapIds": [global_gap_id],
            }
        ],
        "gapIds": [global_gap_id],
    }


def _git_scope() -> dict:
    return {
        "repositoryRelativeRoot": ".",
        "allowedNewPaths": ["ui-replica-handoff/"],
        "allowedModifiedPaths": [],
    }


def _build_implementation_map(assets: list[dict]) -> dict:
    mappings = []
    for number, _asset in enumerate(assets, start=1):
        gap_id = _numbered("G", number)
        mappings.append(
            {
                **_identity(number),
                "route": None,
                "targetFiles": [],
                "shellComponentId": None,
                "regionMappings": [],
                "componentMappings": [],
                "dataBindings": [],
                "interactionMappings": [],
                "responsiveMappings": [
                    {
                        "responsiveVariantId": "baseline-scroll",
                        "strategy": "baseline-scroll",
                        "targetFiles": [],
                        "status": "proposed",
                        "evidenceLevel": "unknown",
                        "gapIds": [gap_id],
                    }
                ],
                "evidenceLevel": "unknown",
                "status": "proposed",
                "gapIds": [gap_id],
            }
        )
    return {
        "schemaVersion": SCHEMA_VERSION,
        "gitScope": _git_scope(),
        "mappings": mappings,
    }


def _capture_profile_id(number: int) -> str:
    identity = _identity(number)
    return (
        f"capture-{identity['pageId']}-{identity['stateId']}-{identity['variantId']}"
    )


def _build_capture_profiles(assets: list[dict]) -> dict:
    profiles = []
    for number, asset in enumerate(assets, start=1):
        gap_id = _numbered("G", number)
        profiles.append(
            {
                "captureProfileId": _capture_profile_id(number),
                "browser": "unclassified",
                "browserVersion": "unclassified",
                "viewport": {"width": asset["width"], "height": asset["height"]},
                "dpr": 1,
                "locale": "unclassified",
                "timezone": "unclassified",
                "theme": "unknown",
                "fontEnvironment": ["unclassified"],
                "colorScheme": "no-preference",
                "reducedMotion": True,
                "evidenceLevel": "unknown",
                "gapIds": [gap_id],
            }
        )
    return {"schemaVersion": SCHEMA_VERSION, "profiles": profiles}


def _build_diff_regions(assets: list[dict]) -> dict:
    pages = []
    for number, asset in enumerate(assets, start=1):
        pages.append(
            {
                **_identity(number),
                "captureProfileId": _capture_profile_id(number),
                "regions": [
                    {
                        "regionId": "region-canvas",
                        "bounds": {
                            "x": 0,
                            "y": 0,
                            "width": asset["width"],
                            "height": asset["height"],
                        },
                        "comparisonModes": [
                            "reference",
                            "current",
                            "overlay",
                            "diff",
                        ],
                        "evidenceTypes": ["visual", "structural", "interaction"],
                        "tolerance": {"pixelRatio": 0},
                        "status": "not-run",
                    }
                ],
            }
        )
    return {"schemaVersion": SCHEMA_VERSION, "pages": pages}


def _json_bytes(document: dict) -> bytes:
    return (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _csv_bytes(fieldnames: list[str], rows: list[dict]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def _read_template(relative_path: str) -> str:
    return (TEMPLATE_ROOT / relative_path).read_text(encoding="utf-8")


def _render_template(relative_path: str, values: dict[str, str]) -> bytes:
    rendered = _read_template(relative_path)
    for key, value in values.items():
        rendered = rendered.replace("{{" + key + "}}", value)
    if "{{" in rendered or "}}" in rendered:
        raise RuntimeError(f"unresolved template placeholder in {relative_path}")
    return rendered.encode("utf-8")


def _page_rows(assets: list[dict], locale: str) -> str:
    if locale == "zh-CN":
        lines = ["| 身份 | 来源 | 画布 | 语义 |", "|---|---|---|---|"]
        unknown = "未分类（见缺口）"
    else:
        lines = ["| Identity | Source | Canvas | Semantics |", "|---|---|---|---|"]
        unknown = "Unclassified (see gap)"
    for number, asset in enumerate(assets, start=1):
        identity = f"P{number:03d}-S01-V01"
        lines.append(
            f"| [{identity}](pages/{identity}-unclassified.md) "
            f"| `{asset['sourceRelativePath']}` "
            f"| {asset['width']}×{asset['height']} px | {unknown} |"
        )
    return "\n".join(lines)


def _gap_summary(assets: list[dict], locale: str) -> str:
    if locale == "zh-CN":
        return (
            f"已登记 {len(assets) + 1} 个未解决缺口。页面语义、路由、交互、实现映射、"
            "捕获环境与样式在获得证据前均保持 unknown/unclassified。"
        )
    return (
        f"{len(assets) + 1} unresolved gaps are registered. Page semantics, routes, "
        "interactions, implementation mappings, capture environments, and styles remain "
        "unknown/unclassified until supported by evidence."
    )


def _page_doc_values(number: int, asset: dict, locale: str) -> dict[str, str]:
    identity = f"P{number:03d}-S01-V01"
    gap_id = _numbered("G", number)
    image_link = f"../../../{asset['deliveryRelativePath']}"
    if locale == "zh-CN":
        identity_text = (
            f"- 身份：`{identity}`\n"
            f"- 来源资产：`{asset['assetId']}` / `{asset['sourceRelativePath']}`\n"
            f"- 直接证据：[设计图副本]({image_link})\n"
            f"- 页面语义：`unclassified`；缺口：`{gap_id}`"
        )
        canvas_text = (
            f"- 画布：{asset['width']} × {asset['height']} px（直接证据）\n"
            f"- Shell：`unclassified`（unknown，`{gap_id}`）\n"
            f"- 区域：整幅画布占位区域；语义角色未知（`{gap_id}`）"
        )
        content_text = "未从像素自动推断布局、文案、图标或数据。相关清单保持为空。"
        behavior_text = (
            "未自动创建组件或交互。默认仅登记原始宽度的 `baseline-scroll` 变体；"
            f"任何额外响应式行为均需证据（`{gap_id}`）。"
        )
        qa_text = (
            f"视觉、结构与交互 QA 均为 `not-run`。完成前必须解决或批准缺口 `{gap_id}`。"
        )
    else:
        identity_text = (
            f"- Identity: `{identity}`\n"
            f"- Source asset: `{asset['assetId']}` / `{asset['sourceRelativePath']}`\n"
            f"- Direct evidence: [design copy]({image_link})\n"
            f"- Page semantics: `unclassified`; gap: `{gap_id}`"
        )
        canvas_text = (
            f"- Canvas: {asset['width']} × {asset['height']} px (direct evidence)\n"
            f"- Shell: `unclassified` (unknown, `{gap_id}`)\n"
            f"- Region: whole-canvas placeholder; semantic role unknown (`{gap_id}`)"
        )
        content_text = (
            "No layout, copy, icon, or data semantics were inferred from pixels. "
            "Those inventories remain empty."
        )
        behavior_text = (
            "No components or interactions were invented. Only an original-width "
            f"`baseline-scroll` variant is registered; responsive behavior needs evidence (`{gap_id}`)."
        )
        qa_text = (
            f"Visual, structural, and interaction QA are `not-run`. Gap `{gap_id}` "
            "must be resolved or approved before completion."
        )
    return {
        "pageId": f"P{number:03d}",
        "stateId": "S01",
        "variantId": "V01",
        "identityAndEvidence": identity_text,
        "canvasShellAndRegions": canvas_text,
        "layoutCopyIconsAndData": content_text,
        "componentsInteractionsAndResponsive": behavior_text,
        "qaAndGaps": qa_text,
    }


def _build_markdown_documents(
    assets: list[dict], design_version: str, source_set_hash: str
) -> dict[str, bytes]:
    documents: dict[str, bytes] = {}
    locale_details = {
        "zh-CN": {
            "directory": "zh",
            "catalog": "设计稿总目录.md",
            "guide": "UI实施说明.md",
            "components": "组件规范.md",
            "template_directory": "zh",
        },
        "en-US": {
            "directory": "en",
            "catalog": "Design-Catalog.md",
            "guide": "UI-Implementation-Guide.md",
            "components": "Component-Specification.md",
            "template_directory": "en",
        },
    }
    for locale in CANONICAL_LOCALES:
        details = locale_details[locale]
        docs_root = f"docs/{details['directory']}"
        template_root = f"docs/{details['template_directory']}"
        documents[f"{docs_root}/{details['catalog']}"] = _render_template(
            f"{template_root}/design-catalog.template.md",
            {
                "designVersion": design_version,
                "sourceSetHash": source_set_hash,
                "pageInventoryTable": _page_rows(assets, locale),
                "gapSummary": _gap_summary(assets, locale),
            },
        )
        if locale == "zh-CN":
            authority = "设计图像是视觉直接证据；产品资料优先于推断；未知项必须关联缺口。"
            qa_git = (
                "视觉、结构与交互 QA 初始均未运行。不得把此骨架声明为实施完成，"
                "也不得修改 Git 状态。"
            )
            registry = "尚未根据人工证据分类组件；注册表保持为空。"
            styles = "样式令牌未知，并已关联全局缺口。"
            states = "不得从单张默认图推断未展示的状态或变体。"
        else:
            authority = (
                "Design images are direct visual evidence; product materials outrank "
                "inference; every unknown must link to a gap."
            )
            qa_git = (
                "Visual, structural, and interaction QA all start not-run. This skeleton "
                "must not be claimed implementation-complete and does not mutate Git state."
            )
            registry = "No components are classified without human-supported evidence."
            styles = "Style tokens are unknown and linked to the global gap."
            states = "Unshown states and variants are not inferred from a default image."
        documents[f"{docs_root}/{details['guide']}"] = _render_template(
            f"{template_root}/ui-implementation-guide.template.md",
            {
                "authorityOrder": authority,
                "implementationMapPath": "../../contracts/implementation-map.json",
                "qaAndGitSafety": qa_git,
            },
        )
        documents[f"{docs_root}/{details['components']}"] = _render_template(
            f"{template_root}/component-specification.template.md",
            {
                "componentRegistry": registry,
                "styleTokens": styles,
                "componentStatesAndVariants": states,
            },
        )
        for number, asset in enumerate(assets, start=1):
            identity = f"P{number:03d}-S01-V01"
            documents[f"{docs_root}/pages/{identity}-unclassified.md"] = _render_template(
                f"{template_root}/page-contract.template.md",
                _page_doc_values(number, asset, locale),
            )
    return documents


def _build_csv_documents(assets: list[dict]) -> dict[str, bytes]:
    requirement_fields = [
        "requirementId",
        "source",
        "authorityRank",
        "summaryZh",
        "summaryEn",
        "pageId",
        "stateId",
        "variantId",
        "evidenceLevel",
        "status",
        "gapId",
    ]
    gap_fields = [
        "gapId",
        "severity",
        "status",
        "category",
        "summaryZh",
        "summaryEn",
        "pageId",
        "stateId",
        "variantId",
        "evidenceLevel",
        "owner",
        "resolution",
    ]
    qa_fields = [
        "qaId",
        "pageId",
        "stateId",
        "variantId",
        "captureProfileId",
        "regionId",
        "evidenceType",
        "referencePath",
        "currentPath",
        "overlayPath",
        "diffPath",
        "status",
        "notesZh",
        "notesEn",
    ]
    requirements = []
    gaps = []
    qa_rows = []
    for number, asset in enumerate(assets, start=1):
        identity = _identity(number)
        gap_id = _numbered("G", number)
        requirements.append(
            {
                "requirementId": _numbered("R", number),
                "source": f"design-image:{asset['sourceRelativePath']}",
                "authorityRank": "1",
                "summaryZh": "保留并复刻此设计图的可见视觉证据",
                "summaryEn": "Preserve and replicate the visible evidence in this design image",
                **identity,
                "evidenceLevel": "direct",
                "status": "approved",
                "gapId": "",
            }
        )
        gaps.append(
            {
                "gapId": gap_id,
                "severity": "major",
                "status": "open",
                "category": "page-semantics-and-behavior",
                "summaryZh": "页面名称、路由、Shell、组件、交互、捕获环境与响应式语义待确认",
                "summaryEn": (
                    "Page name, route, shell, components, interactions, capture environment, "
                    "and responsive semantics need confirmation"
                ),
                **identity,
                "evidenceLevel": "unknown",
                "owner": "",
                "resolution": "",
            }
        )
        for qa in _qa_entries(number):
            evidence_type = qa["evidenceTypes"][0]
            qa_rows.append(
                {
                    "qaId": qa["qaId"],
                    **identity,
                    "captureProfileId": _capture_profile_id(number),
                    "regionId": "region-canvas",
                    "evidenceType": evidence_type,
                    "referencePath": asset["deliveryRelativePath"],
                    "currentPath": "",
                    "overlayPath": "",
                    "diffPath": "",
                    "status": "not-run",
                    "notesZh": "等待实现与验证",
                    "notesEn": "Awaiting implementation and validation",
                }
            )
    global_gap_id = _numbered("G", len(assets) + 1)
    gaps.append(
        {
            "gapId": global_gap_id,
            "severity": "major",
            "status": "open",
            "category": "global-style-and-environment",
            "summaryZh": "全局样式令牌与批准的验证环境待确认",
            "summaryEn": "Global style tokens and the approved validation environment need confirmation",
            "pageId": "",
            "stateId": "",
            "variantId": "",
            "evidenceLevel": "unknown",
            "owner": "",
            "resolution": "",
        }
    )
    return {
        "contracts/requirement-ledger.csv": _csv_bytes(requirement_fields, requirements),
        "contracts/gap-register.csv": _csv_bytes(gap_fields, gaps),
        "contracts/visual-qa-matrix.csv": _csv_bytes(qa_fields, qa_rows),
    }


def _build_generated_files(
    assets: list[dict], design_version: str, source_set_hash: str
) -> dict[str, bytes]:
    global_gap_id = _numbered("G", len(assets) + 1)
    files = {
        "README.md": (
            "# UI Replica Handoff / UI 复刻交付\n\n"
            "This deterministic preparation skeleton preserves source evidence and records "
            "unknowns without inventing UI semantics. It is not an implementation-complete "
            "or validation-passing claim.\n\n"
            "此确定性准备骨架保留来源证据，并在不虚构 UI 语义的前提下登记未知项。"
            "它不代表实现完成或验证通过。\n"
        ).encode("utf-8"),
        "contracts/asset-manifest.json": _json_bytes(
            {
                "schemaVersion": SCHEMA_VERSION,
                "designVersion": design_version,
                "sourceSetHash": source_set_hash,
                "assets": assets,
            }
        ),
        "contracts/page-inventory.json": _json_bytes(_build_page_inventory(assets)),
        "contracts/ui-style-contract.json": _json_bytes(
            _build_ui_style_contract(global_gap_id)
        ),
        "contracts/component-registry.json": _json_bytes(
            {"schemaVersion": SCHEMA_VERSION, "components": []}
        ),
        "contracts/implementation-map.json": _json_bytes(
            _build_implementation_map(assets)
        ),
        "contracts/capture-profile.json": _json_bytes(
            _build_capture_profiles(assets)
        ),
        "contracts/diff-regions.json": _json_bytes(_build_diff_regions(assets)),
        "reports/validation-report.json": _json_bytes(
            {
                "schemaVersion": SCHEMA_VERSION,
                "status": "not-run",
                "issues": [
                    {
                        "code": "VALIDATION_NOT_RUN",
                        "severity": "blocker",
                        "messageZh": "完整验证器尚未运行。",
                        "messageEn": "The full validator has not run.",
                    }
                ],
            }
        ),
        "tools/validate-command.txt": (
            "python validate_handoff.py --handoff-root .\n"
        ).encode("utf-8"),
    }
    files.update(_build_csv_documents(assets))
    files.update(_build_markdown_documents(assets, design_version, source_set_hash))
    return files


def _planned_files(assets: list[dict], generated_files: dict[str, bytes]) -> list[str]:
    return sorted(
        [*generated_files, *(asset["deliveryRelativePath"] for asset in assets), "contracts/design-lock.json"]
    )


def _write_files(root: Path, files: dict[str, bytes]) -> None:
    for relative_path in sorted(files):
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        _write_bytes_exclusive(path, files[relative_path])


def _write_bytes_exclusive(path: Path, content: bytes) -> None:
    with path.open("xb") as stream:
        stream.write(content)


def _copy_and_verify_sources(
    source_root: Path,
    staging_root: Path,
    assets: list[dict],
    image_snapshots: list[dict],
) -> None:
    del source_root
    for asset, image in zip(assets, image_snapshots):
        destination = staging_root / asset["deliveryRelativePath"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        _write_bytes_exclusive(destination, image["_content"])

    for asset in assets:
        copy = staging_root / asset["deliveryRelativePath"]
        try:
            copy_hash = sha256_file(copy)
        except OSError as error:
            raise RuntimeError(
                f"copied asset changed or drifted: {asset['deliveryRelativePath']}"
            ) from error
        if copy_hash != asset["sha256"]:
            raise RuntimeError(
                f"copied asset hash drift: {asset['deliveryRelativePath']}"
            )


def _assert_source_set_unchanged(source_root: Path, initial_images: list[dict]) -> None:
    try:
        current_images = collect_images(source_root)
    except (FileNotFoundError, NotADirectoryError, ValueError, OSError) as error:
        raise RuntimeError("source set changed or drifted during preparation") from error
    initial_records = [
        {key: value for key, value in image.items() if key != "_content"}
        for image in initial_images
    ]
    if (
        _source_set_hash(current_images) != _source_set_hash(initial_records)
        or current_images != initial_records
    ):
        raise RuntimeError("source set changed or drifted during preparation")


def _write_design_lock(
    staging_root: Path, design_version: str, source_set_hash: str
) -> None:
    generated_paths = sorted(
        path
        for path in staging_root.rglob("*")
        if path.is_file()
        and path.relative_to(staging_root).as_posix() != "contracts/design-lock.json"
    )
    locked_files = [
        {
            "relativePath": path.relative_to(staging_root).as_posix(),
            "sha256": sha256_file(path),
        }
        for path in generated_paths
    ]
    contract_files = [
        entry
        for entry in locked_files
        if entry["relativePath"].startswith("contracts/")
    ]
    contracts_hash = _record_set_hash(
        [(entry["relativePath"], entry["sha256"]) for entry in contract_files]
    )
    lock = {
        "schemaVersion": SCHEMA_VERSION,
        "designVersion": design_version,
        "generatedAt": DETERMINISTIC_GENERATED_AT,
        "sourceSetHash": source_set_hash,
        "contractsHash": contracts_hash,
        "files": locked_files,
        "status": "generated",
    }
    lock_path = staging_root / "contracts" / "design-lock.json"
    _write_bytes_exclusive(lock_path, _json_bytes(lock))


def _publication_collision(message: str) -> FileExistsError:
    return FileExistsError(f"output drift/race collision: {message}")


def _create_unique_recovery_root(output_root: Path) -> Path:
    return Path(
        tempfile.mkdtemp(
            prefix=output_root.name + ".recovery-",
            dir=output_root.parent,
        )
    )


def _remove_empty_recovery_root(recovery_root: Path) -> None:
    # Recovery directories are intentionally retained. Removing an apparently
    # empty path has an unavoidable same-owner replacement race.
    del recovery_root


def _publish_staging(
    staging_root: Path, output_root: Path, authorized_snapshot: dict | None
) -> dict:
    recovery_root = _create_unique_recovery_root(output_root)
    publication = {
        "recoveryRoot": recovery_root,
        "previousRoot": None,
    }
    if authorized_snapshot is None:
        if os.path.lexists(output_root):
            raise _publication_collision(output_root.name)
        _atomic_no_replace_directory_move(staging_root, output_root)
        return publication

    if _managed_output_snapshot(output_root) != authorized_snapshot:
        raise _publication_collision(output_root.name)
    previous_root = recovery_root / "previous"
    publication["previousRoot"] = previous_root
    _atomic_no_replace_directory_move(output_root, previous_root)
    if _managed_output_snapshot(previous_root) != authorized_snapshot:
        if not output_root.exists():
            _atomic_no_replace_directory_move(previous_root, output_root)
        raise _publication_collision(output_root.name)
    if output_root.exists():
        raise _publication_collision(
            f"new target appeared; previous package preserved at "
            f"{recovery_root.name}/previous"
        )
    if _managed_output_snapshot(previous_root) != authorized_snapshot:
        if not output_root.exists():
            _atomic_no_replace_directory_move(previous_root, output_root)
        raise _publication_collision(output_root.name)
    try:
        _atomic_no_replace_directory_move(staging_root, output_root)
    except BaseException:
        if previous_root.exists() and not output_root.exists():
            _atomic_no_replace_directory_move(previous_root, output_root)
        raise
    return publication


def _move_to_unique_quarantine(output_root: Path, recovery_root: Path) -> Path:
    while True:
        reservation_root = recovery_root / f"quarantine-{secrets.token_hex(16)}"
        try:
            reservation_root.mkdir(mode=0o700)
        except FileExistsError:
            continue
        quarantine_root = reservation_root / "package"
        try:
            _atomic_no_replace_directory_move(output_root, quarantine_root)
        except OSError as error:
            if error.errno in NO_REPLACE_COLLISION_ERRNOS:
                continue
            raise
        return quarantine_root


def _quarantine_after_source_drift(output_root: Path, publication: dict) -> None:
    previous_root = publication["previousRoot"]
    if not output_root.exists():
        raise RuntimeError("post-publication source drift; public target is missing")
    recovery_root = publication["recoveryRoot"]
    try:
        if not recovery_root.is_dir() or recovery_root.is_symlink():
            raise NotADirectoryError(str(recovery_root))
        _move_to_unique_quarantine(output_root, recovery_root)
    except (FileNotFoundError, NotADirectoryError):
        recovery_root = _create_unique_recovery_root(output_root)
        publication["recoveryRoot"] = recovery_root
        _move_to_unique_quarantine(output_root, recovery_root)
    if previous_root is not None:
        if output_root.exists():
            raise RuntimeError("post-publication source drift; restore collision")
        _atomic_no_replace_directory_move(previous_root, output_root)


def _finalize_publication(publication: dict) -> None:
    if publication["previousRoot"] is None:
        _remove_empty_recovery_root(publication["recoveryRoot"])


def prepare_handoff(
    source_root: Path,
    output_root: Path,
    design_version: str,
    languages: tuple[str, ...] = ("zh-CN", "en-US"),
    dry_run: bool = False,
    force: bool = False,
) -> dict:
    source_root, output_root = _validate_inputs(
        source_root, output_root, design_version, languages
    )
    images = _scan_image_snapshots(source_root)
    authorized_snapshot = _authorize_output(output_root, force)
    source_set_hash = _source_set_hash(images)
    assets = _build_assets(images, design_version)
    generated_files = _build_generated_files(assets, design_version, source_set_hash)
    planned_files = _planned_files(assets, generated_files)
    result = {
        "status": "dry-run" if dry_run else "prepared",
        "assetCount": len(assets),
        "sourceSetHash": source_set_hash,
        "pageIdentities": [
            f"P{number:03d}-S01-V01" for number in range(1, len(assets) + 1)
        ],
        "plannedFiles": planned_files,
        "packageRoot": ".",
    }
    if dry_run:
        return result

    output_root.parent.mkdir(parents=True, exist_ok=True)
    staging_root = Path(
        tempfile.mkdtemp(prefix=f".{output_root.name}.prepare-", dir=output_root.parent)
    )
    published = False
    publication = None
    try:
        _write_files(staging_root, generated_files)
        _copy_and_verify_sources(source_root, staging_root, assets, images)
        _assert_source_set_unchanged(source_root, images)
        _write_design_lock(staging_root, design_version, source_set_hash)
        _assert_source_set_unchanged(source_root, images)
        publication = _publish_staging(staging_root, output_root, authorized_snapshot)
        try:
            _assert_source_set_unchanged(source_root, images)
        except RuntimeError as source_drift:
            try:
                _quarantine_after_source_drift(output_root, publication)
            except (OSError, RuntimeError) as recovery_error:
                raise RuntimeError(
                    "post-publication source drift; recovery failed without deleting data"
                ) from recovery_error
            raise RuntimeError(
                "post-publication source drift; generated package quarantined"
            ) from source_drift
        _finalize_publication(publication)
        published = True
    finally:
        # Unpublished staging is preserved for recovery/inspection. Recursive
        # path cleanup could delete same-owner data inserted after a check.
        pass
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Prepare a deterministic bilingual UI replica handoff skeleton."
    )
    parser.add_argument("source_root", type=Path)
    parser.add_argument("output_root", type=Path)
    parser.add_argument("--design-version", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    arguments = parser.parse_args(argv)
    result = prepare_handoff(
        arguments.source_root,
        arguments.output_root,
        arguments.design_version,
        dry_run=arguments.dry_run,
        force=arguments.force,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
