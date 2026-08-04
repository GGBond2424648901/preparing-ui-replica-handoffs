import csv
import ctypes
import errno
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

from jsonschema import Draft202012Validator
from PIL import Image


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = (
    REPOSITORY_ROOT
    / "skill"
    / "preparing-ui-replica-handoffs"
    / "scripts"
    / "prepare_handoff.py"
)
SCHEMA_ROOT = (
    REPOSITORY_ROOT
    / "skill"
    / "preparing-ui-replica-handoffs"
    / "assets"
    / "schemas"
)


class _FakeCFunction:
    def __init__(self, result=0, error_number=0):
        self.result = result
        self.error_number = error_number
        self.calls = []
        self.argtypes = None
        self.restype = None

    def __call__(self, *arguments):
        self.calls.append(arguments)
        ctypes.set_errno(self.error_number)
        return self.result


POSIX_CHILD_EMPTY_DIRECTORY_RACE = r"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types

jsonschema = types.ModuleType("jsonschema")
jsonschema.Draft202012Validator = object
jsonschema.FormatChecker = object
sys.modules["jsonschema"] = jsonschema
pil = types.ModuleType("PIL")
pil.Image = object
pil.UnidentifiedImageError = ValueError
sys.modules["PIL"] = pil

script_path = Path(sys.argv[1])
module = types.ModuleType("prepare_handoff_posix_race")
module.__file__ = str(script_path)
exec(compile(script_path.read_bytes(), str(script_path), "exec"), module.__dict__)

with tempfile.TemporaryDirectory() as temporary_directory:
    root = Path(temporary_directory)
    output = root / "public-package"
    recovery = root / "public-package.recovery"
    output.mkdir()
    recovery.mkdir()
    (output / "owner.txt").write_text("public package", encoding="utf-8")

    collision_token = "a" * 32
    successful_token = "b" * 32
    collision_package = recovery / f"quarantine-{collision_token}" / "package"
    successful_package = recovery / f"quarantine-{successful_token}" / "package"
    trigger = root / "trigger"
    ready = root / "ready"
    child_code = (
        "import os, pathlib, sys, time; "
        "target=pathlib.Path(sys.argv[1]); "
        "trigger=pathlib.Path(sys.argv[2]); "
        "ready=pathlib.Path(sys.argv[3]); "
        "\nwhile not trigger.exists(): time.sleep(0.001); "
        "\nos.mkdir(target); ready.write_text('ready')"
    )
    child = subprocess.Popen(
        [sys.executable, "-B", "-c", child_code, str(collision_package), str(trigger), str(ready)]
    )

    real_atomic_move = module._atomic_no_replace_directory_move
    first_call = True

    def race_with_child(source, destination):
        global first_call
        if first_call:
            first_call = False
            trigger.write_text("go", encoding="utf-8")
            child.wait(timeout=10)
            if child.returncode != 0 or not ready.is_file():
                raise RuntimeError("POSIX race child failed")
        return real_atomic_move(source, destination)

    tokens = iter((collision_token, successful_token))
    module._atomic_no_replace_directory_move = race_with_child
    module.secrets.token_hex = lambda _size: next(tokens)
    moved = module._move_to_unique_quarantine(output, recovery)

    assert moved == successful_package, moved
    assert collision_package.is_dir()
    assert list(collision_package.iterdir()) == []
    assert not output.exists()
    assert (successful_package / "owner.txt").read_text(encoding="utf-8") == "public package"

print("POSIX child empty-directory race: passed")
"""

PREPARE_HANDOFF = types.ModuleType("prepare_handoff")
PREPARE_HANDOFF.__file__ = str(SCRIPT_PATH)
exec(
    compile(SCRIPT_PATH.read_bytes(), str(SCRIPT_PATH), "exec"),
    PREPARE_HANDOFF.__dict__,
)


def _write_image(path, size, color, image_format):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path, format=image_format)


def _source_set_hash(records):
    digest = hashlib.sha256()
    for relative_path, file_hash in records:
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_hash.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def _file_bytes(root):
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _quarantined_packages(recovery_root):
    return sorted(
        reservation / "package"
        for reservation in recovery_root.iterdir()
        if reservation.is_dir()
        and not reservation.is_symlink()
        and (
            reservation / "package" / "contracts" / "design-lock.json"
        ).is_file()
    )


def _create_directory_link(link, target):
    try:
        link.symlink_to(target, target_is_directory=True)
        return "symlink"
    except OSError as error:
        if os.name != "nt" or getattr(error, "winerror", None) != 1314:
            raise
    subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link), str(target)],
        check=True,
        capture_output=True,
        text=True,
    )
    return "junction"


def _write_json(path, document):
    path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _hash_records(records):
    digest = hashlib.sha256()
    for relative_path, file_hash in records:
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_hash.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


class PrepareHandoffTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)
        self.source = self.root / "design-source"
        self.source.mkdir()

    def make_three_image_source(self):
        duplicate = self.source / "A" / "duplicate.PNG"
        original = self.source / "b" / "原始 页面.png"
        jpeg = self.source / "z final.JPEG"
        _write_image(original, (2, 3), (10, 20, 30), "PNG")
        duplicate.parent.mkdir(parents=True)
        duplicate.write_bytes(original.read_bytes())
        _write_image(jpeg, (4, 2), (80, 90, 100), "JPEG")
        (self.source / "notes.txt").write_text("not an image", encoding="utf-8")
        return duplicate, original, jpeg

    def test_windows_atomic_no_replace_move_uses_os_rename(self):
        source = self.root / "windows-source"
        destination = self.root / "windows-destination"
        collision = FileExistsError(errno.EEXIST, "destination exists")

        with mock.patch.object(PREPARE_HANDOFF.os, "name", "nt"), mock.patch.object(
            PREPARE_HANDOFF.os, "rename", side_effect=collision
        ) as rename:
            with self.assertRaises(FileExistsError) as error:
                PREPARE_HANDOFF._atomic_no_replace_directory_move(
                    source, destination
                )

        self.assertIs(error.exception, collision)
        rename.assert_called_once_with(source, destination)

    def test_linux_atomic_no_replace_move_uses_renameat2_noreplace(self):
        source = self.root / "linux-source"
        destination = self.root / "linux-destination"
        renameat2 = _FakeCFunction(result=-1, error_number=errno.EEXIST)
        library = types.SimpleNamespace(renameat2=renameat2)

        with mock.patch.object(PREPARE_HANDOFF.os, "name", "posix"), mock.patch.object(
            PREPARE_HANDOFF.sys, "platform", "linux"
        ), mock.patch.object(PREPARE_HANDOFF.ctypes, "CDLL", return_value=library):
            with self.assertRaises(FileExistsError) as error:
                PREPARE_HANDOFF._atomic_no_replace_directory_move(
                    source, destination
                )

        self.assertEqual(error.exception.errno, errno.EEXIST)
        self.assertEqual(
            renameat2.calls,
            [
                (
                    PREPARE_HANDOFF.AT_FDCWD_LINUX,
                    os.fsencode(source),
                    PREPARE_HANDOFF.AT_FDCWD_LINUX,
                    os.fsencode(destination),
                    PREPARE_HANDOFF.RENAME_NOREPLACE,
                )
            ],
        )

    def test_bsd_atomic_no_replace_move_uses_renamex_np_excl(self):
        source = self.root / "bsd-source"
        destination = self.root / "bsd-destination"
        renamex_np = _FakeCFunction()
        library = types.SimpleNamespace(renamex_np=renamex_np)

        with mock.patch.object(PREPARE_HANDOFF.os, "name", "posix"), mock.patch.object(
            PREPARE_HANDOFF.sys, "platform", "darwin"
        ), mock.patch.object(PREPARE_HANDOFF.ctypes, "CDLL", return_value=library):
            PREPARE_HANDOFF._atomic_no_replace_directory_move(source, destination)

        self.assertEqual(
            renamex_np.calls,
            [
                (
                    os.fsencode(source),
                    os.fsencode(destination),
                    PREPARE_HANDOFF.RENAME_EXCL,
                )
            ],
        )

    def test_unsupported_platform_never_falls_back_to_ordinary_rename(self):
        source = self.root / "unsupported-source"
        destination = self.root / "unsupported-destination"

        with mock.patch.object(PREPARE_HANDOFF.os, "name", "posix"), mock.patch.object(
            PREPARE_HANDOFF.sys, "platform", "sunos5"
        ), mock.patch.object(PREPARE_HANDOFF.os, "rename") as ordinary_rename:
            with self.assertRaisesRegex(RuntimeError, "atomic.*no-replace|unsupported"):
                PREPARE_HANDOFF._atomic_no_replace_directory_move(
                    source, destination
                )

        ordinary_rename.assert_not_called()

    def test_preflight_cleanup_never_deletes_a_raced_in_empty_directory(self):
        replacement = {}

        def collide_after_replacing_source(source, destination):
            source.rmdir()
            source.mkdir()
            replacement["path"] = source
            replacement["identity"] = (source.stat().st_dev, source.stat().st_ino)
            raise FileExistsError(errno.EEXIST, "destination exists")

        with mock.patch.object(
            PREPARE_HANDOFF,
            "_atomic_no_replace_directory_move",
            side_effect=collide_after_replacing_source,
        ):
            PREPARE_HANDOFF._preflight_atomic_no_replace_directory_move(self.root)

        raced_path = replacement["path"]
        self.assertTrue(raced_path.is_dir())
        self.assertEqual(
            (raced_path.stat().st_dev, raced_path.stat().st_ino),
            replacement["identity"],
        )

    def test_publication_uses_real_atomic_moves_without_a_probe_or_path_rename(self):
        image = self.source / "screen.png"
        output = self.root / "atomic-publication"
        _write_image(image, (2, 2), (10, 20, 30), "PNG")
        real_atomic_move = PREPARE_HANDOFF._atomic_no_replace_directory_move

        with mock.patch.object(
            PREPARE_HANDOFF,
            "_preflight_atomic_no_replace_directory_move",
            side_effect=AssertionError("standalone probe must not run"),
        ) as preflight, mock.patch.object(
            PREPARE_HANDOFF,
            "_atomic_no_replace_directory_move",
            wraps=real_atomic_move,
        ) as atomic_move, mock.patch.object(
            Path,
            "rename",
            side_effect=AssertionError("ordinary path rename must not publish"),
        ):
            PREPARE_HANDOFF.prepare_handoff(
                self.source, output, design_version="v1"
            )
            _write_image(image, (3, 2), (30, 20, 10), "PNG")
            PREPARE_HANDOFF.prepare_handoff(
                self.source, output, design_version="v1", force=True
            )

        preflight.assert_not_called()
        self.assertGreaterEqual(atomic_move.call_count, 3)
        self.assertTrue((output / "contracts" / "design-lock.json").is_file())

    def test_failed_unpublished_staging_is_preserved_without_recursive_cleanup(self):
        image = self.source / "screen.png"
        output = self.root / "failed-publication"
        _write_image(image, (2, 2), (10, 20, 30), "PNG")

        with mock.patch.object(
            PREPARE_HANDOFF, "_write_files", side_effect=RuntimeError("write failed")
        ), mock.patch.object(
            PREPARE_HANDOFF.shutil,
            "rmtree",
            side_effect=AssertionError("unpublished data must not be deleted"),
        ) as recursive_cleanup:
            with self.assertRaisesRegex(RuntimeError, "write failed"):
                PREPARE_HANDOFF.prepare_handoff(
                    self.source, output, design_version="v1"
                )

        recursive_cleanup.assert_not_called()
        preserved = list(self.root.glob(".failed-publication.prepare-*"))
        self.assertEqual(len(preserved), 1)
        self.assertFalse(output.exists())

    def test_unsupported_capability_fails_without_replacing_managed_publication(self):
        image = self.source / "screen.png"
        output = self.root / "managed-preflight"
        _write_image(image, (2, 2), (10, 20, 30), "PNG")
        PREPARE_HANDOFF.prepare_handoff(self.source, output, design_version="v1")
        previous_bytes = _file_bytes(output)
        _write_image(image, (3, 2), (30, 20, 10), "PNG")

        with mock.patch.object(
            PREPARE_HANDOFF,
            "_atomic_no_replace_directory_move",
            side_effect=RuntimeError("atomic no-replace unsupported"),
        ) as atomic_move:
            with self.assertRaisesRegex(RuntimeError, "atomic.*unsupported"):
                PREPARE_HANDOFF.prepare_handoff(
                    self.source, output, design_version="v1", force=True
                )

        atomic_move.assert_called_once()
        self.assertEqual(_file_bytes(output), previous_bytes)

    def assert_quarantine_reservation_collision_recovery(self, collision_kind):
        for managed_output in (False, True):
            with self.subTest(
                collision_kind=collision_kind, managed_output=managed_output
            ):
                case_root = self.root / (
                    f"{collision_kind}-{'managed' if managed_output else 'fresh'}"
                )
                source = case_root / "source"
                output = case_root / "output"
                image = source / "screen.png"
                _write_image(image, (2, 2), (10, 20, 30), "PNG")
                previous_bytes = None
                if managed_output:
                    PREPARE_HANDOFF.prepare_handoff(
                        source, output, design_version="v1"
                    )
                    previous_bytes = _file_bytes(output)
                    _write_image(image, (3, 2), (20, 30, 40), "PNG")

                recovery = output.with_name(output.name + ".recovery")
                collision_token = "a" * 32
                successful_token = "b" * 32
                collision_reservation = recovery / f"quarantine-{collision_token}"
                successful_reservation = recovery / f"quarantine-{successful_token}"
                symlink_target = recovery / "symlink-owner-target"
                link_kind = []
                real_publish = PREPARE_HANDOFF._publish_staging

                def publish_then_collide_and_mutate(*args, **kwargs):
                    publication = real_publish(*args, **kwargs)
                    recovery.mkdir(exist_ok=True)
                    if collision_kind == "regular-file":
                        collision_reservation.write_text(
                            "regular file owner data", encoding="utf-8"
                        )
                    elif collision_kind == "empty-directory":
                        collision_reservation.mkdir()
                    elif collision_kind == "non-empty-directory":
                        collision_reservation.mkdir()
                        (collision_reservation / "owner.txt").write_text(
                            "directory owner data", encoding="utf-8"
                        )
                    elif collision_kind == "symlink":
                        symlink_target.mkdir()
                        (symlink_target / "owner.txt").write_text(
                            "symlink owner data", encoding="utf-8"
                        )
                        link_kind.append(
                            _create_directory_link(
                                collision_reservation, symlink_target
                            )
                        )
                    else:
                        self.fail(f"unsupported collision kind: {collision_kind}")
                    (output / "concurrent-owner.txt").write_text(
                        "new package owner data", encoding="utf-8"
                    )
                    _write_image(image, (4, 2), (40, 30, 20), "PNG")
                    return publication

                with mock.patch.object(
                    PREPARE_HANDOFF,
                    "_publish_staging",
                    side_effect=publish_then_collide_and_mutate,
                ), mock.patch.object(
                    PREPARE_HANDOFF.secrets,
                    "token_hex",
                    side_effect=(collision_token, successful_token),
                ):
                    with self.assertRaisesRegex(
                        RuntimeError, "post-publication|source.*drift"
                    ) as error:
                        PREPARE_HANDOFF.prepare_handoff(
                            source,
                            output,
                            design_version="v1",
                            force=managed_output,
                        )

                if managed_output:
                    self.assertEqual(_file_bytes(output), previous_bytes)
                    self.assertFalse((recovery / "previous").exists())
                else:
                    self.assertFalse(output.exists())
                if collision_kind == "regular-file":
                    self.assertFalse(collision_reservation.is_symlink())
                    self.assertEqual(
                        collision_reservation.read_text(encoding="utf-8"),
                        "regular file owner data",
                    )
                elif collision_kind == "empty-directory":
                    self.assertFalse(collision_reservation.is_symlink())
                    self.assertEqual(list(collision_reservation.iterdir()), [])
                elif collision_kind == "non-empty-directory":
                    self.assertFalse(collision_reservation.is_symlink())
                    self.assertEqual(
                        (collision_reservation / "owner.txt").read_text(
                            encoding="utf-8"
                        ),
                        "directory owner data",
                    )
                else:
                    self.assertEqual(len(link_kind), 1)
                    if link_kind[0] == "symlink":
                        self.assertTrue(collision_reservation.is_symlink())
                        self.assertEqual(
                            Path(os.readlink(collision_reservation)), symlink_target
                        )
                    else:
                        self.assertFalse(collision_reservation.is_symlink())
                        self.assertEqual(
                            collision_reservation.resolve(), symlink_target.resolve()
                        )
                    self.assertEqual(
                        (symlink_target / "owner.txt").read_text(encoding="utf-8"),
                        "symlink owner data",
                    )
                quarantined_package = successful_reservation / "package"
                self.assertTrue(
                    (
                        quarantined_package / "contracts" / "design-lock.json"
                    ).is_file()
                )
                self.assertEqual(
                    (quarantined_package / "concurrent-owner.txt").read_text(
                        encoding="utf-8"
                    ),
                    "new package owner data",
                )
                self.assertNotIn(str(self.root), str(error.exception))

    def assert_contract_valid(self, schema_name, document):
        schema = json.loads((SCHEMA_ROOT / schema_name).read_text(encoding="utf-8"))
        errors = sorted(
            Draft202012Validator(schema).iter_errors(document),
            key=lambda error: list(error.absolute_path),
        )
        self.assertEqual(
            errors,
            [],
            "\n".join(
                f"{schema_name} {list(error.absolute_path)}: {error.message}"
                for error in errors
            ),
        )

    def test_collect_images_orders_paths_and_reports_real_image_metadata(self):
        duplicate, original, jpeg = self.make_three_image_source()

        images = PREPARE_HANDOFF.collect_images(self.source)

        self.assertEqual(
            [image["sourceRelativePath"] for image in images],
            ["A/duplicate.PNG", "b/原始 页面.png", "z final.JPEG"],
        )
        self.assertEqual(
            [
                (
                    image["mediaType"],
                    image["width"],
                    image["height"],
                    image["byteSize"],
                    image["sha256"],
                )
                for image in images
            ],
            [
                (
                    "image/png",
                    2,
                    3,
                    duplicate.stat().st_size,
                    hashlib.sha256(duplicate.read_bytes()).hexdigest(),
                ),
                (
                    "image/png",
                    2,
                    3,
                    original.stat().st_size,
                    hashlib.sha256(original.read_bytes()).hexdigest(),
                ),
                (
                    "image/jpeg",
                    4,
                    2,
                    jpeg.stat().st_size,
                    hashlib.sha256(jpeg.read_bytes()).hexdigest(),
                ),
            ],
        )
        self.assertEqual(
            PREPARE_HANDOFF.sha256_file(jpeg),
            hashlib.sha256(jpeg.read_bytes()).hexdigest(),
        )

    def test_collect_images_builds_metadata_from_one_immutable_byte_snapshot(self):
        image = self.source / "screen.png"
        _write_image(image, (2, 3), (10, 20, 30), "PNG")
        original_bytes = image.read_bytes()
        original_read_bytes = Path.read_bytes
        mutated = False

        def read_then_mutate(path):
            nonlocal mutated
            data = original_read_bytes(path)
            if Path(path) == image and not mutated:
                mutated = True
                _write_image(image, (7, 5), (90, 80, 70), "PNG")
            return data

        with mock.patch.object(Path, "read_bytes", autospec=True, side_effect=read_then_mutate):
            records = PREPARE_HANDOFF.collect_images(self.source)

        self.assertTrue(mutated)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["width"], 2)
        self.assertEqual(records[0]["height"], 3)
        self.assertEqual(records[0]["byteSize"], len(original_bytes))
        self.assertEqual(
            records[0]["sha256"], hashlib.sha256(original_bytes).hexdigest()
        )

    def test_prepare_generates_deterministic_schema_valid_bilingual_skeleton(self):
        self.make_three_image_source()
        source_before = _file_bytes(self.source)
        first_output = self.root / "handoff-one"
        second_output = self.root / "handoff-two"

        first = PREPARE_HANDOFF.prepare_handoff(
            self.source, first_output, design_version="v1"
        )
        second = PREPARE_HANDOFF.prepare_handoff(
            self.source, second_output, design_version="v1"
        )

        self.assertEqual(_file_bytes(self.source), source_before)
        self.assertEqual(_file_bytes(first_output), _file_bytes(second_output))
        self.assertEqual(first["status"], "prepared")
        self.assertEqual(second["status"], "prepared")
        self.assertEqual(first["assetCount"], 3)

        manifest_path = first_output / "contracts" / "asset-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected_source_hash = _source_set_hash(
            [
                (asset["sourceRelativePath"], asset["sha256"])
                for asset in manifest["assets"]
            ]
        )
        self.assertEqual(manifest["sourceSetHash"], expected_source_hash)
        self.assertEqual(first["sourceSetHash"], expected_source_hash)
        self.assertEqual(
            [asset["duplicateGroupId"] for asset in manifest["assets"]],
            ["D001", "D001", None],
        )
        self.assertEqual(
            [asset["deliveryRelativePath"] for asset in manifest["assets"]],
            [
                "assets/designs/v1/P001-S01-V01-unclassified.png",
                "assets/designs/v1/P002-S01-V01-unclassified.png",
                "assets/designs/v1/P003-S01-V01-unclassified.jpg",
            ],
        )
        for asset in manifest["assets"]:
            copied = first_output / asset["deliveryRelativePath"]
            source = self.source / asset["sourceRelativePath"]
            self.assertEqual(copied.read_bytes(), source.read_bytes())
            self.assertEqual(
                hashlib.sha256(copied.read_bytes()).hexdigest(), asset["sha256"]
            )

        inventory = json.loads(
            (first_output / "contracts" / "page-inventory.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            [
                f'{page["pageId"]}-{page["stateId"]}-{page["variantId"]}'
                for page in inventory["pages"]
            ],
            ["P001-S01-V01", "P002-S01-V01", "P003-S01-V01"],
        )
        for page in inventory["pages"]:
            self.assertIsNone(page["route"]["path"])
            self.assertEqual(page["route"]["evidenceLevel"], "unknown")
            self.assertRegex(page["route"]["gapId"], r"^G[0-9]{3,}$")
            self.assertEqual(page["shell"]["shellId"], "unclassified")
            self.assertEqual(page["components"], [])
            self.assertEqual(page["interactions"], [])

        schema_contracts = {
            "asset-manifest.schema.json": "asset-manifest.json",
            "page-inventory.schema.json": "page-inventory.json",
            "ui-style-contract.schema.json": "ui-style-contract.json",
            "component-registry.schema.json": "component-registry.json",
            "implementation-map.schema.json": "implementation-map.json",
            "capture-profile.schema.json": "capture-profile.json",
            "diff-regions.schema.json": "diff-regions.json",
            "design-lock.schema.json": "design-lock.json",
        }
        for schema_name, contract_name in schema_contracts.items():
            with self.subTest(contract=contract_name):
                document = json.loads(
                    (first_output / "contracts" / contract_name).read_text(
                        encoding="utf-8"
                    )
                )
                self.assert_contract_valid(schema_name, document)

        expected_files = {
            "README.md",
            "assets/designs/v1/P001-S01-V01-unclassified.png",
            "assets/designs/v1/P002-S01-V01-unclassified.png",
            "assets/designs/v1/P003-S01-V01-unclassified.jpg",
            "docs/zh/设计稿总目录.md",
            "docs/zh/UI实施说明.md",
            "docs/zh/组件规范.md",
            "docs/zh/pages/P001-S01-V01-unclassified.md",
            "docs/zh/pages/P002-S01-V01-unclassified.md",
            "docs/zh/pages/P003-S01-V01-unclassified.md",
            "docs/en/Design-Catalog.md",
            "docs/en/UI-Implementation-Guide.md",
            "docs/en/Component-Specification.md",
            "docs/en/pages/P001-S01-V01-unclassified.md",
            "docs/en/pages/P002-S01-V01-unclassified.md",
            "docs/en/pages/P003-S01-V01-unclassified.md",
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
            "reports/validation-report.json",
            "tools/validate-command.txt",
        }
        self.assertSetEqual(set(_file_bytes(first_output)), expected_files)
        self.assertFalse((first_output / "reports" / "contact-sheet.png").exists())

        with (first_output / "contracts" / "gap-register.csv").open(
            encoding="utf-8", newline=""
        ) as stream:
            gaps = list(csv.DictReader(stream))
        self.assertGreaterEqual(len(gaps), 4)
        self.assertTrue(all(row["evidenceLevel"] == "unknown" for row in gaps))
        self.assertTrue(all(row["gapId"] for row in gaps))

        for locale_root in (first_output / "docs" / "zh", first_output / "docs" / "en"):
            for document in locale_root.rglob("*.md"):
                text = document.read_text(encoding="utf-8")
                self.assertNotIn("{{", text)
                self.assertNotIn(str(self.root), text)
        english_names = {path.name for path in (first_output / "docs" / "en").iterdir()}
        self.assertSetEqual(
            english_names,
            {
                "Design-Catalog.md",
                "UI-Implementation-Guide.md",
                "Component-Specification.md",
                "pages",
            },
        )

    def test_dry_run_returns_the_plan_without_writing_any_output(self):
        self.make_three_image_source()
        output = self.root / "dry-run-output"
        source_before = _file_bytes(self.source)

        result = PREPARE_HANDOFF.prepare_handoff(
            self.source, output, design_version="draft-2", dry_run=True
        )

        self.assertEqual(result["status"], "dry-run")
        self.assertEqual(result["assetCount"], 3)
        self.assertIn("contracts/design-lock.json", result["plannedFiles"])
        self.assertFalse(output.exists())
        self.assertEqual(_file_bytes(self.source), source_before)

    def test_results_are_identical_and_relative_only_across_machine_roots(self):
        self.make_three_image_source()
        other_root = self.root / "other-machine"
        other_source = other_root / "design-source"
        shutil.copytree(self.source, other_source)

        first = PREPARE_HANDOFF.prepare_handoff(
            self.source,
            self.root / "first-machine-output",
            design_version="v1",
            dry_run=True,
        )
        second = PREPARE_HANDOFF.prepare_handoff(
            other_source,
            other_root / "second-machine-output",
            design_version="v1",
            dry_run=True,
        )

        self.assertEqual(first, second)
        self.assertNotIn("outputRoot", first)
        self.assertEqual(first.get("packageRoot"), ".")
        serialized = json.dumps(first, ensure_ascii=False)
        self.assertNotIn(str(self.root), serialized)
        self.assertNotRegex(serialized, r"(?i)[A-Z]:[\\/]")

    def test_force_replaces_managed_output_but_never_unmanaged_content(self):
        self.make_three_image_source()
        managed = self.root / "managed"
        PREPARE_HANDOFF.prepare_handoff(self.source, managed, design_version="v1")
        before = _file_bytes(managed)

        PREPARE_HANDOFF.prepare_handoff(
            self.source, managed, design_version="v1", force=True
        )

        self.assertEqual(_file_bytes(managed), before)
        owner_note = managed / "owner-note.txt"
        owner_note.write_text("do not replace", encoding="utf-8")
        with self.assertRaisesRegex(FileExistsError, "unmanaged|collision"):
            PREPARE_HANDOFF.prepare_handoff(
                self.source, managed, design_version="v1", force=True
            )
        self.assertEqual(owner_note.read_text(encoding="utf-8"), "do not replace")

        empty_unmanaged = self.root / "empty-unmanaged"
        empty_unmanaged.mkdir()
        for force in (False, True):
            with self.subTest(empty_unmanaged=True, force=force):
                with self.assertRaisesRegex(FileExistsError, "unmanaged|collision"):
                    PREPARE_HANDOFF.prepare_handoff(
                        self.source,
                        empty_unmanaged,
                        design_version="v1",
                        force=force,
                    )
                self.assertTrue(empty_unmanaged.is_dir())
                self.assertEqual(list(empty_unmanaged.iterdir()), [])

        unmanaged = self.root / "unmanaged"
        unmanaged.mkdir()
        sentinel = unmanaged / "keep.txt"
        sentinel.write_text("owner data", encoding="utf-8")
        for force in (False, True):
            with self.subTest(force=force):
                with self.assertRaisesRegex(FileExistsError, "unmanaged|collision"):
                    PREPARE_HANDOFF.prepare_handoff(
                        self.source,
                        unmanaged,
                        design_version="v1",
                        force=force,
                    )
                self.assertEqual(sentinel.read_text(encoding="utf-8"), "owner data")

    def test_new_target_content_inserted_after_authorization_is_preserved(self):
        self.make_three_image_source()
        output = self.root / "concurrent-new-output"
        real_write_lock = PREPARE_HANDOFF._write_design_lock

        def write_lock_then_insert_owner_data(*args, **kwargs):
            result = real_write_lock(*args, **kwargs)
            output.mkdir()
            (output / "owner.txt").write_text("concurrent owner", encoding="utf-8")
            return result

        with mock.patch.object(
            PREPARE_HANDOFF,
            "_write_design_lock",
            side_effect=write_lock_then_insert_owner_data,
        ):
            with self.assertRaisesRegex(FileExistsError, "drift|race|collision|unmanaged"):
                PREPARE_HANDOFF.prepare_handoff(
                    self.source, output, design_version="v1"
                )

        self.assertEqual(
            (output / "owner.txt").read_text(encoding="utf-8"), "concurrent owner"
        )

    def test_managed_target_changed_after_authorization_is_preserved(self):
        self.make_three_image_source()
        output = self.root / "concurrent-managed-output"
        PREPARE_HANDOFF.prepare_handoff(self.source, output, design_version="v1")
        real_write_lock = PREPARE_HANDOFF._write_design_lock

        def write_lock_then_change_target(*args, **kwargs):
            result = real_write_lock(*args, **kwargs)
            (output / "README.md").write_text("concurrent edit", encoding="utf-8")
            return result

        with mock.patch.object(
            PREPARE_HANDOFF,
            "_write_design_lock",
            side_effect=write_lock_then_change_target,
        ):
            with self.assertRaisesRegex(FileExistsError, "drift|race|collision|unmanaged"):
                PREPARE_HANDOFF.prepare_handoff(
                    self.source, output, design_version="v1", force=True
                )

        self.assertEqual(
            (output / "README.md").read_text(encoding="utf-8"), "concurrent edit"
        )

    def test_previous_package_and_late_owner_data_are_never_deleted(self):
        self.make_three_image_source()
        output = self.root / "preserved-output"
        PREPARE_HANDOFF.prepare_handoff(self.source, output, design_version="v1")
        previous_bytes = _file_bytes(output)
        real_snapshot = PREPARE_HANDOFF._managed_output_snapshot
        backup_verifications = 0
        injected = False

        def snapshot_then_inject_after_final_backup_verification(path):
            nonlocal backup_verifications, injected
            snapshot = real_snapshot(path)
            if Path(path) != output and snapshot is not None:
                backup_verifications += 1
                if backup_verifications == 2:
                    injected = True
                    (Path(path) / "late-owner.txt").write_text(
                        "late owner data", encoding="utf-8"
                    )
            return snapshot

        with mock.patch.object(
            PREPARE_HANDOFF,
            "_managed_output_snapshot",
            side_effect=snapshot_then_inject_after_final_backup_verification,
        ):
            result = PREPARE_HANDOFF.prepare_handoff(
                self.source, output, design_version="v1", force=True
            )

        previous = output.with_name(output.name + ".recovery") / "previous"
        self.assertTrue(injected)
        self.assertEqual(_file_bytes(output), previous_bytes)
        self.assertTrue(previous.is_dir())
        for relative_path, content in previous_bytes.items():
            self.assertEqual((previous / relative_path).read_bytes(), content)
        self.assertEqual(
            (previous / "late-owner.txt").read_text(encoding="utf-8"),
            "late owner data",
        )
        serialized = json.dumps(result, ensure_ascii=False)
        self.assertNotIn(str(self.root), serialized)
        self.assertNotRegex(serialized, r"(?i)[A-Z]:[\\/]")

    def test_recovery_name_collision_aborts_without_overwriting_any_content(self):
        for managed_output in (False, True):
            with self.subTest(managed_output=managed_output):
                case_root = self.root / ("managed" if managed_output else "fresh")
                source = case_root / "source"
                output = case_root / "output"
                _write_image(source / "screen.png", (2, 2), (1, 2, 3), "PNG")
                if managed_output:
                    PREPARE_HANDOFF.prepare_handoff(
                        source, output, design_version="v1"
                    )
                output_before = _file_bytes(output) if output.exists() else None
                recovery = output.with_name(output.name + ".recovery")
                recovery.mkdir()
                owner_file = recovery / "owner.txt"
                owner_file.write_text("reserved by owner", encoding="utf-8")

                with self.assertRaisesRegex(
                    FileExistsError, "recovery|backup|collision"
                ):
                    PREPARE_HANDOFF.prepare_handoff(
                        source,
                        output,
                        design_version="v1",
                        force=managed_output,
                    )

                self.assertEqual(
                    owner_file.read_text(encoding="utf-8"), "reserved by owner"
                )
                if managed_output:
                    self.assertEqual(_file_bytes(output), output_before)
                else:
                    self.assertFalse(output.exists())

    def test_post_publication_source_drift_quarantines_fresh_package_and_owner_data(self):
        image = self.source / "screen.png"
        _write_image(image, (2, 2), (10, 20, 30), "PNG")
        output = self.root / "fresh-post-drift"
        real_publish = PREPARE_HANDOFF._publish_staging

        def publish_then_mutate_source_and_target(*args, **kwargs):
            publication = real_publish(*args, **kwargs)
            (output / "concurrent-owner.txt").write_text(
                "preserve me", encoding="utf-8"
            )
            _write_image(image, (3, 2), (30, 20, 10), "PNG")
            return publication

        with mock.patch.object(
            PREPARE_HANDOFF,
            "_publish_staging",
            side_effect=publish_then_mutate_source_and_target,
        ):
            with self.assertRaisesRegex(RuntimeError, "post-publication|source.*drift") as error:
                PREPARE_HANDOFF.prepare_handoff(
                    self.source, output, design_version="v1"
                )

        recovery = output.with_name(output.name + ".recovery")
        quarantines = _quarantined_packages(recovery)
        self.assertFalse(output.exists())
        self.assertEqual(len(quarantines), 1)
        quarantine = quarantines[0]
        self.assertTrue((quarantine / "contracts" / "design-lock.json").is_file())
        self.assertEqual(
            (quarantine / "concurrent-owner.txt").read_text(encoding="utf-8"),
            "preserve me",
        )
        self.assertNotIn(str(self.root), str(error.exception))

    def test_post_publication_source_drift_restores_previous_and_quarantines_new(self):
        image = self.source / "screen.png"
        _write_image(image, (2, 2), (10, 20, 30), "PNG")
        output = self.root / "managed-post-drift"
        PREPARE_HANDOFF.prepare_handoff(self.source, output, design_version="v1")
        previous_bytes = _file_bytes(output)
        _write_image(image, (3, 2), (20, 30, 40), "PNG")
        real_publish = PREPARE_HANDOFF._publish_staging

        def publish_then_mutate_source_and_target(*args, **kwargs):
            publication = real_publish(*args, **kwargs)
            (output / "concurrent-owner.txt").write_text(
                "new package owner data", encoding="utf-8"
            )
            _write_image(image, (4, 2), (40, 30, 20), "PNG")
            return publication

        with mock.patch.object(
            PREPARE_HANDOFF,
            "_publish_staging",
            side_effect=publish_then_mutate_source_and_target,
        ):
            with self.assertRaisesRegex(RuntimeError, "post-publication|source.*drift") as error:
                PREPARE_HANDOFF.prepare_handoff(
                    self.source, output, design_version="v1", force=True
                )

        recovery = output.with_name(output.name + ".recovery")
        quarantines = _quarantined_packages(recovery)
        self.assertEqual(_file_bytes(output), previous_bytes)
        self.assertFalse((recovery / "previous").exists())
        self.assertEqual(len(quarantines), 1)
        quarantine = quarantines[0]
        self.assertTrue((quarantine / "contracts" / "design-lock.json").is_file())
        self.assertEqual(
            (quarantine / "concurrent-owner.txt").read_text(encoding="utf-8"),
            "new package owner data",
        )
        self.assertNotIn(str(self.root), str(error.exception))

    def test_occupied_fixed_quarantine_never_blocks_fresh_drift_recovery(self):
        image = self.source / "screen.png"
        _write_image(image, (2, 2), (10, 20, 30), "PNG")
        output = self.root / "occupied-fixed-quarantine"
        recovery = output.with_name(output.name + ".recovery")
        fixed_quarantine = recovery / "quarantine"
        real_publish = PREPARE_HANDOFF._publish_staging

        def publish_then_occupy_fixed_path_and_mutate(*args, **kwargs):
            publication = real_publish(*args, **kwargs)
            fixed_quarantine.mkdir(parents=True)
            (fixed_quarantine / "owner.txt").write_text(
                "existing recovery owner data", encoding="utf-8"
            )
            (output / "concurrent-owner.txt").write_text(
                "new package owner data", encoding="utf-8"
            )
            _write_image(image, (3, 2), (30, 20, 10), "PNG")
            return publication

        with mock.patch.object(
            PREPARE_HANDOFF,
            "_publish_staging",
            side_effect=publish_then_occupy_fixed_path_and_mutate,
        ):
            with self.assertRaisesRegex(
                RuntimeError, "post-publication|source.*drift"
            ) as error:
                PREPARE_HANDOFF.prepare_handoff(
                    self.source, output, design_version="v1"
                )

        self.assertFalse(output.exists())
        self.assertEqual(
            (fixed_quarantine / "owner.txt").read_text(encoding="utf-8"),
            "existing recovery owner data",
        )
        quarantines = _quarantined_packages(recovery)
        self.assertEqual(len(quarantines), 1)
        self.assertNotEqual(quarantines[0], fixed_quarantine)
        self.assertEqual(
            (quarantines[0] / "concurrent-owner.txt").read_text(encoding="utf-8"),
            "new package owner data",
        )
        self.assertNotIn(str(self.root), str(error.exception))

    def test_regular_file_quarantine_reservation_collision_survives_retry(self):
        self.assert_quarantine_reservation_collision_recovery("regular-file")

    def test_empty_directory_quarantine_reservation_collision_survives_retry(self):
        self.assert_quarantine_reservation_collision_recovery("empty-directory")

    def test_non_empty_directory_quarantine_reservation_collision_survives_retry(self):
        self.assert_quarantine_reservation_collision_recovery(
            "non-empty-directory"
        )

    def test_symlink_quarantine_reservation_collision_survives_retry(self):
        self.assert_quarantine_reservation_collision_recovery("symlink")

    def test_child_collision_errnos_preserve_empty_directories_and_retry(self):
        for collision_errno in (errno.EEXIST, errno.ENOTEMPTY, errno.ENOTDIR):
            with self.subTest(collision_errno=collision_errno):
                case_root = self.root / f"child-collision-{collision_errno}"
                output = case_root / "public-package"
                recovery = case_root / "public-package.recovery"
                output.mkdir(parents=True)
                recovery.mkdir()
                (output / "owner.txt").write_text(
                    "public package", encoding="utf-8"
                )
                collision_token = "a" * 32
                successful_token = "b" * 32
                collision_child = (
                    recovery / f"quarantine-{collision_token}" / "package"
                )
                successful_package = (
                    recovery / f"quarantine-{successful_token}" / "package"
                )
                real_atomic_move = (
                    PREPARE_HANDOFF._atomic_no_replace_directory_move
                )
                injected_inode = []

                def collide_once_then_move(source, destination):
                    destination = Path(destination)
                    if not injected_inode:
                        destination.mkdir()
                        injected_inode.append(destination.stat().st_ino)
                        raise OSError(collision_errno, "simulated child collision")
                    return real_atomic_move(source, destination)

                with mock.patch.object(
                    PREPARE_HANDOFF,
                    "_atomic_no_replace_directory_move",
                    side_effect=collide_once_then_move,
                ), mock.patch.object(
                    PREPARE_HANDOFF.secrets,
                    "token_hex",
                    side_effect=(collision_token, successful_token),
                ):
                    quarantined_package = (
                        PREPARE_HANDOFF._move_to_unique_quarantine(output, recovery)
                    )

                self.assertEqual(collision_child.stat().st_ino, injected_inode[0])
                self.assertEqual(list(collision_child.iterdir()), [])
                self.assertEqual(quarantined_package, successful_package)
                self.assertFalse(output.exists())
                self.assertEqual(
                    (successful_package / "owner.txt").read_text(encoding="utf-8"),
                    "public package",
                )

    def test_child_non_collision_error_is_propagated_without_retry(self):
        output = self.root / "non-collision-public-package"
        recovery = self.root / "non-collision-public-package.recovery"
        output.mkdir()
        recovery.mkdir()
        (output / "owner.txt").write_text("public package", encoding="utf-8")
        collision_token = "a" * 32

        with mock.patch.object(
            PREPARE_HANDOFF,
            "_atomic_no_replace_directory_move",
            side_effect=OSError(errno.EXDEV, "cross-device move"),
        ) as atomic_move, mock.patch.object(
            PREPARE_HANDOFF.secrets,
            "token_hex",
            return_value=collision_token,
        ) as token_hex:
            with self.assertRaises(OSError) as error:
                PREPARE_HANDOFF._move_to_unique_quarantine(output, recovery)

        self.assertEqual(error.exception.errno, errno.EXDEV)
        atomic_move.assert_called_once()
        token_hex.assert_called_once_with(16)
        self.assertTrue(output.is_dir())
        self.assertEqual(
            (output / "owner.txt").read_text(encoding="utf-8"), "public package"
        )

    @unittest.skipUnless(
        os.name != "nt" or shutil.which("wsl.exe"),
        "requires POSIX or WSL",
    )
    def test_posix_child_empty_directory_race_preserves_collision_and_retries(self):
        if os.name == "nt":
            converted_path = subprocess.run(
                ["wsl.exe", "-e", "wslpath", "-a", str(SCRIPT_PATH)],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                encoding="utf-8",
            ).stdout.strip()
            command = [
                "wsl.exe",
                "-e",
                "python3",
                "-B",
                "-c",
                POSIX_CHILD_EMPTY_DIRECTORY_RACE,
                converted_path,
            ]
        else:
            command = [
                sys.executable,
                "-B",
                "-c",
                POSIX_CHILD_EMPTY_DIRECTORY_RACE,
                str(SCRIPT_PATH),
            ]

        completed = subprocess.run(
            command,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )

        self.assertEqual(
            completed.returncode,
            0,
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}",
        )
        self.assertIn("POSIX child empty-directory race: passed", completed.stdout)

    def test_unique_quarantine_collision_retries_without_overwriting_owner_data(self):
        image = self.source / "screen.png"
        _write_image(image, (2, 2), (10, 20, 30), "PNG")
        output = self.root / "unique-quarantine-collision"
        PREPARE_HANDOFF.prepare_handoff(self.source, output, design_version="v1")
        previous_bytes = _file_bytes(output)
        _write_image(image, (3, 2), (20, 30, 40), "PNG")
        recovery = output.with_name(output.name + ".recovery")
        collision_token = "a" * 32
        successful_token = "b" * 32
        collision_quarantine = recovery / f"quarantine-{collision_token}"
        successful_quarantine = (
            recovery / f"quarantine-{successful_token}" / "package"
        )
        real_publish = PREPARE_HANDOFF._publish_staging

        def publish_then_occupy_candidate_and_mutate(*args, **kwargs):
            publication = real_publish(*args, **kwargs)
            collision_quarantine.mkdir()
            (collision_quarantine / "owner.txt").write_text(
                "owner collision data", encoding="utf-8"
            )
            (output / "concurrent-owner.txt").write_text(
                "new package owner data", encoding="utf-8"
            )
            _write_image(image, (4, 2), (40, 30, 20), "PNG")
            return publication

        with mock.patch.object(
            PREPARE_HANDOFF,
            "_publish_staging",
            side_effect=publish_then_occupy_candidate_and_mutate,
        ), mock.patch.object(
            PREPARE_HANDOFF.secrets,
            "token_hex",
            side_effect=(collision_token, successful_token),
        ):
            with self.assertRaisesRegex(
                RuntimeError, "post-publication|source.*drift"
            ) as error:
                PREPARE_HANDOFF.prepare_handoff(
                    self.source,
                    output,
                    design_version="v1",
                    force=True,
                )

        self.assertEqual(_file_bytes(output), previous_bytes)
        self.assertEqual(
            (collision_quarantine / "owner.txt").read_text(encoding="utf-8"),
            "owner collision data",
        )
        self.assertTrue(
            (successful_quarantine / "contracts" / "design-lock.json").is_file()
        )
        self.assertEqual(
            (successful_quarantine / "concurrent-owner.txt").read_text(
                encoding="utf-8"
            ),
            "new package owner data",
        )
        self.assertFalse((recovery / "previous").exists())
        self.assertNotIn(str(self.root), str(error.exception))

    def test_corrupt_lock_metadata_never_authorizes_force_replacement(self):
        mutators = {
            "design version": lambda lock: lock.__setitem__("designVersion", "v2"),
            "source set hash": lambda lock: lock.__setitem__(
                "sourceSetHash", "0" * 64
            ),
            "contracts hash": lambda lock: lock.__setitem__(
                "contractsHash", "0" * 64
            ),
            "generated timestamp": lambda lock: lock.__setitem__(
                "generatedAt", "not-a-date-time"
            ),
            "valid altered timestamp": lambda lock: lock.__setitem__(
                "generatedAt", "2000-01-01T00:00:00Z"
            ),
            "unexpected field": lambda lock: lock.__setitem__("unexpected", True),
            "duplicate inventory": lambda lock: lock["files"].append(
                dict(lock["files"][0])
            ),
        }
        for case, mutate in mutators.items():
            with self.subTest(case=case):
                case_root = self.root / case.replace(" ", "-")
                source = case_root / "source"
                output = case_root / "output"
                _write_image(source / "screen.png", (2, 2), (1, 2, 3), "PNG")
                PREPARE_HANDOFF.prepare_handoff(source, output, design_version="v1")
                lock_path = output / "contracts" / "design-lock.json"
                lock = json.loads(lock_path.read_text(encoding="utf-8"))
                mutate(lock)
                _write_json(lock_path, lock)
                before = _file_bytes(output)

                with self.assertRaisesRegex(FileExistsError, "unmanaged|collision"):
                    PREPARE_HANDOFF.prepare_handoff(
                        source, output, design_version="v1", force=True
                    )

                self.assertEqual(_file_bytes(output), before)

    def test_cross_contract_manifest_drift_never_authorizes_replacement(self):
        image = self.source / "screen.png"
        _write_image(image, (2, 2), (3, 4, 5), "PNG")
        output = self.root / "cross-contract-output"
        PREPARE_HANDOFF.prepare_handoff(self.source, output, design_version="v1")
        manifest_path = output / "contracts" / "asset-manifest.json"
        lock_path = output / "contracts" / "design-lock.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        manifest["designVersion"] = "mismatched-version"
        _write_json(manifest_path, manifest)
        manifest_hash = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        for entry in lock["files"]:
            if entry["relativePath"] == "contracts/asset-manifest.json":
                entry["sha256"] = manifest_hash
        lock["contractsHash"] = _hash_records(
            [
                (entry["relativePath"], entry["sha256"])
                for entry in lock["files"]
                if entry["relativePath"].startswith("contracts/")
            ]
        )
        _write_json(lock_path, lock)
        before = _file_bytes(output)

        with self.assertRaisesRegex(FileExistsError, "unmanaged|collision"):
            PREPARE_HANDOFF.prepare_handoff(
                self.source, output, design_version="v1", force=True
            )

        self.assertEqual(_file_bytes(output), before)

    def test_missing_empty_corrupt_and_nested_sources_fail_closed(self):
        with self.subTest(case="missing source"):
            with self.assertRaises(FileNotFoundError):
                PREPARE_HANDOFF.collect_images(self.root / "missing")

        with self.subTest(case="no supported images"):
            (self.source / "readme.txt").write_text("none", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "supported image"):
                PREPARE_HANDOFF.collect_images(self.source)

        with self.subTest(case="corrupt image"):
            corrupt_source = self.root / "corrupt-source"
            corrupt_source.mkdir()
            (corrupt_source / "broken.png").write_bytes(b"not a png")
            with self.assertRaisesRegex(ValueError, "corrupt|invalid"):
                PREPARE_HANDOFF.collect_images(corrupt_source)

        with self.subTest(case="output nested under source"):
            nested_source = self.root / "nested-source"
            _write_image(nested_source / "screen.png", (1, 1), (1, 2, 3), "PNG")
            source_before = _file_bytes(nested_source)
            nested_output = nested_source / "generated" / "handoff"
            with self.assertRaisesRegex(ValueError, "nested|overlap"):
                PREPARE_HANDOFF.prepare_handoff(
                    nested_source, nested_output, design_version="v1"
                )
            self.assertFalse(nested_output.exists())
            self.assertEqual(_file_bytes(nested_source), source_before)

    def test_source_drift_aborts_before_any_design_lock_is_published(self):
        image = self.source / "screen.png"
        _write_image(image, (2, 2), (15, 25, 35), "PNG")
        output = self.root / "drift-output"
        real_write_lock = PREPARE_HANDOFF._write_design_lock
        mutated = False

        def write_lock_then_mutate(*args, **kwargs):
            nonlocal mutated
            result = real_write_lock(*args, **kwargs)
            if not mutated:
                mutated = True
                _write_image(image, (3, 2), (35, 25, 15), "PNG")
            return result

        with mock.patch.object(
            PREPARE_HANDOFF, "_write_design_lock", side_effect=write_lock_then_mutate
        ):
            with self.assertRaisesRegex(RuntimeError, "source.*changed|drift"):
                PREPARE_HANDOFF.prepare_handoff(
                    self.source, output, design_version="v1"
                )

        self.assertTrue(mutated)
        self.assertFalse((output / "contracts" / "design-lock.json").exists())

    def test_final_source_rescan_rejects_add_remove_rename_and_byte_drift(self):
        def add_image(source):
            _write_image(source / "added.png", (1, 1), (4, 5, 6), "PNG")

        def remove_image(source):
            (source / "screen.png").unlink()

        def rename_image(source):
            (source / "screen.png").rename(source / "renamed.png")

        def replace_image(source):
            _write_image(source / "screen.png", (5, 4), (7, 8, 9), "PNG")

        mutations = {
            "addition": add_image,
            "removal": remove_image,
            "rename": rename_image,
            "byte and metadata drift": replace_image,
        }
        for case, mutate in mutations.items():
            with self.subTest(case=case):
                case_root = self.root / case.replace(" ", "-")
                source = case_root / "source"
                output = case_root / "output"
                _write_image(source / "screen.png", (2, 3), (1, 2, 3), "PNG")
                real_copy = PREPARE_HANDOFF._copy_and_verify_sources

                def copy_then_mutate(*args, **kwargs):
                    result = real_copy(*args, **kwargs)
                    mutate(source)
                    return result

                with mock.patch.object(
                    PREPARE_HANDOFF,
                    "_copy_and_verify_sources",
                    side_effect=copy_then_mutate,
                ):
                    with self.assertRaisesRegex(
                        RuntimeError, "source.*(changed|drift)|source set"
                    ):
                        PREPARE_HANDOFF.prepare_handoff(
                            source, output, design_version="v1"
                        )

                self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
