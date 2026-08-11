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


def _reject_nonfinite_json_constant(value: str) -> object:
    raise ValueError(f"non-finite JSON number is forbidden: {value}")


def _strict_json_loads(text: str) -> object:
    return json.loads(text, parse_constant=_reject_nonfinite_json_constant)


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
    "contracts/reference-inventory.json": "reference-inventory.schema.json",
    "contracts/page-inventory.json": "page-inventory.schema.json",
    "contracts/ui-style-contract.json": "ui-style-contract.schema.json",
    "contracts/micro-visual-contract.json": "micro-visual-contract.schema.json",
    "contracts/component-registry.json": "component-registry.schema.json",
    "contracts/application-system.json": "application-system.schema.json",
    "contracts/implementation-map.json": "implementation-map.schema.json",
    "contracts/implementation-plan.json": "implementation-plan.schema.json",
    "contracts/capture-profile.json": "capture-profile.schema.json",
    "contracts/diff-regions.json": "diff-regions.schema.json",
    "contracts/reference-relationships.json": "reference-relationships.schema.json",
    "contracts/viewport-calibration.json": "viewport-calibration.schema.json",
    "contracts/design-rule-cascade.json": "design-rule-cascade.schema.json",
    "contracts/design-inconsistencies.json": "design-inconsistencies.schema.json",
    "contracts/deterministic-fixtures.json": "deterministic-fixtures.schema.json",
    "contracts/traceability-map.json": "traceability-map.schema.json",
    "contracts/navigation-reconciliation.json": "navigation-reconciliation.schema.json",
    "contracts/motion-contract.json": "motion-contract.schema.json",
    "contracts/semantic-visual-encoding.json": "semantic-visual-encoding.schema.json",
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
    return _strict_json_loads(
        (SCHEMA_ROOT / schema_name).read_text(encoding="utf-8")
    )


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
            document = _strict_json_loads(path.read_text(encoding="utf-8"))
            if not isinstance(document, dict) or not _contract_is_schema_valid(
                schema_name, document
            ):
                return None
            documents[relative_path] = document
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        return None

    lock = documents["contracts/design-lock.json"]
    manifest = documents["contracts/asset-manifest.json"]
    page_inventory = documents["contracts/page-inventory.json"]
    reference_inventory = documents["contracts/reference-inventory.json"]
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

    page_asset_ids = {
        asset_id
        for page in page_inventory["pages"]
        for asset_id in page["sourceAssetIds"]
    }
    reference_asset_ids = {
        reference["assetId"] for reference in reference_inventory["references"]
    }
    if not page_asset_ids.issubset(set(asset_ids)) or reference_asset_ids != set(asset_ids):
        return None

    expected_files = {
        "contracts/design-lock.json",
        "reports/validation-report.json",
    }
    expected_directories = {"reports"}
    optional_contact_sheet = output_root / "reports" / "contact-sheet.png"
    if optional_contact_sheet.is_symlink():
        return None
    if optional_contact_sheet.is_file():
        expected_files.add("reports/contact-sheet.png")
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
                "referenceIds": [_numbered("REF", number)],
                "referenceRelationshipIds": [],
                "calibrationIds": [_numbered("CAL", number)],
                "inheritedDesignRuleIds": [],
                "inconsistencyIds": [],
                "fixtureIds": [_numbered("FIX", number)],
                "traceabilityIds": [_numbered("TR", number)],
                "navigationSystemIds": [_numbered("NAV", 1)],
                "motionIds": [],
                "semanticDimensionIds": [],
                "semanticValueIds": [],
                "microVisualFeatureIds": [],
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
                    "systemLayer": "unclassified",
                    "navigationSystemId": _numbered("NAV", 1),
                    "activeNavigationEntryId": None,
                    "inheritanceMode": "unclassified",
                    "inheritedRegionIds": [],
                    "pageOwnedRegionIds": ["region-canvas"],
                    "globalOffsetOwner": "unclassified",
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
                        "responsiveVariantId": "baseline-elastic",
                        "mode": "baseline-elastic",
                        "targetPlatform": "desktop-web",
                        "layoutPolicy": "desktop-hybrid-elastic",
                        "minWidth": None,
                        "maxWidth": None,
                        "evidenceLevel": "unknown",
                        "status": "proposed",
                        "gapIds": [gap_id],
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
            "borders": [],
            "opacity": [],
            "gradients": [],
            "blur": [],
            "materials": [],
            "layers": [],
            "motion": [],
            "iconography": [],
            "chartLanguage": [],
            "density": [],
            "backgrounds": [],
            "forbiddenPatterns": [],
        },
        "responsiveVariants": [
            {
                "responsiveVariantId": "baseline-elastic",
                "mode": "baseline-elastic",
                "targetPlatform": "desktop-web",
                "layoutPolicy": "desktop-hybrid-elastic",
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
                "navigationComponentId": None,
                "implementationBoundary": "page-content-only",
                "shellOwnedTargetFiles": [],
                "regionMappings": [],
                "componentMappings": [],
                "dataBindings": [],
                "interactionMappings": [],
                "responsiveMappings": [
                    {
                        "responsiveVariantId": "baseline-elastic",
                        "strategy": "baseline-elastic",
                        "targetPlatform": "desktop-web",
                        "layoutPolicy": "desktop-hybrid-elastic",
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
                **_identity(number),
                "purpose": "baseline",
                "acceptanceRole": "replica-score",
                "scoreContribution": True,
                "environmentLock": {
                    "viewport": True,
                    "zoom": True,
                    "dpr": True,
                    "browser": True,
                    "browserVersion": True,
                    "locale": True,
                    "fonts": True,
                },
                "targetPlatform": "desktop-web",
                "layoutPolicy": "desktop-hybrid-elastic",
                "browser": "unclassified",
                "browserVersion": "unclassified",
                "viewport": {"width": asset["width"], "height": asset["height"]},
                "dpr": 1,
                "locale": "unclassified",
                "timezone": "unclassified",
                "theme": "unknown",
                "zoom": "unknown",
                "fontEnvironment": ["unclassified"],
                "colorScheme": "no-preference",
                "reducedMotion": True,
                "evidenceLevel": "unknown",
                "gapIds": [gap_id],
            }
        )
    return {
        "schemaVersion": SCHEMA_VERSION,
        "acceptancePolicy": {
            "canonicalPurpose": "baseline",
            "canonicalEnvironmentMustBeLocked": True,
            "scoreOnlyCanonical": True,
            "requiredStabilityPurposes": ["wide", "narrow", "zoom"],
            "stabilityProfilesAffectReplicaScore": False,
        },
        "profiles": profiles,
    }


def _build_diff_regions(assets: list[dict]) -> dict:
    pages = []
    for number, asset in enumerate(assets, start=1):
        pages.append(
            {
                **_identity(number),
                "captureProfileId": _capture_profile_id(number),
                "scoringProfilePurpose": "baseline",
                "scoringMode": "canonical-fixed-environment-region-aware",
                "regions": [
                    {
                        "regionId": "region-canvas",
                        "regionRole": "whole-canvas",
                        "bounds": {
                            "x": 0,
                            "y": 0,
                            "width": asset["width"],
                            "height": asset["height"],
                        },
                        "alignmentAnchor": "canvas-origin",
                        "propagateGeometryOffset": False,
                        "scoreContribution": True,
                        "comparisonModes": [
                            "reference",
                            "current",
                            "overlay",
                            "diff",
                        ],
                        "evidenceTypes": ["visual", "structural", "interaction"],
                        "comparisonType": "mixed",
                        "dynamicMaskIds": [],
                        "antiAliasing": {
                            "allowEnvironmentNoise": False,
                            "rationale": None,
                        },
                        "textTolerance": {
                            "maxShiftPx": 0,
                            "fontRasterizationOnly": False,
                        },
                        "geometryTolerancePx": 0,
                        "materialChecks": [],
                        "tolerance": {"pixelRatio": 0},
                        "status": "not-run",
                    }
                ],
                "microVisualTargets": [],
                "motionTargets": [],
                "semanticTargets": [],
            }
        )
    return {"schemaVersion": SCHEMA_VERSION, "pages": pages}


def _build_reference_inventory(assets: list[dict]) -> dict:
    references = []
    for number, asset in enumerate(assets, start=1):
        gap_id = _numbered("G", number)
        references.append(
            {
                "referenceId": _numbered("REF", number),
                "assetId": asset["assetId"],
                "role": "unknown",
                "scope": "unknown",
                "authorityClass": "unknown",
                "title": {
                    "zh-CN": "待人工识别的参考图",
                    "en-US": "Reference awaiting visual classification",
                },
                "titleEvidence": {
                    "classification": "unknown",
                    "transcription": {"zh-CN": "", "en-US": ""},
                    "bounds": None,
                    "evidenceLevel": "unknown",
                    "gapIds": [gap_id],
                },
                "designLanguageSetIds": [],
                "version": None,
                "theme": None,
                "module": None,
                "disposition": "unknown",
                "appliesToPageIdentities": [_identity(number)],
                "shellIds": [],
                "componentIds": [],
                "styleSections": [],
                "extractedRuleIds": [],
                "status": "proposed",
                "evidenceLevel": "unknown",
                "gapIds": [gap_id],
            }
        )
    return {"schemaVersion": SCHEMA_VERSION, "references": references}


def _build_reference_relationships() -> dict:
    return {"schemaVersion": SCHEMA_VERSION, "relationships": []}


def _build_viewport_calibrations(assets: list[dict]) -> dict:
    calibrations = []
    for number, asset in enumerate(assets, start=1):
        gap_id = _numbered("G", number)
        calibrations.append(
            {
                "calibrationId": _numbered("CAL", number),
                "referenceId": _numbered("REF", number),
                "sourceCanvas": {
                    "width": asset["width"],
                    "height": asset["height"],
                },
                "uiViewportBounds": {
                    "x": 0,
                    "y": 0,
                    "width": asset["width"],
                    "height": asset["height"],
                },
                "cropOffset": {"x": 0, "y": 0},
                "sourceScale": 1,
                "effectiveDpr": 1,
                "fullContentExtent": {
                    "width": asset["width"],
                    "height": asset["height"],
                },
                "presentationRegions": [
                    {
                        "presentationRegionId": _numbered("PR", number),
                        "role": "unknown",
                        "bounds": {
                            "x": 0,
                            "y": 0,
                            "width": asset["width"],
                            "height": asset["height"],
                        },
                        "includeInImplementation": False,
                        "evidenceLevel": "unknown",
                        "gapIds": [gap_id],
                    }
                ],
                "fixedRegionIds": [],
                "stickyRegionIds": [],
                "status": "proposed",
                "evidenceLevel": "unknown",
                "gapIds": [gap_id],
            }
        )
    return {"schemaVersion": SCHEMA_VERSION, "calibrations": calibrations}


def _build_design_rule_cascade() -> dict:
    return {
        "schemaVersion": SCHEMA_VERSION,
        "designLanguageSets": [],
        "rules": [],
        "conflicts": [],
    }


def _build_design_inconsistencies() -> dict:
    return {"schemaVersion": SCHEMA_VERSION, "inconsistencies": []}


def _build_deterministic_fixtures(assets: list[dict]) -> dict:
    fixtures = []
    for number, asset in enumerate(assets, start=1):
        gap_id = _numbered("G", number)
        fixtures.append(
            {
                "fixtureId": _numbered("FIX", number),
                **_identity(number),
                "locale": "unclassified",
                "permissionProfile": "unclassified",
                "clock": "unclassified",
                "timezone": "unclassified",
                "randomSeed": None,
                "dataFixturePath": None,
                "assetIds": [asset["assetId"]],
                "networkState": "unknown",
                "animationState": "unknown",
                "cursor": "unknown",
                "scrollPositions": [{"ownerId": "page", "x": 0, "y": 0}],
                "dynamicMaskIds": [],
                "status": "proposed",
                "evidenceLevel": "unknown",
                "gapIds": [gap_id],
            }
        )
    return {"schemaVersion": SCHEMA_VERSION, "fixtures": fixtures}


def _build_traceability_map(assets: list[dict]) -> dict:
    entries = []
    for number, asset in enumerate(assets, start=1):
        gap_id = _numbered("G", number)
        reference_id = _numbered("REF", number)
        entries.append(
            {
                "traceabilityId": _numbered("TR", number),
                "sourceReferenceIds": [reference_id],
                "sourceRuleIds": [],
                "sourceBounds": [
                    {
                        "referenceId": reference_id,
                        "bounds": {
                            "x": 0,
                            "y": 0,
                            "width": asset["width"],
                            "height": asset["height"],
                        },
                    }
                ],
                "tokenIds": [],
                "componentIds": [],
                "microVisualFeatureIds": [],
                "pageIdentities": [_identity(number)],
                "implementationTargets": [],
                "qaIds": [entry["qaId"] for entry in _qa_entries(number)],
                "status": "proposed",
                "evidenceLevel": "unknown",
                "gapIds": [gap_id],
            }
        )
    return {"schemaVersion": SCHEMA_VERSION, "entries": entries}


def _build_navigation_reconciliation(assets: list[dict]) -> dict:
    observations = []
    source_reference_ids = []
    gap_ids = []
    for number, _asset in enumerate(assets, start=1):
        gap_id = _numbered("G", number)
        reference_id = _numbered("REF", number)
        source_reference_ids.append(reference_id)
        gap_ids.append(gap_id)
        observations.append(
            {
                "observationId": _numbered("NOBS", number),
                "referenceId": reference_id,
                "pageIdentity": _identity(number),
                "navigationPresence": "unknown",
                "entries": [],
                "evidenceLevel": "unknown",
                "gapIds": [gap_id],
            }
        )
    system = {
        "navigationSystemId": _numbered("NAV", 1),
        "shellId": "unclassified",
        "systemLayer": "unclassified",
        "reuseMode": "unclassified",
        "pageLocalCopyPolicy": "forbidden",
        "implementationTarget": None,
        "geometryPolicy": {
            "referenceWidthTolerancePx": None,
            "crossRouteRuntimeTolerancePx": 0,
            "regionAnchoredComparison": True,
            "propagateReferenceOffsetToContentDiff": False,
        },
        "sourceReferenceIds": source_reference_ids,
        "observations": observations,
        "canonicalEntries": [],
        "discrepancies": [],
        "freezeStatus": "proposed",
        "freezeDecision": {
            "zh-CN": "先按前台、中台、后台或公开认证壳层归类页面，再为每个壳层冻结唯一共享导航树；禁止按页面复制导航。",
            "en-US": "Classify pages into front-, middle-, back-office, or public/auth shell families, then freeze one shared canonical tree per shell; page-local navigation copies are forbidden.",
        },
        "evidenceLevel": "unknown",
        "gapIds": gap_ids,
    }
    return {"schemaVersion": SCHEMA_VERSION, "navigationSystems": [system]}


def _build_motion_contract() -> dict:
    return {"schemaVersion": SCHEMA_VERSION, "motions": []}


def _build_semantic_visual_encoding() -> dict:
    return {"schemaVersion": SCHEMA_VERSION, "dimensions": []}


def _build_application_system(assets: list[dict], global_gap_id: str) -> dict:
    route_entries = []
    for number, _asset in enumerate(assets, start=1):
        gap_id = _numbered("G", number)
        route_entries.append(
            {
                **_identity(number),
                "path": None,
                "shellId": "unclassified",
                "navigationSystemId": _numbered("NAV", 1),
                "activeNavigationEntryId": None,
                "shellInheritanceMode": "unclassified",
                "inheritedRegionIds": [],
                "pageOwnedRegionIds": ["region-canvas"],
                "status": "proposed",
                "evidenceLevel": "unknown",
                "gapIds": [gap_id],
            }
        )
    return {
        "schemaVersion": SCHEMA_VERSION,
        "applicationId": "ui-replica-application",
        "integrationMode": "single-application",
        "runtimeMode": "single-dev-server",
        "portPolicy": "shared-port",
        "port": None,
        "router": None,
        "defaultRoute": None,
        "routeEntries": route_entries,
        "shellFamilies": [
            {
                "shellId": "unclassified",
                "systemLayer": "unclassified",
                "navigationSystemId": _numbered("NAV", 1),
                "routePrefixes": [],
                "layoutComponentId": None,
                "navigationComponentId": None,
                "implementationTarget": None,
                "reuseMode": "unclassified",
                "globalOffsetOwner": "unclassified",
                "geometryPolicy": {
                    "sidebarWidthToken": None,
                    "collapsedSidebarWidthToken": None,
                    "topbarHeightToken": None,
                    "contentInsetToken": None,
                    "referenceWidthTolerancePx": None,
                    "crossRouteRuntimeTolerancePx": 0,
                    "propagateReferenceOffsetToContentDiff": False,
                },
                "scrollOwnership": "unclassified",
                "zoomBehavior": "unclassified",
                "status": "proposed",
                "evidenceLevel": "unknown",
                "gapIds": [global_gap_id],
            }
        ],
        "navigation": {
            "registryMode": "unclassified",
            "activeStateSource": "unclassified",
            "permissionMode": "unclassified",
            "pageLocalNavigationPolicy": "forbidden",
            "crossRouteShellPersistence": "unclassified",
            "status": "proposed",
            "gapIds": [global_gap_id],
        },
        "sharedState": {
            "routeStateOwner": "unclassified",
            "shellStateOwner": "unclassified",
            "navigationStateOwner": "unclassified",
            "status": "proposed",
            "gapIds": [global_gap_id],
        },
        "sharedComponents": ["AppRouter", "SharedShell", "CanonicalNavigationRegistry"],
        "visualAcceptancePolicy": {
            "canonicalProfilePurpose": "baseline",
            "canonicalZoomRequired": True,
            "scoreOnlyCanonicalProfile": True,
            "nonCanonicalPurposes": ["wide", "narrow", "zoom"],
            "nonCanonicalAcceptance": "stability-only",
            "regionAwareDiff": True,
            "navigationReferenceToleranceMode": "explicit-region-geometry-tolerance",
            "crossRouteShellDriftTolerancePx": 0,
        },
        "implementationSequence": [
            "freeze-design-language-and-reference-authority",
            "classify-pages-into-shell-families",
            "freeze-one-canonical-navigation-per-shell",
            "implement-single-router-shared-shells-and-navigation",
            "verify-one-representative-route-per-shell",
            "implement-and-accept-pages-in-order",
            "verify-all-routes-shell-persistence-and-responsive-stability",
        ],
        "status": "proposed",
        "evidenceLevel": "approved",
        "gapIds": [global_gap_id],
    }


def _build_implementation_plan(assets: list[dict]) -> dict:
    page_items = []
    for number, _asset in enumerate(assets, start=1):
        gap_id = _numbered("G", number)
        page_items.append(
            {
                "workItemId": _numbered("WI", number),
                "order": number,
                **_identity(number),
                "dependencies": ["SW004"],
                "route": None,
                "shellId": "unclassified",
                "navigationSystemId": _numbered("NAV", 1),
                "activeNavigationEntryId": None,
                "implementationBoundary": "page-content-only",
                "requiredReferenceIds": [_numbered("REF", number)],
                "requiredMicroVisualFeatureIds": [],
                "gates": {
                    "contractComplete": "not-run",
                    "structural": "not-run",
                    "visual": "not-run",
                    "interaction": "not-run",
                    "integratedNavigation": "not-run",
                },
                "status": "blocked",
                "gapIds": [gap_id],
            }
        )
    system_items = [
        {
            "systemWorkItemId": "SW001",
            "order": 1,
            "kind": "classify-shells",
            "dependencies": [],
            "deliverables": ["front-middle-back-shell-family-map", "page-to-shell-bindings"],
            "exitGate": ["every page has one shell family or an explicit shellless decision"],
            "status": "blocked",
        },
        {
            "systemWorkItemId": "SW002",
            "order": 2,
            "kind": "freeze-navigation",
            "dependencies": ["SW001"],
            "deliverables": ["one-canonical-navigation-tree-per-shell", "route-permission-order-resolution"],
            "exitGate": ["no page-local navigation system remains"],
            "status": "blocked",
        },
        {
            "systemWorkItemId": "SW003",
            "order": 3,
            "kind": "build-router-shells",
            "dependencies": ["SW002"],
            "deliverables": ["single-router", "shared-shell-components", "canonical-navigation-registry"],
            "exitGate": ["shell owns global offsets and pages implement content only"],
            "status": "blocked",
        },
        {
            "systemWorkItemId": "SW004",
            "order": 4,
            "kind": "verify-shell-route-smoke",
            "dependencies": ["SW003"],
            "deliverables": ["one-routed-representative-page-per-shell"],
            "exitGate": ["navigation click preserves shell geometry and selects the route-derived item"],
            "status": "blocked",
        },
    ]
    phases = [
        {
            "phaseId": "system-contract",
            "order": 1,
            "name": {"zh-CN": "系统壳层与导航契约", "en-US": "System shell and navigation contract"},
            "deliverables": ["reference authority", "UI design language", "shell-family map", "canonical navigation trees"],
            "exitGate": ["front/middle/back shell membership frozen", "one canonical navigation tree per shell"],
        },
        {
            "phaseId": "runtime-foundation",
            "order": 2,
            "name": {"zh-CN": "统一运行时基础", "en-US": "Unified runtime foundation"},
            "deliverables": ["single application", "shared port", "router", "shared shells", "navigation registry"],
            "exitGate": ["one representative route per shell preserves shell identity and geometry"],
        },
        {
            "phaseId": "pages",
            "order": 3,
            "name": {"zh-CN": "逐页内容复刻", "en-US": "Page-content replication"},
            "deliverables": ["page contracts", "micro visual contracts", "page-content-only route implementations"],
            "exitGate": ["each page passes five gates inside its inherited shell"],
        },
        {
            "phaseId": "continuous-acceptance",
            "order": 4,
            "name": {"zh-CN": "连续系统验收", "en-US": "Continuous system acceptance"},
            "deliverables": ["full route walk", "canonical visual scoring", "wide/narrow/zoom stability evidence"],
            "exitGate": ["all routes reachable with zero cross-route shell drift"],
        },
    ]
    return {
        "schemaVersion": SCHEMA_VERSION,
        "strategy": "foundation-then-page-by-page-in-one-application",
        "phases": phases,
        "systemWorkItems": system_items,
        "pageWorkItems": page_items,
    }


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
    qa_ids = ", ".join(
        f"`{entry['qaId']}`" for entry in _qa_entries(number)
    )
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
            f"- 区域 ID：`region-canvas`；整幅画布占位区域，语义角色未知（`{gap_id}`）\n"
            f"- 画布仅是测量基线，不是固定容器或最大内容范围；尺寸模式、最小/基准/最大尺寸、宽屏剩余空间分配及整页/模块/混合滚动所有者待证据确认（`{gap_id}`）"
        )
        content_text = "未从像素自动推断布局、文案、图标或数据。相关清单保持为空。"
        behavior_text = (
            "未自动创建组件或交互。已登记桌面端 Web 优先的 `baseline-elastic` 候选：固定/粘性 Shell、"
            "流式或有界流式工作区、组件最小尺寸、按功能归属的滚动、最后才是获批重排；它不预设固定页面宽度或统一滚动所有者。"
            "宽屏铺满或有界、Grid/Flex 伸缩、窄桌面/浏览器缩放后的滚动或重排均需证据；"
            f"禁止用页面根节点整体缩放代替布局（`{gap_id}`）。"
        )
        qa_text = (
            f"视觉、结构与交互 QA 均为 `not-run`。固定缩放的 baseline 是唯一复刻评分环境；"
            f"wide/narrow/zoom 仅做稳定性验收。完成前必须解决或批准缺口 `{gap_id}`。"
        )
        micro_text = (
            f"尚未自动测量微视觉特征。人工检查 `{_numbered('REF', number)}` 后，必须登记图标/Logo、"
            "边框、圆角、阴影、透明度、曲线控制点、圆环、圆柱、渐变、裁切与层级，并建立特征级 Diff；"
            f"当前关联缺口 `{gap_id}`。设计语言继承与动效 `MOT###` 尚未分类，不能从静态图擅自补写。"
        )
        integration_text = (
            "页面内容开发前，必须先完成前/中/后台 Shell 分类、每个 Shell 唯一规范导航冻结、统一 Router/"
            "共享 Shell/导航注册表建设，并接入每个 Shell 的代表路由。本页只实现内容区，不得复制 Sidebar、"
            "TopBar、全局偏移或导航状态。路由、激活导航入口和 Shell 尚未确认"
            f"（`{gap_id}`）。证据图谱：`CAL{number:03d}`、`FIX{number:03d}`、`TR{number:03d}`、`NAV001`。"
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
            f"- Region ID: `region-canvas`; whole-canvas placeholder with unknown semantic role (`{gap_id}`)\n"
            f"- The canvas is a measurement baseline, not a fixed container or maximum content extent; sizing mode, min/base/max dimensions, wide-screen surplus allocation, and page/region/hybrid scroll ownership need evidence (`{gap_id}`)"
        )
        content_text = (
            "No layout, copy, icon, or data semantics were inferred from pixels. "
            "Those inventories remain empty."
        )
        behavior_text = (
            "No components or interactions were invented. A desktop-Web-first `baseline-elastic` candidate is registered: "
            "fixed/sticky shell, fluid or bounded-fluid workspace, component minimum dimensions, function-owned scrolling, "
            "then approved reflow. It assumes neither fixed page width nor one scroll owner. Wide fill versus bounding, "
            "Grid/Flex growth, narrow-desktop/browser-zoom scrolling or reflow all need evidence. "
            f"Whole-page root scaling cannot substitute for layout (`{gap_id}`)."
        )
        qa_text = (
            f"Visual, structural, and interaction QA are `not-run`. The fixed-zoom baseline is the only "
            f"replica-scoring profile; wide/narrow/zoom are stability-only. Gap `{gap_id}` must be resolved "
            "or approved before completion."
        )
        micro_text = (
            f"Micro features are not auto-measured. After inspecting `{_numbered('REF', number)}`, "
            "contract icons/Logo, borders, radii, shadows, opacity, curve control points, rings, cylinders, "
            f"gradients, clipping, and layering with feature-level Diff targets; gap `{gap_id}` remains. "
            "Design-language inheritance and `MOT###` motion remain unclassified and must not be invented from a static board."
        )
        integration_text = (
            "Before page-content work, classify front/middle/back shell families, freeze one canonical navigation "
            "tree per shell, build the unified Router/shared Shell/navigation registry, and route one representative "
            "page per shell. This page implements content only and must not copy Sidebar, TopBar, global offsets, "
            f"or navigation state. Route, active entry, and shell remain unresolved (`{gap_id}`). Evidence graph: "
            f"`CAL{number:03d}`, `FIX{number:03d}`, `TR{number:03d}`, `NAV001`."
        )
    qa_text += f"\nQA IDs: {qa_ids}"
    return {
        "pageId": f"P{number:03d}",
        "stateId": "S01",
        "variantId": "V01",
        "identityAndEvidence": identity_text,
        "canvasShellAndRegions": canvas_text,
        "layoutCopyIconsAndData": content_text,
        "componentsInteractionsAndResponsive": behavior_text,
        "microVisualContract": micro_text,
        "applicationIntegration": integration_text,
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
            "design_language": "UI设计语言.md",
            "template_directory": "zh",
        },
        "en-US": {
            "directory": "en",
            "catalog": "Design-Catalog.md",
            "guide": "UI-Implementation-Guide.md",
            "components": "Component-Specification.md",
            "design_language": "UI-Design-Language.md",
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
            semantics = "语义视觉编码初始为空；必须从优先级、状态、等级等权威图示中逐值测量，禁止按相同颜色合并含义。"
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
            semantics = "Semantic visual encoding starts empty; measure each priority, status, grade, and other value from authoritative evidence and never merge meanings by hue."
        documents[f"{docs_root}/{details['guide']}"] = _render_template(
            f"{template_root}/ui-implementation-guide.template.md",
            {
                "authorityOrder": authority,
                "implementationMapPath": "../../contracts/implementation-map.json",
                "qaAndGitSafety": qa_git,
                "semanticVisualEncoding": semantics,
            },
        )
        documents[f"{docs_root}/{details['components']}"] = _render_template(
            f"{template_root}/component-specification.template.md",
            {
                "componentRegistry": registry,
                "styleTokens": styles,
                "componentStatesAndVariants": states,
                "semanticVisualEncoding": semantics,
            },
        )
        if locale == "zh-CN":
            reference_authority = (
                "初始骨架为每个资产分配 `REF###`，但不会根据像素自动判断它是页面图、设计语言图、"
                "组件板、品牌板、状态板还是装饰背景。视觉检查后先完成角色、作用域与权威分类。"
            )
            style_contract = "样式合同初始为空并关联全局缺口；必须从权威设计语言参考图和重复页面证据中测量。"
            micro_contract = "微视觉合同初始为空；逐页测量后按特征登记并连接到 Diff 目标。"
        else:
            reference_authority = (
                "The skeleton assigns each asset a `REF###` but does not infer whether it is a page, design-language "
                "board, component board, brand board, state board, or decorative background. Classify role, scope, "
                "and authority before page freezing."
            )
            style_contract = "The initial style contract is empty and gap-linked; measure it from authoritative design-language references and repeated page evidence."
            micro_contract = "The initial micro-visual contract is empty; measure page features and link each one to a Diff target."
        documents[f"{docs_root}/{details['design_language']}"] = _render_template(
            f"{template_root}/ui-design-language.template.md",
            {
                "referenceAuthority": reference_authority,
                "styleContract": style_contract,
                "microVisualContract": micro_contract,
                "semanticVisualEncoding": semantics,
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
        "capturePurpose",
        "acceptanceRole",
        "scoreContribution",
        "regionId",
        "evidenceType",
        "referencePath",
        "currentPath",
        "overlayPath",
        "diffPath",
        "evidenceRecordPath",
        "evidenceRecordSha256",
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
                    "capturePurpose": "baseline",
                    "acceptanceRole": "replica-score",
                    "scoreContribution": "true",
                    "regionId": "region-canvas",
                    "evidenceType": evidence_type,
                    "referencePath": asset["deliveryRelativePath"],
                    "currentPath": "",
                    "overlayPath": "",
                    "diffPath": "",
                    "evidenceRecordPath": "",
                    "evidenceRecordSha256": "",
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
            "or validation-passing claim. Its default preparation profile is desktop Web with "
            "mixed fixed, bounded-fluid, fluid, and function-owned scroll regions.\n\n"
            "此确定性准备骨架保留来源证据，并在不虚构 UI 语义的前提下登记未知项。"
            "它不代表实现完成或验证通过；默认准备桌面端 Web 的固定、流式、有界流式和功能型滚动混合合同。\n"
        ).encode("utf-8"),
        "contracts/asset-manifest.json": _json_bytes(
            {
                "schemaVersion": SCHEMA_VERSION,
                "designVersion": design_version,
                "sourceSetHash": source_set_hash,
                "assets": assets,
            }
        ),
        "contracts/reference-inventory.json": _json_bytes(
            _build_reference_inventory(assets)
        ),
        "contracts/page-inventory.json": _json_bytes(_build_page_inventory(assets)),
        "contracts/ui-style-contract.json": _json_bytes(
            _build_ui_style_contract(global_gap_id)
        ),
        "contracts/micro-visual-contract.json": _json_bytes(
            {"schemaVersion": SCHEMA_VERSION, "features": []}
        ),
        "contracts/component-registry.json": _json_bytes(
            {
                "schemaVersion": SCHEMA_VERSION,
                "targetPlatform": "desktop-web",
                "layoutPolicy": "desktop-hybrid-elastic",
                "components": [],
            }
        ),
        "contracts/implementation-map.json": _json_bytes(
            _build_implementation_map(assets)
        ),
        "contracts/application-system.json": _json_bytes(
            _build_application_system(assets, global_gap_id)
        ),
        "contracts/implementation-plan.json": _json_bytes(
            _build_implementation_plan(assets)
        ),
        "contracts/capture-profile.json": _json_bytes(
            _build_capture_profiles(assets)
        ),
        "contracts/diff-regions.json": _json_bytes(_build_diff_regions(assets)),
        "contracts/reference-relationships.json": _json_bytes(
            _build_reference_relationships()
        ),
        "contracts/viewport-calibration.json": _json_bytes(
            _build_viewport_calibrations(assets)
        ),
        "contracts/design-rule-cascade.json": _json_bytes(
            _build_design_rule_cascade()
        ),
        "contracts/design-inconsistencies.json": _json_bytes(
            _build_design_inconsistencies()
        ),
        "contracts/deterministic-fixtures.json": _json_bytes(
            _build_deterministic_fixtures(assets)
        ),
        "contracts/traceability-map.json": _json_bytes(
            _build_traceability_map(assets)
        ),
        "contracts/navigation-reconciliation.json": _json_bytes(
            _build_navigation_reconciliation(assets)
        ),
        "contracts/motion-contract.json": _json_bytes(_build_motion_contract()),
        "contracts/semantic-visual-encoding.json": _json_bytes(
            _build_semantic_visual_encoding()
        ),
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
            'python validate_handoff.py --handoff-root . --source-root "<SOURCE_ROOT>"\n'
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
        and path.relative_to(staging_root).as_posix()
        not in {
            "contracts/design-lock.json",
            "reports/validation-report.json",
        }
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
