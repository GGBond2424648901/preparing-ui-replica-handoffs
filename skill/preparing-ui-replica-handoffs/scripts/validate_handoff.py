from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import tempfile
import types

from jsonschema import Draft202012Validator, FormatChecker


SCHEMA_VERSION = "1.0.0"
SCRIPT_ROOT = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_ROOT.parent
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
CSV_FIELDS = {
    "contracts/requirement-ledger.csv": (
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
    ),
    "contracts/gap-register.csv": (
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
    ),
    "contracts/visual-qa-matrix.csv": (
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
    ),
}
REQUIRED_FILES = tuple(
    sorted(
        {
            "README.md",
            *SCHEMA_CONTRACTS,
            *CSV_FIELDS,
            "docs/zh/设计稿总目录.md",
            "docs/zh/UI实施说明.md",
            "docs/zh/组件规范.md",
            "docs/en/Design-Catalog.md",
            "docs/en/UI-Implementation-Guide.md",
            "docs/en/Component-Specification.md",
            "reports/contact-sheet.png",
            "reports/validation-report.json",
            "tools/validate-command.txt",
        }
    )
)
QA_TYPES = frozenset({"visual", "structural", "interaction"})
DIFF_MODES = frozenset({"reference", "current", "overlay", "diff"})
SUPPORTED_IMAGE_SUFFIXES = frozenset({".gif", ".jpeg", ".jpg", ".png", ".webp"})
PLACEHOLDER_VALUES = frozenset(
    {"", "unknown", "unclassified", "tbd", "todo", "n/a", "not-set"}
)
RESOLVED_GAP_STATUSES = frozenset(
    {"resolved", "closed", "approved", "accepted", "waived"}
)
MACHINE_PATH_FIELDS = frozenset(
    {
        "sourceRelativePath",
        "deliveryRelativePath",
        "relativePath",
        "targetFile",
        "targetFiles",
        "repositoryRelativeRoot",
        "allowedNewPaths",
        "allowedModifiedPaths",
    }
)
LINK_PATTERN = re.compile(r"!?\[[^\]]*\]\(\s*<?([^\s>)]+)>?")
URI_SCHEME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
WINDOWS_ABSOLUTE_PATTERN = re.compile(r"^[A-Za-z]:[\\/]|^\\\\")


def _issue(code: str, path: str, message: str, **details: object) -> dict:
    return {
        "code": code,
        "severity": "error",
        "path": path,
        "message": message,
        **details,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _record_set_hash(records: list[tuple[str, str]]) -> str:
    digest = hashlib.sha256()
    for relative_path, file_hash in sorted(records):
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_hash.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def _is_absolute_path(value: str) -> bool:
    return bool(
        value.startswith(("/", "\\"))
        or WINDOWS_ABSOLUTE_PATTERN.match(value)
        or URI_SCHEME_PATTERN.match(value)
    )


def _safe_relative_path(value: object) -> bool:
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    return not _is_absolute_path(value) and ".." not in PurePosixPath(value).parts


def _resolve_within(root: Path, relative_path: str) -> Path | None:
    if not _safe_relative_path(relative_path):
        return None
    candidate = (root / PurePosixPath(relative_path)).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate


def _load_json(path: Path, relative_path: str, issues: list[dict]) -> dict | None:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        issues.append(_issue("MALFORMED_JSON", relative_path, str(error)))
        return None
    if not isinstance(document, dict):
        issues.append(
            _issue("MALFORMED_JSON", relative_path, "JSON root must be an object")
        )
        return None
    return document


def _load_csv(
    path: Path, relative_path: str, expected_fields: tuple[str, ...], issues: list[dict]
) -> list[dict] | None:
    try:
        text = path.read_text(encoding="utf-8")
        reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
        rows = list(reader)
        if tuple(reader.fieldnames or ()) != expected_fields:
            raise ValueError("CSV header does not match the required contract")
        if any(None in row or any(value is None for value in row.values()) for row in rows):
            raise ValueError("CSV row has a missing or extra column")
    except (OSError, UnicodeError, csv.Error, ValueError) as error:
        issues.append(_issue("MALFORMED_CSV", relative_path, str(error)))
        return None
    return rows


def _validate_schemas(documents: dict[str, dict], issues: list[dict]) -> None:
    for relative_path, schema_name in SCHEMA_CONTRACTS.items():
        document = documents.get(relative_path)
        if document is None:
            continue
        try:
            schema = json.loads((SCHEMA_ROOT / schema_name).read_text(encoding="utf-8"))
            validator = Draft202012Validator(schema, format_checker=FormatChecker())
            errors = sorted(validator.iter_errors(document), key=lambda error: list(error.path))
        except Exception as error:
            issues.append(
                _issue("SCHEMA_VALIDATION_UNAVAILABLE", relative_path, str(error))
            )
            continue
        for error in errors:
            location = "/".join(str(part) for part in error.path)
            issue_path = f"{relative_path}#/{location}" if location else relative_path
            issues.append(_issue("SCHEMA_INVALID", issue_path, error.message))


def _identity(item: dict) -> tuple[object, object, object]:
    return item.get("pageId"), item.get("stateId"), item.get("variantId")


def _identity_text(identity: tuple[object, object, object]) -> str:
    return "-".join(str(value) for value in identity)


def _check_duplicate_identities(documents: dict[str, dict], issues: list[dict]) -> None:
    collections = (
        ("contracts/page-inventory.json", "pages"),
        ("contracts/implementation-map.json", "mappings"),
        ("contracts/diff-regions.json", "pages"),
    )
    for relative_path, collection_name in collections:
        document = documents.get(relative_path)
        if not document or not isinstance(document.get(collection_name), list):
            continue
        seen = set()
        for item in document[collection_name]:
            if not isinstance(item, dict):
                continue
            identity = _identity(item)
            if identity in seen:
                issues.append(
                    _issue(
                        "DUPLICATE_TARGET_IDENTITY",
                        relative_path,
                        f"duplicate page/state/variant identity: {_identity_text(identity)}",
                        identity=_identity_text(identity),
                    )
                )
            seen.add(identity)


def _has_gap(item: dict) -> bool:
    return bool(item.get("gapId")) or bool(item.get("gapIds"))


def _requires_gap(item: dict) -> bool:
    return (
        item.get("evidenceLevel") == "unknown"
        or item.get("status") in {"unknown", "proposed"}
        or item.get("theme") == "unknown"
        or item.get("classification") == "unknown"
    )


def _check_unknown_gaps(value: object, path: str, issues: list[dict]) -> None:
    if isinstance(value, dict):
        if _requires_gap(value) and not _has_gap(value):
            issues.append(
                _issue(
                    "UNKNOWN_WITHOUT_GAP_ID",
                    path,
                    "unknown or proposed state is not linked to a gap ID",
                )
            )
        for key, child in value.items():
            _check_unknown_gaps(child, f"{path}/{key}", issues)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _check_unknown_gaps(child, f"{path}/{index}", issues)


def _check_machine_paths(value: object, path: str, issues: list[dict]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in MACHINE_PATH_FIELDS:
                candidates = child if isinstance(child, list) else [child]
                for candidate in candidates:
                    if isinstance(candidate, str) and not _safe_relative_path(candidate):
                        issues.append(
                            _issue(
                                "ABSOLUTE_PATH",
                                f"{path}/{key}",
                                f"machine contract path must be package-relative: {candidate}",
                            )
                        )
            _check_machine_paths(child, f"{path}/{key}", issues)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _check_machine_paths(child, f"{path}/{index}", issues)


def _check_assets(
    handoff_root: Path,
    source_root: Path | None,
    manifest: dict | None,
    issues: list[dict],
) -> None:
    if not manifest or not isinstance(manifest.get("assets"), list):
        return
    assets = [asset for asset in manifest["assets"] if isinstance(asset, dict)]
    for field, code in (
        ("assetId", "DUPLICATE_ASSET_ID"),
        ("sourceRelativePath", "DUPLICATE_SOURCE_RELATIVE_PATH"),
        ("deliveryRelativePath", "DUPLICATE_DELIVERY_RELATIVE_PATH"),
    ):
        seen = set()
        for asset in assets:
            value = asset.get(field)
            if value in seen:
                issues.append(
                    _issue(
                        code,
                        "contracts/asset-manifest.json",
                        f"manifest {field} is duplicated: {value}",
                    )
                )
            seen.add(value)

    actual_source_records: list[tuple[str, str]] = []
    if source_root is not None:
        if not source_root.is_dir():
            issues.append(
                _issue(
                    "SOURCE_ROOT_MISSING",
                    str(source_root),
                    "source root does not exist or is not a directory",
                )
            )
        else:
            try:
                actual_source_records = [
                    (path.relative_to(source_root).as_posix(), _sha256(path))
                    for path in sorted(source_root.rglob("*"))
                    if path.is_file()
                    and path.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES
                ]
            except OSError as error:
                issues.append(
                    _issue("SOURCE_SCAN_FAILED", str(source_root), str(error))
                )

    for asset in assets:
        if not isinstance(asset, dict):
            continue
        asset_id = str(asset.get("assetId", "unknown"))
        expected_hash = asset.get("sha256")
        delivery = asset.get("deliveryRelativePath")
        if not _safe_relative_path(delivery):
            issues.append(
                _issue("ABSOLUTE_PATH", f"asset:{asset_id}", f"unsafe delivery path: {delivery}")
            )
        else:
            copy = _resolve_within(handoff_root, delivery)
            if copy is None or not copy.is_file():
                issues.append(
                    _issue("MISSING_ASSET_COPY", delivery, "manifest delivery copy is missing")
                )
            elif isinstance(expected_hash, str) and _sha256(copy) != expected_hash:
                issues.append(
                    _issue("COPY_HASH_MISMATCH", delivery, "delivery copy hash differs from manifest")
                )

        source_relative = asset.get("sourceRelativePath")
        if source_root is None:
            continue
        if not _safe_relative_path(source_relative):
            issues.append(
                _issue(
                    "ABSOLUTE_PATH",
                    f"asset:{asset_id}",
                    f"unsafe source path: {source_relative}",
                )
            )
            continue
        source = _resolve_within(source_root, source_relative)
        if source is None or not source.is_file():
            issues.append(
                _issue("SOURCE_FILE_MISSING", source_relative, "manifest source file is missing")
            )
            continue
        source_hash = _sha256(source)
        if isinstance(expected_hash, str) and source_hash != expected_hash:
            issues.append(
                _issue("SOURCE_HASH_MISMATCH", source_relative, "source hash differs from manifest")
            )
    if source_root is not None and source_root.is_dir():
        manifest_source_paths = {
            asset.get("sourceRelativePath")
            for asset in assets
            if _safe_relative_path(asset.get("sourceRelativePath"))
        }
        actual_source_paths = {path for path, _file_hash in actual_source_records}
        missing_from_manifest = sorted(actual_source_paths - manifest_source_paths)
        missing_from_source = sorted(manifest_source_paths - actual_source_paths)
        if missing_from_manifest or missing_from_source:
            issues.append(
                _issue(
                    "SOURCE_SET_COVERAGE_MISMATCH",
                    "contracts/asset-manifest.json",
                    "manifest and supported source image paths are not one-to-one",
                    missingFromManifest=missing_from_manifest,
                    missingFromSource=missing_from_source,
                )
            )
        computed_source_set_hash = _record_set_hash(actual_source_records)
        if computed_source_set_hash != manifest.get("sourceSetHash"):
            issues.append(
                _issue(
                    "SOURCE_SET_HASH_MISMATCH",
                    "contracts/asset-manifest.json",
                    "computed source set hash differs from manifest",
                )
            )


def _check_markdown_links(handoff_root: Path, issues: list[dict]) -> None:
    for path in sorted(handoff_root.rglob("*.md")):
        if not path.is_file():
            continue
        relative_path = path.relative_to(handoff_root).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            issues.append(_issue("UNREADABLE_MARKDOWN", relative_path, str(error)))
            continue
        for match in LINK_PATTERN.finditer(text):
            target = match.group(1).split("#", 1)[0].split("?", 1)[0]
            if not target:
                continue
            if _is_absolute_path(target):
                issues.append(
                    _issue("ABSOLUTE_PATH", relative_path, f"absolute link target: {target}")
                )
                continue
            candidate = (path.parent / PurePosixPath(target)).resolve()
            try:
                candidate.relative_to(handoff_root.resolve())
            except ValueError:
                issues.append(
                    _issue("ABSOLUTE_PATH", relative_path, f"link escapes package: {target}")
                )
                continue
            if not candidate.exists():
                issues.append(
                    _issue("BROKEN_RELATIVE_LINK", relative_path, f"missing link target: {target}")
                )


def _check_qa_paths(
    handoff_root: Path, qa_rows: list[dict] | None, issues: list[dict]
) -> None:
    if qa_rows is None:
        return
    for row in qa_rows:
        evidence_fields = ("referencePath", "currentPath", "overlayPath", "diffPath")
        evidence_paths = [row.get(field, "") for field in evidence_fields]
        if all(evidence_paths) and len(set(evidence_paths)) != len(evidence_paths):
            issues.append(
                _issue(
                    "QA_EVIDENCE_PATH_REUSED",
                    "contracts/visual-qa-matrix.csv",
                    "QA comparison evidence must use four distinct files",
                    qaId=row.get("qaId"),
                )
            )
        evidence_hashes = []
        for field in evidence_fields:
            value = row.get(field, "")
            if not value:
                continue
            if not _safe_relative_path(value):
                issues.append(
                    _issue(
                        "ABSOLUTE_PATH",
                        "contracts/visual-qa-matrix.csv",
                        f"{field} must be package-relative: {value}",
                        qaId=row.get("qaId"),
                    )
                )
                continue
            target = _resolve_within(handoff_root, value)
            if target is None or not target.is_file():
                issues.append(
                    _issue(
                        "BROKEN_RELATIVE_LINK",
                        "contracts/visual-qa-matrix.csv",
                        f"{field} target is missing: {value}",
                        qaId=row.get("qaId"),
                    )
                )
            else:
                evidence_hashes.append(_sha256(target))
        if (
            len(set(evidence_paths)) == len(evidence_fields)
            and len(evidence_hashes) == len(evidence_fields)
            and len(set(evidence_hashes)) != len(evidence_hashes)
        ):
            issues.append(
                _issue(
                    "QA_EVIDENCE_HASH_REUSED",
                    "contracts/visual-qa-matrix.csv",
                    "QA comparison evidence files must have distinct content hashes",
                    qaId=row.get("qaId"),
                )
            )


def _expected_identities(documents: dict[str, dict]) -> set[tuple[object, object, object]]:
    inventory = documents.get("contracts/page-inventory.json") or {}
    return {
        _identity(page)
        for page in inventory.get("pages", [])
        if isinstance(page, dict)
    }


def _check_page_documents(
    handoff_root: Path,
    identities: set[tuple[object, object, object]],
    issues: list[dict],
) -> None:
    for identity in sorted(identities, key=_identity_text):
        name_prefix = _identity_text(identity)
        for locale in ("zh", "en"):
            directory = handoff_root / "docs" / locale / "pages"
            matches = list(directory.glob(f"{name_prefix}-*.md")) if directory.is_dir() else []
            if not matches:
                issues.append(
                    _issue(
                        "MISSING_PAGE_DOCUMENT",
                        f"docs/{locale}/pages",
                        f"missing {locale} page document for {name_prefix}",
                        identity=name_prefix,
                    )
                )


def _load_parity_checker():
    path = SCRIPT_ROOT / "check_bilingual_parity.py"
    module = types.ModuleType("check_bilingual_parity_for_handoff_validation")
    module.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), "exec"), module.__dict__)
    return module.check_bilingual_parity


def _check_bilingual(handoff_root: Path, issues: list[dict]) -> None:
    try:
        parity = _load_parity_checker()(handoff_root)
    except Exception as error:
        issues.append(_issue("BILINGUAL_CHECK_FAILED", "docs", str(error)))
        return
    for parity_issue in parity.get("issues", []):
        details = dict(parity_issue)
        code = str(details.pop("code", "BILINGUAL_MISMATCH"))
        scope = str(details.pop("scope", "docs"))
        key = str(details.pop("key", "unknown"))
        issues.append(
            _issue(code, scope, f"bilingual parity failed for {key}", **details)
        )


def _check_capture_profiles(documents: dict[str, dict], issues: list[dict]) -> None:
    capture = documents.get("contracts/capture-profile.json") or {}
    for profile in capture.get("profiles", []):
        if not isinstance(profile, dict):
            continue
        scalar_fields = ("browser", "browserVersion", "locale", "timezone")
        incomplete = any(
            str(profile.get(field, "")).strip().lower() in PLACEHOLDER_VALUES
            for field in scalar_fields
        )
        fonts = profile.get("fontEnvironment")
        incomplete = incomplete or profile.get("theme") == "unknown"
        incomplete = incomplete or not isinstance(fonts, list) or not fonts
        incomplete = incomplete or any(
            str(font).strip().lower() in PLACEHOLDER_VALUES for font in (fonts or [])
        )
        incomplete = incomplete or profile.get("evidenceLevel") == "unknown"
        if incomplete:
            issues.append(
                _issue(
                    "INCOMPLETE_CAPTURE_PROFILE",
                    "contracts/capture-profile.json",
                    "capture profile contains unknown or placeholder environment fields",
                    captureProfileId=profile.get("captureProfileId"),
                )
            )


def _check_required_collections(
    documents: dict[str, dict],
    csv_documents: dict[str, list[dict]],
    issues: list[dict],
) -> None:
    collections = (
        ("contracts/asset-manifest.json", "assets", "EMPTY_ASSET_MANIFEST"),
        ("contracts/page-inventory.json", "pages", "EMPTY_PAGE_INVENTORY"),
        ("contracts/capture-profile.json", "profiles", "EMPTY_CAPTURE_PROFILES"),
        ("contracts/implementation-map.json", "mappings", "EMPTY_IMPLEMENTATION_MAP"),
        ("contracts/diff-regions.json", "pages", "EMPTY_DIFF_PAGES"),
    )
    for relative_path, key, code in collections:
        document = documents.get(relative_path)
        if document is not None and not document.get(key):
            issues.append(
                _issue(code, relative_path, f"required {key} collection is empty")
            )
    qa_rows = csv_documents.get("contracts/visual-qa-matrix.csv")
    if qa_rows is not None and not qa_rows:
        issues.append(
            _issue(
                "EMPTY_QA_MATRIX",
                "contracts/visual-qa-matrix.csv",
                "visual QA matrix must contain at least one row",
            )
        )


def _check_implementation_coverage(
    documents: dict[str, dict],
    identities: set[tuple[object, object, object]],
    issues: list[dict],
) -> None:
    implementation = documents.get("contracts/implementation-map.json") or {}
    mapped = {
        _identity(mapping)
        for mapping in implementation.get("mappings", [])
        if isinstance(mapping, dict)
    }
    for identity in sorted(identities - mapped, key=_identity_text):
        issues.append(
            _issue(
                "MISSING_IMPLEMENTATION_MAPPING",
                "contracts/implementation-map.json",
                f"implementation mapping is missing for {_identity_text(identity)}",
            )
        )


def _check_diff_and_qa(
    documents: dict[str, dict],
    qa_rows: list[dict] | None,
    identities: set[tuple[object, object, object]],
    issues: list[dict],
) -> None:
    diff = documents.get("contracts/diff-regions.json") or {}
    capture = documents.get("contracts/capture-profile.json") or {}
    capture_profile_ids = {
        profile.get("captureProfileId")
        for profile in capture.get("profiles", [])
        if isinstance(profile, dict)
    }
    diff_by_identity = {
        _identity(page): page
        for page in diff.get("pages", [])
        if isinstance(page, dict)
    }
    qa_rows = qa_rows or []
    for row in qa_rows:
        if _identity(row) not in identities:
            issues.append(
                _issue(
                    "QA_TARGET_IDENTITY_MISSING",
                    "contracts/visual-qa-matrix.csv",
                    f"QA row {row.get('qaId')} references an unknown page identity",
                    identity=_identity_text(_identity(row)),
                )
            )
    for identity in sorted(identities, key=_identity_text):
        identity_name = _identity_text(identity)
        diff_page = diff_by_identity.get(identity)
        regions = diff_page.get("regions", []) if diff_page else []
        diff_capture_profile_id = (
            diff_page.get("captureProfileId") if diff_page else None
        )
        if diff_page and diff_capture_profile_id not in capture_profile_ids:
            issues.append(
                _issue(
                    "DIFF_CAPTURE_PROFILE_MISSING",
                    "contracts/diff-regions.json",
                    f"diff capture profile does not exist for {identity_name}",
                    captureProfileId=diff_capture_profile_id,
                )
            )
        diff_complete = bool(regions)
        for region in regions:
            diff_complete = diff_complete and DIFF_MODES.issubset(
                set(region.get("comparisonModes", []))
            )
            diff_complete = diff_complete and QA_TYPES.issubset(
                set(region.get("evidenceTypes", []))
            )
            if region.get("status") != "pass":
                issues.append(
                    _issue(
                        "DIFF_NOT_PASSED",
                        "contracts/diff-regions.json",
                        f"diff region is not passed for {identity_name}",
                    )
                )
        if not diff_complete:
            issues.append(
                _issue(
                    "MISSING_DIFF_COVERAGE",
                    "contracts/diff-regions.json",
                    f"diff coverage is incomplete for {identity_name}",
                )
            )

        matching_qa = [row for row in qa_rows if _identity(row) == identity]
        region_ids = {
            region.get("regionId") for region in regions if isinstance(region, dict)
        }
        covered = {row.get("evidenceType") for row in matching_qa}
        if not QA_TYPES.issubset(covered):
            issues.append(
                _issue(
                    "MISSING_QA_COVERAGE",
                    "contracts/visual-qa-matrix.csv",
                    f"visual, structural, and interaction QA are required for {identity_name}",
                )
            )
        for row in matching_qa:
            qa_capture_profile_id = row.get("captureProfileId")
            if qa_capture_profile_id not in capture_profile_ids:
                issues.append(
                    _issue(
                        "QA_CAPTURE_PROFILE_MISSING",
                        "contracts/visual-qa-matrix.csv",
                        f"QA row {row.get('qaId')} references a missing capture profile",
                        captureProfileId=qa_capture_profile_id,
                    )
                )
            if diff_page and qa_capture_profile_id != diff_capture_profile_id:
                issues.append(
                    _issue(
                        "QA_DIFF_CAPTURE_PROFILE_MISMATCH",
                        "contracts/visual-qa-matrix.csv",
                        f"QA row {row.get('qaId')} capture profile differs from its diff page",
                    )
                )
            if row.get("regionId") not in region_ids:
                issues.append(
                    _issue(
                        "QA_REGION_MISSING",
                        "contracts/visual-qa-matrix.csv",
                        f"QA row {row.get('qaId')} references a missing diff region",
                        regionId=row.get("regionId"),
                    )
                )
            if row.get("status") != "pass":
                issues.append(
                    _issue(
                        "QA_NOT_PASSED",
                        "contracts/visual-qa-matrix.csv",
                        f"QA row {row.get('qaId')} is not passed",
                    )
                )
            if any(not row.get(field) for field in ("referencePath", "currentPath", "overlayPath", "diffPath")):
                issues.append(
                    _issue(
                        "INCOMPLETE_QA_EVIDENCE",
                        "contracts/visual-qa-matrix.csv",
                        f"QA row {row.get('qaId')} lacks comparison evidence paths",
                    )
                )


def _check_gaps(gap_rows: list[dict] | None, issues: list[dict]) -> None:
    for row in gap_rows or []:
        severity = str(row.get("severity", "")).lower()
        status = str(row.get("status", "")).lower()
        if status in RESOLVED_GAP_STATUSES:
            continue
        if severity == "blocker":
            issues.append(
                _issue(
                    "OPEN_BLOCKER_GAP",
                    "contracts/gap-register.csv",
                    f"blocker gap remains unresolved: {row.get('gapId')}",
                )
            )
        elif severity == "major":
            issues.append(
                _issue(
                    "OPEN_MAJOR_GAP",
                    "contracts/gap-register.csv",
                    f"major gap remains unresolved: {row.get('gapId')}",
                )
            )


def _check_gap_references(
    value: object,
    path: str,
    gap_registry: dict[str, dict],
    issues: list[dict],
) -> None:
    if isinstance(value, dict):
        if _requires_gap(value):
            referenced_ids = []
            if value.get("gapId"):
                referenced_ids.append(value["gapId"])
            referenced_ids.extend(value.get("gapIds") or [])
            for gap_id in referenced_ids:
                gap = gap_registry.get(gap_id)
                if gap is None:
                    issues.append(
                        _issue(
                            "GAP_ID_NOT_FOUND",
                            path,
                            f"referenced gap ID does not exist: {gap_id}",
                            gapId=gap_id,
                        )
                    )
                elif str(gap.get("status", "")).lower() in {"resolved", "closed"}:
                    issues.append(
                        _issue(
                            "UNKNOWN_REFERENCES_RESOLVED_GAP",
                            path,
                            f"unknown or proposed state references resolved gap: {gap_id}",
                            gapId=gap_id,
                        )
                    )
        for key, child in value.items():
            _check_gap_references(child, f"{path}/{key}", gap_registry, issues)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _check_gap_references(child, f"{path}/{index}", gap_registry, issues)


def _check_gap_integrity(
    documents: dict[str, dict],
    gap_rows: list[dict] | None,
    requirement_rows: list[dict] | None,
    issues: list[dict],
) -> None:
    gap_registry = {}
    for row in gap_rows or []:
        gap_id = row.get("gapId")
        if gap_id in gap_registry:
            issues.append(
                _issue(
                    "DUPLICATE_GAP_ID",
                    "contracts/gap-register.csv",
                    f"gap ID is duplicated: {gap_id}",
                )
            )
        gap_registry[gap_id] = row
    for relative_path, document in documents.items():
        if relative_path.startswith("contracts/") and relative_path != "contracts/design-lock.json":
            _check_gap_references(document, relative_path, gap_registry, issues)
    for index, row in enumerate(requirement_rows or []):
        _check_gap_references(
            row,
            f"contracts/requirement-ledger.csv/{index}",
            gap_registry,
            issues,
        )


def _check_design_lock(
    handoff_root: Path,
    documents: dict[str, dict],
    issues: list[dict],
) -> dict:
    result = {"computedContractsHash": None, "computedFileCount": 0}
    lock = documents.get("contracts/design-lock.json")
    if not lock or not isinstance(lock.get("files"), list):
        return result
    manifest = documents.get("contracts/asset-manifest.json") or {}
    if lock.get("sourceSetHash") != manifest.get("sourceSetHash"):
        issues.append(
            _issue(
                "DESIGN_LOCK_SOURCE_SET_HASH_MISMATCH",
                "contracts/design-lock.json",
                "design lock source set hash differs from asset manifest",
            )
        )
    if lock.get("designVersion") != manifest.get("designVersion"):
        issues.append(
            _issue(
                "DESIGN_LOCK_VERSION_MISMATCH",
                "contracts/design-lock.json",
                "design lock version differs from asset manifest",
            )
        )

    actual_records = []
    listed_paths = []
    for entry in lock["files"]:
        if not isinstance(entry, dict):
            continue
        relative_path = entry.get("relativePath")
        if not _safe_relative_path(relative_path):
            issues.append(
                _issue(
                    "ABSOLUTE_PATH",
                    "contracts/design-lock.json",
                    f"unsafe locked path: {relative_path}",
                )
            )
            continue
        listed_paths.append(relative_path)
        target = _resolve_within(handoff_root, relative_path)
        if target is None or not target.is_file():
            issues.append(
                _issue(
                    "DESIGN_LOCK_FILE_MISSING",
                    relative_path,
                    "locked file is missing",
                )
            )
            continue
        actual_hash = _sha256(target)
        actual_records.append((relative_path, actual_hash))
        if actual_hash != entry.get("sha256"):
            issues.append(
                _issue(
                    "DESIGN_LOCK_FILE_HASH_MISMATCH",
                    relative_path,
                    "locked file hash differs from computed hash",
                )
            )
    if len(listed_paths) != len(set(listed_paths)):
        issues.append(
            _issue(
                "DESIGN_LOCK_DUPLICATE_FILE",
                "contracts/design-lock.json",
                "design lock lists a file more than once",
            )
        )

    expected_locked_paths = {
        path.relative_to(handoff_root).as_posix()
        for path in handoff_root.rglob("*")
        if path.is_file()
        and path.relative_to(handoff_root).as_posix()
        not in {
            "contracts/design-lock.json",
            "reports/contact-sheet.png",
            "reports/validation-report.json",
        }
    }
    if set(listed_paths) != expected_locked_paths:
        issues.append(
            _issue(
                "DESIGN_LOCK_FILE_SET_MISMATCH",
                "contracts/design-lock.json",
                "design lock file set differs from package contents",
            )
        )

    contract_records = [
        record for record in actual_records if record[0].startswith("contracts/")
    ]
    computed_contracts_hash = _record_set_hash(contract_records)
    result = {
        "computedContractsHash": computed_contracts_hash,
        "computedFileCount": len(actual_records),
    }
    if computed_contracts_hash != lock.get("contractsHash"):
        issues.append(
            _issue(
                "DESIGN_LOCK_CONTRACTS_HASH_MISMATCH",
                "contracts/design-lock.json",
                "computed contract material differs from design lock",
            )
        )
    return result


def _check_git(
    repo_root: Path | None,
    allowed_git_prefix: str | None,
    issues: list[dict],
) -> dict:
    result = {"status": "skipped", "reason": "not-requested", "stagedPaths": []}
    if repo_root is None:
        return result
    repo_root = Path(repo_root)
    if allowed_git_prefix is None:
        result["reason"] = "allowlist-not-configured"
        return result
    try:
        probe = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--is-inside-work-tree"],
            check=False,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.SubprocessError):
        result["reason"] = "git-unavailable"
        return result
    if probe.returncode != 0 or probe.stdout.strip() != "true":
        result["reason"] = "not-a-repository"
        return result
    prefix = allowed_git_prefix.replace("\\", "/").strip("/")
    if prefix not in {"", "."} and not _safe_relative_path(prefix):
        issues.append(
            _issue(
                "INVALID_GIT_ALLOWLIST_PREFIX",
                "git",
                f"Git allowlist prefix must be repository-relative: {allowed_git_prefix}",
            )
        )
        return {"status": "failed", "reason": "invalid-prefix", "stagedPaths": []}
    try:
        staged = subprocess.run(
            ["git", "-C", str(repo_root), "diff", "--cached", "--name-only", "-z"],
            check=False,
            capture_output=True,
        )
    except (OSError, subprocess.SubprocessError) as error:
        issues.append(
            _issue(
                "GIT_STATUS_FAILED",
                "git",
                f"could not launch staged-path query: {error}",
            )
        )
        return {"status": "failed", "reason": "git-unavailable", "stagedPaths": []}
    if staged.returncode != 0:
        issues.append(_issue("GIT_STATUS_FAILED", "git", "could not read staged paths"))
        return {"status": "failed", "reason": "git-command-failed", "stagedPaths": []}
    staged_paths = sorted(
        value.decode("utf-8", errors="surrogateescape").replace("\\", "/")
        for value in staged.stdout.split(b"\0")
        if value
    )
    outside = []
    for path in staged_paths:
        allowed = prefix in {"", "."} or path == prefix or path.startswith(prefix + "/")
        if not allowed:
            outside.append(path)
            issues.append(
                _issue(
                    "GIT_STAGED_PATH_OUTSIDE_ALLOWLIST",
                    path,
                    f"staged path is outside allowed prefix {allowed_git_prefix}",
                )
            )
    return {
        "status": "failed" if outside else "passed",
        "reason": "outside-allowlist" if outside else "within-allowlist",
        "stagedPaths": staged_paths,
    }


def _deduplicate_and_sort(issues: list[dict]) -> list[dict]:
    unique = {}
    for issue in issues:
        key = (
            issue.get("code", ""),
            issue.get("path", ""),
            issue.get("message", ""),
            json.dumps(issue, ensure_ascii=False, sort_keys=True),
        )
        unique[key] = issue
    return [unique[key] for key in sorted(unique)]


def _write_validation_report_atomic(handoff_root: Path, report: dict) -> None:
    reports_root = handoff_root / "reports"
    reports_root.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".validation-report-", suffix=".tmp", dir=reports_root
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, reports_root / "validation-report.json")
    finally:
        if os.path.lexists(temporary_path):
            temporary_path.unlink()


def validate_handoff(
    handoff_root: Path,
    source_root: Path | None = None,
    repo_root: Path | None = None,
    allowed_git_prefix: str | None = None,
) -> dict:
    """Return a fail-closed, JSON-serializable validation report."""

    handoff_root = Path(handoff_root)
    source_root = Path(source_root) if source_root is not None else None
    issues: list[dict] = []
    checks = {"git": {"status": "skipped", "reason": "not-run", "stagedPaths": []}}
    design_lock = {"computedContractsHash": None, "computedFileCount": 0}

    if not handoff_root.is_dir():
        issues.append(
            _issue("HANDOFF_ROOT_MISSING", ".", "handoff root does not exist or is not a directory")
        )
    else:
        try:
            for relative_path in REQUIRED_FILES:
                if not (handoff_root / PurePosixPath(relative_path)).is_file():
                    issues.append(
                        _issue(
                            "MISSING_REQUIRED_FILE",
                            relative_path,
                            "required handoff file is missing",
                        )
                    )

            documents = {}
            for relative_path in (*SCHEMA_CONTRACTS, "reports/validation-report.json"):
                path = handoff_root / PurePosixPath(relative_path)
                if path.is_file():
                    document = _load_json(path, relative_path, issues)
                    if document is not None:
                        documents[relative_path] = document
            csv_documents = {}
            for relative_path, fields in CSV_FIELDS.items():
                path = handoff_root / PurePosixPath(relative_path)
                if path.is_file():
                    rows = _load_csv(path, relative_path, fields, issues)
                    if rows is not None:
                        csv_documents[relative_path] = rows

            _validate_schemas(documents, issues)
            _check_required_collections(documents, csv_documents, issues)
            _check_duplicate_identities(documents, issues)
            for relative_path, document in documents.items():
                if relative_path.startswith("contracts/") and relative_path != "contracts/design-lock.json":
                    _check_unknown_gaps(document, relative_path, issues)
                if relative_path.startswith("contracts/"):
                    _check_machine_paths(document, relative_path, issues)
            _check_assets(
                handoff_root,
                source_root,
                documents.get("contracts/asset-manifest.json"),
                issues,
            )
            _check_markdown_links(handoff_root, issues)
            qa_rows = csv_documents.get("contracts/visual-qa-matrix.csv")
            _check_qa_paths(handoff_root, qa_rows, issues)
            identities = _expected_identities(documents)
            _check_implementation_coverage(documents, identities, issues)
            _check_page_documents(handoff_root, identities, issues)
            _check_bilingual(handoff_root, issues)
            _check_capture_profiles(documents, issues)
            _check_diff_and_qa(documents, qa_rows, identities, issues)
            gap_rows = csv_documents.get("contracts/gap-register.csv")
            _check_gap_integrity(
                documents,
                gap_rows,
                csv_documents.get("contracts/requirement-ledger.csv"),
                issues,
            )
            _check_gaps(gap_rows, issues)
            design_lock = _check_design_lock(handoff_root, documents, issues)
        except Exception as error:
            issues.append(
                _issue(
                    "VALIDATION_INTERNAL_ERROR",
                    ".",
                    f"unexpected validation failure: {type(error).__name__}: {error}",
                )
            )

    checks["git"] = _check_git(repo_root, allowed_git_prefix, issues)
    issues = _deduplicate_and_sort(issues)
    result = {
        "schemaVersion": SCHEMA_VERSION,
        "status": "failed" if issues else "passed",
        "issues": issues,
        "checks": checks,
        "designLock": design_lock,
    }
    if handoff_root.is_dir():
        try:
            _write_validation_report_atomic(handoff_root, result)
        except (OSError, UnicodeError, TypeError, ValueError) as error:
            issues.append(
                _issue(
                    "VALIDATION_REPORT_WRITE_FAILED",
                    "reports/validation-report.json",
                    f"could not atomically persist validation report: {error}",
                )
            )
            result["issues"] = _deduplicate_and_sort(issues)
            result["status"] = "failed"
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail-closed validation for UI replica handoff packages."
    )
    parser.add_argument("root", nargs="?", type=Path)
    parser.add_argument("--handoff-root", type=Path)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--allowed-git-prefix")
    arguments = parser.parse_args(argv)
    roots = [root for root in (arguments.root, arguments.handoff_root) if root]
    if len(roots) != 1:
        parser.error("provide exactly one handoff root")
    result = validate_handoff(
        roots[0],
        source_root=arguments.source_root,
        repo_root=arguments.repo_root,
        allowed_git_prefix=arguments.allowed_git_prefix,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
