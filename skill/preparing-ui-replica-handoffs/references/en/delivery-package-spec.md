# Delivery Package Specification

sectionId: package-tree

## Fixed tree

ruleId: DP-001

The standard root contains `README.md`, `assets/designs/<design-version>/`, `docs/zh/`, `docs/en/`, `contracts/`, `reports/`, and `tools/`. Do not add runtime dependencies on the creating machine, another skill, or remote resources.

ruleId: DP-002

Chinese documents include at least `设计稿总目录.md`, `UI实施说明.md`, `组件规范.md`, and `pages/<page-state-variant>.md`; English mirrors are `Design-Catalog.md`, `UI-Implementation-Guide.md`, `Component-Specification.md`, and same-ID page documents.

sectionId: catalog

## Catalog responsibility

ruleId: DP-003

The design catalog records page/state/variant ID, name, module, source and copied image, original canvas, SHA-256, suggested route and evidence, status, priority, shell type, assets, per-page contract link, and gaps. It is a navigation index, not a replacement for page contracts.

sectionId: implementation-guide

## Implementation guide responsibility

ruleId: DP-004

The UI implementation guide defines global workflow, authority order, native-pixel baseline, scroll strategy, implementation sequence, and for each `P###-S##-V##` its regions, geometry, components, copy, icons, data, interactions, states, responsiveness, mappings, and acceptance contract.

ruleId: DP-005

Each page document lets a downstream Agent distinguish direct evidence, derivation, candidate, approval, and unknown. Any pending decision references a `gapId` rather than hiding uncertainty in prose.

sectionId: component-spec

## Component specification responsibility

ruleId: DP-006

The component specification records exact tokens, shells, Logo, icon mappings, component anatomy/dimensions/states/interactions/content bounds/accessibility, and page reuse matrix. Complex coverage includes visible navigation, cards, buttons, tables, AI conversation, files, workflows, Diff, and logs.

sectionId: contracts

## Machine contracts

ruleId: DP-007

`contracts/` contains the requirement ledger, gap register, asset manifest, page inventory, UI style contract, component registry, implementation map, capture profile, diff regions, visual QA matrix, and design lock. Stable keys are English; readable fields expose `zh-CN`/`en-US`.

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
