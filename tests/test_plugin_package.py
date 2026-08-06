import hashlib
import json
from pathlib import Path
import re
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_SKILL = REPOSITORY_ROOT / "skill" / "preparing-ui-replica-handoffs"
PLUGIN_ROOT = REPOSITORY_ROOT / "plugin" / "preparing-ui-replica-handoffs"
PLUGIN_SKILL = PLUGIN_ROOT / "skills" / "preparing-ui-replica-handoffs"


def _files(root: Path) -> dict[str, str]:
    result = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            result[path.relative_to(root).as_posix()] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
    return result


class PluginPackageTests(unittest.TestCase):
    def test_manifest_declares_one_embedded_skill_and_bilingual_interface(self):
        manifest = json.loads(
            (PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(manifest["name"], "preparing-ui-replica-handoffs")
        self.assertRegex(manifest["version"], r"^\d+\.\d+\.\d+(?:\+codex\.\d+)?$")
        self.assertEqual(manifest["skills"], "./skills/")
        self.assertIn("中文", manifest["description"])
        self.assertIn("English", manifest["description"])
        self.assertEqual(
            manifest["interface"]["displayName"],
            "UI 复刻交付准备 / UI Replica Handoff Prep",
        )
        self.assertIn("中文", manifest["interface"]["shortDescription"])
        self.assertIn("English", manifest["interface"]["shortDescription"])
        self.assertGreaterEqual(len(manifest["interface"]["defaultPrompt"]), 2)
        self.assertTrue(
            any("$preparing-ui-replica-handoffs" in prompt for prompt in manifest["interface"]["defaultPrompt"])
        )

        forbidden = {"mcpServers", "apps", "hooks"}
        self.assertSetEqual(forbidden & set(manifest), set())

    def test_embedded_skill_is_byte_identical_to_repository_skill(self):
        self.assertDictEqual(_files(SOURCE_SKILL), _files(PLUGIN_SKILL))

    def test_plugin_contains_no_capability_directories_outside_the_skill(self):
        allowed = {".codex-plugin", "skills"}
        actual = {path.name for path in PLUGIN_ROOT.iterdir() if path.is_dir()}
        self.assertSetEqual(actual, allowed)


if __name__ == "__main__":
    unittest.main()
