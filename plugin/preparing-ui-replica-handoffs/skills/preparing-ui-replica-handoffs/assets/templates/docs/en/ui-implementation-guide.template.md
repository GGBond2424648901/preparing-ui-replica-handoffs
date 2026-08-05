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

sectionId: canvas-and-overflow

## Canvas Expansion and Scrolling

Treat the original canvas as a native-pixel measurement baseline, not a fixed container or the maximum page, workspace, or module content extent. When content exceeds it, preserve minimum component dimensions, ratios, typography, and key positional relationships, and record wrapping, reflow, and page-level, region-level, or hybrid scrolling from design and functional evidence. Link an unresolved choice to a `gapId`; never compress, scale the whole page, or crop merely to fit the window.

sectionId: elastic-layout

## Elastic Layout and Browser Zoom

For every page, record each shell, region, grid, and component as `fixed`, `fluid`, `bounded-fluid`, `intrinsic`, or `mixed`, together with min/base/max dimensions, Grid/Flex tracks, grow weights, shrink floors, and overflow owner. On wide screens, the main workspace consumes available width and distributes surplus space according to evidence instead of leaving broad unexplained blank areas. On narrow effective viewports, including browser zoom, after minimum dimensions are reached the contract selects wrapping, reflow, or scrolling. Root `transform: scale()` is forbidden; an evidenced `max-width` is allowed and must be recorded.

sectionId: desktop-web-first

## Desktop-Web-first order

The default policy is `desktop-web` + `desktop-hybrid-elastic`: fixed/sticky shell → fluid or bounded-fluid primary workspace → component min/base/max dimensions → function-owned page/region/hybrid scrolling → approved reflow. Ordinary vertical content prefers page scrolling; tables, code, workflows, canvases, and logs may use dedicated scroll surfaces. A narrow desktop window or browser zoom does not automatically become a mobile single column; mobile uses a separate `variantId`.

sectionId: qa-and-git-safety

## QA and Git Safety

{{qaAndGitSafety}}
