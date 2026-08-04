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


def _document_details(path: Path, relative_path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    return {
        "path": path,
        "key": _document_key(path, relative_path, text),
        "ruleIds": set(RULE_ID_PATTERN.findall(text)),
        "sectionIds": set(SECTION_ID_PATTERN.findall(text)),
        "placeholders": set(PLACEHOLDER_PATTERN.findall(text)),
        "images": _image_references(text),
    }


def _documents(directory: Path) -> dict[str, dict]:
    documents = {}
    for path in sorted(directory.rglob("*.md")):
        if not path.is_file():
            continue
        document = _document_details(path, path.relative_to(directory))
        documents.setdefault(document["key"], document)
    return documents


def _language_scopes(root: Path) -> list[tuple[Path, Path]]:
    scopes = []
    for zh_directory in root.rglob("zh"):
        if not zh_directory.is_dir():
            continue
        en_directory = zh_directory.with_name("en")
        if en_directory.is_dir():
            scopes.append((zh_directory, en_directory))
    return sorted(scopes, key=lambda scope: scope[0].as_posix())


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
    issues = []
    for zh_directory, en_directory in _language_scopes(root):
        scope = zh_directory.parent.relative_to(root).as_posix() or "."
        zh_documents = _documents(zh_directory)
        en_documents = _documents(en_directory)
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
