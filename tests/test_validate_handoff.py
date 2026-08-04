import csv
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest

from PIL import Image


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = (
    REPOSITORY_ROOT / "skill" / "preparing-ui-replica-handoffs" / "scripts"
)
PREPARE_PATH = SCRIPTS_ROOT / "prepare_handoff.py"
VALIDATE_PATH = SCRIPTS_ROOT / "validate_handoff.py"


def _load_module(path, name):
    module = types.ModuleType(name)
    module.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), "exec"), module.__dict__)
    return module


PREPARE = _load_module(PREPARE_PATH, "prepare_handoff_for_validation_tests")


def _write_image(path, size=(18, 12), color="navy", image_format="PNG"):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path, format=image_format)


def _read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path, document):
    path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _read_csv(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _write_csv(path, rows, fieldnames):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _record_set_hash(records):
    digest = hashlib.sha256()
    for relative_path, file_hash in records:
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_hash.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def _refresh_design_lock(handoff):
    lock_path = handoff / "contracts" / "design-lock.json"
    lock = _read_json(lock_path)
    ignored = {"contracts/design-lock.json", "reports/contact-sheet.png"}
    files = [
        {
            "relativePath": path.relative_to(handoff).as_posix(),
            "sha256": _sha256(path),
        }
        for path in sorted(handoff.rglob("*"))
        if path.is_file() and path.relative_to(handoff).as_posix() not in ignored
    ]
    contract_records = [
        (entry["relativePath"], entry["sha256"])
        for entry in files
        if entry["relativePath"].startswith("contracts/")
    ]
    lock["files"] = files
    lock["contractsHash"] = _record_set_hash(contract_records)
    _write_json(lock_path, lock)


def _resolve_generated_skeleton(handoff):
    manifest = _read_json(handoff / "contracts" / "asset-manifest.json")
    page_inventory_path = handoff / "contracts" / "page-inventory.json"
    page_inventory = _read_json(page_inventory_path)
    for page in page_inventory["pages"]:
        for criterion in page["acceptanceCriteria"]:
            criterion["status"] = "pass"
    _write_json(page_inventory_path, page_inventory)

    capture_path = handoff / "contracts" / "capture-profile.json"
    capture = _read_json(capture_path)
    for profile in capture["profiles"]:
        profile.update(
            {
                "browser": "Chromium",
                "browserVersion": "120",
                "locale": "en-US",
                "timezone": "UTC",
                "theme": "light",
                "fontEnvironment": ["Arial"],
                "evidenceLevel": "approved",
                "gapIds": [],
            }
        )
    _write_json(capture_path, capture)

    diff_path = handoff / "contracts" / "diff-regions.json"
    diff = _read_json(diff_path)
    for page in diff["pages"]:
        for region in page["regions"]:
            region["status"] = "pass"
    _write_json(diff_path, diff)

    qa_path = handoff / "contracts" / "visual-qa-matrix.csv"
    qa_rows = _read_csv(qa_path)
    delivery_by_page = {
        f"P{number:03d}": asset["deliveryRelativePath"]
        for number, asset in enumerate(manifest["assets"], start=1)
    }
    for row in qa_rows:
        evidence = delivery_by_page[row["pageId"]]
        row.update(
            {
                "referencePath": evidence,
                "currentPath": evidence,
                "overlayPath": evidence,
                "diffPath": evidence,
                "status": "pass",
            }
        )
    _write_csv(qa_path, qa_rows, list(qa_rows[0]))

    gap_path = handoff / "contracts" / "gap-register.csv"
    gap_rows = _read_csv(gap_path)
    for row in gap_rows:
        row["status"] = "resolved"
        row["resolution"] = "Evidence reviewed for validation fixture"
    _write_csv(gap_path, gap_rows, list(gap_rows[0]))

    _write_image(handoff / "reports" / "contact-sheet.png", (64, 32), "white")
    _refresh_design_lock(handoff)


class ValidateHandoffTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)
        self.source = self.root / "source"
        self.handoff = self.root / "allowed" / "handoff"
        _write_image(self.source / "screen.png")
        PREPARE.prepare_handoff(self.source, self.handoff, "v1")
        _resolve_generated_skeleton(self.handoff)

    def validate(self, **kwargs):
        validator = _load_module(VALIDATE_PATH, "validate_handoff")
        return validator.validate_handoff(self.handoff, **kwargs)

    def codes(self, result):
        return {issue["code"] for issue in result["issues"]}

    def test_accepts_complete_package_and_exposes_computed_lock_material(self):
        result = self.validate(source_root=self.source)

        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["issues"], [])
        lock = _read_json(self.handoff / "contracts" / "design-lock.json")
        self.assertEqual(
            result["designLock"]["computedContractsHash"], lock["contractsHash"]
        )
        self.assertEqual(result["designLock"]["computedFileCount"], len(lock["files"]))

    def test_reports_missing_required_file(self):
        (self.handoff / "README.md").unlink()
        _refresh_design_lock(self.handoff)

        result = self.validate()

        self.assertEqual(result["status"], "failed")
        self.assertIn("MISSING_REQUIRED_FILE", self.codes(result))

    def test_reports_malformed_json(self):
        (self.handoff / "contracts" / "page-inventory.json").write_text(
            "{not-json", encoding="utf-8"
        )
        _refresh_design_lock(self.handoff)

        self.assertIn("MALFORMED_JSON", self.codes(self.validate()))

    def test_reports_malformed_csv(self):
        (self.handoff / "contracts" / "visual-qa-matrix.csv").write_text(
            'qaId,pageId\n"unterminated', encoding="utf-8"
        )
        _refresh_design_lock(self.handoff)

        self.assertIn("MALFORMED_CSV", self.codes(self.validate()))

    def test_reports_source_hash_drift(self):
        _write_image(self.source / "screen.png", color="red")

        self.assertIn(
            "SOURCE_HASH_MISMATCH",
            self.codes(self.validate(source_root=self.source)),
        )

    def test_reports_delivery_copy_hash_drift(self):
        manifest = _read_json(self.handoff / "contracts" / "asset-manifest.json")
        copy = self.handoff / manifest["assets"][0]["deliveryRelativePath"]
        _write_image(copy, color="green")

        self.assertIn("COPY_HASH_MISMATCH", self.codes(self.validate()))

    def test_reports_duplicate_page_state_variant_identity(self):
        path = self.handoff / "contracts" / "page-inventory.json"
        inventory = _read_json(path)
        inventory["pages"].append(dict(inventory["pages"][0]))
        _write_json(path, inventory)
        _refresh_design_lock(self.handoff)

        self.assertIn("DUPLICATE_TARGET_IDENTITY", self.codes(self.validate()))

    def test_reports_absolute_path_leak(self):
        path = self.handoff / "contracts" / "visual-qa-matrix.csv"
        rows = _read_csv(path)
        rows[0]["currentPath"] = r"C:\captures\current.png"
        _write_csv(path, rows, list(rows[0]))
        _refresh_design_lock(self.handoff)

        self.assertIn("ABSOLUTE_PATH", self.codes(self.validate()))

    def test_reports_absolute_target_file_in_machine_contract(self):
        path = self.handoff / "contracts" / "implementation-map.json"
        implementation_map = _read_json(path)
        implementation_map["mappings"][0]["targetFiles"] = [r"C:\app\page.py"]
        _write_json(path, implementation_map)
        _refresh_design_lock(self.handoff)

        self.assertIn("ABSOLUTE_PATH", self.codes(self.validate()))

    def test_reports_broken_relative_markdown_link(self):
        for locale in ("zh", "en"):
            page = next((self.handoff / "docs" / locale / "pages").glob("*.md"))
            text = page.read_text(encoding="utf-8")
            text = text.replace("../../../assets/", "../../../missing-assets/")
            page.write_text(text, encoding="utf-8")
        _refresh_design_lock(self.handoff)

        self.assertIn("BROKEN_RELATIVE_LINK", self.codes(self.validate()))

    def test_reports_missing_page_document(self):
        next((self.handoff / "docs" / "en" / "pages").glob("*.md")).unlink()
        _refresh_design_lock(self.handoff)

        self.assertIn("MISSING_PAGE_DOCUMENT", self.codes(self.validate()))

    def test_reports_unknown_state_without_gap_id(self):
        path = self.handoff / "contracts" / "page-inventory.json"
        inventory = _read_json(path)
        inventory["pages"][0]["route"]["gapId"] = None
        _write_json(path, inventory)
        _refresh_design_lock(self.handoff)

        self.assertIn("UNKNOWN_WITHOUT_GAP_ID", self.codes(self.validate()))

    def test_preserves_bilingual_parity_issue_codes(self):
        page = next((self.handoff / "docs" / "en" / "pages").glob("*.md"))
        text = page.read_text(encoding="utf-8")
        page.write_text(
            text.replace("sectionId: identity", "sectionId: changed-identity"),
            encoding="utf-8",
        )
        _refresh_design_lock(self.handoff)

        self.assertIn("BILINGUAL_SECTION_ID_MISMATCH", self.codes(self.validate()))

    def test_reports_incomplete_capture_profile(self):
        path = self.handoff / "contracts" / "capture-profile.json"
        capture = _read_json(path)
        capture["profiles"][0]["browser"] = "unclassified"
        _write_json(path, capture)
        _refresh_design_lock(self.handoff)

        self.assertIn("INCOMPLETE_CAPTURE_PROFILE", self.codes(self.validate()))

    def test_reports_missing_diff_coverage(self):
        path = self.handoff / "contracts" / "diff-regions.json"
        diff = _read_json(path)
        diff["pages"].clear()
        _write_json(path, diff)
        _refresh_design_lock(self.handoff)

        self.assertIn("MISSING_DIFF_COVERAGE", self.codes(self.validate()))

    def test_reports_missing_visual_structural_or_interaction_qa_coverage(self):
        path = self.handoff / "contracts" / "visual-qa-matrix.csv"
        rows = [row for row in _read_csv(path) if row["evidenceType"] != "interaction"]
        _write_csv(path, rows, list(rows[0]))
        _refresh_design_lock(self.handoff)

        self.assertIn("MISSING_QA_COVERAGE", self.codes(self.validate()))

    def test_reports_open_blocker_and_major_gaps(self):
        path = self.handoff / "contracts" / "gap-register.csv"
        rows = _read_csv(path)
        rows[0]["status"] = "open"
        rows[0]["severity"] = "blocker"
        rows[1]["status"] = "open"
        rows[1]["severity"] = "major"
        _write_csv(path, rows, list(rows[0]))
        _refresh_design_lock(self.handoff)

        codes = self.codes(self.validate())

        self.assertIn("OPEN_BLOCKER_GAP", codes)
        self.assertIn("OPEN_MAJOR_GAP", codes)

    def test_reports_design_lock_hash_and_contract_material_drift(self):
        readme = self.handoff / "README.md"
        readme.write_text(readme.read_text(encoding="utf-8") + "drift\n", encoding="utf-8")
        lock_path = self.handoff / "contracts" / "design-lock.json"
        lock = _read_json(lock_path)
        lock["contractsHash"] = "0" * 64
        _write_json(lock_path, lock)

        codes = self.codes(self.validate())

        self.assertIn("DESIGN_LOCK_FILE_HASH_MISMATCH", codes)
        self.assertIn("DESIGN_LOCK_CONTRACTS_HASH_MISMATCH", codes)

    def test_git_check_is_skipped_without_repository_and_does_not_initialize_one(self):
        repo = self.root / "not-a-repository"
        repo.mkdir()

        result = self.validate(repo_root=repo, allowed_git_prefix="allowed")

        self.assertEqual(result["checks"]["git"]["status"], "skipped")
        self.assertFalse((repo / ".git").exists())

    def test_reports_staged_file_outside_optional_git_allowlist(self):
        subprocess.run(["git", "init"], cwd=self.root, check=True, capture_output=True)
        outside = self.root / "outside.txt"
        outside.write_text("outside\n", encoding="utf-8")
        subprocess.run(
            ["git", "add", "outside.txt"], cwd=self.root, check=True, capture_output=True
        )

        result = self.validate(repo_root=self.root, allowed_git_prefix="allowed")

        self.assertIn("GIT_STAGED_PATH_OUTSIDE_ALLOWLIST", self.codes(result))
        self.assertIn("outside.txt", result["checks"]["git"]["stagedPaths"])

    def test_cli_emits_json_and_returns_nonzero_on_errors(self):
        (self.handoff / "README.md").unlink()
        completed = subprocess.run(
            [sys.executable, str(VALIDATE_PATH), "--handoff-root", str(self.handoff)],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(json.loads(completed.stdout)["status"], "failed")


if __name__ == "__main__":
    unittest.main()
