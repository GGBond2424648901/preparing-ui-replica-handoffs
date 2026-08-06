---
templateId: ui-implementation-guide
locale: en-US
---

# UI Implementation Guide

sectionId: authority

## Authority and Evidence

{{authorityOrder}}

sectionId: implementation-flow

## Implementation Flow

Use `{{implementationMapPath}}` for page, region, component, data, interaction, responsive, and Git-scope mappings.

Freeze the global UI design language, tokens, shell, Logo/icon strategy, and shared components first, then implement pages in `implementation-plan.json` order. Each page passes contract-completeness, structural, visual, interaction, and integrated-navigation gates before the next page begins. All routes finish in one application on one development server and shared port; do not create per-page ports or isolated demos.

sectionId: reference-classification

## Reference Classification and Design-language Inheritance

Read `../../contracts/reference-inventory.json` and `UI-Design-Language.md` first. Gather evidence separately from global design-language boards, component boards, brand boards, state boards, and page references. A page inherits applicable shared rules, then applies page-direct evidence. Page-specific designs and user corrections win conflicts, with the winning evidence recorded rather than silently overriding rules.

sectionId: visual-assets

## SVG, CSS, Canvas, and Decorative Backgrounds

Prefer SVG for Logos/proprietary marks, a locked icon library for standard icons, CSS for simple geometry and materials, SVG for precise curves/rings/charts, Canvas for high-density dynamic graphics, and local raster assets for ambient decoration. A login page may use one full decorative background plus real DOM UI; a screenshot containing copy, controls, data, or state cannot be the implementation.

sectionId: canvas-and-overflow

## Canvas Expansion and Scrolling

Treat the original canvas as a native-pixel measurement baseline, not a fixed container or the maximum page, workspace, or module content extent. When content exceeds it, preserve minimum component dimensions, ratios, typography, and key positional relationships, and record wrapping, reflow, and page-level, region-level, or hybrid scrolling from design and functional evidence. Link an unresolved choice to a `gapId`; never compress, scale the whole page, or crop merely to fit the window.

sectionId: elastic-layout

## Elastic Layout and Browser Zoom

For every page, record each shell, region, grid, and component as `fixed`, `fluid`, `bounded-fluid`, `intrinsic`, or `mixed`, together with min/base/max dimensions, Grid/Flex tracks, grow weights, shrink floors, and overflow owner. On wide screens, the main workspace consumes available width and distributes surplus space according to evidence instead of leaving broad unexplained blank areas. On narrow effective viewports, including browser zoom, after minimum dimensions are reached the contract selects wrapping, reflow, or scrolling. Root `transform: scale()` is forbidden; an evidenced `max-width` is allowed and must be recorded.

sectionId: desktop-web-first

## Desktop-Web-first order

The default policy is `desktop-web` + `desktop-hybrid-elastic`: fixed/sticky shell → fluid or bounded-fluid primary workspace → component min/base/max dimensions → function-owned page/region/hybrid scrolling → approved reflow. Ordinary vertical content prefers page scrolling; tables, code, workflows, canvases, and logs may use dedicated scroll surfaces. A narrow desktop window or browser zoom does not automatically become a mobile single column; mobile uses a separate `variantId`.

sectionId: evidence-graph-and-navigation

## Evidence Graph and Navigation Freeze

Before page implementation, complete reference relationships, UI-viewport calibration, multi-board design-language sets/rule cascade, inconsistency treatment, deterministic fixtures, traceability, and navigation reconciliation. Aggregate labels, icons, order, hierarchy, routes, and permissions from every board, resolve omissions/extras/differences, and freeze one canonical tree; do not approve pages against unfrozen navigation.

sectionId: material-controls-and-motion

## Governing Material, Control Inheritance, and Motion

Decompose Apple-like, frosted, premium-glass, translucent-frosted, and other governing language into material tokens/rules inherited by every state of buttons, search, inputs, radio/checkbox, switches, selects, navigation, cards, table actions, and overlays. Use `MOT###` for hover/focus/press/selection/expand/enter behavior with start/end visuals, timing, animated properties, equivalent focus, and Reduced Motion; static evidence that cannot prove motion remains unresolved.

sectionId: semantic-visual-implementation

## Semantic-state implementation and acceptance

Generate dimension-isolated semantic tokens/variants from `semantic-visual-encoding.json`; never merge by color name. Table status columns, filters, detail labels, metric cards, navigation badges, and dialogs reference the same `SEMVAL###`. Preserve evidenced text/background/border/dot/icon colors and pill geometry, and register color, geometry, and contrast `semanticTargets` for every page-used value.

sectionId: qa-and-git-safety

## QA and Git Safety

{{qaAndGitSafety}}
