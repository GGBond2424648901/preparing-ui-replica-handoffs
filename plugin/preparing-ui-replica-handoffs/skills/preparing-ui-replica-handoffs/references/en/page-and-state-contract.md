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

Record original canvas width/height, pixel density when known, background, content origin, Sidebar/TopBar/footer dimensions, fixed/sticky/scroll layers, and clipping boundary. Use `unknown` plus `gapId` for unavailable dimensions.

ruleId: PS-004

The original canvas is the 1:1 baseline. When the viewport is too narrow, retain card widths, column ratios, typography, and module positions through an extended workspace or horizontal scrolling; do not compress, rearrange, move, or crop to make it fit.

sectionId: regions

## Regions and geometry

ruleId: PS-005

For every visible region, record a unique region ID, reference `x/y/width/height` bounds, parent, neighbor relationships, alignment, column ratio, gap, padding, min/max size, layer, and overflow behavior. Coordinates are a measurement baseline, not an instruction to absolutely position the entire page.

ruleId: PS-006

Also describe the implementation layout model (normal flow, Grid, Flex, overlay), anchors, and scroll owner. When pixel measurement is uncertain, record tolerance and method instead of fabricating integer precision.

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

Create a responsive `variantId` only from design evidence, formal product material, or user approval. Record breakpoint evidence, container change, order change, hidden/replaced elements, and scroll behavior; never assume common breakpoints.

ruleId: PS-014

An unapproved narrow viewport inherits original geometry and uses horizontal scrolling. If an adaptation must be proposed, label it `candidate`/`proposed`, accept it separately, and never overwrite the native-pixel baseline.

sectionId: page-acceptance

## Per-page completion

ruleId: PS-015

Each page contract covers identity, source, canvas, shell, regions, layout, components, copy, icons, data, interactions, states, responsiveness, implementation mapping, QA, and gaps. If any is absent, status is incomplete and the package cannot say “no inference required.”
