# Component and Style Contract

sectionId: tokens

## Visual tokens

ruleId: CS-001

Extract color, font family, size, weight, line height, tracking, spacing, radius, border, shadow, opacity, layer, and motion from visible evidence. Record raw value, normalized token, evidence level, source page/region, and measurement tolerance.

ruleId: CS-002

Do not force near values together for neatness. Establish a global token only through repeated evidence or approval; retain one-page values in page scope as `candidate`.

sectionId: shell

## Global shell

ruleId: CS-003

Define navigation, Sidebar, TopBar, breadcrumb, workspace, footer, overlay root, and notification layer with dimensions, stacking, scroll ownership, and page reuse matrix. Mark each as fixed, fluid, bounded-fluid, or intrinsic. Model a common fixed Sidebar and elastic main workspace separately; do not hard-code the screenshot's main-content width as a global ceiling that leaves accidental blank space on wide screens. Assign separate IDs to distinct shell types instead of forcing one shell onto every page.

ruleId: CS-004

For Logo use, record formal asset relative path, rendered size, clear space, safe area, light/dark variants, background restrictions, and placement. If the formal asset is missing, create a `gapId`; never pass a screenshot crop off as the official Logo.

sectionId: registry

## Component registry and reuse

ruleId: CS-005

The registry covers navigation, cards, buttons, inputs, selectors, tags, tables, pagination, charts, AI conversation, files, workflows, Diff, logs, modals, drawers, Toast, Tooltip, empty states, and skeletons when present.

ruleId: CS-006

For each component, record component ID, name, scope, anatomy, dimensions, variants, states, slots, content bounds, interactions, accessibility, tokens, icons, and consuming pages. Its sizing contract includes width mode, min/base/max width and height, `flex-grow`/`flex-shrink` or Grid-track weights, wrapping threshold, and overflow owner. Similar appearance remains `candidate`; share only after structure and behavior both match and are approved.

sectionId: controls

## Precise control rules

ruleId: CS-007

For buttons, record height, horizontal padding, icon gap, radius, typography, default/hover/focus/pressed/disabled/loading/danger states, and click result. Unshown states remain `unknown` or `proposed`.

ruleId: CS-008

For inputs and selectors, record label, placeholder, prefix/suffix, help/error copy, character/file limits, focus border, clear, search, multi-select, keyboard, and submit behavior. Do not infer validation logic from one static image.

sectionId: data-components

## Data and complex components

ruleId: CS-009

For tables, record column order/width/alignment, headers, row height, pinned columns, sort/filter, selection, expansion, pagination, empty/loading/error/long-text states, and horizontal scrolling. Example rows remain `sample`.

ruleId: CS-010

For AI conversation, record roles, bubble/message blocks, Markdown/code/citations, streaming, stop/retry/copy/feedback, attachments, and errors. For files, record type, size, progress, preview, download, failure, and permission. Do not invent unseen capabilities.

ruleId: CS-011

For workflows, record nodes/ports/edges/canvas, zoom/pan/selection, run states, and panels; for Diff, record side-by-side/inline mode, add/delete/change marks, line numbers, and folding; for logs, record level, time, source, wrapping, filtering, copy, auto-scroll, and long-content performance.

sectionId: icons-assets

## Icon and asset mapping

ruleId: CS-012

Use this priority: formal asset > confirmed exact icon-library name > approved candidate. Every mapping records library, name, version when known, size, viewBox, stroke, fill/outline, color, coordinates, and applicable states.

ruleId: CS-013

Images, avatars, illustrations, chart textures, and file thumbnails use package-relative paths with hashes. Prefer SVG for formal Logos/proprietary marks, a version/name-locked icon library for standard icons, CSS for simple geometry/materials, SVG for precise curves/rings/chart marks, Canvas for high-density dynamic graphics, and local raster assets for ambient illustration. Reject absolute paths, remote hotlinks, Emoji, and font-character icon substitutes.

ruleId: CS-013A

A login, Hero, or ambient scene may use one full-canvas decorative background with real DOM Logo, headings, form, buttons, errors, dynamic data, and interactions over it. Record source/generated status, native dimensions, aspect ratio, fit, focal point, safe area, crop, and responsive variants. A full-page screenshot containing controls, copy, data, or states cannot implement interactive UI; use decorative backgrounds locally on ordinary product pages only when evidenced.

sectionId: accessibility

## Accessibility and long content

ruleId: CS-014

Record semantic role, accessible name, focus order, keyboard actions, contrast risk, reduced motion, and screen-reader feedback. When not visually evidenced, label these as implementation requirements or `proposed`, not visual facts.

ruleId: CS-015

Define shortest/longest/empty/multilingual content plus wrapping, truncation, Tooltip, and scroll behavior for text and data components. Never hide long-content problems by shrinking type or breaking column ratios.

sectionId: elastic-sizing

## Elastic sizing and zoom

ruleId: CS-016

For dashboards, card groups, table regions, chart regions, and multicolumn workspaces, record parent available width, column count, track formula such as ratios or `minmax()`, gaps, each column's min/base/max width, and surplus-space allocation. A wide screen preserves evidenced column count, order, and visual hierarchy while contracted flexible columns or cards absorb space. Do not invent extra columns without evidence or retain a fixed content width that creates broad accidental dead space.

ruleId: CS-017

Treat browser zoom as a change to the effective CSS viewport, not as permission to visually scale the page root or screenshot. Components may shrink according to their contract until minimum dimensions are reached; after that, select wrapping, reflow, or page/region/hybrid scrolling from evidence. Typography, icons, borders, and spacing continue to use contracted tokens without an extra scale factor.

sectionId: desktop-mixed-layout

## Desktop mixed-layout roles

ruleId: CS-018

Assign every shell, region, and component a desktop role: `fixed-shell`, `flexible-workspace`, `bounded-content`, `scroll-surface`, or `intrinsic`. Sidebar, TopBar, and toolbars are fixed/sticky only when supported by evidence; the primary workspace absorbs surplus space; text/form content may be bounded; and tables, code editors, workflows, canvases, and logs may be dedicated scroll surfaces. Never impose one growth rule on every role.

ruleId: CS-019

A desktop page has one primary vertical scroll chain by default. Region scrolling is reserved for fixed-height or two-dimensional/continuous functional surfaces and records axis, boundary, chaining, wheel handoff, and reachability. On wide screens, bounded columns, maximum line length, and component caps prevent over-stretching. On narrow desktop screens, prefer scrolling after minimum dimensions; broad reflow requires an approved variant.

sectionId: design-language-authority

## Authoritative UI Design-language References

ruleId: CS-020

Classify inputs as page references, UI design-language overviews, component boards, brand boards, interaction-state boards, motion references, or decorative backgrounds before page inventory. Put principles, materials, tokens, shell, iconography, charts, motion, and forbidden patterns from design-language references into dedicated `UI-Design-Language.md` and `reference-inventory.json` records instead of losing their global authority among pages.

ruleId: CS-021

Every shared design-language rule records its source `referenceId`, crop/coordinates, scope, exceptions, evidence level, and affected pages/components. A page inherits applicable rules and then adds page-direct evidence. User corrections and page-specific designs outrank shared rules; log every conflict.

sectionId: micro-visual-contract

## Micro-visual Contract

ruleId: CS-022

For every page, contract visible icon size/stroke, Logo proportion/clear space, device/cylinder proportions, curve control points, ring outer/inner diameter and angles, borders, per-corner radii, shadows, opacity, gradient stops, blur, clipping, masks, layering, and overflow in `micro-visual-contract.json`; “roughly similar” is insufficient.

ruleId: CS-023

Bind each micro feature to page, region, source `referenceId`, bounds, rendering strategy, responsive behavior, and geometry/color/opacity tolerances, then add a feature-level reference/current/overlay/diff target to `diff-regions.json`.
