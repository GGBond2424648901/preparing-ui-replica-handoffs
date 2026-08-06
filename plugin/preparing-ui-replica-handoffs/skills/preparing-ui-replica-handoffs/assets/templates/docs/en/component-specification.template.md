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

Buttons, icon buttons, search, inputs, radio, checkbox, switches, selects, multi-select chips, tabs, pagination, table actions, navigation items, cards, dialogs, and drawers reference governing `DR###` rules and `styleTokenRefs` per state, with local overrides listed. Default component-library styling cannot bypass the governing material language.

sectionId: semantic-visual-components

## Semantic labels, indicators, and grade components

{{semanticVisualEncoding}}

Priority, workflow status, evidence grade, feedback, approval, risk, sync, permission, and AI state do not share one generic Badge. Components bind meaning by `SEM###` dimension and `SEMVAL###` value, recording text/background/border/dot/icon colors, pill geometry, typography, long copy, locales, contrast, and default/hover/focus-visible/selected/disabled states. A visual color match with incorrect business meaning fails.

sectionId: motion-and-focus

## Motion, Hover, and Focus

Every `MOT###` records trigger, initial/final visuals, duration, delay, easing, animated properties, transform origin, stacking, pointer/focus behavior, state-frame evidence, and Reduced Motion. Mouse hover has an equivalent visible keyboard focus state.

sectionId: rendering-strategy

## Rendering and Asset Strategy

Record `renderingStrategy` and asset references for each component: DOM for real content/controls, local SVG for formal Logos/proprietary marks, a locked icon library for standard icons, CSS for simple geometry/materials, SVG for precise curves/rings/charts, Canvas for high-density dynamic graphics, and local raster assets for ambient decoration. A login page may layer DOM interaction over a purely decorative full image; screenshot UI is forbidden.

sectionId: micro-visual-reuse

## Micro-visual Reuse

Shared components still contract icon stroke, borders, radii, shadows, opacity, gradients, clipping, and stacking; page exceptions remain local overrides. Link each reuse decision to design-language `referenceId`s, page evidence, and micro-visual feature IDs.

sectionId: elastic-sizing

## Elastic Sizing

Every shell, region, and component records width mode, desktop role, narrow-desktop behavior, min/base/max width and height, Grid/Flex tracks or grow/shrink weights, wrapping/reflow triggers, wide-screen surplus-space allocation, and overflow owner. `fixed-shell`, `flexible-workspace`, `bounded-content`, `scroll-surface`, and `intrinsic` may coexist on one page; never impose uniform stretching or scrolling on every component. Treat browser zoom as a change to the effective CSS viewport; never scale the whole page root.
