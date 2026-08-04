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
        "allowedModifiedPaths": ["existing/file.ts"],
    }


def _get_at(document, path):
    value = document
    for part in path:
        value = value[part]
    return value


def _set_at(document, path, value):
    _get_at(document, path[:-1])[path[-1]] = value


def _link_gap(document, path):
    _set_at(document, path, ["G999"] if path[-1] == "gapIds" else "G999")


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
                "gapIds": [],
            }
        ],
    },
    "page-inventory.schema.json": {
        "schemaVersion": "1.0.0",
        "pages": [
            {
                **_identity(),
                "sourceAssetIds": ["A001"],
                "route": {
                    "path": "/dashboard",
                    "evidenceLevel": "unknown",
                    "gapId": "G001",
                },
                "canvas": {"width": 1440, "height": 900, "unit": "px"},
                "shell": {
                    "shellId": "shell-main",
                    "evidenceLevel": "derived",
                    "gapId": None,
                },
                "regions": [
                    {
                        "regionId": "region-main",
                        "role": "main",
                        "evidenceLevel": "direct",
                        "gapIds": [],
                    }
                ],
                "layoutRelationships": [
                    {
                        "relationshipId": "layout-001",
                        "containerId": "region-main",
                        "display": "grid",
                        "relation": "contains",
                        "targetIds": ["instance-001"],
                        "overflow": "visible",
                        "evidenceLevel": "derived",
                        "gapIds": [],
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
                        "gapId": None,
                    }
                ],
                "components": [
                    {
                        "instanceId": "instance-001",
                        "componentId": "component-hero",
                        "regionId": "region-main",
                        "evidenceLevel": "candidate",
                        "gapId": None,
                    }
                ],
                "data": [
                    {
                        "dataId": "data-001",
                        "classification": "sample",
                        "valueShape": "list",
                        "evidenceLevel": "direct",
                        "gapId": None,
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
            "colors": [
                {
                    "tokenId": "color-primary",
                    "value": "#ffffff",
                    "evidenceLevel": "direct",
                    "status": "approved",
                    "gapIds": [],
                }
            ],
            "typography": [],
            "spacing": [],
            "radii": [],
            "shadows": [],
        },
        "responsiveVariants": [
            {
                "responsiveVariantId": "desktop-base",
                "mode": "baseline-scroll",
                "evidenceLevel": "direct",
                "status": "approved",
                "gapIds": [],
            }
        ],
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
                "variants": [
                    {
                        "variantId": "primary",
                        "status": "approved",
                        "evidenceLevel": "direct",
                        "gapIds": [],
                    }
                ],
                "states": [
                    {
                        "stateId": "default",
                        "status": "approved",
                        "evidenceLevel": "direct",
                        "gapIds": [],
                    }
                ],
                "props": [
                    {
                        "propId": "title",
                        "type": "string",
                        "required": True,
                        "evidenceLevel": "direct",
                        "gapIds": [],
                    }
                ],
                "interactions": [
                    {
                        "interactionId": "component-action",
                        "trigger": "click",
                        "outcome": {"zh-CN": "提交", "en-US": "Submit"},
                        "status": "approved",
                        "evidenceLevel": "direct",
                        "gapId": None,
                    }
                ],
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
                "regionMappings": [
                    {
                        "regionId": "region-main",
                        "targetSelector": "main",
                        "targetFile": "src/pages/dashboard.tsx",
                        "evidenceLevel": "direct",
                        "gapIds": [],
                    }
                ],
                "componentMappings": [
                    {
                        "instanceId": "instance-001",
                        "componentId": "component-hero",
                        "targetSymbol": "Hero",
                        "targetFile": "src/components/hero.tsx",
                        "evidenceLevel": "direct",
                        "gapIds": [],
                    }
                ],
                "dataBindings": [
                    {
                        "dataId": "data-001",
                        "targetSource": "dashboard.items",
                        "classification": "sample",
                        "evidenceLevel": "direct",
                        "gapId": None,
                    }
                ],
                "interactionMappings": [
                    {
                        "interactionId": "interaction-001",
                        "targetHandler": "handleAction",
                        "status": "approved",
                        "evidenceLevel": "direct",
                        "gapId": None,
                    }
                ],
                "responsiveMappings": [
                    {
                        "responsiveVariantId": "desktop-base",
                        "strategy": "baseline-scroll",
                        "targetFiles": ["src/pages/dashboard.tsx"],
                        "status": "approved",
                        "evidenceLevel": "direct",
                        "gapIds": [],
                    }
                ],
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
                "gapIds": [],
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


EVIDENCE_CASES = (
    ("asset-manifest.schema.json", ("assets", 0, "evidenceLevel"), ("assets", 0, "gapIds")),
    ("page-inventory.schema.json", ("pages", 0, "route", "evidenceLevel"), ("pages", 0, "route", "gapId")),
    ("page-inventory.schema.json", ("pages", 0, "shell", "evidenceLevel"), ("pages", 0, "shell", "gapId")),
    ("page-inventory.schema.json", ("pages", 0, "regions", 0, "evidenceLevel"), ("pages", 0, "regions", 0, "gapIds")),
    ("page-inventory.schema.json", ("pages", 0, "layoutRelationships", 0, "evidenceLevel"), ("pages", 0, "layoutRelationships", 0, "gapIds")),
    ("page-inventory.schema.json", ("pages", 0, "copy", 0, "evidenceLevel"), ("pages", 0, "copy", 0, "gapId")),
    ("page-inventory.schema.json", ("pages", 0, "icons", 0, "evidenceLevel"), ("pages", 0, "icons", 0, "gapId")),
    ("page-inventory.schema.json", ("pages", 0, "components", 0, "evidenceLevel"), ("pages", 0, "components", 0, "gapId")),
    ("page-inventory.schema.json", ("pages", 0, "data", 0, "evidenceLevel"), ("pages", 0, "data", 0, "gapId")),
    ("page-inventory.schema.json", ("pages", 0, "interactions", 0, "evidenceLevel"), ("pages", 0, "interactions", 0, "gapId")),
    ("page-inventory.schema.json", ("pages", 0, "responsiveVariants", 0, "evidenceLevel"), ("pages", 0, "responsiveVariants", 0, "gapIds")),
    ("page-inventory.schema.json", ("pages", 0, "evidenceLevel"), ("pages", 0, "gapIds")),
    ("ui-style-contract.schema.json", ("evidenceLevel",), ("gapIds",)),
    ("ui-style-contract.schema.json", ("tokens", "colors", 0, "evidenceLevel"), ("tokens", "colors", 0, "gapIds")),
    ("ui-style-contract.schema.json", ("responsiveVariants", 0, "evidenceLevel"), ("responsiveVariants", 0, "gapIds")),
    ("component-registry.schema.json", ("components", 0, "evidenceLevel"), ("components", 0, "gapIds")),
    ("component-registry.schema.json", ("components", 0, "variants", 0, "evidenceLevel"), ("components", 0, "variants", 0, "gapIds")),
    ("component-registry.schema.json", ("components", 0, "states", 0, "evidenceLevel"), ("components", 0, "states", 0, "gapIds")),
    ("component-registry.schema.json", ("components", 0, "props", 0, "evidenceLevel"), ("components", 0, "props", 0, "gapIds")),
    ("component-registry.schema.json", ("components", 0, "interactions", 0, "evidenceLevel"), ("components", 0, "interactions", 0, "gapId")),
    ("implementation-map.schema.json", ("mappings", 0, "evidenceLevel"), ("mappings", 0, "gapIds")),
    ("implementation-map.schema.json", ("mappings", 0, "regionMappings", 0, "evidenceLevel"), ("mappings", 0, "regionMappings", 0, "gapIds")),
    ("implementation-map.schema.json", ("mappings", 0, "componentMappings", 0, "evidenceLevel"), ("mappings", 0, "componentMappings", 0, "gapIds")),
    ("implementation-map.schema.json", ("mappings", 0, "dataBindings", 0, "evidenceLevel"), ("mappings", 0, "dataBindings", 0, "gapId")),
    ("implementation-map.schema.json", ("mappings", 0, "interactionMappings", 0, "evidenceLevel"), ("mappings", 0, "interactionMappings", 0, "gapId")),
    ("implementation-map.schema.json", ("mappings", 0, "responsiveMappings", 0, "evidenceLevel"), ("mappings", 0, "responsiveMappings", 0, "gapIds")),
    ("capture-profile.schema.json", ("profiles", 0, "evidenceLevel"), ("profiles", 0, "gapIds")),
)

LIFECYCLE_CASES = (
    ("page-inventory.schema.json", ("pages", 0, "interactions", 0, "status"), ("pages", 0, "interactions", 0, "gapId")),
    ("page-inventory.schema.json", ("pages", 0, "responsiveVariants", 0, "status"), ("pages", 0, "responsiveVariants", 0, "gapIds")),
    ("page-inventory.schema.json", ("pages", 0, "status"), ("pages", 0, "gapIds")),
    ("ui-style-contract.schema.json", ("status",), ("gapIds",)),
    ("ui-style-contract.schema.json", ("tokens", "colors", 0, "status"), ("tokens", "colors", 0, "gapIds")),
    ("ui-style-contract.schema.json", ("responsiveVariants", 0, "status"), ("responsiveVariants", 0, "gapIds")),
    ("component-registry.schema.json", ("components", 0, "status"), ("components", 0, "gapIds")),
    ("component-registry.schema.json", ("components", 0, "variants", 0, "status"), ("components", 0, "variants", 0, "gapIds")),
    ("component-registry.schema.json", ("components", 0, "states", 0, "status"), ("components", 0, "states", 0, "gapIds")),
    ("component-registry.schema.json", ("components", 0, "interactions", 0, "status"), ("components", 0, "interactions", 0, "gapId")),
    ("implementation-map.schema.json", ("mappings", 0, "status"), ("mappings", 0, "gapIds")),
    ("implementation-map.schema.json", ("mappings", 0, "interactionMappings", 0, "status"), ("mappings", 0, "interactionMappings", 0, "gapId")),
    ("implementation-map.schema.json", ("mappings", 0, "responsiveMappings", 0, "status"), ("mappings", 0, "responsiveMappings", 0, "gapIds")),
)

QA_CASES = (
    ("page-inventory.schema.json", ("pages", 0, "acceptanceCriteria", 0, "status")),
    ("diff-regions.schema.json", ("pages", 0, "regions", 0, "status")),
)

SEMANTIC_GAP_CASES = (
    ("page-inventory.schema.json", ("pages", 0, "route", "path"), ("pages", 0, "route", "gapId"), None),
    ("page-inventory.schema.json", ("pages", 0, "regions", 0, "role"), ("pages", 0, "regions", 0, "gapIds"), "unknown"),
    ("page-inventory.schema.json", ("pages", 0, "layoutRelationships", 0, "display"), ("pages", 0, "layoutRelationships", 0, "gapIds"), "unknown"),
    ("page-inventory.schema.json", ("pages", 0, "layoutRelationships", 0, "relation"), ("pages", 0, "layoutRelationships", 0, "gapIds"), "unknown"),
    ("page-inventory.schema.json", ("pages", 0, "layoutRelationships", 0, "overflow"), ("pages", 0, "layoutRelationships", 0, "gapIds"), "unknown"),
    ("page-inventory.schema.json", ("pages", 0, "copy", 0, "classification"), ("pages", 0, "copy", 0, "gapId"), "unknown"),
    ("page-inventory.schema.json", ("pages", 0, "copy", 0, "classification"), ("pages", 0, "copy", 0, "gapId"), "inferred"),
    ("page-inventory.schema.json", ("pages", 0, "icons", 0, "assetId"), ("pages", 0, "icons", 0, "gapId"), None),
    ("page-inventory.schema.json", ("pages", 0, "data", 0, "classification"), ("pages", 0, "data", 0, "gapId"), "unknown"),
    ("implementation-map.schema.json", ("mappings", 0, "dataBindings", 0, "classification"), ("mappings", 0, "dataBindings", 0, "gapId"), "unknown"),
    ("capture-profile.schema.json", ("profiles", 0, "theme"), ("profiles", 0, "gapIds"), "unknown"),
)

PATH_CASES = (
    ("handoff-config.schema.json", ("designSourceDir",)),
    ("handoff-config.schema.json", ("outputDir",)),
    ("handoff-config.schema.json", ("gitScope", "repositoryRelativeRoot")),
    ("handoff-config.schema.json", ("gitScope", "allowedNewPaths", 0)),
    ("handoff-config.schema.json", ("gitScope", "allowedModifiedPaths", 0)),
    ("asset-manifest.schema.json", ("assets", 0, "sourceRelativePath")),
    ("asset-manifest.schema.json", ("assets", 0, "deliveryRelativePath")),
    ("implementation-map.schema.json", ("gitScope", "repositoryRelativeRoot")),
    ("implementation-map.schema.json", ("gitScope", "allowedNewPaths", 0)),
    ("implementation-map.schema.json", ("gitScope", "allowedModifiedPaths", 0)),
    ("implementation-map.schema.json", ("mappings", 0, "targetFiles", 0)),
    ("implementation-map.schema.json", ("mappings", 0, "regionMappings", 0, "targetFile")),
    ("implementation-map.schema.json", ("mappings", 0, "componentMappings", 0, "targetFile")),
    ("implementation-map.schema.json", ("mappings", 0, "responsiveMappings", 0, "targetFiles", 0)),
    ("design-lock.schema.json", ("files", 0, "relativePath")),
)

RESPONSIVE_CASES = (
    (
        "page-inventory.schema.json",
        ("pages", 0, "responsiveVariants"),
        "mode",
        {
            "responsiveVariantId": "tablet-approved",
            "mode": "responsive",
            "minWidth": 768,
            "evidenceLevel": "derived",
            "status": "approved",
            "gapIds": [],
        },
    ),
    (
        "ui-style-contract.schema.json",
        ("responsiveVariants",),
        "mode",
        {
            "responsiveVariantId": "tablet-approved",
            "mode": "responsive",
            "evidenceLevel": "derived",
            "status": "approved",
            "gapIds": [],
        },
    ),
    (
        "implementation-map.schema.json",
        ("mappings", 0, "responsiveMappings"),
        "strategy",
        {
            "responsiveVariantId": "tablet-approved",
            "strategy": "responsive",
            "targetFiles": ["src/pages/dashboard.tsx"],
            "status": "approved",
            "evidenceLevel": "derived",
            "gapIds": [],
        },
    ),
)


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

    def test_evidence_lifecycle_and_qa_enums_are_consistent_at_every_boundary(self):
        domain_cases = (
            (EVIDENCE_CASES, EVIDENCE_LEVELS, {"unknown"}),
            (LIFECYCLE_CASES, LIFECYCLE_STATUSES, {"unknown", "proposed"}),
        )
        for cases, allowed_values, gap_linked_values in domain_cases:
            for schema_name, value_path, gap_path in cases:
                for allowed in allowed_values:
                    with self.subTest(
                        schema=schema_name, path=value_path, allowed=allowed
                    ):
                        valid = copy.deepcopy(VALID_DOCUMENTS[schema_name])
                        _set_at(valid, value_path, allowed)
                        if allowed in gap_linked_values:
                            _link_gap(valid, gap_path)
                        self.assertValid(schema_name, valid)

                with self.subTest(
                    schema=schema_name, path=value_path, rejected="outside-domain"
                ):
                    invalid = copy.deepcopy(VALID_DOCUMENTS[schema_name])
                    _set_at(invalid, value_path, "outside-domain")
                    self.assertInvalid(schema_name, invalid)

        for schema_name, value_path in QA_CASES:
            for allowed in QA_STATUSES:
                with self.subTest(
                    schema=schema_name, path=value_path, allowed=allowed
                ):
                    valid = copy.deepcopy(VALID_DOCUMENTS[schema_name])
                    _set_at(valid, value_path, allowed)
                    self.assertValid(schema_name, valid)
            invalid = copy.deepcopy(VALID_DOCUMENTS[schema_name])
            _set_at(invalid, value_path, "outside-domain")
            self.assertInvalid(schema_name, invalid)

    def test_unknown_evidence_status_and_semantics_require_a_gap_link(self):
        unknown_cases = [
            (schema_name, value_path, gap_path, "unknown")
            for schema_name, value_path, gap_path in EVIDENCE_CASES
        ]
        unknown_cases.extend(
            (schema_name, value_path, gap_path, value)
            for schema_name, value_path, gap_path in LIFECYCLE_CASES
            for value in ("unknown", "proposed")
        )
        unknown_cases.extend(
            (schema_name, value_path, gap_path, unresolved_value)
            for schema_name, value_path, gap_path, unresolved_value in SEMANTIC_GAP_CASES
        )

        for schema_name, value_path, gap_path, unresolved_value in unknown_cases:
            with self.subTest(
                schema=schema_name, path=value_path, value=unresolved_value
            ):
                valid = copy.deepcopy(VALID_DOCUMENTS[schema_name])
                _set_at(valid, value_path, unresolved_value)
                _link_gap(valid, gap_path)
                self.assertValid(schema_name, valid)

                invalid = copy.deepcopy(valid)
                _set_at(invalid, gap_path, [] if gap_path[-1] == "gapIds" else None)
                self.assertInvalid(schema_name, invalid)

    def test_all_stored_package_paths_reject_absolute_traversal_and_uri_values(self):
        forbidden_paths = (
            "C:/workspace/file.png",
            "C:\\workspace\\file.png",
            "\\\\server\\share\\file.png",
            "\\rooted\\file.png",
            "/rooted/file.png",
            "../secret.png",
            "folder/../../secret.png",
            "file:///tmp/file.png",
            "http://example.test/file.png",
            "https://example.test/file.png",
            "custom:payload",
        )
        for schema_name, value_path in PATH_CASES:
            for forbidden in forbidden_paths:
                with self.subTest(
                    schema=schema_name, path=value_path, forbidden=forbidden
                ):
                    invalid = copy.deepcopy(VALID_DOCUMENTS[schema_name])
                    _set_at(invalid, value_path, forbidden)
                    self.assertInvalid(schema_name, invalid)

        for schema_name in (
            "handoff-config.schema.json",
            "asset-manifest.schema.json",
            "implementation-map.schema.json",
            "design-lock.schema.json",
        ):
            relative_path_schema = self.schemas[schema_name]["$defs"]["relativePath"]
            validator = Draft202012Validator(relative_path_schema)
            for forbidden in forbidden_paths:
                with self.subTest(
                    schema=schema_name, definition="relativePath", forbidden=forbidden
                ):
                    self.assertTrue(list(validator.iter_errors(forbidden)))

    def test_responsive_contracts_require_baseline_scroll_and_evidence_or_approval(self):
        for schema_name, variants_path, mode_key, responsive_entry in RESPONSIVE_CASES:
            with self.subTest(schema=schema_name, rule="baseline-required"):
                missing_baseline = copy.deepcopy(VALID_DOCUMENTS[schema_name])
                _set_at(missing_baseline, variants_path, [])
                self.assertInvalid(schema_name, missing_baseline)

            approved = copy.deepcopy(VALID_DOCUMENTS[schema_name])
            _get_at(approved, variants_path).append(copy.deepcopy(responsive_entry))
            self.assertValid(schema_name, approved)

            directly_evidenced = copy.deepcopy(approved)
            responsive = _get_at(directly_evidenced, variants_path)[-1]
            responsive["evidenceLevel"] = "direct"
            responsive["status"] = "candidate"
            self.assertValid(schema_name, directly_evidenced)

            approved_evidence = copy.deepcopy(approved)
            responsive = _get_at(approved_evidence, variants_path)[-1]
            responsive["evidenceLevel"] = "approved"
            responsive["status"] = "candidate"
            self.assertValid(schema_name, approved_evidence)

            unsupported = copy.deepcopy(approved)
            responsive = _get_at(unsupported, variants_path)[-1]
            responsive["evidenceLevel"] = "derived"
            responsive["status"] = "candidate"
            self.assertInvalid(schema_name, unsupported)

            unknown_with_gap = copy.deepcopy(approved)
            responsive = _get_at(unknown_with_gap, variants_path)[-1]
            responsive["evidenceLevel"] = "unknown"
            responsive["gapIds"] = ["G999"]
            self.assertValid(schema_name, unknown_with_gap)

            unknown_without_gap = copy.deepcopy(unknown_with_gap)
            _get_at(unknown_without_gap, variants_path)[-1]["gapIds"] = []
            self.assertInvalid(schema_name, unknown_without_gap)

            self.assertIn(mode_key, _get_at(approved, variants_path)[-1])

    def test_component_variants_and_states_use_distinct_identity_keys(self):
        valid = VALID_DOCUMENTS["component-registry.schema.json"]
        self.assertValid("component-registry.schema.json", valid)

        variant_with_state_id = copy.deepcopy(valid)
        variant = variant_with_state_id["components"][0]["variants"][0]
        variant["stateId"] = variant.pop("variantId")
        self.assertInvalid("component-registry.schema.json", variant_with_state_id)

        state_with_variant_id = copy.deepcopy(valid)
        state = state_with_variant_id["components"][0]["states"][0]
        state["variantId"] = state.pop("stateId")
        self.assertInvalid("component-registry.schema.json", state_with_variant_id)

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
