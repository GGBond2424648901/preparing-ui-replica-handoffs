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

Treat the original canvas as a native-pixel measurement baseline, not the maximum page, workspace, or module content extent. When content exceeds it, preserve component size, ratios, typography, and positional relationships, and record page-level, region-level, or hybrid scrolling from design and functional evidence. Link an unresolved choice to a `gapId`; never compress, scale down, rearrange, or crop merely to fit the window.

sectionId: qa-and-git-safety

## QA and Git Safety

{{qaAndGitSafety}}
