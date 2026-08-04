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

Define navigation, Sidebar, TopBar, breadcrumb, workspace, footer, overlay root, and notification layer with dimensions, stacking, scroll ownership, and page reuse matrix. Assign separate IDs to distinct shell types instead of forcing one shell onto every page.

ruleId: CS-004

For Logo use, record formal asset relative path, rendered size, clear space, safe area, light/dark variants, background restrictions, and placement. If the formal asset is missing, create a `gapId`; never pass a screenshot crop off as the official Logo.

sectionId: registry

## Component registry and reuse

ruleId: CS-005

The registry covers navigation, cards, buttons, inputs, selectors, tags, tables, pagination, charts, AI conversation, files, workflows, Diff, logs, modals, drawers, Toast, Tooltip, empty states, and skeletons when present.

ruleId: CS-006

For each component, record component ID, name, scope, anatomy, dimensions, variants, states, slots, content bounds, interactions, accessibility, tokens, icons, and consuming pages. Similar appearance remains `candidate`; share only after structure and behavior both match and are approved.

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

Images, avatars, illustrations, chart textures, and file thumbnails use package-relative paths with hashes. Reject absolute paths, remote hotlinks, and full-page screenshots used as implementation backgrounds.

sectionId: accessibility

## Accessibility and long content

ruleId: CS-014

Record semantic role, accessible name, focus order, keyboard actions, contrast risk, reduced motion, and screen-reader feedback. When not visually evidenced, label these as implementation requirements or `proposed`, not visual facts.

ruleId: CS-015

Define shortest/longest/empty/multilingual content plus wrapping, truncation, Tooltip, and scroll behavior for text and data components. Never hide long-content problems by shrinking type or breaking column ratios.
