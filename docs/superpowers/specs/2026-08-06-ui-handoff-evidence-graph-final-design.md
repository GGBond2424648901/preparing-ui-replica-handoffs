# UI Handoff Evidence Graph Final Design

## Objective

Upgrade `preparing-ui-replica-handoffs` from a detailed file collection into a bilingual, evidence-graph-driven contract system. A downstream multimodal Agent must be able to distinguish authoritative UI design-language images from product pages, combine several design-language boards without silent overwrite, calibrate the actual UI canvas, resolve contradictions, and reproduce every page inside one routed desktop-Web application.

## Approved assumptions

- Input is primarily raster design imagery inspected directly by a multimodal Agent; no separate OCR service is required.
- A design set may contain zero, one, or many images whose visible title explicitly says `UI 设计语言`, `UI Design Language`, `Design System`, `视觉规范`, `组件规范`, or an equivalent product-specific phrase.
- Visible title text and its source bounds are direct classification evidence. Filenames are only candidate clues.
- Several design-language images form one or more reference sets. They may be complementary, duplicate, scoped to different modules/themes, different versions, or contradictory.
- All generated human-readable material remains Chinese-English bilingual. Machine keys remain stable English.
- Desktop Web remains the primary target. One application, one Router, one development server, and one shared port remain mandatory unless the user explicitly approves a microfrontend exception.
- The original design directory remains read-only. The existing untracked ZIP is user-owned and must not be staged or modified.

## Evidence-graph architecture

### Reference nodes

Every copied source has `assetId` and `referenceId`. A multimodal inspection pass records:

- visible title transcription, language, bounds, and confidence;
- role: page, design language, component board, brand board, state board, motion reference, decorative background, content asset, or unknown;
- presentation frame: real UI, annotation/redline, browser/device chrome, explanatory text, watermark, or mixed;
- actual UI bounds inside the source image;
- authority class, version, theme, module, and scope.

Explicit design-language titles make the role direct evidence and remove that reference from formal page candidates.

### Reference edges

`reference-relationships.json` stores typed edges rather than relying on filename order. Supported relationships include:

- `same-page-continuation`, `detail-of`, `state-of`, `variant-of`, `responsive-of`, `overlay-of`;
- `design-language-for`, `component-source-for`, `brand-source-for`;
- `duplicates`, `complements`, `supersedes`, `conflicts-with`, and `derived-from`.

Every edge has direction, evidence bounds or rationale, status, evidence level, and gaps. This lets several images describe one page or several boards describe one design language.

### Design-language sets and cascade

`design-rule-cascade.json` groups multiple design-language references into stable sets. A set records product/module/theme/version scope and contains atomic rules. Each rule has one or more source `referenceIds`, source regions, value, scope, exceptions, precedence, affected tokens/components/pages, and conflict status.

Merge behavior is explicit:

- identical rules retain all supporting sources;
- complementary rules merge into the same set;
- scoped rules coexist by module/theme/version;
- later versions supersede earlier versions only when version evidence is direct or approved;
- conflicting rules create a conflict record and remain unresolved until authority order selects a winner;
- a user correction or page-specific direct design can override an inherited rule without rewriting the global rule.

### Canvas calibration and presentation-frame exclusion

`viewport-calibration.json` separates source-image pixels from implementation coordinates. Each reference records source dimensions, actual UI viewport bounds, crop offset, inferred/source scale, effective DPR, browser/device frame bounds, annotation regions, full content extent, fixed/sticky regions, and confidence.

Redlines, measurement arrows, explanatory notes, watermarks, device mockup frames, and browser chrome are evidence metadata, not implementation content, unless explicitly identified as part of the product UI.

### Inconsistency ledger

`design-inconsistencies.json` records AI-generated or cross-board contradictions such as malformed icons, impossible perspective, different component geometry, conflicting copy, broken alignments, and incompatible tokens. Each issue records competing evidence, affected objects, recommended treatment (`preserve-page-specific`, `canonicalize`, `redraw`, `infer-copy`, or `unresolved`), authority decision, and acceptance impact.

The Agent must never silently choose the most convenient interpretation.

### Deterministic reproduction

`deterministic-fixtures.json` stabilizes visual capture. It records page/state/variant, locale, permissions, sample dataset, time, timezone, random seed, avatar/media assets, chart values, network state, animation completion, cursor, scroll positions, and masking rules. Unknown values remain gap-linked.

The existing capture profile records the browser environment; fixtures record application state. Both are required for reproducible Diff.

### Traceability

`traceability-map.json` links:

`reference region → design-language rule/token → component or micro feature → page instance → implementation target → QA target`.

This is the downstream Agent's audit trail and prevents rules from existing only as prose.

## Existing-contract upgrades

- `reference-inventory.json`: add title evidence, presentation-frame classification, version/theme/module, UI bounds, design-language-set membership, and frozen page-candidate disposition.
- `page-inventory.json`: add reference relationship IDs, calibration IDs, inherited design-rule IDs, inconsistency IDs, fixture IDs, and traceability IDs.
- `asset-manifest.json`: add asset purpose, pixel density, alpha/color-profile observations, formal/generated status, license/source gaps, and extraction needs.
- `ui-style-contract.json`: link every token to design-rule IDs and allow module/theme/version scopes.
- `component-registry.json`: add inheritance and override lineage, font/icon/asset readiness, overlay/portal behavior, and shared-component drift handling.
- `micro-visual-contract.json`: link calibration and design-rule sources and distinguish geometry, paint, text-rendering, and asset tolerances.
- `capture-profile.json`: add operating system, font rasterization, color gamut/profile, screenshot mode, full-page/sticky handling, and readiness waits.
- `diff-regions.json`: add perceptual/geometry/text modes, dynamic masks, anti-alias tolerance, sticky-region capture rules, and feature-level targets.
- `application-system.json`: add page-family inheritance, overlay roots, theme/density families, and shared deterministic state.
- `implementation-plan.json`: require reference classification, calibration, inconsistency resolution, fixture readiness, and traceability before a page can become ready.

## Bilingual human contracts

The four existing top-level documents remain. They gain these responsibilities:

- `设计稿总目录.md / Design-Catalog.md`: list reference sets, relationships, page candidates removed after classification, versions, modules, and unresolved conflicts.
- `UI设计语言.md / UI-Design-Language.md`: document every design-language set, all source boards, atomic rules, merge decisions, cascade, exceptions, and conflicts.
- `UI实施说明.md / UI-Implementation-Guide.md`: define multimodal title recognition, presentation-frame exclusion, calibration, deterministic fixtures, single-app implementation, and page gates.
- `组件规范.md / Component-Specification.md`: define font, icon, SVG/CSS/Canvas/raster readiness, overlays/portals, inheritance, and cross-page drift policy.

Every page contract gains source relationships, calibrated coordinate space, inherited rules and overrides, inconsistency decisions, deterministic fixture, traceability, and advanced Diff sections.

## Validation and readiness

Readiness fails when any of the following is true:

- a visible design-language title remains classified as an ordinary approved page;
- a design-language reference has no set membership or no extracted-rule/gap disposition;
- multiple design-language boards silently overwrite one another;
- a page references annotation/browser/device-frame pixels as UI without explicit evidence;
- approved page geometry lacks calibration;
- unresolved major inconsistencies affect implementation;
- an approved page lacks deterministic fixture and traceability coverage;
- Diff lacks geometry/paint/text or justified exclusions;
- a page is only available on an isolated server/port.

## Testing strategy

- Unit-test all new schemas with valid and invalid multi-board examples.
- Add RED tests proving the current generator omits the new contracts, then generate deterministic skeletons for them.
- Add validator tests for missing contracts, broken references, silent multi-board conflict, approved pages without calibration/fixtures/traceability, and illegal page use of non-UI presentation frames.
- Run bilingual parity, complete unit suite, skill validation, plugin validation, and a forward generation/validation scenario from temporary images.
- Reinstall only after all checks pass and the source skill matches the embedded plugin copy.

## Definition of final

The upgraded plugin is the final version for the currently approved problem scope when all planned contracts, bilingual guidance, generator output, validator gates, unit tests, forward scenario, plugin validation, installation, and Git-scope checks pass. Future product-specific rules may extend evidence content, but must not require another structural redesign of the handoff architecture.
