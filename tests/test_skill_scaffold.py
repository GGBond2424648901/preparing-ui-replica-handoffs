from pathlib import Path
import re
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPOSITORY_ROOT / "skill" / "preparing-ui-replica-handoffs"


class SkillScaffoldTests(unittest.TestCase):
    def test_scaffold_exposes_the_required_bilingual_skill_structure(self):
        required_directories = {
            "scripts",
            "references",
            "references/zh",
            "references/en",
            "assets",
            "assets/schemas",
            "assets/templates",
        }

        missing = sorted(
            directory
            for directory in required_directories
            if not (SKILL_ROOT / directory).is_dir()
        )

        self.assertEqual(missing, [])

    def test_skill_and_agent_metadata_expose_the_required_contract(self):
        skill_content = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        frontmatter = re.match(r"^---\n(.*?)\n---", skill_content, re.DOTALL)

        self.assertIsNotNone(frontmatter)
        frontmatter_keys = [
            line.partition(":")[0]
            for line in frontmatter.group(1).splitlines()
            if line and not line.startswith((" ", "\t"))
        ]
        self.assertEqual(frontmatter_keys, ["name", "description"])
        self.assertIn("name: preparing-ui-replica-handoffs", frontmatter.group(1))

        agent_content = (SKILL_ROOT / "agents" / "openai.yaml").read_text(
            encoding="utf-8"
        )
        self.assertIn("interface:", agent_content)
        self.assertIn(
            'display_name: "UI 复刻交付准备 / UI Replica Handoff Prep"', agent_content
        )
        self.assertIn(
            'short_description: "中英双语 UI 复刻交付准备 / Bilingual UI handoff preparation"',
            agent_content,
        )
        self.assertIn("default_prompt:", agent_content)
        self.assertIn("$preparing-ui-replica-handoffs", agent_content)


if __name__ == "__main__":
    unittest.main()
