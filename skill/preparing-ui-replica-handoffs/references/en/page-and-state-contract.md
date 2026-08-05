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

The original canvas is the 1:1 measurement baseline, not a page or workspace size ceiling. When content exceeds it, retain card widths, column ratios, typography, spacing, and module positions while extending the document, workspace, or module content extent. Use page scrolling, region scrolling, or both according to design and functional evidence. Do not compress, scale down, rearrange, move, or crop merely to fit the captured viewport or browser.

sectionId: regions

## Regions and geometry

ruleId: PS-005

For every visible region, record a unique region ID, reference `x/y/width/height` bounds, parent, neighbor relationships, alignment, column ratio, gap, padding, min/max size, layer, and overflow behavior. State whether overflow belongs to the browser page, a specific region, or both, including scroll axis, fixed-size evidence, and scroll chaining. Coordinates are a measurement baseline, not an instruction to absolutely position the entire page.

ruleId: PS-006

Also describe the implementation layout model (normal flow, Grid, Flex, overlay), anchors, and scroll owner. Constrain scrolling to a module only when design or functional evidence proves a fixed viewport; otherwise retain page, region, and hybrid candidates as `unknown` with a `gapId`. When pixel measurement is uncertain, record tolerance and method instead of fabricating integer precision.

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

An unapproved viewport change inherits original geometry without treating the source canvas as a maximum width or height and without assuming that scrolling must belong only to the page or only to a module. Select page-level, region-level, or hybrid overflow from design and functional evidence; otherwise mark the choice `candidate`/`proposed` with a `gapId`. Accept adaptations separately and never overwrite the native-pixel baseline.

sectionId: page-acceptance

## Per-page completion

ruleId: PS-015

Each page contract covers identity, source, canvas, shell, regions, layout, components, copy, icons, data, interactions, states, responsiveness, implementation mapping, QA, and gaps. If any is absent, status is incomplete and the package cannot say “no inference required.”
