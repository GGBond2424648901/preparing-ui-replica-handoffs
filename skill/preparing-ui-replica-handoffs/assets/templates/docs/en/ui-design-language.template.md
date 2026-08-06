---
templateId: ui-design-language
locale: en-US
---

# UI Design Language

sectionId: authority-references

## Authoritative References and Scope

{{referenceAuthority}}

Classify every input first in `../../contracts/reference-inventory.json`. Record `design-language-reference`, `component-board`, `brand-reference`, `interaction-state-board`, and `page-reference` separately. Never treat a design-language overview as a product page or promote a page exception into a global rule. Every shared rule states its `referenceId`, crop/coordinates, scope, conflict priority, and applicable/excluded pages.

When a visible title explicitly names a UI design language, preserve its text and bounds as direct evidence. There may be several boards: group them by product/version/theme/module into one or more `DLS###` sets in `design-rule-cascade.json`, preserve every source, and record complementary, superseding, and conflicting relationships separately.

sectionId: principles-and-materials

## Principles, Layers, and Materials

Record design principles, information density, the 8px or other grid, background/content/overlay layers, glass/frosted/solid materials, blur, saturation, opacity, borders, shadows, glow, and stacking. Unknown values stay `unknown + gapId`; do not insert generic SaaS defaults.

Governing labels such as Apple-like, frosted, premium glass, or translucent frosted are decomposed into background, blur, opacity, tint/saturation, border/highlight, shadow, texture, depth, and forbidden combinations rather than retained as adjectives only.

sectionId: tokens

## Exact Visual Tokens

{{styleContract}}

Record colors, gradients, typography, weights, sizes, line height, tracking, spacing, radii, borders, shadows, opacity, blur, layers, motion, density, and backgrounds separately with raw measurements, normalized tokens, sources, and tolerances. Do not merge near values automatically.

sectionId: shell-components

## Shell, Component, and Reuse Language

Describe Sidebar, TopBar, navigation selection, workspace, cards, buttons, inputs, Tabs, tags, tables, charts, modals, drawers, Toasts, Tooltips, and AI states with anatomy, dimensions, material, states, and reuse boundaries. Include a shared-rule → shell/component → consuming-page matrix.

Buttons, search, inputs, radio/checkbox, switches, selects, and navigation items include a design rule/token → component → default/hover/focus-visible/pressed/selected/disabled/loading/error → page inheritance matrix.

sectionId: semantic-status-grammar

## Semantic color, status, and grade grammar

{{semanticVisualEncoding}}

Create separate `SEM###` dimensions for priority, workflow status, evidence grade, feedback, approval, risk, sync, presence, permission, AI state, data freshness, and validation. Every `SEMVAL###` records code/label/meaning, pill or indicator form, text/background/border/dot/icon colors, geometry, typography, interaction states, source Bounds, and contrast. Never merge equal colors across dimensions automatically; values absent from evidence remain gaps.

sectionId: brand-icons-assets

## Logo, Icon, and Asset Rendering Strategy

Use package-local SVG for formal Logos; a version-locked icon library with exact names for standard icons; local SVG for proprietary marks; CSS for simple blocks, dots, pills, borders, and gradients; SVG by default for precise curves, connectors, rings, and chart marks; Canvas only for high-volume dynamic graphics; and local raster assets for ambient illustration or texture. Forbid Emoji, font-character icon substitutes, remote hotlinks, and unproven assets.

sectionId: micro-visual-language

## Micro-visual Language

{{microVisualContract}}

Icon size/stroke, Logo clear space, device and cylinder proportions, curve control points, ring diameter/width/start/end angles, borders, per-corner radii, shadows, opacity, gradient stops, clipping, masks, layers, and overflow belong in the micro-visual contract and in structural plus regional Diff acceptance.

sectionId: decorative-backgrounds

## Decorative Background Strategy

A login, Hero, or ambient scene may use one generated/exported full-canvas decorative background with real DOM Logo, heading, form, buttons, errors, dynamic data, and interactions over it. Record source/generated status, native dimensions, aspect ratio, `cover/contain/position`, focal point, safe areas, crop, and wide/narrow variants. Never use a full-page screenshot containing controls, text, data, or states as interactive UI; use this technique locally on business pages only when evidenced.

sectionId: motion-states-accessibility

## Motion, States, and Accessibility

Record default, Hover, Focus, Pressed, Disabled, Loading, Empty, Error, permission, and AI-running states together with duration, easing, position/opacity change, and reduced-motion. Unshown states remain `proposed`, not direct evidence.

Every evidenced micro-interaction enters `motion-contract.json` with trigger, initial/final states, animated properties, duration, delay, easing, layer/pointer/focus behavior, state-frame sources, and Reduced Motion. Static evidence alone does not prove motion.

sectionId: forbidden-and-gaps

## Forbidden Patterns and Gaps

Forbid screenshot implementations, whole-page `transform: scale()`, unsupported compression/reflow/cropping, arbitrary Logo/icon replacement, promotion of local exceptions into global rules, omitted micro-details, and hidden conflicts or unknowns. Every unresolved item links to a `gapId`.
