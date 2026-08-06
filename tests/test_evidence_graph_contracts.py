import copy
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = (
    REPOSITORY_ROOT
    / "skill"
    / "preparing-ui-replica-handoffs"
    / "assets"
    / "schemas"
)

SCHEMA_NAMES = {
    "reference-relationships.schema.json",
    "viewport-calibration.schema.json",
    "design-rule-cascade.schema.json",
    "design-inconsistencies.schema.json",
    "deterministic-fixtures.schema.json",
    "traceability-map.schema.json",
    "navigation-reconciliation.schema.json",
    "motion-contract.schema.json",
    "semantic-visual-encoding.schema.json",
}


def _localized(zh, en):
    return {"zh-CN": zh, "en-US": en}


VALID_DOCUMENTS = {
    "reference-relationships.schema.json": {
        "schemaVersion": "1.0.0",
        "relationships": [
            {
                "relationshipId": "RR001",
                "fromReferenceId": "REF001",
                "toReferenceId": "REF002",
                "type": "complements",
                "direction": "bidirectional",
                "sourceBounds": None,
                "rationale": _localized("两张设计语言图互补", "The design-language boards complement each other"),
                "status": "approved",
                "evidenceLevel": "direct",
                "gapIds": [],
            }
        ],
    },
    "viewport-calibration.schema.json": {
        "schemaVersion": "1.0.0",
        "calibrations": [
            {
                "calibrationId": "CAL001",
                "referenceId": "REF001",
                "sourceCanvas": {"width": 1920, "height": 1080},
                "uiViewportBounds": {"x": 120, "y": 80, "width": 1600, "height": 900},
                "cropOffset": {"x": 0, "y": 0},
                "sourceScale": 1,
                "effectiveDpr": 1,
                "fullContentExtent": {"width": 1600, "height": 1800},
                "presentationRegions": [
                    {
                        "presentationRegionId": "PR001",
                        "role": "annotation",
                        "bounds": {"x": 0, "y": 0, "width": 100, "height": 40},
                        "includeInImplementation": False,
                        "evidenceLevel": "direct",
                        "gapIds": [],
                    }
                ],
                "fixedRegionIds": [],
                "stickyRegionIds": [],
                "status": "approved",
                "evidenceLevel": "derived",
                "gapIds": [],
            }
        ],
    },
    "design-rule-cascade.schema.json": {
        "schemaVersion": "1.0.0",
        "designLanguageSets": [
            {
                "designLanguageSetId": "DLS001",
                "name": _localized("产品设计语言", "Product design language"),
                "referenceIds": ["REF001", "REF002"],
                "version": "v1",
                "theme": "light",
                "module": "global",
                "scope": "global",
                "mergeStrategy": "evidence-graph",
                "ruleIds": ["DR001"],
                "status": "approved",
                "evidenceLevel": "direct",
                "gapIds": [],
            }
        ],
        "rules": [
            {
                "ruleId": "DR001",
                "designLanguageSetId": "DLS001",
                "category": "materials",
                "name": _localized("卡片材质", "Card material"),
                "value": {"blur": 20, "border": "1px solid rgba(255,255,255,.5)"},
                "sourceEvidence": [
                    {"referenceId": "REF001", "bounds": {"x": 10, "y": 20, "width": 200, "height": 100}},
                    {"referenceId": "REF002", "bounds": {"x": 30, "y": 40, "width": 220, "height": 120}},
                ],
                "scope": "global",
                "module": "global",
                "theme": "light",
                "version": "v1",
                "precedence": 100,
                "exceptionPageIdentities": [],
                "affectedTokenIds": ["material-card"],
                "affectedComponentIds": ["card"],
                "affectedPageIdentities": [],
                "conflictIds": [],
                "status": "approved",
                "evidenceLevel": "direct",
                "gapIds": [],
            }
        ],
        "conflicts": [],
    },
    "design-inconsistencies.schema.json": {
        "schemaVersion": "1.0.0",
        "inconsistencies": [
            {
                "inconsistencyId": "INC001",
                "category": "component-geometry",
                "summary": _localized("卡片圆角不一致", "Card radii differ"),
                "referenceIds": ["REF001", "REF002"],
                "affectedObjectIds": ["card"],
                "severity": "major",
                "treatment": "canonicalize",
                "winningEvidenceReferenceIds": ["REF002"],
                "decisionRationale": _localized("新版设计语言优先", "The newer design-language board wins"),
                "acceptanceImpact": _localized("全部卡片使用新版圆角", "All cards use the newer radius"),
                "status": "resolved",
                "evidenceLevel": "approved",
                "gapIds": [],
            }
        ],
    },
    "deterministic-fixtures.schema.json": {
        "schemaVersion": "1.0.0",
        "fixtures": [
            {
                "fixtureId": "FIX001",
                "pageId": "P001",
                "stateId": "S01",
                "variantId": "V01",
                "locale": "zh-CN",
                "permissionProfile": "admin",
                "clock": "2026-08-06T10:00:00+08:00",
                "timezone": "Asia/Shanghai",
                "randomSeed": 42,
                "dataFixturePath": "fixtures/P001-S01-V01.json",
                "assetIds": ["A001"],
                "networkState": "settled",
                "animationState": "completed",
                "cursor": "hidden",
                "scrollPositions": [{"ownerId": "page", "x": 0, "y": 0}],
                "dynamicMaskIds": ["MASK001"],
                "status": "approved",
                "evidenceLevel": "approved",
                "gapIds": [],
            }
        ],
    },
    "traceability-map.schema.json": {
        "schemaVersion": "1.0.0",
        "entries": [
            {
                "traceabilityId": "TR001",
                "sourceReferenceIds": ["REF001", "REF002"],
                "sourceRuleIds": ["DR001"],
                "sourceBounds": [{"referenceId": "REF001", "bounds": {"x": 10, "y": 20, "width": 200, "height": 100}}],
                "tokenIds": ["material-card"],
                "componentIds": ["card"],
                "microVisualFeatureIds": [],
                "pageIdentities": [{"pageId": "P001", "stateId": "S01", "variantId": "V01"}],
                "implementationTargets": [{"file": "src/components/card.tsx", "symbol": "Card"}],
                "qaIds": ["QA001"],
                "status": "approved",
                "evidenceLevel": "approved",
                "gapIds": [],
            }
        ],
    },
    "navigation-reconciliation.schema.json": {
        "schemaVersion": "1.0.0",
        "navigationSystems": [
            {
                "navigationSystemId": "NAV001",
                "shellId": "app-shell",
                "sourceReferenceIds": ["REF001", "REF002"],
                "observations": [
                    {
                        "observationId": "NOBS001",
                        "referenceId": "REF001",
                        "pageIdentity": {"pageId": "P001", "stateId": "S01", "variantId": "V01"},
                        "navigationPresence": "present",
                        "entries": [
                            {
                                "navigationEvidenceId": "NEV001",
                                "parentEvidenceId": None,
                                "order": 1,
                                "label": _localized("管理驾驶舱", "Management cockpit"),
                                "copyClassification": "verbatim",
                                "iconName": "gauge",
                                "targetRoute": "/dashboard",
                                "visibilityRule": "all-users",
                                "bounds": {"x": 20, "y": 100, "width": 180, "height": 40},
                                "evidenceLevel": "direct",
                                "gapIds": [],
                            }
                        ],
                        "evidenceLevel": "direct",
                        "gapIds": [],
                    }
                ],
                "canonicalEntries": [
                    {
                        "navigationEntryId": "NAVITEM001",
                        "parentNavigationEntryId": None,
                        "order": 1,
                        "label": _localized("管理驾驶舱", "Management cockpit"),
                        "iconName": "gauge",
                        "targetRoute": "/dashboard",
                        "visibilityRule": "all-users",
                        "sourceObservationIds": ["NOBS001"],
                        "status": "approved",
                        "evidenceLevel": "approved",
                        "gapIds": [],
                    }
                ],
                "discrepancies": [
                    {
                        "navigationDiscrepancyId": "NAVD001",
                        "type": "missing-entry",
                        "referenceIds": ["REF002"],
                        "affectedNavigationEntryIds": ["NAVITEM001"],
                        "resolution": _localized("按公共导航保留", "Keep as a shared navigation entry"),
                        "winningObservationIds": ["NOBS001"],
                        "status": "resolved",
                        "evidenceLevel": "approved",
                        "gapIds": [],
                    }
                ],
                "freezeStatus": "approved",
                "freezeDecision": _localized("导航树已冻结", "The navigation tree is frozen"),
                "evidenceLevel": "approved",
                "gapIds": [],
            }
        ],
    },
    "motion-contract.schema.json": {
        "schemaVersion": "1.0.0",
        "motions": [
            {
                "motionId": "MOT001",
                "name": _localized("导航悬停高亮", "Navigation hover highlight"),
                "targetType": "navigation",
                "targetIds": ["NAVITEM001"],
                "trigger": "hover",
                "sourceEvidence": [
                    {"referenceId": "REF001", "bounds": {"x": 20, "y": 100, "width": 180, "height": 40}}
                ],
                "initialState": {"backgroundOpacity": 0, "translateX": 0},
                "finalState": {"backgroundOpacity": 1, "translateX": 2},
                "durationMs": 180,
                "delayMs": 0,
                "easing": "cubic-bezier(0.2, 0, 0, 1)",
                "animatedProperties": ["background-color", "transform"],
                "transformOrigin": "center",
                "layerBehavior": "preserve-stacking-context",
                "pointerBehavior": "pointer remains interactive",
                "focusBehavior": "keyboard focus receives an equivalent visible state",
                "reducedMotion": {"strategy": "remove-transform", "durationMs": 0, "finalState": {"backgroundOpacity": 1}},
                "stateFrameReferenceIds": ["REF001"],
                "status": "approved",
                "evidenceLevel": "direct",
                "gapIds": [],
            }
        ],
    },
    "semantic-visual-encoding.schema.json": {
        "schemaVersion": "1.0.0",
        "dimensions": [
            {
                "semanticDimensionId": "SEM001",
                "name": _localized("优先级", "Priority"),
                "category": "priority",
                "exclusivity": "single",
                "sourceReferenceIds": ["REF001"],
                "values": [
                    {
                        "semanticValueId": "SEMVAL001",
                        "code": "P0",
                        "label": _localized("P0", "P0"),
                        "meaning": _localized("最高优先级", "Highest priority"),
                        "shape": "pill",
                        "colorRoles": {
                            "text": {"tokenId": "semantic-priority-p0-text", "rawValue": "#E5484D"},
                            "background": {"tokenId": "semantic-priority-p0-bg", "rawValue": "#FFF1F1"},
                            "border": {"tokenId": "semantic-priority-p0-border", "rawValue": "#FFD1D1"},
                            "indicator": {"tokenId": None, "rawValue": None},
                            "icon": {"tokenId": None, "rawValue": None},
                        },
                        "geometry": {
                            "height": 28, "minWidth": 46, "paddingX": 12,
                            "paddingY": 4, "gap": 6, "radius": 999,
                            "borderWidth": 1, "indicatorDiameter": None, "iconSize": None,
                        },
                        "typography": {
                            "fontTokenId": "label-sm", "fontSize": 14,
                            "fontWeight": 600, "lineHeight": 20,
                        },
                        "interactionStates": ["default", "hover", "focus-visible", "selected", "disabled"],
                        "ordering": 0,
                        "contrastRequirement": "WCAG AA for text and non-text indicators",
                        "sourceEvidence": [{"referenceId": "REF001", "bounds": {"x": 10, "y": 60, "width": 48, "height": 28}}],
                        "status": "approved",
                        "evidenceLevel": "direct",
                        "gapIds": [],
                    }
                ],
                "forbiddenConflations": [
                    _localized("P0 红色表示优先级，不自动表示错误状态", "P0 red means priority and does not automatically mean an error")
                ],
                "status": "approved",
                "evidenceLevel": "direct",
                "gapIds": [],
            }
        ],
    },
}


class EvidenceGraphContractTests(unittest.TestCase):
    def _schema(self, name):
        path = SCHEMA_ROOT / name
        self.assertTrue(path.is_file(), f"missing schema: {name}")
        schema = json.loads(path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        return schema

    def assertValid(self, name, document):
        errors = list(Draft202012Validator(self._schema(name)).iter_errors(document))
        self.assertEqual(errors, [], "\n".join(error.message for error in errors))

    def assertInvalid(self, name, document):
        errors = list(Draft202012Validator(self._schema(name)).iter_errors(document))
        self.assertTrue(errors, f"{name} unexpectedly accepted {document!r}")

    def test_all_evidence_graph_schemas_accept_complete_contracts(self):
        self.assertSetEqual(set(VALID_DOCUMENTS), SCHEMA_NAMES)
        for name, document in VALID_DOCUMENTS.items():
            with self.subTest(schema=name):
                self.assertValid(name, document)

    def test_design_language_set_preserves_multiple_source_boards(self):
        document = copy.deepcopy(VALID_DOCUMENTS["design-rule-cascade.schema.json"])
        self.assertValid("design-rule-cascade.schema.json", document)
        self.assertEqual(document["designLanguageSets"][0]["referenceIds"], ["REF001", "REF002"])
        self.assertEqual(
            [source["referenceId"] for source in document["rules"][0]["sourceEvidence"]],
            ["REF001", "REF002"],
        )

    def test_design_rule_requires_at_least_one_source_reference(self):
        document = copy.deepcopy(VALID_DOCUMENTS["design-rule-cascade.schema.json"])
        document["rules"][0]["sourceEvidence"] = []
        self.assertInvalid("design-rule-cascade.schema.json", document)

    def test_resolved_inconsistency_requires_winning_evidence(self):
        document = copy.deepcopy(VALID_DOCUMENTS["design-inconsistencies.schema.json"])
        document["inconsistencies"][0]["winningEvidenceReferenceIds"] = []
        self.assertInvalid("design-inconsistencies.schema.json", document)

    def test_traceability_requires_source_and_qa_endpoints(self):
        for field in ("sourceReferenceIds", "qaIds"):
            with self.subTest(field=field):
                document = copy.deepcopy(VALID_DOCUMENTS["traceability-map.schema.json"])
                document["entries"][0][field] = []
                self.assertInvalid("traceability-map.schema.json", document)

    def test_navigation_discrepancy_requires_an_evidence_backed_resolution(self):
        document = copy.deepcopy(VALID_DOCUMENTS["navigation-reconciliation.schema.json"])
        document["navigationSystems"][0]["discrepancies"][0]["winningObservationIds"] = []
        self.assertInvalid("navigation-reconciliation.schema.json", document)

    def test_motion_contract_requires_source_evidence_and_reduced_motion(self):
        for field, value in (("sourceEvidence", []), ("reducedMotion", None)):
            with self.subTest(field=field):
                document = copy.deepcopy(VALID_DOCUMENTS["motion-contract.schema.json"])
                document["motions"][0][field] = value
                self.assertInvalid("motion-contract.schema.json", document)

    def test_semantic_value_requires_measured_source_evidence(self):
        document = copy.deepcopy(VALID_DOCUMENTS["semantic-visual-encoding.schema.json"])
        document["dimensions"][0]["values"][0]["sourceEvidence"] = []
        self.assertInvalid("semantic-visual-encoding.schema.json", document)

    def test_equal_hues_do_not_merge_independent_semantic_dimensions(self):
        document = copy.deepcopy(VALID_DOCUMENTS["semantic-visual-encoding.schema.json"])
        error_dimension = copy.deepcopy(document["dimensions"][0])
        error_dimension["semanticDimensionId"] = "SEM002"
        error_dimension["name"] = _localized("反馈状态", "Feedback status")
        error_dimension["category"] = "feedback"
        error_dimension["values"][0]["semanticValueId"] = "SEMVAL002"
        error_dimension["values"][0]["code"] = "error"
        error_dimension["values"][0]["meaning"] = _localized("错误", "Error")
        document["dimensions"].append(error_dimension)
        self.assertValid("semantic-visual-encoding.schema.json", document)

    def test_visible_reference_title_requires_measured_bounds(self):
        schema = json.loads(
            (SCHEMA_ROOT / "reference-inventory.schema.json").read_text(
                encoding="utf-8"
            )
        )
        reference = copy.deepcopy(
            __import__("tests.test_contract_assets", fromlist=["VALID_DOCUMENTS"])
            .VALID_DOCUMENTS["reference-inventory.schema.json"]
        )
        reference["references"][0]["titleEvidence"]["bounds"] = None
        errors = list(Draft202012Validator(schema).iter_errors(reference))
        self.assertTrue(errors)


if __name__ == "__main__":
    unittest.main()
