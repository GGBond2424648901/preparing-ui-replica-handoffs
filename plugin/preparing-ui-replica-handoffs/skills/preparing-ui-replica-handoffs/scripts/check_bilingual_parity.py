"""Check structural parity between Chinese and English Markdown handoff files."""

import argparse
import json
from pathlib import Path
import re


IMAGE_SUFFIXES = {".avif", ".gif", ".jpeg", ".jpg", ".png", ".svg", ".webp"}
PAGE_ID_PATTERN = re.compile(r"P\d{3,}-S\d{2,}-V\d{2,}")
TEMPLATE_ID_PATTERN = re.compile(r"^templateId:\s*(\S+)\s*$", re.MULTILINE)
RULE_ID_PATTERN = re.compile(r"^ruleId:\s*(\S+)\s*$", re.MULTILINE)
SECTION_ID_PATTERN = re.compile(r"^sectionId:\s*(\S+)\s*$", re.MULTILINE)
PLACEHOLDER_PATTERN = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}")
LINK_PATTERN = re.compile(r"!?\[[^\]]*\]\(\s*<?([^\s>)]+)>?")
URI_SCHEME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
WINDOWS_ABSOLUTE_PATTERN = re.compile(r"^[A-Za-z]:[\\/]|^\\\\")

HANDOFF_DOCUMENT_KEYS = {
    "设计稿总目录.md": "handoff:design-catalog",
    "Design-Catalog.md": "handoff:design-catalog",
    "UI实施说明.md": "handoff:ui-implementation-guide",
    "UI-Implementation-Guide.md": "handoff:ui-implementation-guide",
    "组件规范.md": "handoff:component-specification",
    "Component-Specification.md": "handoff:component-specification",
}


def _issue(code: str, scope: str, key: str, **details: object) -> dict:
    return {"code": code, "scope": scope, "key": key, **details}


def _document_key(path: Path, relative_path: Path, text: str) -> str:
    template_id = TEMPLATE_ID_PATTERN.search(text)
    if template_id:
        return f"template:{template_id.group(1)}"
    page_id = PAGE_ID_PATTERN.search(path.name)
    if page_id:
        return f"page:{page_id.group(0)}"
    return HANDOFF_DOCUMENT_KEYS.get(path.name, f"path:{relative_path.as_posix()}")


def _image_references(text: str) -> set[str]:
    references = set()
    for match in LINK_PATTERN.finditer(text):
        destination = match.group(1).split("#", 1)[0].split("?", 1)[0]
        if Path(destination).suffix.lower() in IMAGE_SUFFIXES:
            references.add(destination)
    return references


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _invalid_image_references(root: Path, path: Path, references: set[str]) -> set[str]:
    invalid = set()
    for reference in references:
        if (
            reference.startswith(("/", "\\"))
            or WINDOWS_ABSOLUTE_PATTERN.match(reference)
            or URI_SCHEME_PATTERN.match(reference)
        ):
            invalid.add(reference)
            continue
        if not _is_within((path.parent / reference).resolve(), root):
            invalid.add(reference)
    return invalid


def _document_details(path: Path, relative_path: Path, root: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    images = _image_references(text)
    return {
        "path": path,
        "key": _document_key(path, relative_path, text),
        "ruleIds": set(RULE_ID_PATTERN.findall(text)),
        "sectionIds": set(SECTION_ID_PATTERN.findall(text)),
        "placeholders": set(PLACEHOLDER_PATTERN.findall(text)),
        "images": images,
        "invalidImages": _invalid_image_references(root, path, images),
    }


def _documents(directory: Path, root: Path) -> dict[str, dict]:
    documents = {}
    for path in sorted(directory.rglob("*.md")):
        if not path.is_file():
            continue
        document = _document_details(path, path.relative_to(directory), root)
        documents.setdefault(document["key"], document)
    return documents


def _language_scopes(root: Path) -> list[tuple[Path, Path]]:
    parents = set()
    for locale in ("zh", "en"):
        parents.update(
            directory.parent
            for directory in root.rglob(locale)
            if directory.is_dir()
        )
    return [
        (parent / "zh", parent / "en")
        for parent in sorted(parents, key=lambda path: path.as_posix())
    ]


def _compare_pair(scope: str, key: str, zh_document: dict, en_document: dict) -> list[dict]:
    issues = []
    for field, code in (
        ("ruleIds", "BILINGUAL_RULE_ID_MISMATCH"),
        ("sectionIds", "BILINGUAL_SECTION_ID_MISMATCH"),
        ("placeholders", "BILINGUAL_PLACEHOLDER_MISMATCH"),
        ("images", "BILINGUAL_IMAGE_REFERENCE_MISMATCH"),
    ):
        zh_values = sorted(zh_document[field])
        en_values = sorted(en_document[field])
        if zh_values != en_values:
            issues.append(
                _issue(code, scope, key, zhValues=zh_values, enValues=en_values)
            )
    return issues


def check_bilingual_parity(root: Path) -> dict:
    """Return a JSON-serializable bilingual parity report for ``root``.

    Parity means mirrored document coverage and matching machine-readable IDs,
    placeholders, and image references. It deliberately does not compare prose.
    """

    root = Path(root)
    resolved_root = root.resolve()
    issues = []
    for zh_directory, en_directory in _language_scopes(root):
        scope = zh_directory.parent.relative_to(root).as_posix() or "."
        if not zh_directory.is_dir() or not en_directory.is_dir():
            issues.append(
                _issue(
                    "BILINGUAL_MISSING_LANGUAGE_DIRECTORY",
                    scope,
                    "locale-directory",
                    missingLocale="zh-CN" if not zh_directory.is_dir() else "en-US",
                )
            )
            continue
        zh_documents = _documents(zh_directory, resolved_root)
        en_documents = _documents(en_directory, resolved_root)
        for locale, documents in (("zh-CN", zh_documents), ("en-US", en_documents)):
            for document in documents.values():
                if document["invalidImages"]:
                    issues.append(
                        _issue(
                            "BILINGUAL_INVALID_IMAGE_TARGET",
                            scope,
                            document["key"],
                            locale=locale,
                            invalidTargets=sorted(document["invalidImages"]),
                        )
                    )
        for key in sorted(set(zh_documents) | set(en_documents)):
            zh_document = zh_documents.get(key)
            en_document = en_documents.get(key)
            if zh_document is None or en_document is None:
                code = (
                    "BILINGUAL_MISSING_PAGE_DOCUMENT"
                    if key.startswith("page:")
                    else "BILINGUAL_MISSING_MIRROR"
                )
                issues.append(
                    _issue(
                        code,
                        scope,
                        key,
                        missingLocale="zh-CN" if zh_document is None else "en-US",
                    )
                )
                continue
            issues.extend(_compare_pair(scope, key, zh_document, en_document))
    issues.sort(key=lambda issue: (issue["code"], issue["scope"], issue["key"]))
    return {"status": "passed" if not issues else "failed", "issues": issues}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check Chinese/English handoff Markdown parity."
    )
    parser.add_argument("root", nargs="?", type=Path)
    root_group = parser.add_mutually_exclusive_group()
    root_group.add_argument("--skill-root", type=Path)
    root_group.add_argument("--handoff-root", type=Path)
    arguments = parser.parse_args(argv)
    roots = [root for root in (arguments.root, arguments.skill_root, arguments.handoff_root) if root]
    if len(roots) != 1:
        parser.error("provide exactly one root path")
    result = check_bilingual_parity(roots[0])
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
