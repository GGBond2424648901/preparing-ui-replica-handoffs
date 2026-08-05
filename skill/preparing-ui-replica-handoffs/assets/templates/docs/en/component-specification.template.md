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

sectionId: elastic-sizing

## Elastic Sizing

Every shell, region, and component records width mode, desktop role, narrow-desktop behavior, min/base/max width and height, Grid/Flex tracks or grow/shrink weights, wrapping/reflow triggers, wide-screen surplus-space allocation, and overflow owner. `fixed-shell`, `flexible-workspace`, `bounded-content`, `scroll-surface`, and `intrinsic` may coexist on one page; never impose uniform stretching or scrolling on every component. Treat browser zoom as a change to the effective CSS viewport; never scale the whole page root.
