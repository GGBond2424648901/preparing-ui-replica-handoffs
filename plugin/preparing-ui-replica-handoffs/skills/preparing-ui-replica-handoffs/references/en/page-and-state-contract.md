# Page, State, and Interaction Contract

sectionId: identity

## Stable identity

ruleId: PS-001

Identify every acceptance target uniquely by `pageId + stateId + variantId` in `P###-S##-V##` form. File order, screenshot sequence, and route cannot replace identity; renaming must not change frozen IDs.

ruleId: PS-002

Map every source image one-to-one to a delivery copy and at least one target identity. Preserve separate source records for duplicate images and declare their duplicate group; never silently discard them.

sectionId: canvas-shell

## Canvas and shell

ruleId: PS-003

Record original canvas width/height, pixel density when known, background, content origin, Sidebar/TopBar/footer dimensions, fixed/sticky layers, clipping boundaries, and page-level and region-level scroll owners, axes, and triggers. Treat the original canvas as captured viewport evidence, not automatically as the final content extent or maximum page size. Use `unknown` plus `gapId` for unavailable facts.

ruleId: PS-004

The original canvas is the 1:1 measurement baseline, not a fixed container or page/workspace size ceiling. On a wider effective viewport, the main workspace consumes available width according to evidence and distributes surplus space through column ratios, grow weights, or bounded-fluid rules instead of preserving screenshot pixel width and leaving accidental dead space; an evidenced `max-width` is the exception. When space is insufficient, preserve minimum card widths, column ratios, typography, and key positional relationships, then select wrapping, reflow, expanded page/module extent, and page, region, or hybrid scrolling from evidence. Never use whole-page `transform: scale()` or arbitrarily compress, move, or crop to fit the window.

sectionId: regions

## Regions and geometry

ruleId: PS-005

For every visible region, record a unique region ID, reference `x/y/width/height` bounds, parent, neighbor relationships, alignment, column ratio, gap, padding, layer, and overflow behavior. Also record `fixed`, `fluid`, `bounded-fluid`, `intrinsic`, or `mixed` sizing, min/base/max dimensions, Grid/Flex track formulas, grow weights, shrink floors, and wide/narrow viewport behavior. State whether overflow belongs to the browser page, a specific region, or both, including scroll axis, fixed-size evidence, and scroll chaining. Coordinates are a measurement baseline, not an instruction to absolutely position the entire page.

ruleId: PS-006

Also describe the implementation layout model (normal flow, Grid, Flex, overlay), the boundary between fixed shell and elastic workspace, anchors, grow/shrink rules, and scroll owner. Constrain scrolling to a module only when design or functional evidence proves a fixed viewport; otherwise retain page, region, and hybrid candidates as `unknown` with a `gapId`. Never substitute whole-screenshot scaling for real layout. When pixel measurement is uncertain, record tolerance and method instead of fabricating integer precision.

sectionId: visible-content

## Visible components, copy, icons, and data

ruleId: PS-007

List component instances, visible copy, buttons, inputs, table columns, cards, charts, AI conversation, files, workflows, Diff, logs, badges, and feedback per region. Each item references a component ID or remains a page-local `candidate`.

ruleId: PS-008

For icons, record library/asset source, candidate name, size, stroke, color, position, and evidence level. When the exact icon is unavailable, use `unknown` + `gapId`; never substitute arbitrary emoji or an incorrect icon.

sectionId: interactions

## Interaction contract

ruleId: PS-009

For every actionable element, record initial state, trigger, precondition, action, immediate feedback, success result, failure result, focus change, data change, modal/drawer/menu, route target, and return behavior. Unshown outcomes remain `unknown`.

ruleId: PS-010

Routes are proposals with evidence levels unless approved product material establishes them. External links, download, copy, upload, delete, and permission actions must state side effects and confirmation behavior.

sectionId: states

## Page states

ruleId: PS-011

A default screenshot proves only the visible state at capture time. Classify Loading, Empty, Error, Forbidden, Disabled, Hover, Focus, Selected, Expanded, Modal, Drawer, Toast, long-content, and extreme-data states separately as `direct`, `approved`, `proposed`, or `unknown`.

ruleId: PS-012

Every `unknown` state references an unresolved `gapId`; do not copy generic states to pretend design evidence exists. Keep `proposed` states separate from the original baseline until approval promotes them to `approved`.

sectionId: responsive

## Responsive variants

ruleId: PS-013

Create a responsive `variantId` only from design evidence, formal product material, or user approval. Record breakpoint evidence, container sizing mode, min/base/max dimensions, Grid/Flex track and growth changes, order changes, hidden/replaced elements, wrapping/reflow, and scroll behavior. Never assume common breakpoints or create a new layout from one browser-zoom observation alone.

ruleId: PS-014

An unapproved viewport change inherits original visual relationships and minimum geometry without treating the source canvas as fixed width or height. The default wide-screen candidate preserves column count and order while an elastic workspace absorbs surplus width according to evidence. On a narrow effective viewport, including one produced by browser zoom, after minimum dimensions are reached select wrapping, reflow, page, region, or hybrid overflow from evidence. Otherwise mark the choice `candidate`/`proposed` with a `gapId`. Accept original, wide, narrow, and zoom capture profiles separately and never overwrite the native-pixel baseline.

sectionId: page-acceptance

## Per-page completion

ruleId: PS-015

Each page contract covers identity, source, canvas, shell, regions, layout, components, copy, icons, data, interactions, states, responsiveness, implementation mapping, QA, and gaps. If any is absent, status is incomplete and the package cannot say “no inference required.”

sectionId: desktop-web-first

## Desktop-Web-first contract

ruleId: PS-016

Apply and record this order for every desktop region: fixed/sticky shell and tool areas; fluid or bounded-fluid primary workspace; min/base/max dimensions for cards, tables, editors, canvases, and other components; page, region, or hybrid scroll ownership; and only then evidence-backed or approved wrapping/reflow. `baseline-elastic` means space is used through this order, not that every region stretches unconditionally.

ruleId: PS-017

A narrow desktop window or browser zoom does not automatically trigger a mobile single-column layout. Components first shrink to contracted minima. Ordinary vertical content prefers page scrolling, while tables, code, workflows, canvases, logs, and other two-dimensional or continuous surfaces may own region scrolling. Mobile navigation replacement, hidden elements, or single-column reflow requires a mobile design, formal material, or explicit approval.

sectionId: micro-visual-and-integration

## Micro Visuals and System Integration

ruleId: PS-018

Beyond region bounds, each page contract enumerates visible micro features: icons/Logo, curves, rings, cylinders/devices, borders, radii, shadows, opacity, gradients, clipping/masks, and layering. Bind each to `MV###`, source `REF###`, region, rendering strategy, responsive behavior, and Diff tolerance.

ruleId: PS-019

Each page contract declares its unified-application route, shell, navigation entry, shared state/components, page dependencies, and integration acceptance. A page may be developed and captured separately, but cannot remain on its own port or as an isolated demo outside the unified Router.

sectionId: page-evidence-graph

## Page evidence-graph bindings

ruleId: PS-020

Every page identity lists `referenceRelationshipIds`, `calibrationIds`, `inheritedDesignRuleIds`, `inconsistencyIds`, `fixtureIds`, `traceabilityIds`, `navigationSystemIds`, and `motionIds`. Region coordinates use the calibrated real UI viewport; source-image frames, redlines, explanatory copy, and device chrome never become component bounds.

ruleId: PS-021

A page inherits the applicable governing design language before adding page-direct evidence. Every button, search, selection control, navigation item, card, and other instance traces to its component, tokens, and `DR###`. A page exception states overridden fields and source evidence instead of bypassing the shared language with copied local styling.

sectionId: page-navigation-and-motion

## Page navigation and motion states

ruleId: PS-022

A page references only reconciled canonical navigation entries and declares its selected item, expanded parent, permission-visible items, labels/icons, and target routes. A navigation item that is incidentally missing or extra in one screenshot does not become page-specific until the discrepancy contract resolves it.

ruleId: PS-023

Page hover, focus-visible, pressed, selected, loading, expand/collapse, and overlay enter/exit states reference `MOT###`. Interaction acceptance covers motion start, intermediate key state, finish, timing, and Reduced Motion in addition to the result; a static screenshot cannot replace replayable state acceptance.

sectionId: page-semantic-visuals

## Page semantic-visual usage contract

ruleId: PS-024

Pages declare used semantic dimensions through `semanticDimensionIds` and list the exact values visible in that page/state/variant through `semanticValueIds`. Table columns, filters, detail labels, metric cards, and dialogs reference the same `SEMVAL###` rather than copying approximate local colors; page-specific exceptions require direct evidence.

ruleId: PS-025

Semantic labels cover default view, selected/filter use, hover, focus-visible, disabled, long copy, locale variants, light/dark carriers, and high-contrast conditions. Different dimensions such as priority, workflow status, and evidence grade never exchange meaning even when they share a hue. Every visible `SEMVAL###` on an approved page has a `semanticTargets` Diff.
