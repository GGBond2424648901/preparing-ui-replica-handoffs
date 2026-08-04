# Visual QA and Git Safety

sectionId: capture-profile

## Reproducible capture environment

ruleId: QG-001

Every QA target references a capture profile containing browser/version, operating system, viewport, DPR, locale, timezone, theme, zoom, fonts, and load-wait condition. Unknown environment fields remain `unknown` with a `gapId`; never present local defaults as the design environment.

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

Visual acceptance checks canvas, color, typography, spacing, dimensions, borders, radii, shadows, icons, images, stacking, overflow, and reference/current/overlay/diff. Each failure links page, region, severity, and repair evidence.

ruleId: QG-006

Structural acceptance checks DOM/component/region/requirement/implementation mappings, page and state coverage, accessible semantics, scroll ownership, and relative paths. Visual similarity does not replace structural acceptance.

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
