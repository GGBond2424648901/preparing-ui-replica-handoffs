import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import types
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = (
    REPOSITORY_ROOT
    / "skill"
    / "preparing-ui-replica-handoffs"
    / "scripts"
    / "check_bilingual_parity.py"
)


def _load_parity_module():
    module = types.ModuleType("check_bilingual_parity")
    module.__file__ = str(SCRIPT_PATH)
    exec(compile(SCRIPT_PATH.read_bytes(), str(SCRIPT_PATH), "exec"), module.__dict__)
    return module


def _write_markdown(
    path,
    *,
    template_id=None,
    rules=(),
    sections=(),
    placeholders=(),
    images=(),
    prose="",
):
    lines = []
    if template_id is not None:
        lines.extend(("---", f"templateId: {template_id}", "---", ""))
    lines.append("# Document")
    if prose:
        lines.append(prose)
    for rule_id in rules:
        lines.append(f"ruleId: {rule_id}")
    for section_id in sections:
        lines.append(f"sectionId: {section_id}")
    for placeholder in placeholders:
        lines.append(f"{{{{{placeholder}}}}}")
    for image in images:
        lines.append(f"![design]({image})")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


class BilingualParityTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)

    def make_valid_pair(self):
        _write_markdown(
            self.root / "assets/templates/docs/zh/guide.template.md",
            template_id="guide",
            rules=("R-1",),
            sections=("authority",),
            placeholders=("authorityOrder",),
            images=("../../assets/P001.png",),
            prose="中文说明保留视觉证据。",
        )
        _write_markdown(
            self.root / "assets/templates/docs/en/guide.template.md",
            template_id="guide",
            rules=("R-1",),
            sections=("authority",),
            placeholders=("authorityOrder",),
            images=("../../assets/P001.png",),
            prose="English guidance preserves visible evidence.",
        )
        _write_markdown(
            self.root / "docs/zh/pages/P001-S01-V01-unclassified.md",
            sections=("identity",),
        )
        _write_markdown(
            self.root / "docs/en/pages/P001-S01-V01-unclassified.md",
            sections=("identity",),
        )

    def issue_codes(self):
        parity = _load_parity_module()
        return {issue["code"] for issue in parity.check_bilingual_parity(self.root)["issues"]}

    def test_accepts_paired_documents_with_different_translated_text(self):
        self.make_valid_pair()

        parity = _load_parity_module()
        result = parity.check_bilingual_parity(self.root)

        self.assertNotEqual(
            (self.root / "assets/templates/docs/zh/guide.template.md").read_text(
                encoding="utf-8"
            ),
            (self.root / "assets/templates/docs/en/guide.template.md").read_text(
                encoding="utf-8"
            ),
        )
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["issues"], [])

    def test_reports_missing_entire_language_directory_and_cli_failure(self):
        self.make_valid_pair()
        shutil.rmtree(self.root / "docs/en")

        completed = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--handoff-root", str(self.root)],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(
            "BILINGUAL_MISSING_LANGUAGE_DIRECTORY",
            {issue["code"] for issue in json.loads(completed.stdout)["issues"]},
        )

    def test_reports_missing_mirrored_file(self):
        self.make_valid_pair()
        (self.root / "assets/templates/docs/en/guide.template.md").unlink()

        self.assertIn("BILINGUAL_MISSING_MIRROR", self.issue_codes())

    def test_reports_mismatched_rule_and_section_ids(self):
        self.make_valid_pair()
        _write_markdown(
            self.root / "assets/templates/docs/en/guide.template.md",
            template_id="guide",
            rules=("R-2",),
            sections=("implementation",),
            placeholders=("authorityOrder",),
            images=("../../assets/P001.png",),
        )

        issue_codes = self.issue_codes()

        self.assertIn("BILINGUAL_RULE_ID_MISMATCH", issue_codes)
        self.assertIn("BILINGUAL_SECTION_ID_MISMATCH", issue_codes)

    def test_reports_mismatched_placeholders(self):
        self.make_valid_pair()
        _write_markdown(
            self.root / "assets/templates/docs/en/guide.template.md",
            template_id="guide",
            rules=("R-1",),
            sections=("authority",),
            placeholders=("implementationMapPath",),
            images=("../../assets/P001.png",),
        )

        self.assertIn("BILINGUAL_PLACEHOLDER_MISMATCH", self.issue_codes())

    def test_reports_missing_page_document(self):
        self.make_valid_pair()
        (self.root / "docs/en/pages/P001-S01-V01-unclassified.md").unlink()

        self.assertIn("BILINGUAL_MISSING_PAGE_DOCUMENT", self.issue_codes())

    def test_reports_one_sided_image_reference_and_cli_failure(self):
        self.make_valid_pair()
        _write_markdown(
            self.root / "assets/templates/docs/en/guide.template.md",
            template_id="guide",
            rules=("R-1",),
            sections=("authority",),
            placeholders=("authorityOrder",),
        )

        completed = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--skill-root", str(self.root)],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(
            "BILINGUAL_IMAGE_REFERENCE_MISMATCH",
            {issue["code"] for issue in json.loads(completed.stdout)["issues"]},
        )

    def test_rejects_unsafe_matching_image_targets(self):
        unsafe_targets = (
            r"C:\\handoff\\design.png",
            r"\\\\server\\share\\design.png",
            "/assets/design.png",
            "../../../../../outside.png",
            "file:///assets/design.png",
            "https://example.test/design.png",
            "custom-scheme:design.png",
        )
        for target in unsafe_targets:
            with self.subTest(target=target):
                self.make_valid_pair()
                for locale in ("zh", "en"):
                    _write_markdown(
                        self.root
                        / f"assets/templates/docs/{locale}/guide.template.md",
                        template_id="guide",
                        rules=("R-1",),
                        sections=("authority",),
                        placeholders=("authorityOrder",),
                        images=(target,),
                    )

                self.assertIn("BILINGUAL_INVALID_IMAGE_TARGET", self.issue_codes())


if __name__ == "__main__":
    unittest.main()
