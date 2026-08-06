# Delivery Package Specification

sectionId: package-tree

## Fixed tree

ruleId: DP-001

The standard root contains `README.md`, `assets/designs/<design-version>/`, `docs/zh/`, `docs/en/`, `contracts/`, `reports/`, and `tools/`. Do not add runtime dependencies on the creating machine, another skill, or remote resources.

ruleId: DP-002

Chinese documents include at least `设计稿总目录.md`, `UI设计语言.md`, `UI实施说明.md`, `组件规范.md`, and `pages/<page-state-variant>.md`; English mirrors are `Design-Catalog.md`, `UI-Design-Language.md`, `UI-Implementation-Guide.md`, `Component-Specification.md`, and same-ID page documents.

sectionId: catalog

## Catalog responsibility

ruleId: DP-003

The design catalog records page/state/variant ID, name, module, source and copied image, original canvas, SHA-256, suggested route and evidence, status, priority, shell type, assets, per-page contract link, and gaps. It is a navigation index, not a replacement for page contracts.

sectionId: implementation-guide

## Implementation guide responsibility

ruleId: DP-004

The UI implementation guide defines global workflow, authority order, native-pixel baseline, the distinction between captured canvas and content extent, fixed/fluid/bounded-fluid sizing, min/base/max dimensions, Grid/Flex growth and surplus-space allocation, wide/narrow/browser-zoom behavior, page/region/hybrid scroll strategy, implementation sequence, and for each `P###-S##-V##` its regions, geometry, components, copy, icons, data, interactions, states, responsiveness, mappings, and acceptance contract.

ruleId: DP-005

Each page document lets a downstream Agent distinguish direct evidence, derivation, candidate, approval, and unknown. Any pending decision references a `gapId` rather than hiding uncertainty in prose.

sectionId: component-spec

## Component specification responsibility

ruleId: DP-006

The component specification records exact tokens, shells, Logo, icon mappings, component anatomy/dimensions/states/interactions/content bounds/accessibility, and page reuse matrix. Complex coverage includes visible navigation, cards, buttons, tables, AI conversation, files, workflows, Diff, and logs.

sectionId: contracts

## Machine contracts

ruleId: DP-007

`contracts/` contains the requirement ledger, gap register, asset manifest, reference inventory, page inventory, UI style contract, micro visual contract, component registry, application system, implementation map, implementation plan, capture profile, diff regions, visual QA matrix, and design lock. Stable keys are English; readable fields expose `zh-CN`/`en-US`.

ruleId: DP-008

The requirement ledger maps every requirement to page, region, component, interaction, and QA. The implementation map points the same target to proposed code locations without fabricating real files. The gap register preserves unknowns and approval lifecycle.

ruleId: DP-009

The script computes the design lock from the delivery file set and hashes. Never hand-author it, copy an old lock, or include the validation report as lock input; a change to any locked file fails and requires refreezing.

sectionId: paths-links

## Paths and links

ruleId: DP-010

All stored paths and Markdown image/document links are relative paths contained by the handoff root. Reject drive paths, UNC paths, root paths, `file:`/HTTP URIs, traversal, linked directories, and alias overwrites.

ruleId: DP-011

Every normalized design copy maps one-to-one to a source, is byte-hash identical, and has a stable Agent-readable English numbered name. Use `unclassified` when semantics are unknown; the utility never guesses page business meaning from filenames.

sectionId: generation

## Generation and Agent enrichment

ruleId: DP-012

`prepare_handoff.py` creates a deterministic initial skeleton and `build_contact_sheet.py` creates its index. An Agent then inspects full-resolution images and enriches every contract. The initial skeleton has unresolved `blocker`/`major` items and is expected to fail closed.

ruleId: DP-013

Updates operate only on clearly owned handoff directories and use collision-safe no-overwrite publication. On concurrent conflict, invalid recovery directory, or unclear ownership, preserve evidence and stop; never recursively delete unknown content.

sectionId: bilingual

## Bilingual parity

ruleId: DP-014

Chinese and English prose may differ, but file pairing, page IDs, section IDs, rule IDs, placeholders, and image-reference sets match. Run `check_bilingual_parity.py`; translating titles while omitting rules is not parity.

sectionId: completion

## Definition of done

ruleId: DP-015

Claim implementation readiness only when sources are unchanged, bilingual coverage is complete, machine contracts are nonempty and referentially valid, every image/document/QA path resolves, the design lock passes, all three QA classes are complete, no unresolved `blocker`/`major` remains, and optional Git allowlist passes.

ruleId: DP-016

When unknowns remain, the package may still be delivered as an “initial handoff,” but README and validation report must state incomplete/failed, list each `gapId`, and identify next steps. Never claim “fully replicated” or “no inference required.”

ruleId: DP-017

Implementation-readiness validation requires the caller to supply the original design directory and rechecks the source set plus every source-image hash. The package stores only relative source paths, never the creating machine's absolute path. Missing source input fails validation and is not an “offline waiver.”

ruleId: DP-018

An approved page's machine contract and both page documents contain substantive, cross-referenced regions, layout, copy, components, data, and interactions, with component instances resolving to a nonempty registry. A truly absent category requires a resolved page-linked gap explicitly marked `[absence:<field>]`; an empty array does not pass by default.

ruleId: DP-019

Validate semantic ownership by page-document section ID: identity/source belongs in identity, shell/regions in canvas, layout/copy/icons/data in their section, components/interactions/responsiveness in behavior, and QA/gaps in acceptance. Appending every ID to an arbitrary section does not satisfy coverage.

ruleId: DP-020

Every approved-page section contains `contractHash: sha256:<hex>` computed from that section's machine-contract subset plus substantive prose in the locale; an ID/hash-only list does not pass. Copy, data shapes, component names, and interaction outcomes appear in their semantically matching sections.

sectionId: desktop-web-profile

## Desktop Web delivery profile

ruleId: DP-021

Configuration, page contracts, component registry, implementation map, and QA profiles declare target platform and layout policy consistently. Default delivery values are `desktop-web` and `desktop-hybrid-elastic`; every region also records a desktop role and narrow-desktop behavior. Mobile Web or native desktop uses a separate platform value and variant instead of silently inheriting the desktop-Web contract.

sectionId: reference-authority

## Reference Roles and Design Language

ruleId: DP-022

Give every input asset a stable `REF###`, then classify it as page reference, UI design-language reference, component board, brand board, interaction-state board, motion reference, decorative background, content asset, or unknown. A non-page reference cannot freeze as a product page. If the skeleton provisionally lists it as a page candidate, enrichment must reclassify and remove that candidate while preserving aliases and source mappings.

ruleId: DP-023

`UI-Design-Language.md` is shared visual authority, not a page catalog. It records principles, layers/materials, tokens, shell, components, Logo/icons, charts, micro visuals, background strategy, motion/states, scope, exceptions, and conflicts, cross-referencing `reference-inventory.json`, `ui-style-contract.json`, and `micro-visual-contract.json`.

sectionId: integrated-application

## Single-application Page-by-page Delivery

ruleId: DP-024

`application-system.json` defines one software system, one application entry, one development server/shared port, a unified Router, shell families, navigation, and shared state. Integrate all pages through routes instead of defaulting to separate projects, ports, or isolated demos. A microfrontend exception requires user approval.

ruleId: DP-025

`implementation-plan.json` follows global design language/tokens/shell/shared components → page-by-page implementation → system integration. Accept a page only after contract-completeness, structural, visual, interaction, and integrated-navigation gates pass, including its micro-visual features.

sectionId: evidence-graph-contracts

## Evidence-graph machine contracts

ruleId: DP-026

The package includes `reference-relationships.json`, `viewport-calibration.json`, `design-rule-cascade.json`, `design-inconsistencies.json`, `deterministic-fixtures.json`, `traceability-map.json`, `navigation-reconciliation.json`, and `motion-contract.json`. They cross-resolve pages, references, rules, components, implementation targets, and QA IDs; isolated records and dangling IDs are forbidden.

ruleId: DP-027

`design-rule-cascade.json` supports multiple `DLS###` design-language sets and multiple source boards per set. Every `DR###` has at least one source region and may retain several. Conflicts, version supersession, theme/module scope, and page exceptions remain machine-readable instead of scattered prose.

ruleId: DP-028

`navigation-reconciliation.json` aggregates all navigation observations and freezes one canonical tree before page implementation. Missing, extra, label, icon, order, hierarchy, route, and permission differences are resolved individually; affected pages cannot be approved before `freezeStatus: approved`.

ruleId: DP-029

`motion-contract.json` preserves interaction-state/motion evidence, start/end frames, timing, layer/focus behavior, and Reduced Motion. `deterministic-fixtures.json` fixes role/permission, data, clock, timezone, random seed, network, animation, cursor, and scroll positions so Reference/Current/Overlay/Diff are repeatable.

ruleId: DP-030

`traceability-map.json` closes the chain from reference region → design rule/token → component/micro feature/motion → page identity → implementation file/symbol → QA. An approved page's linked calibration, navigation, fixture, traceability, and motion contracts are approved as well.

ruleId: DP-031

`semantic-visual-encoding.json` stores status/grade grammar as `SEM###` dimensions and `SEMVAL###` values. Every value has a source reference and Bounds plus complete color roles, shape, geometry, typography, interaction states, contrast, evidence level, and gaps. Page contracts and Diff targets resolve to these IDs.
