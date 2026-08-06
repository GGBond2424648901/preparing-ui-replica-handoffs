# Visual QA and Git Safety

sectionId: capture-profile

## Reproducible capture environment

ruleId: QG-001

Every QA target references a capture profile containing browser/version, operating system, CSS viewport, DPR, locale, timezone, theme, browser zoom, fonts, and load-wait condition. Use separate profiles for original baseline, wide, narrow, and zoom scenarios. Unknown environment fields remain `unknown` with a `gapId`; never present local defaults as the design environment.

ruleId: QG-002

Before capture, fix route, initial data/fixture, permission, scroll position, animation/cursor policy, and stable network conditions. Reference and current must use compatible environments and the same region definitions.

sectionId: evidence-files

## Four visual evidence files

ruleId: QG-003

For each target, store separate package-relative `reference/current/overlay/diff` files; paths must not alias one another. Pixel-perfect results may have identical content hashes, but file identity, origin, and generation steps remain traceable.

ruleId: QG-004

Diff regions reference real region IDs and record crop bounds, threshold, permitted variance, ignored areas, and rationale. Never use high thresholds, blur, or broad masks to hide structural errors.

sectionId: acceptance-classes

## Three acceptance classes

ruleId: QG-005

Visual acceptance checks canvas, occupied content width, surplus-space allocation, column ratios, minimum dimensions, color, typography, spacing, dimensions, borders, radii, shadows, icons, images, stacking, overflow, and reference/current/overlay/diff. Broad unexplained blank space on wide screens, or squashing, clipping, and drift on narrow screens, are layout failures. Each failure links page, region, severity, and repair evidence.

ruleId: QG-006

Structural acceptance checks DOM/component/region/requirement/implementation mappings, page and state coverage, accessible semantics, fixed/fluid/bounded-fluid sizing, min/base/max dimensions, Grid/Flex growth rules, scroll ownership, and relative paths. Visual similarity does not replace structural acceptance.

ruleId: QG-007

Interaction acceptance uses cases to verify initial state, action, feedback, success/failure, modal/drawer, route, keyboard, focus, and data changes. A passing static screenshot does not replace interaction acceptance.

ruleId: QG-008

A completion claim requires visual acceptance, structural acceptance, and interaction acceptance together. If any class is not-run, incomplete, or failed, the overall result cannot pass.

sectionId: severity

## Severity and fail-closed behavior

ruleId: QG-009

`blocker` means reliable implementation/acceptance is impossible or evidence/security integrity is at risk; `major` means key layout, state, interaction, or asset is missing; `minor` is a non-blocking local deviation. Resolve `blocker`/`major` or obtain an explicit exception from an authorized user.

ruleId: QG-010

The validator computes its result only from real contracts and files. Never hand-edit a validation report to passed; the report is derived output, not authoritative input. Revalidate after any original input, contract, or lock change.

sectionId: git-safety

## Git scope

ruleId: QG-011

Git checks are read-only. Scripts do not initialize repositories, create/delete worktrees, stage, commit, push, reset, clean, or rewrite user changes; report skipped when no repository exists.

ruleId: QG-012

Only when the user supplies a repository and allowed relative prefix, verify every staged path is in the allowlist. Out-of-scope paths fail and are listed; never unstage or move them automatically.

ruleId: QG-013

Before a proposed commit, manually confirm `git status`, target branch, diff, and file list contain only this handoff/plugin work. Preserve existing uncommitted user changes; commit/push require separate authorization.

sectionId: release-gate

## Release gate

ruleId: QG-014

Before release, run bilingual, structural, Schema, path, hash, design-lock, coverage, QA, gap, and optional Git allowlist checks. Record result, command, time, tool version, and open items without leaking machine absolute paths into the report.

ruleId: QG-015

Every passing QA row references a SHA-256-bound machine-readable evidence record. It binds QA/page/state/variant/evidence type, tool, replayable command, actual artifact paths and hashes, and per-check results; arbitrary images or a handwritten `pass` are not passing evidence.

ruleId: QG-016

For visual pass, the validator decodes reference/current, recomputes overlay/diff and pixel-difference ratio, and compares it with region tolerance. Structural pass maps requirements, regions, and components to real contracts. Interaction pass cites replayable cases for page-declared interaction IDs. All three results are derived from evidence, not trusted declarations.

ruleId: QG-017

Reference binds to the page's verified design copy in the asset manifest. Every passing record also binds a hashed runner result containing tool/version/command, start/end times, exit code 0, nonempty all-passing assertions, and artifact hashes; the validator never executes untrusted commands from a handoff.

ruleId: QG-018

A structural runner binds DOM and implementation snapshots and cross-checks region/component/target-file identities with machine contracts. An interaction runner binds each case to a declared interaction ID and nonempty assertions. JSON `NaN`, infinities, and every non-finite tolerance or metric are invalid input.

ruleId: QG-019

Structural mappings use exact-set validation: requirements, regions, components, DOM nodes, and implementation targets allow no missing, duplicate, or extra entries. With valid `[absence:components]`, the corresponding sets are empty and a resolved-gap-bound absence assertion proves that fact.

ruleId: QG-020

A valid `[absence:interactions]` page may have no interaction cases only when its runner supplies a resolved-gap-bound absence-check and passing assertion that no interaction IDs/cases exist. Empty cases still fail without that evidence.

sectionId: elastic-layout-acceptance

## Elastic layout acceptance

ruleId: QG-021

A wide profile verifies that fixed shell dimensions remain contracted, the main workspace consumes available width, and cards and columns distribute surplus space by contracted weights without enlarging typography/icons or scaling the whole page. When the design proves a centered cap, accept that `max-width` and its side margins; otherwise broad one-sided dead space cannot pass.

ruleId: QG-022

Narrow and zoom profiles verify the effective CSS viewport, component minimum dimensions, wrapping/reflow triggers, and page/region/hybrid scroll ownership. Root `transform: scale()`, extra zoom, or changed token dimensions cannot manufacture adaptation. Horizontal clipping, overlap, fixed-region drift, or unreachable content fails.

sectionId: desktop-web-acceptance

## Desktop Web acceptance

ruleId: QG-023

Accept desktop behavior separately at the original baseline, a wide viewport, a narrow desktop window, and browser zoom. Check fixed shell, workspace occupancy, bounded-content caps, component minimum dimensions, and scroll owners. A mobile single-column result cannot replace narrow-desktop acceptance, and a wide screenshot cannot prove zoom behavior.

ruleId: QG-024

Scroll acceptance verifies one primary vertical scroll chain plus the necessity, axes, boundaries, wheel handoff, and complete reachability of every dedicated scroll surface. Unjustified nested vertical scrolling, trapped wheel input, sticky-boundary drift, fixed regions covering content, or unbounded wide-screen stretching fails.

sectionId: micro-visual-acceptance

## Micro-visual and Integration Acceptance

ruleId: QG-025

Compare every `MV###` in reference/current/overlay/diff modes at the native baseline profile, checking geometry, stroke, color, opacity, clipping, and stacking tolerances. A whole-page pixel comparison cannot replace feature-level checks for curve control points, ring/cylinder proportions, Logo clear space, or icon stroke.

ruleId: QG-026

Page acceptance also proves that the route/navigation reaches it in the unified application on the shared port, that it reuses the correct shell/tokens/components, and that it does not regress accepted pages. A passing isolated screenshot with failing integrated navigation cannot mark the page accepted.
