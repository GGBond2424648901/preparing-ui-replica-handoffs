# UI Handoff Evidence Graph Final Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade `preparing-ui-replica-handoffs` into a bilingual evidence-graph handoff system that supports multiple authoritative UI design-language images, calibrated UI coordinates, explicit conflicts, deterministic fixtures, traceability, and single-application page delivery.

**Architecture:** Keep the existing deterministic preparation/validation pipeline and add six focused contracts around it: reference relationships, viewport calibration, design-rule cascade, inconsistency ledger, deterministic fixtures, and traceability. Expand existing contracts only where ownership already exists, then enforce cross-contract readiness in the validator. Multimodal visual reading classifies titles and regions; scripts create fail-closed skeletons and validate the Agent-enriched result.

**Tech Stack:** Python 3, JSON Schema Draft 2020-12, Markdown templates, `unittest`, existing plugin/skill helper scripts, Git, Codex plugin CLI.

## Global Constraints

- Original design input is read-only; copied assets remain byte-identical.
- Human-readable output is Chinese-English bilingual; machine keys are stable English.
- A design set may include several design-language boards. Preserve all source boards and merge atomic rules without silent overwrite.
- Explicit visible titles such as `UI 设计语言`, `UI Design Language`, `Design System`, `视觉规范`, and `组件规范` are direct role evidence with source bounds.
- OCR is performed by the multimodal Agent; no external OCR service or runtime dependency is added.
- Desktop Web uses mixed fixed/fluid/bounded/scrollable behavior and one routed application on one development server/shared port.
- Annotation, redline, explanatory, watermark, browser-frame, and device-frame pixels are not implementation UI unless explicitly evidenced.
- Preserve `skill/preparing-ui-replica-handoffs.zip` as an untracked user-owned file.
- Follow RED → GREEN → REFACTOR for behavior changes. Do not install until all verification gates pass.

---

### Task 1: Evidence-graph schemas

**Files:**
- Create: `skill/preparing-ui-replica-handoffs/assets/schemas/reference-relationships.schema.json`
- Create: `skill/preparing-ui-replica-handoffs/assets/schemas/viewport-calibration.schema.json`
- Create: `skill/preparing-ui-replica-handoffs/assets/schemas/design-rule-cascade.schema.json`
- Create: `skill/preparing-ui-replica-handoffs/assets/schemas/design-inconsistencies.schema.json`
- Create: `skill/preparing-ui-replica-handoffs/assets/schemas/deterministic-fixtures.schema.json`
- Create: `skill/preparing-ui-replica-handoffs/assets/schemas/traceability-map.schema.json`
- Modify: `skill/preparing-ui-replica-handoffs/assets/schemas/reference-inventory.schema.json`
- Modify: `skill/preparing-ui-replica-handoffs/assets/schemas/page-inventory.schema.json`
- Modify: `skill/preparing-ui-replica-handoffs/assets/schemas/asset-manifest.schema.json`
- Modify: `tests/test_contract_assets.py`

**Interfaces:**
- Produces contract IDs `RR###`, `CAL###`, `DLS###`, `DR###`, `INC###`, `FIX###`, and `TR###` used by later builders and validator checks.
- `design-rule-cascade.json` supports several `referenceIds` per set and per rule; source duplication is valid, silent conflict resolution is not.

- [ ] **Step 1: Write failing schema inventory and valid-document tests**

Add the six filenames to `REQUIRED_SCHEMAS`, add literal valid documents containing two design-language references in one set, and assert every schema accepts its valid document.

- [ ] **Step 2: Run RED tests**

Run: `python -m unittest tests.test_contract_assets -v`

Expected: FAIL because the six schema files are absent and expanded fields are unsupported.

- [ ] **Step 3: Add invalid multi-board and calibration cases**

Assert rejection of a rule without source references, a silently resolved conflict without winning evidence, calibration whose UI bounds exceed the source canvas, fixture without a page identity, and traceability without source or QA endpoints.

- [ ] **Step 4: Implement schemas and expanded fields**

Use closed objects, bilingual localized text, stable ID patterns, evidence/status/gap fields, and explicit scope/version/theme/module fields. Require title evidence and presentation-frame classification in enriched references while allowing the generated skeleton to use `unknown` plus a gap.

- [ ] **Step 5: Run GREEN tests**

Run: `python -m unittest tests.test_contract_assets -v`

Expected: PASS.

### Task 2: Deterministic skeleton generation

**Files:**
- Modify: `tests/test_prepare_handoff.py`
- Modify: `skill/preparing-ui-replica-handoffs/scripts/prepare_handoff.py`
- Modify: `skill/preparing-ui-replica-handoffs/assets/templates/docs/zh/design-catalog.template.md`
- Modify: `skill/preparing-ui-replica-handoffs/assets/templates/docs/en/design-catalog.template.md`
- Modify: `skill/preparing-ui-replica-handoffs/assets/templates/docs/zh/ui-design-language.template.md`
- Modify: `skill/preparing-ui-replica-handoffs/assets/templates/docs/en/ui-design-language.template.md`
- Modify: `skill/preparing-ui-replica-handoffs/assets/templates/docs/zh/page-contract.template.md`
- Modify: `skill/preparing-ui-replica-handoffs/assets/templates/docs/en/page-contract.template.md`

**Interfaces:**
- Produces all six new JSON files for every preparation run.
- Existing image scanning remains deterministic and does not guess image semantics from filenames.

- [ ] **Step 1: Write failing output-tree test**

Prepare two temporary images and assert the output includes all six contracts, one provisional relationship/calibration/fixture/traceability record per candidate page where appropriate, and an empty but gap-linked design-language set/inconsistency skeleton.

- [ ] **Step 2: Run RED test**

Run: `python -m unittest tests.test_prepare_handoff.PrepareHandoffTests.test_generates_evidence_graph_contracts -v`

Expected: FAIL because the files do not exist.

- [ ] **Step 3: Implement focused builders**

Add `_build_reference_relationships`, `_build_viewport_calibrations`, `_build_design_rule_cascade`, `_build_design_inconsistencies`, `_build_deterministic_fixtures`, and `_build_traceability_map`. Register schemas in `SCHEMA_CONTRACTS`, include references in page inventory, and preserve deterministic ordering.

- [ ] **Step 4: Expand bilingual skeleton documents**

Add explicit multimodal title recognition, multiple-board grouping/merge rules, presentation-frame exclusion, calibration, inconsistency, fixture, and traceability sections with no claim that the script performed OCR.

- [ ] **Step 5: Run GREEN and determinism tests**

Run: `python -m unittest tests.test_prepare_handoff -v`

Expected: PASS, including byte-identical repeated output.

### Task 3: Cross-contract readiness validation

**Files:**
- Modify: `tests/test_validate_handoff.py`
- Modify: `skill/preparing-ui-replica-handoffs/scripts/validate_handoff.py`

**Interfaces:**
- Consumes all new contracts and emits stable issue codes.
- Produces fail-closed readiness checks without changing source or Git state.

- [ ] **Step 1: Write failing missing-contract and reference-integrity tests**

Add cases for missing new files, unknown referenced IDs, design-language references with no set/rule/gap disposition, approved pages without calibration/fixture/traceability, and traceability endpoints that do not exist.

- [ ] **Step 2: Write failing multiple-board conflict tests**

Create two design-language references whose rules conflict and assert `DESIGN_RULE_CONFLICT_UNRESOLVED`; assert no issue when the conflict has explicit winner evidence and the losing rule remains preserved.

- [ ] **Step 3: Write failing presentation-frame test**

Approve a page whose UI bounds include a declared annotation/browser-frame region without explicit inclusion evidence and assert a stable failure code.

- [ ] **Step 4: Run RED tests**

Run: `python -m unittest tests.test_validate_handoff -v`

Expected: new tests FAIL because checks are absent.

- [ ] **Step 5: Implement validation in focused functions**

Add schema registration, nonempty/unknown checks, ID indexes, relationship endpoint checks, calibration containment checks, design-language set coverage, conflict-resolution checks, inconsistency severity checks, fixture coverage, and traceability endpoint checks. Keep skeleton output incomplete by design.

- [ ] **Step 6: Run GREEN tests**

Run: `python -m unittest tests.test_validate_handoff -v`

Expected: PASS.

### Task 4: Advanced assets, capture, Diff, components, and application contracts

**Files:**
- Modify: `skill/preparing-ui-replica-handoffs/assets/schemas/ui-style-contract.schema.json`
- Modify: `skill/preparing-ui-replica-handoffs/assets/schemas/component-registry.schema.json`
- Modify: `skill/preparing-ui-replica-handoffs/assets/schemas/micro-visual-contract.schema.json`
- Modify: `skill/preparing-ui-replica-handoffs/assets/schemas/capture-profile.schema.json`
- Modify: `skill/preparing-ui-replica-handoffs/assets/schemas/diff-regions.schema.json`
- Modify: `skill/preparing-ui-replica-handoffs/assets/schemas/application-system.schema.json`
- Modify: `skill/preparing-ui-replica-handoffs/assets/schemas/implementation-plan.schema.json`
- Modify: `tests/test_contract_assets.py`
- Modify: `tests/test_prepare_handoff.py`

**Interfaces:**
- Adds rule lineage, font/icon/asset readiness, overlay/portal behavior, color/text/perceptual capture semantics, masks, and page-family inheritance.

- [ ] **Step 1: Write failing contract examples**

Add literal tests for font fallback metrics, overlay roots and scroll lock, geometry/paint/text tolerances, dynamic masks, color profile, full-page sticky capture, theme/density families, and page readiness prerequisites.

- [ ] **Step 2: Run RED contract tests**

Run: `python -m unittest tests.test_contract_assets -v`

Expected: FAIL on unsupported fields.

- [ ] **Step 3: Implement schema and builder expansions**

Add fields without adding external dependencies. Generated values remain `unknown`/`proposed` and gap-linked when not directly known.

- [ ] **Step 4: Run GREEN tests**

Run: `python -m unittest tests.test_contract_assets tests.test_prepare_handoff -v`

Expected: PASS.

### Task 5: Bilingual operational guidance and discovery

**Files:**
- Modify: `skill/preparing-ui-replica-handoffs/SKILL.md`
- Modify: `skill/preparing-ui-replica-handoffs/agents/openai.yaml`
- Modify: all paired files under `skill/preparing-ui-replica-handoffs/references/zh/` and `references/en/`
- Modify: paired templates under `assets/templates/docs/zh/` and `assets/templates/docs/en/`
- Modify: `tests/test_skill_content.py`
- Modify: `tests/test_bilingual_parity.py`
- Modify: `tests/test_skill_scaffold.py`

**Interfaces:**
- Gives downstream Agents the exact inspection order and decision recipes.
- Keeps detailed rules in references while `SKILL.md` remains procedural and discoverable.

- [ ] **Step 1: Write failing behavioral-structure tests**

Assert required bundled files and generated document pairs exist. Assert generated output exposes corresponding section IDs and machine references instead of merely searching for prose wording.

- [ ] **Step 2: Run RED tests**

Run: `python -m unittest tests.test_skill_content tests.test_bilingual_parity tests.test_skill_scaffold -v`

Expected: FAIL until the new workflow and files are wired.

- [ ] **Step 3: Update bilingual guidance**

Add recipes for title-based direct classification, several design-language images, set grouping, duplicate/complement/conflict behavior, frame exclusion, calibration, inconsistency treatment, deterministic state, overlays, fonts/assets, and traceability. Include a quick-reference decision table and common mistakes.

- [ ] **Step 4: Run GREEN tests and parity**

Run: `python -m unittest tests.test_skill_content tests.test_bilingual_parity tests.test_skill_scaffold -v`

Expected: PASS.

### Task 6: Mirror, package, and final verification

**Files:**
- Mirror: `skill/preparing-ui-replica-handoffs/` → `plugin/preparing-ui-replica-handoffs/skills/preparing-ui-replica-handoffs/`
- Modify: `plugin/preparing-ui-replica-handoffs/.codex-plugin/plugin.json`
- Update: `D:/AI_Demo/Result/preparing-ui-replica-handoffs-plugin.zip`

**Interfaces:**
- Produces an embedded plugin skill byte-equivalent to the source skill and a new cachebuster version.

- [ ] **Step 1: Run the full repository test suite**

Run: `python -m unittest discover -s tests -v`

Expected: all tests PASS.

- [ ] **Step 2: Run a forward temporary-image scenario**

Generate a handoff from temporary images, verify all schemas and bilingual parity, then run the full validator and confirm it fails only for intentional unresolved enrichment gaps—not structural/schema/path errors.

- [ ] **Step 3: Validate source skill**

Run the official `quick_validate.py` against the source skill and expect success.

- [ ] **Step 4: Mirror and update plugin metadata/version**

Use checked `robocopy /MIR` within the exact repository plugin target, update capabilities, and run `update_plugin_cachebuster.py`.

- [ ] **Step 5: Validate embedded skill, plugin, and parity**

Run official skill validation on the embedded copy, plugin validation on the plugin root, repository parity tests, and source/embedded file-hash comparison. Expect all checks to pass.

- [ ] **Step 6: Commit only intended repository files**

Stage tracked changes and explicit new files. Confirm `skill/preparing-ui-replica-handoffs.zip` remains untracked. Commit with `feat: finalize UI handoff evidence graph`.

- [ ] **Step 7: Reinstall and package**

Mirror to `C:/Users/PC/plugins/preparing-ui-replica-handoffs`, run `codex plugin add preparing-ui-replica-handoffs@personal`, and rebuild `D:/AI_Demo/Result/preparing-ui-replica-handoffs-plugin.zip`.

- [ ] **Step 8: Fresh post-install verification**

Read the installed manifest and skill path, confirm the installed version matches the new cachebuster, rerun plugin validation against the installed root, and report exact test counts and paths.
