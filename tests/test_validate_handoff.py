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
from unittest import mock

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
    ignored = {
        "contracts/design-lock.json",
        "reports/contact-sheet.png",
        "reports/validation-report.json",
    }
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
    page_inventory_path = handoff / "contracts" / "page-inventory.json"
    page_inventory = _read_json(page_inventory_path)
    for number, page in enumerate(page_inventory["pages"], start=1):
        page["route"].update(
            {"path": f"/page-{number}", "evidenceLevel": "direct", "gapId": None}
        )
        page["shell"].update(
            {"shellId": "app-shell", "evidenceLevel": "direct", "gapId": None}
        )
        for region in page["regions"]:
            region.update({"role": "content", "evidenceLevel": "direct", "gapIds": []})
        for criterion in page["acceptanceCriteria"]:
            criterion["status"] = "pass"
        page.update({"status": "approved", "gapIds": []})
    _write_json(page_inventory_path, page_inventory)

    style_path = handoff / "contracts" / "ui-style-contract.json"
    style = _read_json(style_path)
    style.update({"evidenceLevel": "approved", "status": "approved", "gapIds": []})
    for variant in style["responsiveVariants"]:
        variant.update(
            {"evidenceLevel": "approved", "status": "approved", "gapIds": []}
        )
    _write_json(style_path, style)

    implementation_path = handoff / "contracts" / "implementation-map.json"
    implementation = _read_json(implementation_path)
    for number, mapping in enumerate(implementation["mappings"], start=1):
        target = f"src/pages/page-{number}.py"
        mapping.update(
            {
                "route": f"/page-{number}",
                "targetFiles": [target],
                "evidenceLevel": "approved",
                "status": "approved",
                "gapIds": [],
            }
        )
        for responsive in mapping["responsiveMappings"]:
            responsive.update(
                {
                    "targetFiles": [target],
                    "evidenceLevel": "approved",
                    "status": "approved",
                    "gapIds": [],
                }
            )
    _write_json(implementation_path, implementation)

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
    for row_number, row in enumerate(qa_rows, start=1):
        paths = {}
        for artifact_number, field in enumerate(
            ("referencePath", "currentPath", "overlayPath", "diffPath"), start=1
        ):
            relative_path = f"reports/qa/{row['qaId']}/{field[:-4]}.png"
            _write_image(
                handoff / relative_path,
                size=(16 + row_number, 12 + artifact_number),
                color=(row_number * 20 % 255, artifact_number * 40, 100),
            )
            paths[field] = relative_path
        row.update({**paths, "status": "pass"})
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
        persisted = _read_json(self.handoff / "reports" / "validation-report.json")
        self.assertEqual(persisted, result)

    def test_completed_package_report_rerun_is_stable(self):
        first = self.validate(source_root=self.source)
        report_path = self.handoff / "reports" / "validation-report.json"
        first_bytes = report_path.read_bytes()

        second = self.validate(source_root=self.source)

        self.assertEqual(first["status"], "passed")
        self.assertEqual(_read_json(report_path), second)
        self.assertEqual(second, first)
        self.assertEqual(report_path.read_bytes(), first_bytes)

    def test_untouched_generated_package_fails_and_replaces_not_run_report(self):
        raw_handoff = self.root / "raw-handoff"
        PREPARE.prepare_handoff(self.source, raw_handoff, "v1")
        validator = _load_module(VALIDATE_PATH, "validate_raw_handoff")

        result = validator.validate_handoff(raw_handoff, source_root=self.source)

        self.assertEqual(result["status"], "failed")
        self.assertNotIn("VALIDATION_NOT_RUN", self.codes(result))
        self.assertEqual(
            _read_json(raw_handoff / "reports" / "validation-report.json"), result
        )

    def test_reports_missing_required_file(self):
        (self.handoff / "README.md").unlink()
        _refresh_design_lock(self.handoff)

        result = self.validate()

        self.assertEqual(result["status"], "failed")
        self.assertIn("MISSING_REQUIRED_FILE", self.codes(result))

    def test_empty_package_contracts_and_top_level_docs_fail_closed(self):
        collections = (
            ("asset-manifest.json", "assets"),
            ("page-inventory.json", "pages"),
            ("capture-profile.json", "profiles"),
            ("implementation-map.json", "mappings"),
            ("diff-regions.json", "pages"),
        )
        for filename, key in collections:
            path = self.handoff / "contracts" / filename
            document = _read_json(path)
            document[key] = []
            _write_json(path, document)
        qa_path = self.handoff / "contracts" / "visual-qa-matrix.csv"
        qa_rows = _read_csv(qa_path)
        _write_csv(qa_path, [], list(qa_rows[0]))
        for relative_path in (
            "docs/zh/设计稿总目录.md",
            "docs/zh/UI实施说明.md",
            "docs/zh/组件规范.md",
            "docs/en/Design-Catalog.md",
            "docs/en/UI-Implementation-Guide.md",
            "docs/en/Component-Specification.md",
        ):
            (self.handoff / relative_path).unlink()
        _refresh_design_lock(self.handoff)

        codes = self.codes(self.validate())

        self.assertTrue(
            {
                "MISSING_REQUIRED_FILE",
                "EMPTY_ASSET_MANIFEST",
                "EMPTY_PAGE_INVENTORY",
                "EMPTY_CAPTURE_PROFILES",
                "EMPTY_IMPLEMENTATION_MAP",
                "EMPTY_DIFF_PAGES",
                "EMPTY_QA_MATRIX",
            }.issubset(codes),
            codes,
        )

    def test_reports_missing_implementation_mapping_for_page_identity(self):
        path = self.handoff / "contracts" / "implementation-map.json"
        implementation = _read_json(path)
        implementation["mappings"] = []
        _write_json(path, implementation)
        _refresh_design_lock(self.handoff)

        self.assertIn("MISSING_IMPLEMENTATION_MAPPING", self.codes(self.validate()))

    def test_reports_qa_capture_profile_that_does_not_exist(self):
        path = self.handoff / "contracts" / "visual-qa-matrix.csv"
        rows = _read_csv(path)
        rows[0]["captureProfileId"] = "capture-missing"
        _write_csv(path, rows, list(rows[0]))
        _refresh_design_lock(self.handoff)

        self.assertIn("QA_CAPTURE_PROFILE_MISSING", self.codes(self.validate()))

    def test_reports_diff_capture_profile_that_does_not_exist(self):
        path = self.handoff / "contracts" / "diff-regions.json"
        diff = _read_json(path)
        diff["pages"][0]["captureProfileId"] = "capture-missing"
        _write_json(path, diff)
        _refresh_design_lock(self.handoff)

        self.assertIn("DIFF_CAPTURE_PROFILE_MISSING", self.codes(self.validate()))

    def test_reports_qa_capture_profile_mismatch_with_diff_page(self):
        capture_path = self.handoff / "contracts" / "capture-profile.json"
        capture = _read_json(capture_path)
        other = dict(capture["profiles"][0])
        other["captureProfileId"] = "capture-other"
        capture["profiles"].append(other)
        _write_json(capture_path, capture)
        qa_path = self.handoff / "contracts" / "visual-qa-matrix.csv"
        rows = _read_csv(qa_path)
        rows[0]["captureProfileId"] = "capture-other"
        _write_csv(qa_path, rows, list(rows[0]))
        _refresh_design_lock(self.handoff)

        self.assertIn("QA_DIFF_CAPTURE_PROFILE_MISMATCH", self.codes(self.validate()))

    def test_reports_qa_region_missing_from_diff_page(self):
        path = self.handoff / "contracts" / "visual-qa-matrix.csv"
        rows = _read_csv(path)
        rows[0]["regionId"] = "region-missing"
        _write_csv(path, rows, list(rows[0]))
        _refresh_design_lock(self.handoff)

        self.assertIn("QA_REGION_MISSING", self.codes(self.validate()))

    def test_reports_qa_row_for_unknown_page_identity(self):
        path = self.handoff / "contracts" / "visual-qa-matrix.csv"
        rows = _read_csv(path)
        orphan = dict(rows[0])
        orphan.update({"qaId": "QA999", "pageId": "P999"})
        rows.append(orphan)
        _write_csv(path, rows, list(rows[0]))
        _refresh_design_lock(self.handoff)

        self.assertIn("QA_TARGET_IDENTITY_MISSING", self.codes(self.validate()))

    def test_reports_reused_qa_evidence_path(self):
        path = self.handoff / "contracts" / "visual-qa-matrix.csv"
        rows = _read_csv(path)
        rows[0]["currentPath"] = rows[0]["referencePath"]
        _write_csv(path, rows, list(rows[0]))
        _refresh_design_lock(self.handoff)

        self.assertIn("QA_EVIDENCE_PATH_REUSED", self.codes(self.validate()))

    def test_reports_distinct_qa_paths_with_reused_content_hash(self):
        path = self.handoff / "contracts" / "visual-qa-matrix.csv"
        rows = _read_csv(path)
        duplicate_path = "reports/qa/duplicate-current.png"
        source = self.handoff / rows[0]["referencePath"]
        duplicate = self.handoff / duplicate_path
        duplicate.parent.mkdir(parents=True, exist_ok=True)
        duplicate.write_bytes(source.read_bytes())
        rows[0]["currentPath"] = duplicate_path
        _write_csv(path, rows, list(rows[0]))
        _refresh_design_lock(self.handoff)

        self.assertIn("QA_EVIDENCE_HASH_REUSED", self.codes(self.validate()))

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

    def test_reports_supported_source_image_omitted_from_manifest(self):
        _write_image(self.source / "extra.png", color="orange")

        result = self.validate(source_root=self.source)

        self.assertIn("SOURCE_SET_COVERAGE_MISMATCH", self.codes(result))
        issue = next(
            issue
            for issue in result["issues"]
            if issue["code"] == "SOURCE_SET_COVERAGE_MISMATCH"
        )
        self.assertEqual(issue["missingFromManifest"], ["extra.png"])

    def test_reports_duplicate_manifest_asset_source_and_delivery_identities(self):
        path = self.handoff / "contracts" / "asset-manifest.json"
        manifest = _read_json(path)
        manifest["assets"].append(dict(manifest["assets"][0]))
        _write_json(path, manifest)
        _refresh_design_lock(self.handoff)

        codes = self.codes(self.validate(source_root=self.source))

        self.assertTrue(
            {
                "DUPLICATE_ASSET_ID",
                "DUPLICATE_SOURCE_RELATIVE_PATH",
                "DUPLICATE_DELIVERY_RELATIVE_PATH",
            }.issubset(codes),
            codes,
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
        inventory["pages"][0]["route"]["evidenceLevel"] = "unknown"
        inventory["pages"][0]["route"]["gapId"] = None
        _write_json(path, inventory)
        _refresh_design_lock(self.handoff)

        self.assertIn("UNKNOWN_WITHOUT_GAP_ID", self.codes(self.validate()))

    def test_reports_unknown_state_with_missing_gap_reference(self):
        path = self.handoff / "contracts" / "page-inventory.json"
        inventory = _read_json(path)
        inventory["pages"][0]["route"].update(
            {"evidenceLevel": "unknown", "gapId": "G999"}
        )
        _write_json(path, inventory)
        _refresh_design_lock(self.handoff)

        self.assertIn("GAP_ID_NOT_FOUND", self.codes(self.validate()))

    def test_reports_unknown_state_linked_to_resolved_gap(self):
        path = self.handoff / "contracts" / "page-inventory.json"
        inventory = _read_json(path)
        inventory["pages"][0]["route"].update(
            {"evidenceLevel": "unknown", "gapId": "G001"}
        )
        _write_json(path, inventory)
        _refresh_design_lock(self.handoff)

        self.assertIn(
            "UNKNOWN_REFERENCES_RESOLVED_GAP", self.codes(self.validate())
        )

    def test_reports_missing_gap_reference_from_requirement_ledger(self):
        path = self.handoff / "contracts" / "requirement-ledger.csv"
        rows = _read_csv(path)
        rows[0].update(
            {"evidenceLevel": "unknown", "status": "proposed", "gapId": "G999"}
        )
        _write_csv(path, rows, list(rows[0]))
        _refresh_design_lock(self.handoff)

        self.assertIn("GAP_ID_NOT_FOUND", self.codes(self.validate()))

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

    def test_git_probe_launch_error_is_reported_as_skipped(self):
        validator = _load_module(VALIDATE_PATH, "validate_git_probe_error")

        with mock.patch.object(
            validator.subprocess, "run", side_effect=OSError("git unavailable")
        ):
            result = validator.validate_handoff(
                self.handoff,
                repo_root=self.root,
                allowed_git_prefix="allowed",
            )

        self.assertEqual(result["checks"]["git"]["status"], "skipped")
        self.assertEqual(result["checks"]["git"]["reason"], "git-unavailable")

    def test_git_staged_query_launch_error_returns_stable_failed_report(self):
        validator = _load_module(VALIDATE_PATH, "validate_git_staged_error")
        repository_probe = subprocess.CompletedProcess(
            args=["git"], returncode=0, stdout="true\n", stderr=""
        )

        with mock.patch.object(
            validator.subprocess,
            "run",
            side_effect=(repository_probe, OSError("git disappeared")),
        ):
            result = validator.validate_handoff(
                self.handoff,
                repo_root=self.root,
                allowed_git_prefix="allowed",
            )

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["checks"]["git"]["status"], "failed")
        self.assertIn("GIT_STATUS_FAILED", self.codes(result))
        self.assertEqual(
            _read_json(self.handoff / "reports" / "validation-report.json"), result
        )

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
