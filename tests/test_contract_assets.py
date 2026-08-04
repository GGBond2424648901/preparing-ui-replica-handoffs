import copy
import csv
import io
import json
from pathlib import Path
import re
import unittest

from jsonschema import Draft202012Validator


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = (
    REPOSITORY_ROOT / "skill" / "preparing-ui-replica-handoffs" / "assets"
)
SCHEMA_ROOT = ASSET_ROOT / "schemas"
TEMPLATE_ROOT = ASSET_ROOT / "templates"

SCHEMA_NAMES = {
    "asset-manifest.schema.json",
    "capture-profile.schema.json",
    "component-registry.schema.json",
    "design-lock.schema.json",
    "diff-regions.schema.json",
    "handoff-config.schema.json",
    "implementation-map.schema.json",
    "page-inventory.schema.json",
    "ui-style-contract.schema.json",
}

MARKDOWN_TEMPLATE_NAMES = {
    "component-specification.template.md",
    "design-catalog.template.md",
    "page-contract.template.md",
    "ui-implementation-guide.template.md",
}

EVIDENCE_LEVELS = {"direct", "derived", "candidate", "approved", "unknown"}
LIFECYCLE_STATUSES = {"unknown", "proposed", "candidate", "approved"}
QA_STATUSES = {"not-run", "pass", "fail", "blocked"}


def _identity():
    return {"pageId": "P001", "stateId": "S01", "variantId": "V01"}


def _git_scope():
    return {
        "repositoryRelativeRoot": ".",
        "allowedNewPaths": ["ui-replica-handoff/"],
        "allowedModifiedPaths": [],
    }


VALID_DOCUMENTS = {
    "handoff-config.schema.json": {
        "schemaVersion": "1.0.0",
        "designSourceDir": "design-source",
        "outputDir": "ui-replica-handoff",
        "designVersion": "v1",
        "locales": ["zh-CN", "en-US"],
        "gitScope": _git_scope(),
    },
    "asset-manifest.schema.json": {
        "schemaVersion": "1.0.0",
        "designVersion": "v1",
        "sourceSetHash": "a" * 64,
        "assets": [
            {
                "assetId": "A001",
                "sourceRelativePath": "screen.png",
                "deliveryRelativePath": "assets/designs/v1/screen.png",
                "mediaType": "image/png",
                "byteSize": 1,
                "width": 1,
                "height": 1,
                "sha256": "b" * 64,
                "duplicateGroupId": None,
                "evidenceLevel": "direct",
            }
        ],
    },
    "page-inventory.schema.json": {
        "schemaVersion": "1.0.0",
        "pages": [
            {
                **_identity(),
                "sourceAssetIds": ["A001"],
                "route": {"path": "/dashboard", "evidenceLevel": "unknown"},
                "canvas": {"width": 1440, "height": 900, "unit": "px"},
                "shell": {"shellId": "shell-main", "evidenceLevel": "derived"},
                "regions": [
                    {
                        "regionId": "region-main",
                        "role": "main",
                        "evidenceLevel": "direct",
                    }
                ],
                "layoutRelationships": [
                    {
                        "relationshipId": "layout-001",
                        "containerId": "region-main",
                        "display": "grid",
                        "relation": "contains",
                        "targetIds": ["instance-001"],
                        "evidenceLevel": "derived",
                    }
                ],
                "copy": [
                    {
                        "copyId": "copy-001",
                        "text": {"zh-CN": "示例", "en-US": "Example"},
                        "classification": "verbatim",
                        "evidenceLevel": "direct",
                        "sourceBounds": {"x": 0, "y": 0, "width": 10, "height": 10},
                        "gapId": None,
                    }
                ],
                "icons": [
                    {
                        "iconId": "icon-001",
                        "assetId": "A001",
                        "meaning": {"zh-CN": "示例", "en-US": "Example"},
                        "evidenceLevel": "direct",
                    }
                ],
                "components": [
                    {
                        "instanceId": "instance-001",
                        "componentId": "component-hero",
                        "regionId": "region-main",
                        "evidenceLevel": "candidate",
                    }
                ],
                "data": [
                    {
                        "dataId": "data-001",
                        "classification": "sample",
                        "valueShape": "list",
                        "evidenceLevel": "direct",
                    }
                ],
                "interactions": [
                    {
                        "interactionId": "interaction-001",
                        "trigger": "click",
                        "outcome": {"zh-CN": "待确认", "en-US": "To confirm"},
                        "status": "unknown",
                        "evidenceLevel": "unknown",
                        "gapId": "G001",
                    }
                ],
                "responsiveVariants": [
                    {
                        "responsiveVariantId": "desktop-base",
                        "mode": "baseline-scroll",
                        "minWidth": 1440,
                        "evidenceLevel": "direct",
                        "status": "approved",
                        "gapIds": [],
                    }
                ],
                "acceptanceCriteria": [
                    {
                        "qaId": "QA001",
                        "evidenceTypes": ["visual", "structural", "interaction"],
                        "status": "not-run",
                    }
                ],
                "evidenceLevel": "direct",
                "status": "approved",
                "gapIds": [],
            }
        ],
    },
    "ui-style-contract.schema.json": {
        "schemaVersion": "1.0.0",
        "evidenceLevel": "candidate",
        "status": "candidate",
        "tokens": {
            "colors": [],
            "typography": [],
            "spacing": [],
            "radii": [],
            "shadows": [],
        },
        "responsiveVariants": [],
        "gapIds": [],
    },
    "component-registry.schema.json": {
        "schemaVersion": "1.0.0",
        "components": [
            {
                "componentId": "component-hero",
                "name": {"zh-CN": "主视觉", "en-US": "Hero"},
                "status": "candidate",
                "evidenceLevel": "candidate",
                "sourcePageIdentities": [_identity()],
                "anatomy": ["title", "action"],
                "variants": [],
                "states": [
                    {
                        "stateId": "default",
                        "status": "approved",
                        "evidenceLevel": "direct",
                        "gapIds": [],
                    }
                ],
                "props": [],
                "interactions": [],
                "styleTokenRefs": [],
                "gapIds": [],
            }
        ],
    },
    "implementation-map.schema.json": {
        "schemaVersion": "1.0.0",
        "gitScope": _git_scope(),
        "mappings": [
            {
                **_identity(),
                "route": "/dashboard",
                "targetFiles": ["src/pages/dashboard.tsx"],
                "shellComponentId": "shell-main",
                "regionMappings": [],
                "componentMappings": [],
                "dataBindings": [],
                "interactionMappings": [],
                "responsiveMappings": [],
                "evidenceLevel": "candidate",
                "status": "proposed",
                "gapIds": ["G001"],
            }
        ],
    },
    "capture-profile.schema.json": {
        "schemaVersion": "1.0.0",
        "profiles": [
            {
                "captureProfileId": "capture-desktop",
                "browser": "chromium",
                "browserVersion": "pinned-by-runner",
                "viewport": {"width": 1440, "height": 900},
                "dpr": 1,
                "locale": "en-US",
                "timezone": "UTC",
                "theme": "light",
                "fontEnvironment": ["Inter"],
                "colorScheme": "light",
                "reducedMotion": True,
                "evidenceLevel": "approved",
            }
        ],
    },
    "diff-regions.schema.json": {
        "schemaVersion": "1.0.0",
        "pages": [
            {
                **_identity(),
                "captureProfileId": "capture-desktop",
                "regions": [
                    {
                        "regionId": "region-main",
                        "bounds": {"x": 0, "y": 0, "width": 100, "height": 100},
                        "comparisonModes": ["reference", "current", "overlay", "diff"],
                        "evidenceTypes": ["visual", "structural", "interaction"],
                        "tolerance": {"pixelRatio": 0},
                        "status": "not-run",
                    }
                ],
            }
        ],
    },
    "design-lock.schema.json": {
        "schemaVersion": "1.0.0",
        "designVersion": "v1",
        "generatedAt": "2026-08-04T00:00:00Z",
        "sourceSetHash": "a" * 64,
        "contractsHash": "b" * 64,
        "files": [
            {"relativePath": "contracts/page-inventory.json", "sha256": "c" * 64}
        ],
        "status": "generated",
    },
}


class ContractAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schemas = {
            path.name: json.loads(path.read_text(encoding="utf-8"))
            for path in SCHEMA_ROOT.glob("*.schema.json")
        }

    def assertValid(self, schema_name, document):
        self.assertIn(schema_name, self.schemas, f"missing schema: {schema_name}")
        errors = sorted(
            Draft202012Validator(self.schemas[schema_name]).iter_errors(document),
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

    def assertInvalid(self, schema_name, document):
        self.assertIn(schema_name, self.schemas, f"missing schema: {schema_name}")
        self.assertTrue(
            list(Draft202012Validator(self.schemas[schema_name]).iter_errors(document)),
            f"{schema_name} unexpectedly accepted {document!r}",
        )

    def test_all_schema_and_json_template_files_are_valid_json(self):
        self.assertSetEqual(
            {path.name for path in SCHEMA_ROOT.glob("*.schema.json")}, SCHEMA_NAMES
        )
        for schema in self.schemas.values():
            Draft202012Validator.check_schema(schema)

        template = json.loads(
            (TEMPLATE_ROOT / "handoff-config.template.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertValid("handoff-config.schema.json", template)

    def test_every_schema_accepts_its_minimal_complete_contract(self):
        for schema_name, document in VALID_DOCUMENTS.items():
            with self.subTest(schema=schema_name):
                self.assertValid(schema_name, document)

    def test_stable_top_level_keys_and_page_identity_are_required(self):
        required_top_level_keys = {
            name: set(document) for name, document in VALID_DOCUMENTS.items()
        }
        for schema_name, keys in required_top_level_keys.items():
            for key in keys:
                with self.subTest(schema=schema_name, missing=key):
                    invalid = copy.deepcopy(VALID_DOCUMENTS[schema_name])
                    invalid.pop(key)
                    self.assertInvalid(schema_name, invalid)

        for schema_name, collection_key in (
            ("page-inventory.schema.json", "pages"),
            ("implementation-map.schema.json", "mappings"),
            ("diff-regions.schema.json", "pages"),
        ):
            for key in ("pageId", "stateId", "variantId"):
                with self.subTest(schema=schema_name, missing=key):
                    invalid = copy.deepcopy(VALID_DOCUMENTS[schema_name])
                    invalid[collection_key][0].pop(key)
                    self.assertInvalid(schema_name, invalid)

    def test_evidence_and_status_enums_accept_only_the_stable_values(self):
        asset = VALID_DOCUMENTS["asset-manifest.schema.json"]
        for evidence_level in EVIDENCE_LEVELS:
            valid = copy.deepcopy(asset)
            valid["assets"][0]["evidenceLevel"] = evidence_level
            self.assertValid("asset-manifest.schema.json", valid)
        invalid = copy.deepcopy(asset)
        invalid["assets"][0]["evidenceLevel"] = "assumed"
        self.assertInvalid("asset-manifest.schema.json", invalid)

        page = VALID_DOCUMENTS["page-inventory.schema.json"]
        for status in LIFECYCLE_STATUSES:
            valid = copy.deepcopy(page)
            valid["pages"][0]["status"] = status
            valid["pages"][0]["gapIds"] = (
                ["G001"] if status in {"unknown", "proposed"} else []
            )
            self.assertValid("page-inventory.schema.json", valid)
        invalid = copy.deepcopy(page)
        invalid["pages"][0]["status"] = "done"
        self.assertInvalid("page-inventory.schema.json", invalid)

        for status in QA_STATUSES:
            valid = copy.deepcopy(page)
            valid["pages"][0]["acceptanceCriteria"][0]["status"] = status
            self.assertValid("page-inventory.schema.json", valid)
        invalid = copy.deepcopy(page)
        invalid["pages"][0]["acceptanceCriteria"][0]["status"] = "skipped"
        self.assertInvalid("page-inventory.schema.json", invalid)

    def test_csv_templates_expose_stable_qa_git_and_gap_fields(self):
        expected_headers = {
            "requirement-ledger.template.csv": [
                "requirementId",
                "source",
                "authorityRank",
                "summaryZh",
                "summaryEn",
                "pageId",
                "stateId",
                "variantId",
                "evidenceLevel",
                "status",
                "gapId",
            ],
            "gap-register.template.csv": [
                "gapId",
                "severity",
                "status",
                "category",
                "summaryZh",
                "summaryEn",
                "pageId",
                "stateId",
                "variantId",
                "evidenceLevel",
                "owner",
                "resolution",
            ],
            "visual-qa-matrix.template.csv": [
                "qaId",
                "pageId",
                "stateId",
                "variantId",
                "captureProfileId",
                "regionId",
                "evidenceType",
                "referencePath",
                "currentPath",
                "overlayPath",
                "diffPath",
                "status",
                "notesZh",
                "notesEn",
            ],
        }
        for name, expected in expected_headers.items():
            with self.subTest(template=name):
                path = TEMPLATE_ROOT / name
                self.assertTrue(path.is_file(), f"missing template: {name}")
                rows = list(
                    csv.reader(io.StringIO(path.read_text(encoding="utf-8")))
                )
                self.assertEqual(rows, [expected])

    def test_markdown_templates_have_paired_ids_sections_and_placeholders(self):
        language_roots = {
            "zh-CN": TEMPLATE_ROOT / "docs" / "zh",
            "en-US": TEMPLATE_ROOT / "docs" / "en",
        }
        for locale, root in language_roots.items():
            self.assertSetEqual(
                {path.name for path in root.glob("*.template.md")},
                MARKDOWN_TEMPLATE_NAMES,
            )
            for name in MARKDOWN_TEMPLATE_NAMES:
                content = (root / name).read_text(encoding="utf-8")
                self.assertRegex(content, rf"(?m)^locale:\s*{re.escape(locale)}$")

        for name in MARKDOWN_TEMPLATE_NAMES:
            paired = [
                (root / name).read_text(encoding="utf-8")
                for root in language_roots.values()
            ]
            id_sets = [
                set(re.findall(r"(?m)^(?:templateId|sectionId):\s*([a-z0-9-]+)$", text))
                for text in paired
            ]
            placeholder_sets = [
                set(re.findall(r"\{\{([A-Za-z][A-Za-z0-9_.-]*)\}\}", text))
                for text in paired
            ]
            self.assertTrue(id_sets[0], f"{name} has no stable IDs")
            self.assertSetEqual(id_sets[0], id_sets[1], name)
            self.assertSetEqual(placeholder_sets[0], placeholder_sets[1], name)

    def test_packaged_examples_do_not_embed_machine_absolute_paths(self):
        forbidden_patterns = (
            re.compile(r"(?i)\b[A-Z]:[\\/]"),
            re.compile(r"(?i)file://"),
            re.compile(r"(?m)(?<!:)\b/(?:Users|home)/"),
            re.compile(r"\\\\[^\\\s]+\\"),
        )
        example_files = [
            path
            for path in TEMPLATE_ROOT.rglob("*")
            if path.is_file() and path.name != ".gitkeep"
        ]
        self.assertTrue(example_files)
        for path in example_files:
            content = path.read_text(encoding="utf-8")
            for pattern in forbidden_patterns:
                self.assertIsNone(
                    pattern.search(content),
                    f"{path.relative_to(ASSET_ROOT)} contains an absolute path example",
                )


if __name__ == "__main__":
    unittest.main()
