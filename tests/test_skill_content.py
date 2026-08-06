from pathlib import Path
import re
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPOSITORY_ROOT / "skill" / "preparing-ui-replica-handoffs"
REFERENCE_NAMES = (
    "intake-and-authority.md",
    "page-and-state-contract.md",
    "component-and-style-contract.md",
    "visual-qa-and-git-safety.md",
    "delivery-package-spec.md",
)
RULE_PATTERN = re.compile(r"^ruleId:\s*(\S+)\s*$", re.MULTILINE)
SECTION_PATTERN = re.compile(r"^sectionId:\s*(\S+)\s*$", re.MULTILINE)


class SkillContentTests(unittest.TestCase):
    def test_skill_routes_every_operating_stage_to_a_mirrored_reference(self):
        content = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")

        for reference_name in REFERENCE_NAMES:
            self.assertIn(f"references/zh/{reference_name}", content)
            self.assertIn(f"references/en/{reference_name}", content)

        self.assertIn("prepare_handoff.py", content)
        self.assertIn("build_contact_sheet.py", content)
        self.assertIn("check_bilingual_parity.py", content)
        self.assertIn("validate_handoff.py", content)

    def test_skill_keeps_the_canonical_package_shape_at_the_entry_point(self):
        content = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")

        for path in (
            "assets/designs/<design-version>/",
            "docs/zh/",
            "docs/en/",
            "contracts/requirement-ledger.csv",
            "contracts/gap-register.csv",
            "contracts/asset-manifest.json",
            "contracts/page-inventory.json",
            "contracts/ui-style-contract.json",
            "contracts/component-registry.json",
            "contracts/implementation-map.json",
            "contracts/capture-profile.json",
            "contracts/diff-regions.json",
            "contracts/visual-qa-matrix.csv",
            "contracts/design-lock.json",
            "reports/contact-sheet.png",
            "reports/validation-report.json",
            "tools/validate-command.txt",
        ):
            self.assertIn(path, content)

        for alien in (".design-replica/", "schema-v4", "capture-jobs.json"):
            self.assertNotIn(alien, content)

        self.assertIn("only before freezing", content)
        self.assertIn("冻结前", content)
        self.assertIn("immutable", content)

    def test_skill_is_independent_and_forbids_source_and_git_mutation(self):
        content = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")

        required_literals = (
            "self-contained",
            "design-image-to-web-replica",
            "never modify the original design directory",
            "do not initialize, stage, commit, push, or create a worktree",
            "fail closed",
            "relative paths",
            "Chinese and English",
            "Omitting `--source-root` is an error",
            "validated evidence records",
            "replayable interaction cases",
        )
        for literal in required_literals:
            self.assertIn(literal, content)

    def test_reference_pairs_have_matching_nonempty_rule_and_section_ids(self):
        for reference_name in REFERENCE_NAMES:
            zh = (SKILL_ROOT / "references" / "zh" / reference_name).read_text(
                encoding="utf-8"
            )
            en = (SKILL_ROOT / "references" / "en" / reference_name).read_text(
                encoding="utf-8"
            )

            zh_rules = set(RULE_PATTERN.findall(zh))
            en_rules = set(RULE_PATTERN.findall(en))
            zh_sections = set(SECTION_PATTERN.findall(zh))
            en_sections = set(SECTION_PATTERN.findall(en))

            self.assertTrue(zh_rules, reference_name)
            self.assertTrue(zh_sections, reference_name)
            self.assertSetEqual(zh_rules, en_rules, reference_name)
            self.assertSetEqual(zh_sections, en_sections, reference_name)

    def test_references_cover_the_nonnegotiable_handoff_rules(self):
        zh = "\n".join(
            (SKILL_ROOT / "references" / "zh" / name).read_text(encoding="utf-8")
            for name in REFERENCE_NAMES
        )
        en = "\n".join(
            (SKILL_ROOT / "references" / "en" / name).read_text(encoding="utf-8")
            for name in REFERENCE_NAMES
        )

        shared_tokens = (
            "direct",
            "derived",
            "candidate",
            "approved",
            "unknown",
            "inferred",
            "sample",
            "pageId + stateId + variantId",
            "reference/current/overlay/diff",
            "blocker",
            "major",
            "gapId",
        )
        for token in shared_tokens:
            self.assertIn(token, zh)
            self.assertIn(token, en)

        for literal in (
            "用户最新明确修正",
            "水平滚动",
            "结构验收",
            "视觉验收",
            "交互验收",
            "相对路径",
            "推断文案",
            "机器可读 evidence record",
            "[absence:<field>]",
        ):
            self.assertIn(literal, zh)

        for literal in (
            "latest explicit user correction",
            "horizontal scrolling",
            "structural acceptance",
            "visual acceptance",
            "interaction acceptance",
            "relative paths",
            "inferred copy",
            "machine-readable evidence record",
            "[absence:<field>]",
            "hashed runner result",
            "never executes untrusted commands",
            "contractHash: sha256:<hex>",
            "exact-set validation",
        ):
            self.assertIn(literal, en)


if __name__ == "__main__":
    unittest.main()
