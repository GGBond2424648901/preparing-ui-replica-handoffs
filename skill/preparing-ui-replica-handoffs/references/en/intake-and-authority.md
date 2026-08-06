# Intake and Authority

sectionId: intake

## Minimum intake

ruleId: IA-001

Resolve and record the read-only design-image directory, a separate handoff output directory, the design version, and delivery languages (default `zh-CN,en-US`) before work starts. The output must not be inside the input or reuse an unmanaged directory.

ruleId: IA-002

Optional inputs include product goals, roles, modules, formal requirements, routes, data/permission notes, brand assets, target stack, target platform, layout policy, approved pages/states/responsive variants, browser/viewport/DPR/locale/timezone/theme/font environment, and Git repository plus allowlist. When absent, create a `gapId`; never silently guess.

sectionId: source-immutability

## Read-only source boundary

ruleId: IA-003

The original design directory is evidence: only read, hash, and copy it. Never rename, move, delete, transcode, compress, overwrite, or add a contact sheet in place. Normalized English numbered names apply only to copies in `assets/designs/<design-version>/`.

ruleId: IA-004

Record relative source path, MIME/format, byte size, pixel dimensions, SHA-256, duplicate group, and source-set hash. Recompute before and after freezing; drift fails and prevents a trusted design lock.

sectionId: authority

## Conflict authority order

ruleId: IA-005

Use this fixed order: latest explicit user correction > approved reference image > approved asset > verified product material > formal requirement > current implementation > recorded assumption. Log candidate evidence, winner, rationale, and affected contract IDs; apparent plausibility cannot override higher authority.

ruleId: IA-006

Images are visual authority, not automatically business-rule authority. Classify design examples as `sample`; they do not prove APIs, formulas, permissions, production truth, or error states.

sectionId: evidence

## Evidence levels and gaps

ruleId: IA-007

Use one evidence vocabulary for material conclusions: `direct` (visibly explicit), `derived` (calculated from visible facts with derivation), `candidate` (reuse/mapping awaiting confirmation), `approved` (accepted by the user or authoritative material), and `unknown` (insufficient evidence). Never present `candidate` or `unknown` as fact.

ruleId: IA-008

Every unresolved item needs a unique `gapId`, severity, affected object, evidence location, decision owner, status, and resolution condition. An unresolved `blocker` or `major` prevents completion.

sectionId: copy-and-data

## Copy and data

ruleId: IA-009

Transcribe clear text; cite confirmed product copy. For unreadable text, use business-appropriate, similar-length inferred copy only when layout needs it, mark it `inferred`, and retain source coordinates/crop plus `gapId`. Do not reproduce gibberish or mark inferred copy as `direct`.

ruleId: IA-010

Classify each data item as `sample`, `product-confirmed`, `derived`, or `unknown`, with format, long-content boundary, and masking needs. Never infer a backend contract from sample values.

sectionId: intake-gate

## Intake gate

ruleId: IA-011

Before generation, report the source to read, output to write, image count, design version, languages, and known gaps. Stop with a stable diagnostic when path relationships are unsafe, sources are empty/corrupt, or output ownership is unclear.

sectionId: target-platform

## Target platform and layout policy

ruleId: IA-012

This skill prepares a `desktop-web` + `desktop-hybrid-elastic` contract by default. An explicit user choice or direct mobile/native-desktop design evidence overrides that default and records its authority. The desktop default establishes implementation priority; it is not misrepresented as direct screenshot evidence.

ruleId: IA-013

A desktop contract distinguishes fixed/sticky shell, fluid or bounded-fluid workspace, min/max-constrained components, page scrolling, and function-owned region scrolling. Mobile single-column layout, hidden navigation, or broad reflow requires a separate `variantId` backed by direct evidence or explicit approval.

sectionId: reference-roles

## Reference-role Classification

ruleId: IA-014

The first visual pass only classifies role: page reference, UI design-language reference, component board, brand board, interaction-state board, motion reference, decorative background, content asset, or unknown. A filename is only a candidate clue, never visual evidence. Assign stable `REF###` identity, scope, and authority class to each item.

ruleId: IA-015

A UI design-language image may become cross-page visual authority only with per-rule scope. A global principle cannot override more specific page-direct evidence, and a page exception cannot contaminate global tokens. Record inheritance, override, exception, and conflict separately.

sectionId: design-language-sets

## Multiple design-language boards and title evidence

ruleId: IA-016

When a visible title explicitly says “UI Design Language,” “Design Language,” “Design System,” “Visual Specification,” or an equivalent product-specific name, record the title and bounds as direct role evidence and remove that board from page candidates. Read the image with the multimodal model; external OCR is not required, and filenames remain clues that cannot override the visible title.

ruleId: IA-017

There may be several design-language boards. Group them into one or more `DLS###` sets by product, version, theme, module, and scope before creating `DR###` rules. Identical rules retain every source region; complementary rules merge; theme/module variants coexist; supersession requires explicit version evidence; conflicts become `DRC###` and block affected-page approval until resolved.

sectionId: evidence-graph

## Evidence graph and canvas calibration

ruleId: IA-018

Use `reference-relationships.json` for continuation, detail, state, variant, responsive, overlay, component, brand, duplicate, complementary, superseding, and conflicting relationships. Use `viewport-calibration.json` to separate source canvas, real UI viewport, crop offset, scale/DPR, full content extent, fixed/sticky regions, and presentation matter such as annotations, redlines, measurements, explanatory copy, watermarks, browser chrome, and device frames; presentation matter is excluded from implementation by default.

ruleId: IA-019

Use `design-inconsistencies.json` for malformed icons, impossible perspective, geometry drift, copy conflicts, asset conflicts, and interaction conflicts in generated or cross-board designs. Each entry chooses page-specific preservation, canonicalization, redraw, inferred copy, or unresolved treatment, with winning evidence and acceptance impact.

sectionId: navigation-authority

## Navigation authority and freeze

ruleId: IA-020

Before page implementation, observe every navigation label, icon, order, parent hierarchy, route, selected state, and role/permission visibility across references. Record omissions, extras, label/icon/order/parent/route/visibility differences in `navigation-reconciliation.json`; an approved canonical navigation tree with `freezeStatus: approved` is required before page approval.
