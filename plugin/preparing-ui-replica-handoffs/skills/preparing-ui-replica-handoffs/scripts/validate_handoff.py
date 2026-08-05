from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime
import hashlib
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import tempfile
import types

from jsonschema import Draft202012Validator, FormatChecker
from PIL import Image, ImageChops, UnidentifiedImageError


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
        "evidenceRecordPath",
        "evidenceRecordSha256",
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
            "tools/validate-command.txt",
        }
    )
)
QA_TYPES = frozenset({"visual", "structural", "interaction"})
DIFF_MODES = frozenset({"reference", "current", "overlay", "diff"})
PAGE_SECTION_IDS = frozenset(
    {
        "identity-and-evidence",
        "canvas-shell-regions",
        "layout-copy-icons-data",
        "components-interactions-responsive",
        "qa-and-gaps",
    }
)
PAGE_SECTION_CONTRACT_FIELDS = {
    "identity-and-evidence": (
        "pageId",
        "stateId",
        "variantId",
        "sourceAssetIds",
        "route",
        "evidenceLevel",
        "status",
    ),
    "canvas-shell-regions": ("canvas", "shell", "regions"),
    "layout-copy-icons-data": ("layoutRelationships", "copy", "icons", "data"),
    "components-interactions-responsive": (
        "components",
        "interactions",
        "responsiveVariants",
    ),
    "qa-and-gaps": ("acceptanceCriteria", "gapIds"),
}
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


def _canonical_contract_hash(page: dict, section_id: str) -> str:
    subset = {
        field: page.get(field)
        for field in PAGE_SECTION_CONTRACT_FIELDS[section_id]
    }
    canonical = json.dumps(
        subset,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


def _resolved_absence_gap_ids(
    page: dict, field: str, gap_rows: list[dict] | None
) -> set[str]:
    marker = f"[absence:{field}]".lower()
    registry = {
        row.get("gapId"): row
        for row in (gap_rows or [])
        if isinstance(row, dict) and row.get("gapId")
    }
    return {
        gap_id
        for gap_id in page.get("gapIds", [])
        if str(registry.get(gap_id, {}).get("status", "")).lower()
        in RESOLVED_GAP_STATUSES
        and marker in str(registry.get(gap_id, {}).get("resolution", "")).lower()
    }


def _unique_nonempty_strings(values: object) -> bool:
    return (
        isinstance(values, list)
        and all(isinstance(value, str) and value.strip() for value in values)
        and len(values) == len(set(values))
    )


def _reject_nonfinite_json_constant(value: str) -> object:
    raise ValueError(f"non-finite JSON number is forbidden: {value}")


def _strict_json_loads(text: str) -> object:
    return json.loads(text, parse_constant=_reject_nonfinite_json_constant)


def _is_finite_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


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
        document = _strict_json_loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
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
            schema = _strict_json_loads(
                (SCHEMA_ROOT / schema_name).read_text(encoding="utf-8")
            )
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
        if not text.strip():
            issues.append(
                _issue(
                    "EMPTY_MARKDOWN",
                    relative_path,
                    "required Markdown content must not be blank",
                )
            )
        if re.search(r"\{\{[^{}]+\}\}", text):
            issues.append(
                _issue(
                    "UNRESOLVED_MARKDOWN_PLACEHOLDER",
                    relative_path,
                    "Markdown contains an unresolved {{...}} placeholder",
                )
            )
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


def _expected_identities(documents: dict[str, dict]) -> set[tuple[object, object, object]]:
    inventory = documents.get("contracts/page-inventory.json") or {}
    return {
        _identity(page)
        for page in inventory.get("pages", [])
        if isinstance(page, dict)
    }


def _check_page_documents(
    handoff_root: Path,
    documents: dict[str, dict],
    issues: list[dict],
) -> None:
    def section_bodies(text: str) -> dict[str, str]:
        matches = list(
            re.finditer(r"(?m)^\s*sectionId:\s*([^\s]+)\s*$", text)
        )
        return {
            match.group(1): text[
                match.end() : matches[index + 1].start()
                if index + 1 < len(matches)
                else len(text)
            ]
            for index, match in enumerate(matches)
        }

    def referenced_gap_ids(value: object) -> set[str]:
        found: set[str] = set()
        if isinstance(value, dict):
            if isinstance(value.get("gapId"), str):
                found.add(value["gapId"])
            for gap_id in value.get("gapIds") or []:
                if isinstance(gap_id, str):
                    found.add(gap_id)
            for child in value.values():
                found.update(referenced_gap_ids(child))
        elif isinstance(value, list):
            for child in value:
                found.update(referenced_gap_ids(child))
        return found

    def require_values(
        body: str,
        values: set[str],
        relative_path: str,
        identity_name: str,
        section_id: str,
        field: str,
        issues: list[dict],
    ) -> None:
        missing = sorted(value for value in values if value not in body)
        if not missing:
            return
        details = {
            "identity": identity_name,
            "sectionId": section_id,
            "field": field,
            "missingIds": missing,
        }
        issues.append(
            _issue(
                "PAGE_DOCUMENT_SECTION_REFERENCE_MISSING",
                relative_path,
                "page document section is missing required machine IDs or absence marker",
                **details,
            )
        )
        issues.append(
            _issue(
                "PAGE_DOCUMENT_REFERENCE_MISSING",
                relative_path,
                "page document does not mention every machine contract ID in its required section",
                **details,
            )
        )

    def meaningful_prose(body: str, page: dict, locale: str) -> str:
        machine_ids: set[str] = set()

        def collect_ids(value: object, key: str = "") -> None:
            if isinstance(value, dict):
                for child_key, child in value.items():
                    collect_ids(child, child_key)
            elif isinstance(value, list):
                for child in value:
                    collect_ids(child, key)
            elif (
                isinstance(value, str)
                and (key.endswith("Id") or key.endswith("Ids"))
            ):
                machine_ids.add(value)

        collect_ids(page)
        machine_ids.add(_identity_text(_identity(page)))
        prose = re.sub(r"(?m)^\s*(?:contractHash|sectionId):.*$", "", body)
        prose = re.sub(r"(?m)^\s*#{1,6}\s+.*$", "", prose)
        prose = re.sub(r"`[^`]*`", "", prose)
        prose = re.sub(r"!?\[[^\]]*\]\([^)]*\)", "", prose)
        prose = re.sub(r"sha256:[0-9a-fA-F]{64}", "", prose)
        for machine_id in sorted(machine_ids, key=len, reverse=True):
            prose = prose.replace(machine_id, "")
        prose = re.sub(
            r"\b(?:P\d{3,}|S\d{2,}|V\d{2,}|A\d{3,}|G\d{3,}|QA\d{3,}|(?:component|instance|interaction|region|layout|copy|icon|data|responsive)[-_][A-Za-z0-9_-]+)\b",
            "",
            prose,
            flags=re.IGNORECASE,
        )
        normalized = "".join(character for character in prose if character.isalnum())
        if len(normalized) < 40:
            return ""
        folded = normalized.casefold()
        if len(set(folded)) / len(folded) < 0.12:
            return ""
        if re.search(r"(.)\1{7,}", folded):
            return ""
        if locale == "zh":
            cjk = re.findall(r"[\u3400-\u4dbf\u4e00-\u9fff]", prose)
            if len(cjk) < 12 or len(set(cjk)) < 8:
                return ""
        else:
            words = [word.casefold() for word in re.findall(r"[A-Za-z]+", prose)]
            if len(words) < 8 or len(set(words)) < 5:
                return ""
            if Counter(words).most_common(1)[0][1] / len(words) > 0.4:
                return ""
        return normalized

    inventory = documents.get("contracts/page-inventory.json") or {}
    registry = documents.get("contracts/component-registry.json") or {}
    component_names = {
        component.get("componentId"): component.get("name")
        for component in registry.get("components", [])
        if isinstance(component, dict) and component.get("componentId")
    }
    pages = [page for page in inventory.get("pages", []) if isinstance(page, dict)]
    for page in sorted(pages, key=lambda item: _identity_text(_identity(item))):
        identity = _identity(page)
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
                continue
            for page_document in matches:
                relative_path = page_document.relative_to(handoff_root).as_posix()
                try:
                    text = page_document.read_text(encoding="utf-8")
                except (OSError, UnicodeError):
                    continue
                bodies = section_bodies(text)
                present_sections = set(bodies)
                missing_sections = sorted(PAGE_SECTION_IDS - present_sections)
                if missing_sections:
                    issues.append(
                        _issue(
                            "PAGE_DOCUMENT_SECTION_MISSING",
                            relative_path,
                            "page document is missing required section IDs",
                            identity=name_prefix,
                            missingSectionIds=missing_sections,
                        )
                    )
                if page.get("status") == "approved":
                    locale_code = "zh-CN" if locale == "zh" else "en-US"
                    for section_id in PAGE_SECTION_CONTRACT_FIELDS:
                        body = bodies.get(section_id, "")
                        expected_hash = _canonical_contract_hash(page, section_id)
                        hashes = re.findall(
                            r"(?m)^\s*contractHash:\s*(sha256:[0-9a-f]{64})\s*$",
                            body,
                        )
                        if hashes != [expected_hash]:
                            issues.append(
                                _issue(
                                    "PAGE_DOCUMENT_CONTRACT_HASH_MISMATCH",
                                    relative_path,
                                    "approved page section must contain exactly its canonical contract hash",
                                    identity=name_prefix,
                                    sectionId=section_id,
                                    expectedContractHash=expected_hash,
                                )
                            )
                        if not meaningful_prose(body, page, locale):
                            issues.append(
                                _issue(
                                    "PAGE_DOCUMENT_SECTION_PROSE_INSUFFICIENT",
                                    relative_path,
                                    "approved page section requires at least 40 meaningful locale characters",
                                    identity=name_prefix,
                                    sectionId=section_id,
                                    locale=locale_code,
                                )
                            )
                    localized_layout_values = {
                        str(item.get("text", {}).get(locale_code))
                        for item in page.get("copy", [])
                        if isinstance(item, dict)
                        and isinstance(item.get("text"), dict)
                        and item.get("text", {}).get(locale_code)
                    } | {
                        str(item.get("valueShape"))
                        for item in page.get("data", [])
                        if isinstance(item, dict) and item.get("valueShape")
                    }
                    localized_behavior_values = {
                        str(item.get("outcome", {}).get(locale_code))
                        for item in page.get("interactions", [])
                        if isinstance(item, dict)
                        and isinstance(item.get("outcome"), dict)
                        and item.get("outcome", {}).get(locale_code)
                    } | {
                        str(component_names.get(item.get("componentId"), {}).get(locale_code))
                        for item in page.get("components", [])
                        if isinstance(item, dict)
                        and isinstance(component_names.get(item.get("componentId")), dict)
                        and component_names.get(item.get("componentId"), {}).get(locale_code)
                    }
                    missing_localized = sorted(
                        value
                        for value in localized_layout_values
                        if value not in bodies.get("layout-copy-icons-data", "")
                    ) + sorted(
                        value
                        for value in localized_behavior_values
                        if value
                        not in bodies.get("components-interactions-responsive", "")
                    )
                    if missing_localized:
                        issues.append(
                            _issue(
                                "PAGE_DOCUMENT_LOCALIZED_CONTENT_MISSING",
                                relative_path,
                                "approved page sections must include locale copy, value shapes, component names, and interaction outcomes",
                                identity=name_prefix,
                                locale=locale_code,
                                missingValues=missing_localized,
                            )
                        )
                require_values(
                    bodies.get("identity-and-evidence", ""),
                    {name_prefix, *(str(value) for value in page.get("sourceAssetIds", []))},
                    relative_path,
                    name_prefix,
                    "identity-and-evidence",
                    "identity",
                    issues,
                )
                require_values(
                    bodies.get("canvas-shell-regions", ""),
                    {
                        str(page.get("shell", {}).get("shellId")),
                        *(
                            str(region.get("regionId"))
                            for region in page.get("regions", [])
                            if isinstance(region, dict) and region.get("regionId")
                        ),
                    },
                    relative_path,
                    name_prefix,
                    "canvas-shell-regions",
                    "canvasShellRegions",
                    issues,
                )
                section_contracts = (
                    (
                        "layout-copy-icons-data",
                        "layoutRelationships",
                        "relationshipId",
                    ),
                    ("layout-copy-icons-data", "copy", "copyId"),
                    ("layout-copy-icons-data", "icons", "iconId"),
                    ("layout-copy-icons-data", "data", "dataId"),
                    (
                        "components-interactions-responsive",
                        "components",
                        "instanceId",
                    ),
                    (
                        "components-interactions-responsive",
                        "components",
                        "componentId",
                    ),
                    (
                        "components-interactions-responsive",
                        "interactions",
                        "interactionId",
                    ),
                    (
                        "components-interactions-responsive",
                        "responsiveVariants",
                        "responsiveVariantId",
                    ),
                )
                for section_id, field, id_field in section_contracts:
                    collection = page.get(field) or []
                    values = {
                        str(item.get(id_field))
                        for item in collection
                        if isinstance(item, dict) and item.get(id_field)
                    }
                    if (
                        not collection
                        and page.get("status") == "approved"
                        and field
                        in {
                            "layoutRelationships",
                            "copy",
                            "icons",
                            "components",
                            "data",
                            "interactions",
                        }
                    ):
                        values = {f"[absence:{field}]"}
                    require_values(
                        bodies.get(section_id, ""),
                        values,
                        relative_path,
                        name_prefix,
                        section_id,
                        field,
                        issues,
                    )
                require_values(
                    bodies.get("qa-and-gaps", ""),
                    {
                        *(
                            str(item.get("qaId"))
                            for item in page.get("acceptanceCriteria", [])
                            if isinstance(item, dict) and item.get("qaId")
                        ),
                        *referenced_gap_ids(page),
                    },
                    relative_path,
                    name_prefix,
                    "qa-and-gaps",
                    "qaAndGaps",
                    issues,
                )


def _check_semantic_readiness(
    documents: dict[str, dict],
    gap_rows: list[dict] | None,
    issues: list[dict],
) -> None:
    inventory = documents.get("contracts/page-inventory.json") or {}
    registry = documents.get("contracts/component-registry.json") or {}
    pages = [page for page in inventory.get("pages", []) if isinstance(page, dict)]
    registered_components = {
        component.get("componentId")
        for component in registry.get("components", [])
        if isinstance(component, dict) and component.get("componentId")
    }
    component_instances = [
        component
        for page in pages
        for component in page.get("components", [])
        if isinstance(component, dict)
    ]
    if component_instances and not registered_components:
        issues.append(
            _issue(
                "COMPONENT_REGISTRY_EMPTY",
                "contracts/component-registry.json",
                "component registry must be nonempty when page instances exist",
            )
        )
    for page in pages:
        identity_name = _identity_text(_identity(page))
        for component in page.get("components", []):
            if not isinstance(component, dict):
                continue
            component_id = component.get("componentId")
            if component_id not in registered_components:
                issues.append(
                    _issue(
                        "COMPONENT_ID_NOT_FOUND",
                        "contracts/page-inventory.json",
                        f"page component does not resolve in registry: {component_id}",
                        identity=identity_name,
                        componentId=component_id,
                    )
                )
        if page.get("status") != "approved":
            continue
        for field in (
            "layoutRelationships",
            "copy",
            "icons",
            "components",
            "data",
            "interactions",
        ):
            if page.get(field) or _resolved_absence_gap_ids(page, field, gap_rows):
                continue
            issues.append(
                _issue(
                    "APPROVED_PAGE_SUBSTANTIVE_FIELD_EMPTY",
                    "contracts/page-inventory.json",
                    f"approved page has an empty substantive field: {field}",
                    identity=identity_name,
                    field=field,
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
        incomplete = incomplete or profile.get("zoom") in (None, "unknown")
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
    inventory = documents.get("contracts/page-inventory.json") or {}
    pages = {
        _identity(page): page
        for page in inventory.get("pages", [])
        if isinstance(page, dict)
    }
    for mapping in implementation.get("mappings", []):
        if not isinstance(mapping, dict) or mapping.get("status") != "approved":
            continue
        identity = _identity(mapping)
        page = pages.get(identity)
        if page is None:
            continue
        raw_target_files = mapping.get("targetFiles")
        target_files_valid = _unique_nonempty_strings(raw_target_files)
        target_files = set(raw_target_files) if target_files_valid else set()
        region_mappings = mapping.get("regionMappings")
        component_mappings = mapping.get("componentMappings")
        expected_regions = {
            region.get("regionId")
            for region in page.get("regions", [])
            if isinstance(region, dict) and region.get("regionId")
        }
        expected_components = {
            (component.get("instanceId"), component.get("componentId"))
            for component in page.get("components", [])
            if isinstance(component, dict)
        }
        actual_regions = [
            item.get("regionId")
            for item in region_mappings or []
            if isinstance(item, dict)
        ]
        actual_components = [
            (item.get("instanceId"), item.get("componentId"))
            for item in component_mappings or []
            if isinstance(item, dict)
        ]
        region_ids_valid = all(
            isinstance(region_id, str) and region_id
            for region_id in actual_regions
        )
        component_ids_valid = all(
            isinstance(instance_id, str)
            and instance_id
            and isinstance(component_id, str)
            and component_id
            for instance_id, component_id in actual_components
        )
        mapping_files_valid = all(
            isinstance(item, dict)
            and item.get("targetFile") in target_files
            for item in [*(region_mappings or []), *(component_mappings or [])]
        )
        exact = (
            isinstance(region_mappings, list)
            and isinstance(component_mappings, list)
            and target_files_valid
            and region_ids_valid
            and component_ids_valid
            and len(actual_regions) == len(region_mappings) == len(set(actual_regions))
            and set(actual_regions) == expected_regions
            and len(actual_components)
            == len(component_mappings)
            == len(set(actual_components))
            and set(actual_components) == expected_components
            and mapping_files_valid
        )
        if not exact:
            issues.append(
                _issue(
                    "IMPLEMENTATION_MAPPING_COVERAGE_MISMATCH",
                    "contracts/implementation-map.json",
                    "approved region/component mappings must exactly and uniquely cover the page contract and target approved files",
                    identity=_identity_text(identity),
                )
            )


def _load_qa_image(path: Path) -> Image.Image:
    with Image.open(path) as image:
        image.load()
        return image.convert("RGBA")


def _nonplaceholder_text(value: object) -> bool:
    return bool(
        isinstance(value, str)
        and value.strip()
        and value.strip().lower() not in PLACEHOLDER_VALUES
    )


def _valid_runner_timestamp(value: object) -> bool:
    if not _nonplaceholder_text(value):
        return False
    try:
        datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def _load_hashed_json_artifact(
    handoff_root: Path,
    metadata: object,
    record_relative: str,
    qa_id: object,
    artifact_name: str,
    issues: list[dict],
) -> tuple[dict | None, Path | None]:
    if not isinstance(metadata, dict):
        issues.append(
            _issue(
                "QA_RUNNER_ARTIFACT_REQUIRED",
                record_relative,
                f"runner result requires artifact metadata: {artifact_name}",
                qaId=qa_id,
                artifact=artifact_name,
            )
        )
        return None, None
    relative_path = metadata.get("path")
    if not _safe_relative_path(relative_path):
        issues.append(
            _issue(
                "QA_RUNNER_ARTIFACT_PATH_UNSAFE",
                record_relative,
                f"runner artifact path must be package-relative: {artifact_name}",
                qaId=qa_id,
                artifact=artifact_name,
            )
        )
        return None, None
    artifact_path = _resolve_within(handoff_root, relative_path)
    if artifact_path is None or not artifact_path.is_file():
        issues.append(
            _issue(
                "QA_RUNNER_ARTIFACT_MISSING",
                str(relative_path),
                f"runner artifact is missing: {artifact_name}",
                qaId=qa_id,
                artifact=artifact_name,
            )
        )
        return None, None
    if metadata.get("sha256") != _sha256(artifact_path):
        issues.append(
            _issue(
                "QA_RUNNER_ARTIFACT_HASH_MISMATCH",
                str(relative_path),
                f"runner artifact SHA-256 is invalid: {artifact_name}",
                qaId=qa_id,
                artifact=artifact_name,
            )
        )
    try:
        document = _strict_json_loads(artifact_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        issues.append(
            _issue(
                "QA_RUNNER_ARTIFACT_INVALID_JSON",
                str(relative_path),
                str(error),
                qaId=qa_id,
                artifact=artifact_name,
            )
        )
        return None, artifact_path
    if not isinstance(document, dict):
        issues.append(
            _issue(
                "QA_RUNNER_ARTIFACT_INVALID_JSON",
                str(relative_path),
                "runner artifact JSON root must be an object",
                qaId=qa_id,
                artifact=artifact_name,
            )
        )
        return None, artifact_path
    return document, artifact_path


def _check_qa_evidence_records(
    handoff_root: Path,
    documents: dict[str, dict],
    qa_rows: list[dict] | None,
    requirement_rows: list[dict] | None,
    gap_rows: list[dict] | None,
    issues: list[dict],
) -> None:
    inventory = documents.get("contracts/page-inventory.json") or {}
    diff_contract = documents.get("contracts/diff-regions.json") or {}
    registry = documents.get("contracts/component-registry.json") or {}
    manifest = documents.get("contracts/asset-manifest.json") or {}
    implementation = documents.get("contracts/implementation-map.json") or {}
    pages = {
        _identity(page): page
        for page in inventory.get("pages", [])
        if isinstance(page, dict)
    }
    diff_pages = {
        _identity(page): page
        for page in diff_contract.get("pages", [])
        if isinstance(page, dict)
    }
    registry_ids = {
        component.get("componentId")
        for component in registry.get("components", [])
        if isinstance(component, dict) and component.get("componentId")
    }
    assets_by_id = {
        asset.get("assetId"): asset
        for asset in manifest.get("assets", [])
        if isinstance(asset, dict) and asset.get("assetId")
    }
    implementations = {
        _identity(mapping): mapping
        for mapping in implementation.get("mappings", [])
        if isinstance(mapping, dict)
    }
    requirement_ids_by_identity: dict[tuple[object, object, object], set[object]] = {}
    for requirement in requirement_rows or []:
        if not isinstance(requirement, dict):
            continue
        requirement_ids_by_identity.setdefault(_identity(requirement), set()).add(
            requirement.get("requirementId")
        )

    for row in qa_rows or []:
        if row.get("status") != "pass":
            continue
        qa_id = row.get("qaId")
        record_relative = row.get("evidenceRecordPath", "")
        expected_record_hash = row.get("evidenceRecordSha256", "")
        if not record_relative or not expected_record_hash:
            issues.append(
                _issue(
                    "QA_EVIDENCE_RECORD_REQUIRED",
                    "contracts/visual-qa-matrix.csv",
                    "passed QA row requires an evidence record path and SHA-256",
                    qaId=qa_id,
                )
            )
            continue
        if not _safe_relative_path(record_relative):
            issues.append(
                _issue(
                    "QA_EVIDENCE_RECORD_PATH_UNSAFE",
                    "contracts/visual-qa-matrix.csv",
                    f"evidence record path must be package-relative: {record_relative}",
                    qaId=qa_id,
                )
            )
            continue
        record_path = _resolve_within(handoff_root, record_relative)
        if record_path is None or not record_path.is_file():
            issues.append(
                _issue(
                    "QA_EVIDENCE_RECORD_MISSING",
                    record_relative,
                    "passed QA evidence record is missing",
                    qaId=qa_id,
                )
            )
            continue
        actual_record_hash = _sha256(record_path)
        if actual_record_hash != expected_record_hash:
            issues.append(
                _issue(
                    "QA_EVIDENCE_RECORD_HASH_MISMATCH",
                    record_relative,
                    "evidence record SHA-256 differs from the QA matrix",
                    qaId=qa_id,
                )
            )
        try:
            record = _strict_json_loads(record_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
            issues.append(
                _issue(
                    "QA_EVIDENCE_RECORD_INVALID_JSON",
                    record_relative,
                    str(error),
                    qaId=qa_id,
                )
            )
            continue
        if not isinstance(record, dict):
            issues.append(
                _issue(
                    "QA_EVIDENCE_RECORD_INVALID_JSON",
                    record_relative,
                    "evidence record root must be an object",
                    qaId=qa_id,
                )
            )
            continue

        expected_fields = {
            field: row.get(field)
            for field in (
                "qaId",
                "pageId",
                "stateId",
                "variantId",
                "evidenceType",
                "status",
            )
        }
        mismatches = {
            field: {"expected": expected, "actual": record.get(field)}
            for field, expected in expected_fields.items()
            if record.get(field) != expected
        }
        for field in ("tool", "command"):
            if not isinstance(record.get(field), str) or not record[field].strip():
                mismatches[field] = {"expected": "nonempty string", "actual": record.get(field)}
        if mismatches:
            issues.append(
                _issue(
                    "QA_EVIDENCE_RECORD_FIELD_MISMATCH",
                    record_relative,
                    "evidence record identity, status, tool, or command is invalid",
                    qaId=qa_id,
                    mismatches=mismatches,
                )
            )

        identity = _identity(row)
        page = pages.get(identity) or {}
        runner_relative = record.get("runnerResultPath")
        expected_runner_hash = record.get("runnerResultSha256")
        runner: dict | None = None
        if not runner_relative or not expected_runner_hash:
            issues.append(
                _issue(
                    "QA_RUNNER_RESULT_REQUIRED",
                    record_relative,
                    "passed QA evidence requires runnerResultPath and runnerResultSha256",
                    qaId=qa_id,
                )
            )
        elif not _safe_relative_path(runner_relative):
            issues.append(
                _issue(
                    "QA_RUNNER_RESULT_PATH_UNSAFE",
                    record_relative,
                    "runner result path must be package-relative",
                    qaId=qa_id,
                )
            )
        else:
            runner_path = _resolve_within(handoff_root, runner_relative)
            if runner_path is None or not runner_path.is_file():
                issues.append(
                    _issue(
                        "QA_RUNNER_RESULT_MISSING",
                        str(runner_relative),
                        "runner result file is missing",
                        qaId=qa_id,
                    )
                )
            else:
                if _sha256(runner_path) != expected_runner_hash:
                    issues.append(
                        _issue(
                            "QA_RUNNER_RESULT_HASH_MISMATCH",
                            str(runner_relative),
                            "runner result SHA-256 differs from the evidence record",
                            qaId=qa_id,
                        )
                    )
                try:
                    loaded_runner = _strict_json_loads(
                        runner_path.read_text(encoding="utf-8")
                    )
                except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
                    issues.append(
                        _issue(
                            "QA_RUNNER_RESULT_INVALID_JSON",
                            str(runner_relative),
                            str(error),
                            qaId=qa_id,
                        )
                    )
                else:
                    if isinstance(loaded_runner, dict):
                        runner = loaded_runner
                    else:
                        issues.append(
                            _issue(
                                "QA_RUNNER_RESULT_INVALID_JSON",
                                str(runner_relative),
                                "runner result JSON root must be an object",
                                qaId=qa_id,
                            )
                        )
        runner_assertions: list[dict] = []
        if runner is not None:
            runner_mismatches = {
                field: {"expected": row.get(field), "actual": runner.get(field)}
                for field in (
                    "qaId",
                    "pageId",
                    "stateId",
                    "variantId",
                    "evidenceType",
                )
                if runner.get(field) != row.get(field)
            }
            for field in ("tool", "version", "command"):
                if not _nonplaceholder_text(runner.get(field)):
                    runner_mismatches[field] = {
                        "expected": "nonplaceholder string",
                        "actual": runner.get(field),
                    }
            if runner_mismatches:
                issues.append(
                    _issue(
                        "QA_RUNNER_RESULT_FIELD_MISMATCH",
                        str(runner_relative),
                        "runner identity, evidence type, tool, version, or command is invalid",
                        qaId=qa_id,
                        mismatches=runner_mismatches,
                    )
                )
            timestamps_valid = _valid_runner_timestamp(
                runner.get("startedAt")
            ) and _valid_runner_timestamp(runner.get("finishedAt"))
            if runner.get("exitCode") != 0 or not timestamps_valid:
                issues.append(
                    _issue(
                        "QA_RUNNER_EXECUTION_INVALID",
                        str(runner_relative),
                        "runner exitCode must be 0 and timestamps must be nonplaceholder ISO values",
                        qaId=qa_id,
                    )
                )
            raw_assertions = runner.get("assertions")
            if not isinstance(raw_assertions, list) or not raw_assertions:
                issues.append(
                    _issue(
                        "QA_RUNNER_ASSERTIONS_REQUIRED",
                        str(runner_relative),
                        "runner assertions must be a nonempty array",
                        qaId=qa_id,
                    )
                )
            else:
                runner_assertions = [
                    assertion
                    for assertion in raw_assertions
                    if isinstance(assertion, dict)
                ]
                for index, assertion in enumerate(raw_assertions):
                    if (
                        not isinstance(assertion, dict)
                        or assertion.get("status") != "pass"
                    ):
                        issues.append(
                            _issue(
                                "QA_RUNNER_ASSERTION_NOT_PASSED",
                                f"{runner_relative}#/assertions/{index}",
                                "every runner assertion must be an object with status pass",
                                qaId=qa_id,
                            )
                        )

        checks = record.get("checks")
        if not isinstance(checks, list) or not checks:
            issues.append(
                _issue(
                    "QA_EVIDENCE_CHECKS_REQUIRED",
                    record_relative,
                    "evidence record checks must be a nonempty array",
                    qaId=qa_id,
                )
            )
            checks = []
        for index, check in enumerate(checks):
            if not isinstance(check, dict) or check.get("status") != "pass":
                issues.append(
                    _issue(
                        "QA_EVIDENCE_CHECK_NOT_PASSED",
                        f"{record_relative}#/checks/{index}",
                        "every evidence check must be an object with status pass",
                        qaId=qa_id,
                    )
                )

        artifacts = record.get("artifacts")
        if not isinstance(artifacts, dict):
            artifacts = {}
        artifact_paths: dict[str, Path] = {}
        for name, csv_field in (
            ("reference", "referencePath"),
            ("current", "currentPath"),
            ("overlay", "overlayPath"),
            ("diff", "diffPath"),
        ):
            artifact = artifacts.get(name)
            csv_path = row.get(csv_field)
            if not isinstance(artifact, dict):
                issues.append(
                    _issue(
                        "QA_ARTIFACT_RECORD_INVALID",
                        record_relative,
                        f"evidence record is missing artifact metadata: {name}",
                        qaId=qa_id,
                    )
                )
                continue
            artifact_relative = artifact.get("path")
            if artifact_relative != csv_path or not _safe_relative_path(artifact_relative):
                issues.append(
                    _issue(
                        "QA_ARTIFACT_PATH_MISMATCH",
                        record_relative,
                        f"artifact path is unsafe or differs from QA matrix: {name}",
                        qaId=qa_id,
                    )
                )
                continue
            artifact_path = _resolve_within(handoff_root, artifact_relative)
            if artifact_path is None or not artifact_path.is_file():
                issues.append(
                    _issue(
                        "QA_ARTIFACT_MISSING",
                        artifact_relative,
                        f"QA artifact is missing: {name}",
                        qaId=qa_id,
                    )
                )
                continue
            artifact_paths[name] = artifact_path
            if artifact.get("sha256") != _sha256(artifact_path):
                issues.append(
                    _issue(
                        "QA_ARTIFACT_HASH_MISMATCH",
                        artifact_relative,
                        f"QA artifact SHA-256 is invalid: {name}",
                        qaId=qa_id,
                    )
                )

        if row.get("evidenceType") == "visual":
            page_assets = [
                assets_by_id.get(asset_id)
                for asset_id in page.get("sourceAssetIds", [])
                if assets_by_id.get(asset_id) is not None
            ]
            reference_matches = [
                asset
                for asset in page_assets
                if asset.get("deliveryRelativePath") == row.get("referencePath")
            ]
            if len(reference_matches) != 1:
                issues.append(
                    _issue(
                        "QA_VISUAL_REFERENCE_NOT_MANIFEST_ASSET",
                        "contracts/visual-qa-matrix.csv",
                        "visual referencePath must equal exactly one page source asset deliveryRelativePath",
                        qaId=qa_id,
                    )
                )

        images: dict[str, Image.Image] = {}
        for name, artifact_path in artifact_paths.items():
            try:
                images[name] = _load_qa_image(artifact_path)
            except (OSError, ValueError, UnidentifiedImageError) as error:
                issues.append(
                    _issue(
                        "QA_IMAGE_DECODE_FAILED",
                        artifact_path.relative_to(handoff_root).as_posix(),
                        f"could not decode QA image {name}: {error}",
                        qaId=qa_id,
                    )
                )
        if len(images) == 4:
            dimensions = {image.size for image in images.values()}
            if len(dimensions) != 1:
                issues.append(
                    _issue(
                        "QA_IMAGE_DIMENSION_MISMATCH",
                        record_relative,
                        "reference/current/overlay/diff dimensions must match",
                        qaId=qa_id,
                    )
                )
            elif row.get("evidenceType") == "visual":
                canvas = page.get("canvas") or {}
                expected_size = (canvas.get("width"), canvas.get("height"))
                manifest_size = (
                    (
                        reference_matches[0].get("width"),
                        reference_matches[0].get("height"),
                    )
                    if len(reference_matches) == 1
                    else None
                )
                diff_page = diff_pages.get(identity) or {}
                region = next(
                    (
                        item
                        for item in diff_page.get("regions", [])
                        if isinstance(item, dict)
                        and item.get("regionId") == row.get("regionId")
                    ),
                    None,
                )
                bounds = region.get("bounds", {}) if isinstance(region, dict) else {}
                full_region = (
                    bounds.get("x") == 0
                    and bounds.get("y") == 0
                    and bounds.get("width") == canvas.get("width")
                    and bounds.get("height") == canvas.get("height")
                )
                if (
                    images["reference"].size != expected_size
                    or manifest_size != expected_size
                    or not full_region
                ):
                    issues.append(
                        _issue(
                            "QA_VISUAL_REFERENCE_DIMENSION_MISMATCH",
                            row.get("referencePath", ""),
                            "uncropped reference dimensions and diff region must match the page canvas",
                            qaId=qa_id,
                            referenceSize=list(images["reference"].size),
                            canvasSize=list(expected_size),
                        )
                    )
                expected_overlay = Image.blend(
                    images["reference"], images["current"], 0.5
                )
                expected_diff = ImageChops.difference(
                    images["reference"], images["current"]
                )
                if expected_overlay.tobytes() != images["overlay"].tobytes():
                    issues.append(
                        _issue(
                            "QA_OVERLAY_PIXEL_MISMATCH",
                            row.get("overlayPath", ""),
                            "overlay pixels are not the 50% reference/current blend",
                            qaId=qa_id,
                        )
                    )
                if expected_diff.tobytes() != images["diff"].tobytes():
                    issues.append(
                        _issue(
                            "QA_DIFF_PIXEL_MISMATCH",
                            row.get("diffPath", ""),
                            "diff pixels do not equal ImageChops.difference(reference, current)",
                            qaId=qa_id,
                        )
                    )
                different_pixels = sum(
                    1
                    for pixel in expected_diff.get_flattened_data()
                    if any(pixel)
                )
                actual_pixel_ratio = different_pixels / (
                    expected_diff.width * expected_diff.height
                )
                pixel_checks = [
                    check
                    for check in checks
                    if isinstance(check, dict)
                    and check.get("checkType") == "pixel-diff"
                ]
                if not pixel_checks:
                    issues.append(
                        _issue(
                            "QA_VISUAL_PIXEL_CHECK_REQUIRED",
                            record_relative,
                            "visual evidence requires a pixel-diff check",
                            qaId=qa_id,
                        )
                    )
                elif not any(
                    _is_finite_number(check.get("actualPixelRatio"))
                    and math.isclose(
                        float(check["actualPixelRatio"]),
                        actual_pixel_ratio,
                        rel_tol=0.0,
                        abs_tol=1e-12,
                    )
                    for check in pixel_checks
                ):
                    issues.append(
                        _issue(
                            "QA_PIXEL_RATIO_MISMATCH",
                            record_relative,
                            "recorded actualPixelRatio differs from computed pixels",
                            qaId=qa_id,
                            computedPixelRatio=actual_pixel_ratio,
                        )
                    )
                tolerance = (
                    region.get("tolerance", {}).get("pixelRatio")
                    if isinstance(region, dict)
                    else None
                )
                if not _is_finite_number(tolerance):
                    issues.append(
                        _issue(
                            "QA_PIXEL_TOLERANCE_REQUIRED",
                            "contracts/diff-regions.json",
                            "visual QA region requires numeric tolerance.pixelRatio",
                            qaId=qa_id,
                        )
                    )
                elif actual_pixel_ratio > float(tolerance):
                    issues.append(
                        _issue(
                            "QA_PIXEL_RATIO_EXCEEDS_TOLERANCE",
                            record_relative,
                            "computed pixel ratio exceeds region tolerance",
                            qaId=qa_id,
                            actualPixelRatio=actual_pixel_ratio,
                            tolerancePixelRatio=float(tolerance),
                        )
                    )

        identity = _identity(row)
        page = pages.get(identity) or {}
        if runner is not None and row.get("evidenceType") == "visual":
            current_metadata = (runner.get("artifacts") or {}).get("current")
            current_path = row.get("currentPath")
            current_artifact = _resolve_within(handoff_root, current_path)
            visual_runner_valid = (
                runner.get("route") == page.get("route", {}).get("path")
                and runner.get("captureProfileId") == row.get("captureProfileId")
                and isinstance(current_metadata, dict)
                and current_metadata.get("path") == current_path
                and current_artifact is not None
                and current_artifact.is_file()
                and current_metadata.get("sha256") == _sha256(current_artifact)
            )
            if not visual_runner_valid:
                issues.append(
                    _issue(
                        "QA_VISUAL_RUNNER_BINDING_MISMATCH",
                        str(runner_relative),
                        "visual runner must bind route, capture profile, and current capture path/hash",
                        qaId=qa_id,
                    )
                )

        if runner is not None and row.get("evidenceType") == "structural":
            runner_artifacts = runner.get("artifacts") or {}
            dom_snapshot, _dom_path = _load_hashed_json_artifact(
                handoff_root,
                runner_artifacts.get("domSnapshot"),
                str(runner_relative),
                qa_id,
                "domSnapshot",
                issues,
            )
            implementation_snapshot, _implementation_path = (
                _load_hashed_json_artifact(
                    handoff_root,
                    runner_artifacts.get("implementationSnapshot"),
                    str(runner_relative),
                    qa_id,
                    "implementationSnapshot",
                    issues,
                )
            )
            page_region_ids = {
                region.get("regionId")
                for region in page.get("regions", [])
                if isinstance(region, dict) and region.get("regionId")
            }
            expected_components = {
                (
                    component.get("instanceId"),
                    component.get("componentId"),
                    component.get("regionId"),
                )
                for component in page.get("components", [])
                if isinstance(component, dict)
            }
            page_component_ids = {item[1] for item in expected_components}
            component_absence_gaps = _resolved_absence_gap_ids(
                page, "components", gap_rows
            )
            if dom_snapshot is not None:
                nodes = dom_snapshot.get("nodes")
                dom_identity_matches = all(
                    dom_snapshot.get(field) == row.get(field)
                    for field in ("pageId", "stateId", "variantId")
                )
                node_ids = [
                    node.get("nodeId")
                    for node in nodes or []
                    if isinstance(node, dict)
                ]
                region_nodes = [
                    node
                    for node in nodes or []
                    if isinstance(node, dict) and node.get("nodeType") == "region"
                ]
                component_nodes = [
                    node
                    for node in nodes or []
                    if isinstance(node, dict)
                    and node.get("nodeType") == "component"
                ]
                actual_regions = [node.get("regionId") for node in region_nodes]
                actual_components = [
                    (
                        node.get("instanceId"),
                        node.get("componentId"),
                        node.get("regionId"),
                    )
                    for node in component_nodes
                ]
                regions_valid = all(
                    isinstance(region_id, str) and region_id
                    for region_id in actual_regions
                )
                components_valid = all(
                    all(isinstance(value, str) and value for value in component)
                    for component in actual_components
                )
                dom_nodes_match = (
                    isinstance(nodes, list)
                    and all(isinstance(node, dict) for node in nodes)
                    and _unique_nonempty_strings(node_ids)
                    and len(node_ids) == len(nodes)
                    and len(region_nodes) + len(component_nodes) == len(nodes)
                    and regions_valid
                    and len(actual_regions) == len(set(actual_regions))
                    and set(actual_regions) == page_region_ids
                    and components_valid
                    and len(actual_components) == len(set(actual_components))
                    and set(actual_components) == expected_components
                    and page_component_ids.issubset(registry_ids)
                    and (not component_absence_gaps or not component_nodes)
                )
                if not dom_identity_matches or not dom_nodes_match:
                    issues.append(
                        _issue(
                            "QA_STRUCTURAL_DOM_COVERAGE_MISMATCH",
                            str(runner_relative),
                            "DOM snapshot must uniquely and exactly cover typed page region and component instances",
                            qaId=qa_id,
                        )
                    )
                    issues.append(
                        _issue(
                            "QA_STRUCTURAL_DOM_BINDING_MISMATCH",
                            str(runner_relative),
                            "DOM snapshot identity and typed region/component bindings must resolve exactly",
                            qaId=qa_id,
                        )
                    )
            mapping = implementations.get(identity) or {}
            if implementation_snapshot is not None:
                entries = implementation_snapshot.get("entries")
                raw_expected_targets = mapping.get("targetFiles")
                expected_targets_valid = _unique_nonempty_strings(
                    raw_expected_targets
                )
                expected_targets = (
                    set(raw_expected_targets) if expected_targets_valid else set()
                )
                actual_targets = [
                    entry.get("targetFile")
                    for entry in entries or []
                    if isinstance(entry, dict)
                ]
                entries_valid = (
                    mapping.get("status") == "approved"
                    and isinstance(entries, list)
                    and bool(entries)
                    and expected_targets_valid
                    and _unique_nonempty_strings(actual_targets)
                    and len(actual_targets) == len(entries)
                    and set(actual_targets) == expected_targets
                    and all(
                        isinstance(entry, dict)
                        and _safe_relative_path(entry.get("targetFile"))
                        and (
                            target := _resolve_within(
                                handoff_root, entry.get("targetFile")
                            )
                        )
                        is not None
                        and target.is_file()
                        and entry.get("sha256") == _sha256(target)
                        for entry in entries
                    )
                    and all(
                        implementation_snapshot.get(field) == row.get(field)
                        for field in ("pageId", "stateId", "variantId")
                    )
                )
                if not entries_valid:
                    issues.append(
                        _issue(
                            "QA_STRUCTURAL_IMPLEMENTATION_SNAPSHOT_MISMATCH",
                            str(runner_relative),
                            "implementation snapshot must hash every approved implementation targetFile",
                            qaId=qa_id,
                        )
                    )
                def normalized_mappings(value: object) -> list[str] | None:
                    if not isinstance(value, list) or not all(
                        isinstance(item, dict) for item in value
                    ):
                        return None
                    return [
                        json.dumps(
                            item,
                            ensure_ascii=False,
                            sort_keys=True,
                            separators=(",", ":"),
                            allow_nan=False,
                        )
                        for item in value
                    ]

                snapshot_regions = normalized_mappings(
                    implementation_snapshot.get("regionMappings")
                )
                snapshot_components = normalized_mappings(
                    implementation_snapshot.get("componentMappings")
                )
                approved_regions = normalized_mappings(mapping.get("regionMappings"))
                approved_components = normalized_mappings(
                    mapping.get("componentMappings")
                )
                mappings_valid = (
                    snapshot_regions is not None
                    and snapshot_components is not None
                    and approved_regions is not None
                    and approved_components is not None
                    and len(snapshot_regions) == len(set(snapshot_regions))
                    and set(snapshot_regions) == set(approved_regions)
                    and len(snapshot_components) == len(set(snapshot_components))
                    and set(snapshot_components) == set(approved_components)
                    and (not component_absence_gaps or not snapshot_components)
                )
                if not mappings_valid:
                    issues.append(
                        _issue(
                            "QA_STRUCTURAL_IMPLEMENTATION_MAPPING_MISMATCH",
                            str(runner_relative),
                            "implementation snapshot mappings must uniquely equal every approved region/component mapping",
                            qaId=qa_id,
                        )
                    )
            runner_requirement_ids = requirement_ids_by_identity.get(identity, set())
            requirement_mappings = runner.get("requirementMappings")
            requirement_coverage_valid = (
                _unique_nonempty_strings(requirement_mappings)
                and set(requirement_mappings) == runner_requirement_ids
            )
            if not requirement_coverage_valid:
                issues.append(
                    _issue(
                        "QA_STRUCTURAL_REQUIREMENT_COVERAGE_MISMATCH",
                        str(runner_relative),
                        "runner requirementMappings must uniquely and exactly cover target ledger requirements",
                        qaId=qa_id,
                    )
                )

            def assertion_entity(assertion: dict) -> tuple | None:
                check_type = assertion.get("checkType")
                if check_type == "requirement-map":
                    value = assertion.get("requirementId")
                    return (check_type, value) if _nonplaceholder_text(value) else None
                if check_type == "region-map":
                    value = assertion.get("regionId")
                    return (check_type, value) if _nonplaceholder_text(value) else None
                if check_type == "component-map":
                    values = (
                        assertion.get("instanceId"), assertion.get("componentId")
                    )
                    return (
                        (check_type, *values)
                        if all(_nonplaceholder_text(value) for value in values)
                        else None
                    )
                if check_type == "absence-check":
                    values = (assertion.get("field"), assertion.get("gapId"))
                    return (
                        (check_type, *values)
                        if all(_nonplaceholder_text(value) for value in values)
                        else None
                    )
                return None

            expected_assertions = {
                *(
                    ("requirement-map", requirement_id)
                    for requirement_id in runner_requirement_ids
                ),
                *(("region-map", region_id) for region_id in page_region_ids),
                *(
                    ("component-map", instance_id, component_id)
                    for instance_id, component_id, _region_id in expected_components
                ),
            }
            if component_absence_gaps:
                expected_assertions |= {
                    ("absence-check", "components", gap_id)
                    for gap_id in component_absence_gaps
                }
            actual_assertions = [
                assertion_entity(assertion) for assertion in runner_assertions
            ]
            absence_assertions_valid = all(
                assertion.get("actualInstanceIds") == []
                and assertion.get("actualComponentIds") == []
                for assertion in runner_assertions
                if assertion.get("checkType") == "absence-check"
                and assertion.get("field") == "components"
            )
            runner_assertions_valid = (
                all(entity is not None for entity in actual_assertions)
                and len(actual_assertions) == len(set(actual_assertions))
                and set(actual_assertions) == expected_assertions
                and absence_assertions_valid
            )
            if not runner_assertions_valid:
                issues.append(
                    _issue(
                        "QA_STRUCTURAL_RUNNER_ASSERTIONS_INVALID",
                        str(runner_relative),
                        "structural assertions must uniquely and exactly cover every required mapping entity and approved absence",
                        qaId=qa_id,
                    )
                )

        if runner is not None and row.get("evidenceType") == "interaction":
            runner_artifacts = runner.get("artifacts") or {}
            interaction_result, _result_path = _load_hashed_json_artifact(
                handoff_root,
                runner_artifacts.get("interactionResult"),
                str(runner_relative),
                qa_id,
                "interactionResult",
                issues,
            )
            test_cases = runner.get("testCases")
            page_interaction_ids = {
                interaction.get("interactionId")
                for interaction in page.get("interactions", [])
                if isinstance(interaction, dict)
            }
            interaction_absence_gaps = _resolved_absence_gap_ids(
                page, "interactions", gap_rows
            )
            cases_valid = isinstance(test_cases, list) and (
                bool(test_cases) or bool(interaction_absence_gaps)
            )
            covered_ids = set()
            case_ids = []
            for index, test_case in enumerate(test_cases or []):
                if not isinstance(test_case, dict):
                    cases_valid = False
                    continue
                test_case_id = test_case.get("testCaseId")
                interaction_id = test_case.get("interactionId")
                case_ids.append(test_case_id)
                if _nonplaceholder_text(interaction_id):
                    covered_ids.add(interaction_id)
                else:
                    cases_valid = False
                assertions = test_case.get("assertions")
                if test_case.get("status") != "pass":
                    cases_valid = False
                if not isinstance(assertions, list) or not assertions:
                    cases_valid = False
                    issues.append(
                        _issue(
                            "QA_INTERACTION_CASE_ASSERTIONS_REQUIRED",
                            f"{runner_relative}#/testCases/{index}",
                            "interaction test case assertions must be nonempty",
                            qaId=qa_id,
                        )
                    )
                elif any(
                    not isinstance(assertion, dict)
                    or assertion.get("status") != "pass"
                    for assertion in assertions
                ):
                    cases_valid = False
                    issues.append(
                        _issue(
                            "QA_INTERACTION_CASE_ASSERTION_NOT_PASSED",
                            f"{runner_relative}#/testCases/{index}",
                            "every interaction case assertion must pass",
                            qaId=qa_id,
                        )
                    )
            if (
                covered_ids != page_interaction_ids
                or not _unique_nonempty_strings(case_ids)
                or len(test_cases or []) != len(page_interaction_ids)
            ):
                cases_valid = False
            expected_interaction_assertions = (
                {
                    ("absence-check", "interactions", gap_id)
                    for gap_id in interaction_absence_gaps
                }
                if interaction_absence_gaps
                else {
                    ("interaction-case", interaction_id)
                    for interaction_id in page_interaction_ids
                }
            )
            actual_interaction_assertions = [
                (
                    assertion.get("checkType"),
                    assertion.get("field"),
                    assertion.get("gapId"),
                )
                if assertion.get("checkType") == "absence-check"
                and _nonplaceholder_text(assertion.get("field"))
                and _nonplaceholder_text(assertion.get("gapId"))
                else (
                    assertion.get("checkType"),
                    assertion.get("interactionId"),
                )
                if assertion.get("checkType") == "interaction-case"
                and _nonplaceholder_text(assertion.get("interactionId"))
                else None
                for assertion in runner_assertions
            ]
            absence_assertions_valid = all(
                assertion.get("actualInteractionIds") == []
                and assertion.get("actualCaseCount") == 0
                for assertion in runner_assertions
                if assertion.get("checkType") == "absence-check"
                and assertion.get("field") == "interactions"
            )
            if (
                any(assertion is None for assertion in actual_interaction_assertions)
                or len(actual_interaction_assertions)
                != len(set(actual_interaction_assertions))
                or set(actual_interaction_assertions)
                != expected_interaction_assertions
                or not absence_assertions_valid
            ):
                cases_valid = False
            if not cases_valid:
                issues.append(
                    _issue(
                        "QA_INTERACTION_TEST_CASES_INVALID",
                        str(runner_relative),
                        "interaction runner must exactly cover page interactions, or prove a resolved interaction absence",
                        qaId=qa_id,
                    )
                )
            if interaction_result is not None:
                result_matches = (
                    all(
                        interaction_result.get(field) == row.get(field)
                        for field in ("pageId", "stateId", "variantId")
                    )
                    and interaction_result.get("testCases") == test_cases
                )
                if not result_matches:
                    issues.append(
                        _issue(
                            "QA_INTERACTION_RESULT_MISMATCH",
                            str(runner_relative),
                            "hashed interaction result must match runner identity and test cases",
                            qaId=qa_id,
                        )
                    )

        if row.get("evidenceType") == "structural":
            page_region_ids = {
                region.get("regionId")
                for region in page.get("regions", [])
                if isinstance(region, dict) and region.get("regionId")
            }
            page_components = {
                (component.get("instanceId"), component.get("componentId"))
                for component in page.get("components", [])
                if isinstance(component, dict)
            }
            component_absence_gaps = _resolved_absence_gap_ids(
                page, "components", gap_rows
            )
            expected_checks = {
                *(
                    ("requirement-map", requirement_id)
                    for requirement_id in requirement_ids_by_identity.get(identity, set())
                ),
                *(("region-map", region_id) for region_id in page_region_ids),
                *(
                    ("component-map", instance_id, component_id)
                    for instance_id, component_id in page_components
                ),
            }
            if component_absence_gaps:
                expected_checks |= {
                    ("absence-check", "components", gap_id)
                    for gap_id in component_absence_gaps
                }

            def check_entity(check: dict) -> tuple | None:
                check_type = check.get("checkType")
                if check_type == "requirement-map":
                    value = check.get("requirementId")
                    return (check_type, value) if _nonplaceholder_text(value) else None
                if check_type == "region-map":
                    value = check.get("regionId")
                    return (check_type, value) if _nonplaceholder_text(value) else None
                if check_type == "component-map":
                    values = (check.get("instanceId"), check.get("componentId"))
                    return (
                        (check_type, *values)
                        if all(_nonplaceholder_text(value) for value in values)
                        else None
                    )
                if check_type == "absence-check":
                    values = (check.get("field"), check.get("gapId"))
                    return (
                        (check_type, *values)
                        if all(_nonplaceholder_text(value) for value in values)
                        else None
                    )
                return None

            actual_checks = [
                check_entity(check) for check in checks if isinstance(check, dict)
            ]
            for check in checks:
                if not isinstance(check, dict):
                    continue
                if (
                    check.get("checkType") == "requirement-map"
                    and check.get("requirementId")
                    not in requirement_ids_by_identity.get(identity, set())
                ):
                    issues.append(
                        _issue(
                            "QA_STRUCTURAL_REQUIREMENT_NOT_FOUND",
                            record_relative,
                            "structural requirementId does not resolve for the target",
                            qaId=qa_id,
                        )
                    )
                elif (
                    check.get("checkType") == "region-map"
                    and check.get("regionId") not in page_region_ids
                ):
                    issues.append(
                        _issue(
                            "QA_STRUCTURAL_REGION_NOT_FOUND",
                            record_relative,
                            "structural regionId does not resolve for the target",
                            qaId=qa_id,
                        )
                    )
                elif check.get("checkType") == "component-map":
                    component = (
                        check.get("instanceId"),
                        check.get("componentId"),
                    )
                    if component not in page_components or component[1] not in registry_ids:
                        issues.append(
                            _issue(
                                "QA_STRUCTURAL_COMPONENT_NOT_FOUND",
                                record_relative,
                                "structural instance/component IDs must resolve in the page and registry",
                                qaId=qa_id,
                            )
                        )
            checks_valid = (
                len(actual_checks) == len(checks)
                and all(entity is not None for entity in actual_checks)
                and len(actual_checks) == len(set(actual_checks))
                and set(actual_checks) == expected_checks
                and all(component_id in registry_ids for _, component_id in page_components)
                and all(
                    check.get("actualInstanceIds") == []
                    and check.get("actualComponentIds") == []
                    for check in checks
                    if isinstance(check, dict)
                    and check.get("checkType") == "absence-check"
                    and check.get("field") == "components"
                )
            )
            if not checks_valid:
                issues.append(
                    _issue(
                        "QA_STRUCTURAL_CHECK_COVERAGE_MISSING",
                        record_relative,
                        "structural evidence checks must uniquely and exactly cover every requirement, region, component, and approved absence",
                        qaId=qa_id,
                    )
                )
        elif row.get("evidenceType") == "interaction":
            page_interaction_ids = {
                interaction.get("interactionId")
                for interaction in page.get("interactions", [])
                if isinstance(interaction, dict)
            }
            interaction_absence_gaps = _resolved_absence_gap_ids(
                page, "interactions", gap_rows
            )
            expected_checks = (
                {
                    ("absence-check", "interactions", gap_id)
                    for gap_id in interaction_absence_gaps
                }
                if interaction_absence_gaps
                else {
                    ("interaction-case", interaction_id)
                    for interaction_id in page_interaction_ids
                }
            )
            actual_checks = []
            for check in checks:
                if not isinstance(check, dict):
                    actual_checks.append(None)
                elif check.get("checkType") == "interaction-case":
                    value = check.get("interactionId")
                    actual_checks.append(
                        ("interaction-case", value)
                        if _nonplaceholder_text(value)
                        else None
                    )
                elif check.get("checkType") == "absence-check":
                    values = (check.get("field"), check.get("gapId"))
                    actual_checks.append(
                        ("absence-check", *values)
                        if all(_nonplaceholder_text(value) for value in values)
                        else None
                    )
                else:
                    actual_checks.append(None)
            if (
                any(check is None for check in actual_checks)
                or len(actual_checks) != len(set(actual_checks))
                or set(actual_checks) != expected_checks
                or not all(
                    check.get("actualInteractionIds") == []
                    and check.get("actualCaseCount") == 0
                    for check in checks
                    if isinstance(check, dict)
                    and check.get("checkType") == "absence-check"
                    and check.get("field") == "interactions"
                )
            ):
                issues.append(
                    _issue(
                        "QA_INTERACTION_CHECK_REQUIRED",
                        record_relative,
                        "interaction evidence must exactly cover interactions or a resolved absence",
                        qaId=qa_id,
                    )
                )
            for check in checks:
                if (
                    isinstance(check, dict)
                    and check.get("checkType") == "interaction-case"
                    and check.get("interactionId") not in page_interaction_ids
                ):
                    issues.append(
                        _issue(
                            "QA_INTERACTION_NOT_FOUND",
                            record_relative,
                            "interactionId does not resolve for the target page",
                            qaId=qa_id,
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
                elif str(gap.get("status", "")).lower() in RESOLVED_GAP_STATUSES:
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
    immutable_listed_paths = []
    legacy_validation_report_ignored = False
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
        if relative_path == "reports/validation-report.json":
            legacy_validation_report_ignored = True
            continue
        immutable_listed_paths.append(relative_path)
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
    if set(immutable_listed_paths) != expected_locked_paths:
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
    if legacy_validation_report_ignored:
        result["legacyValidationReportIgnored"] = True
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


class UnsafeValidationReportLayoutError(OSError):
    pass


def _is_link_or_reparse_point(path: Path) -> bool:
    try:
        metadata = os.lstat(path)
    except FileNotFoundError:
        return False
    return stat.S_ISLNK(metadata.st_mode) or bool(
        getattr(metadata, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    )


def _safe_validation_report_paths(handoff_root: Path) -> tuple[Path, Path, Path]:
    try:
        canonical_root = handoff_root.resolve(strict=True)
    except OSError as error:
        raise UnsafeValidationReportLayoutError(
            "canonical handoff root is unavailable"
        ) from error
    reports_root = handoff_root / "reports"
    if _is_link_or_reparse_point(reports_root):
        raise UnsafeValidationReportLayoutError(
            "reports directory is a link or reparse point"
        )
    try:
        canonical_reports_root = reports_root.resolve(strict=True)
    except OSError as error:
        raise UnsafeValidationReportLayoutError(
            "reports directory is unavailable"
        ) from error
    if not canonical_reports_root.is_dir():
        raise UnsafeValidationReportLayoutError(
            "reports path is not a directory"
        )
    try:
        relative_reports_root = canonical_reports_root.relative_to(canonical_root)
    except ValueError as error:
        raise UnsafeValidationReportLayoutError(
            "reports directory escapes the canonical handoff root"
        ) from error
    if relative_reports_root != Path("reports"):
        raise UnsafeValidationReportLayoutError(
            "reports directory is not the canonical package reports directory"
        )
    report_path = reports_root / "validation-report.json"
    if _is_link_or_reparse_point(report_path):
        raise UnsafeValidationReportLayoutError(
            "validation report is a link or reparse point"
        )
    if os.path.lexists(report_path) and not report_path.is_file():
        raise UnsafeValidationReportLayoutError(
            "validation report path is not a regular file"
        )
    return reports_root, canonical_reports_root, report_path


def _write_validation_report_atomic(handoff_root: Path, report: dict) -> None:
    reports_root, canonical_reports_root, report_path = (
        _safe_validation_report_paths(handoff_root)
    )
    descriptor = -1
    temporary_path = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".validation-report-", suffix=".tmp", dir=reports_root
        )
        temporary_path = Path(temporary_name)
        if (
            _is_link_or_reparse_point(temporary_path)
            or temporary_path.resolve(strict=True).parent != canonical_reports_root
        ):
            raise UnsafeValidationReportLayoutError(
                "temporary validation report escapes the canonical reports directory"
            )
        rechecked_reports_root, rechecked_canonical_root, rechecked_report_path = (
            _safe_validation_report_paths(handoff_root)
        )
        if (
            rechecked_reports_root != reports_root
            or rechecked_canonical_root != canonical_reports_root
            or rechecked_report_path != report_path
        ):
            raise UnsafeValidationReportLayoutError(
                "validation report layout changed during persistence"
            )
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            descriptor = -1
            stream.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        rechecked_reports_root, rechecked_canonical_root, rechecked_report_path = (
            _safe_validation_report_paths(handoff_root)
        )
        if (
            rechecked_reports_root != reports_root
            or rechecked_canonical_root != canonical_reports_root
            or rechecked_report_path != report_path
            or temporary_path.resolve(strict=True).parent != canonical_reports_root
        ):
            raise UnsafeValidationReportLayoutError(
                "validation report layout changed during persistence"
            )
        os.replace(temporary_path, report_path)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary_path is not None and os.path.lexists(temporary_path):
            try:
                temporary_parent = temporary_path.resolve(strict=True).parent
            except OSError:
                temporary_parent = None
            if (
                temporary_parent == canonical_reports_root
                and not _is_link_or_reparse_point(temporary_path)
            ):
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

    if source_root is None:
        issues.append(
            _issue(
                "SOURCE_VERIFICATION_REQUIRED",
                "contracts/asset-manifest.json",
                "source_root is required to verify source integrity and readiness",
            )
        )

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
            for relative_path in SCHEMA_CONTRACTS:
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
            _check_page_documents(handoff_root, documents, issues)
            _check_bilingual(handoff_root, issues)
            _check_capture_profiles(documents, issues)
            _check_diff_and_qa(documents, qa_rows, identities, issues)
            gap_rows = csv_documents.get("contracts/gap-register.csv")
            _check_qa_evidence_records(
                handoff_root,
                documents,
                qa_rows,
                csv_documents.get("contracts/requirement-ledger.csv"),
                gap_rows,
                issues,
            )
            _check_semantic_readiness(documents, gap_rows, issues)
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
        except UnsafeValidationReportLayoutError as error:
            issues.append(
                _issue(
                    "VALIDATION_REPORT_UNSAFE_LAYOUT",
                    "reports/validation-report.json",
                    f"refused unsafe validation report layout: {error}",
                )
            )
            result["issues"] = _deduplicate_and_sort(issues)
            result["status"] = "failed"
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
