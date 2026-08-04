import hashlib
import json
from pathlib import Path
import re
import tempfile
import types
import unittest

from PIL import Image


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = (
    REPOSITORY_ROOT / "skill" / "preparing-ui-replica-handoffs" / "scripts"
)
PREPARE_PATH = SCRIPTS_ROOT / "prepare_handoff.py"
CONTACT_SHEET_PATH = SCRIPTS_ROOT / "build_contact_sheet.py"


def _load_module(path, name):
    module = types.ModuleType(name)
    module.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), "exec"), module.__dict__)
    return module


PREPARE = _load_module(PREPARE_PATH, "prepare_handoff_for_contact_sheet_tests")


def _write_image(path, size, color, image_format):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path, format=image_format)


def _file_hashes(root):
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


class ContactSheetTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)
        self.source = self.root / "source"
        self.handoff = self.root / "handoff"
        _write_image(self.source / "z-last.png", (24, 12), "red", "PNG")
        _write_image(
            self.source / "nested" / "a-first.jpg",
            (10, 20),
            "blue",
            "JPEG",
        )
        PREPARE.prepare_handoff(self.source, self.handoff, "v1")

    def test_builds_png_from_manifest_package_paths_without_changing_inputs(self):
        contact_sheet = _load_module(CONTACT_SHEET_PATH, "build_contact_sheet")
        output = self.handoff / "reports" / "contact-sheet.png"
        source_before = _file_hashes(self.source)
        package_before = _file_hashes(self.handoff)

        result = contact_sheet.build_contact_sheet(self.handoff, output)

        self.assertEqual(result["status"], "created")
        self.assertEqual(result["assetCount"], 2)
        self.assertEqual(result["outputPath"], "reports/contact-sheet.png")
        self.assertTrue(output.is_file())
        with Image.open(output) as rendered:
            self.assertEqual(rendered.format, "PNG")
            self.assertGreater(rendered.width, 0)
            self.assertGreater(rendered.height, 0)
        self.assertEqual(_file_hashes(self.source), source_before)
        package_after = _file_hashes(self.handoff)
        package_after.pop("reports/contact-sheet.png")
        self.assertEqual(package_after, package_before)

    def test_emits_stable_id_dimension_and_filename_labels(self):
        contact_sheet = _load_module(CONTACT_SHEET_PATH, "build_contact_sheet")
        first = self.handoff / "reports" / "first.png"
        second = self.handoff / "reports" / "second.png"

        first_result = contact_sheet.build_contact_sheet(self.handoff, first)
        second_result = contact_sheet.build_contact_sheet(self.handoff, second)

        self.assertEqual(
            first_result["labels"],
            [
                "A001 | 10x20 | P001-S01-V01-unclassified.jpg",
                "A002 | 24x12 | P002-S01-V01-unclassified.png",
            ],
        )
        self.assertEqual(first_result["labels"], second_result["labels"])
        self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_rejects_nonfinite_numbers_in_manifest_json(self):
        contact_sheet = _load_module(CONTACT_SHEET_PATH, "build_contact_sheet_strict")
        manifest_path = self.handoff / "contracts" / "asset-manifest.json"
        original = manifest_path.read_text(encoding="utf-8")
        for index, constant in enumerate(("NaN", "Infinity", "-Infinity"), start=1):
            with self.subTest(constant=constant):
                output = self.handoff / "reports" / f"nonfinite-{index}.png"
                manifest_path.write_text(
                    original.replace('"byteSize": 633', f'"byteSize": {constant}')
                    if '"byteSize": 633' in original
                    else re.sub(
                        r'"byteSize":\s*[0-9]+',
                        f'"byteSize": {constant}',
                        original,
                        count=1,
                    ),
                    encoding="utf-8",
                )

                with self.assertRaisesRegex(ValueError, "non-finite JSON"):
                    contact_sheet.build_contact_sheet(self.handoff, output)

                self.assertFalse(output.exists())

    def test_rejects_output_that_already_exists_or_aliases_an_input(self):
        contact_sheet = _load_module(CONTACT_SHEET_PATH, "build_contact_sheet")
        manifest_path = self.handoff / "contracts" / "asset-manifest.json"
        manifest_before = manifest_path.read_bytes()
        manifest = json.loads(manifest_before)
        delivery = self.handoff / manifest["assets"][0]["deliveryRelativePath"]
        delivery_before = delivery.read_bytes()
        existing = self.handoff / "reports" / "existing.png"
        existing.parent.mkdir(parents=True, exist_ok=True)
        existing.write_bytes(b"owner data")

        for output, original in (
            (manifest_path, manifest_before),
            (delivery, delivery_before),
            (existing, b"owner data"),
        ):
            with self.subTest(output=output.relative_to(self.handoff)):
                try:
                    with self.assertRaises(FileExistsError):
                        contact_sheet.build_contact_sheet(self.handoff, output)
                finally:
                    output.write_bytes(original)

        self.assertEqual(manifest_path.read_bytes(), manifest_before)
        self.assertEqual(delivery.read_bytes(), delivery_before)
        self.assertEqual(existing.read_bytes(), b"owner data")


if __name__ == "__main__":
    unittest.main()
