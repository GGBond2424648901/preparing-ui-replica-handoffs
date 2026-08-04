from pathlib import Path
import re
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPOSITORY_ROOT / "skill" / "preparing-ui-replica-handoffs"


SCAFFOLD_ENTRY_CONTRACT = {
    ".": {
        "directories": {
            "required": {"agents", "assets", "references", "scripts"},
            "allowed": {"agents", "assets", "references", "scripts"},
        },
        "files": {"required": {"SKILL.md"}, "allowed": {"SKILL.md"}},
    },
    "agents": {
        "directories": {"required": set(), "allowed": set()},
        "files": {"required": {"openai.yaml"}, "allowed": {"openai.yaml"}},
    },
    "scripts": {
        "directories": {"required": set(), "allowed": set()},
        "files": {
            "required": {".gitkeep"},
            "allowed": {
                ".gitkeep",
                "build_contact_sheet.py",
                "check_bilingual_parity.py",
                "prepare_handoff.py",
                "validate_handoff.py",
            },
        },
    },
    "references": {
        "directories": {"required": {"en", "zh"}, "allowed": {"en", "zh"}},
        "files": {"required": set(), "allowed": set()},
    },
    "references/en": {
        "directories": {"required": set(), "allowed": set()},
        "files": {
            "required": {".gitkeep"},
            "allowed": {
                ".gitkeep",
                "component-and-style-contract.md",
                "delivery-package-spec.md",
                "intake-and-authority.md",
                "page-and-state-contract.md",
                "visual-qa-and-git-safety.md",
            },
        },
    },
    "references/zh": {
        "directories": {"required": set(), "allowed": set()},
        "files": {
            "required": {".gitkeep"},
            "allowed": {
                ".gitkeep",
                "component-and-style-contract.md",
                "delivery-package-spec.md",
                "intake-and-authority.md",
                "page-and-state-contract.md",
                "visual-qa-and-git-safety.md",
            },
        },
    },
    "assets": {
        "directories": {
            "required": {"schemas", "templates"},
            "allowed": {"schemas", "templates"},
        },
        "files": {"required": set(), "allowed": set()},
    },
    "assets/schemas": {
        "directories": {"required": set(), "allowed": set()},
        "files": {
            "required": {".gitkeep"},
            "allowed": {
                ".gitkeep",
                "asset-manifest.schema.json",
                "capture-profile.schema.json",
                "component-registry.schema.json",
                "design-lock.schema.json",
                "diff-regions.schema.json",
                "handoff-config.schema.json",
                "implementation-map.schema.json",
                "page-inventory.schema.json",
                "ui-style-contract.schema.json",
            },
        },
    },
    "assets/templates": {
        "directories": {"required": set(), "allowed": {"docs"}},
        "files": {
            "required": {".gitkeep"},
            "allowed": {
                ".gitkeep",
                "gap-register.template.csv",
                "handoff-config.template.json",
                "requirement-ledger.template.csv",
                "visual-qa-matrix.template.csv",
            },
        },
    },
}


class SkillScaffoldTests(unittest.TestCase):
    def test_scaffold_exposes_the_required_bilingual_skill_structure(self):
        for relative_directory, contract in SCAFFOLD_ENTRY_CONTRACT.items():
            directory = SKILL_ROOT / relative_directory
            entries = {entry.name: entry for entry in directory.iterdir()}

            for entry_type, predicate in (("directories", Path.is_dir), ("files", Path.is_file)):
                actual_entries = {
                    name for name, entry in entries.items() if predicate(entry)
                }
                expected_entries = contract[entry_type]

                self.assertSetEqual(
                    expected_entries["required"] - actual_entries,
                    set(),
                    f"{relative_directory} is missing required {entry_type}",
                )
                self.assertSetEqual(
                    actual_entries - expected_entries["allowed"],
                    set(),
                    f"{relative_directory} contains unapproved {entry_type}",
                )

            unclassified_entries = set(entries) - {
                name
                for entry_type in ("directories", "files")
                for name, entry in entries.items()
                if (Path.is_dir if entry_type == "directories" else Path.is_file)(entry)
            }
            self.assertSetEqual(
                unclassified_entries,
                set(),
                f"{relative_directory} contains entries that are neither files nor directories",
            )

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
