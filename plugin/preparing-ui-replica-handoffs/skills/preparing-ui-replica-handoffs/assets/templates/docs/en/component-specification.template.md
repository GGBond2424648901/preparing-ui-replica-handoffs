---
templateId: component-specification
locale: en-US
---

# Component Specification

sectionId: component-registry

## Component Registry

{{componentRegistry}}

sectionId: style-tokens

## Style Tokens

{{styleTokens}}

sectionId: states-and-variants

## States and Variants

{{componentStatesAndVariants}}

sectionId: rendering-strategy

## Rendering and Asset Strategy

Record `renderingStrategy` and asset references for each component: DOM for real content/controls, local SVG for formal Logos/proprietary marks, a locked icon library for standard icons, CSS for simple geometry/materials, SVG for precise curves/rings/charts, Canvas for high-density dynamic graphics, and local raster assets for ambient decoration. A login page may layer DOM interaction over a purely decorative full image; screenshot UI is forbidden.

sectionId: micro-visual-reuse

## Micro-visual Reuse

Shared components still contract icon stroke, borders, radii, shadows, opacity, gradients, clipping, and stacking; page exceptions remain local overrides. Link each reuse decision to design-language `referenceId`s, page evidence, and micro-visual feature IDs.

sectionId: elastic-sizing

## Elastic Sizing

Every shell, region, and component records width mode, desktop role, narrow-desktop behavior, min/base/max width and height, Grid/Flex tracks or grow/shrink weights, wrapping/reflow triggers, wide-screen surplus-space allocation, and overflow owner. `fixed-shell`, `flexible-workspace`, `bounded-content`, `scroll-surface`, and `intrinsic` may coexist on one page; never impose uniform stretching or scrolling on every component. Treat browser zoom as a change to the effective CSS viewport; never scale the whole page root.
