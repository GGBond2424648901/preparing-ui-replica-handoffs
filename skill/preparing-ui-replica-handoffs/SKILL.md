---
name: preparing-ui-replica-handoffs
description: "Prepare bilingual, evidence-bounded UI replica handoff packages from design images. Use when screenshots, Figma exports, generated mockups, or approved UI images must become precise Chinese-English implementation contracts for a downstream Agent."
---

# Preparing UI Replica Handoffs / UI 复刻交付准备

Create a self-contained, bilingual handoff package that lets a downstream UI Agent implement what the design proves without inventing missing facts. 本技能把设计图片整理为可追溯、可验证、可失败关闭的中英双语 UI 复刻合同。

This skill is independent. Do not call, require, or route work through `design-image-to-web-replica`; ordinary image inspection, document, browser, and filesystem tools may be used when available. 本技能不依赖其他 UI 复刻技能。

## Non-negotiables / 不可协商规则

- Treat the input as read-only: never modify the original design directory. 只扫描源目录并复制字节，不重命名、不移动、不转码源文件。
- Write only beneath the approved output root. Store relative paths; reject absolute paths, URI targets, and traversal.
- Produce Chinese and English human-readable documents plus one English-keyed machine-contract set.
- Separate evidence from inference. Unknowns stay `unknown`, `candidate`, or `proposed` and reference a `gapId`.
- Preserve the original canvas as the baseline. If it does not fit, retain geometry and use horizontal scrolling; do not compress or rearrange it without evidenced or approved responsive variants.
- Scripts do not initialize, stage, commit, push, or create a worktree. They may only inspect Git and report an allowlist result.
- Validation must fail closed. Never claim implementation-ready or complete while blocker/major gaps, missing evidence classes, drift, unsafe paths, or validation errors remain.

## Workflow / 工作流

1. Read both intake references and establish source, output, authority order, languages, version, optional product evidence, environment, and Git allowlist. Do not silently fill missing optional inputs.
   - [中文：输入与权威顺序](references/zh/intake-and-authority.md)
   - [English: intake and authority](references/en/intake-and-authority.md)
2. Run `scripts/prepare_handoff.py` first with `--dry-run`, review its plan, then create the skeleton. The script only scans and copies; it does not visually infer page meaning.
3. Run `scripts/build_contact_sheet.py`. Inspect every source image at readable resolution, using the contact sheet for inventory—not as a replacement for full-resolution inspection.
4. Assign stable `pageId + stateId + variantId` identities and enrich every page contract under the rules below.
   - [中文：页面、状态与交互合同](references/zh/page-and-state-contract.md)
   - [English: page, state, and interaction contract](references/en/page-and-state-contract.md)
5. Extract global tokens, shells, components, icons, copy, data classifications, and reuse decisions. Keep page-local candidates local until evidence supports sharing.
   - [中文：组件与样式合同](references/zh/component-and-style-contract.md)
   - [English: component and style contract](references/en/component-and-style-contract.md)
6. Complete the package tree, bilingual documents, machine contracts, requirement ledger, gap register, implementation map, capture profile, diff regions, and QA matrix.
   - [中文：交付包规格](references/zh/delivery-package-spec.md)
   - [English: delivery package specification](references/en/delivery-package-spec.md)
7. Run `scripts/check_bilingual_parity.py`, then `scripts/validate_handoff.py`. Resolve findings or leave them explicitly open; do not edit a validation report to manufacture success.
8. Apply visual, structural, and interaction acceptance plus Git-scope checks.
   - [中文：视觉验收与 Git 安全](references/zh/visual-qa-and-git-safety.md)
   - [English: visual QA and Git safety](references/en/visual-qa-and-git-safety.md)

## Decision rules / 决策规则

- If a visible fact is unambiguous, record it as `direct` with source coordinates.
- If a relationship is calculated from visible facts, record it as `derived` and include the derivation.
- If text is clear, transcribe it. If unreadable, use business-appropriate, similar-length inferred copy only when needed for layout, mark it `inferred`, and link the crop/coordinates and `gapId`.
- If the design shows example records or metrics, classify them as `sample`; do not invent APIs, formulas, permissions, or production truth.
- If a route, state, breakpoint, interaction result, icon identity, asset, or component reuse decision is not evidenced or approved, keep it unresolved.
- If references conflict, apply the documented authority order and log the conflict and winning evidence.
- If any required evidence changes after preparation, rebuild the lock from source; never hand-edit hashes.

## Completion gate / 完成门禁

A handoff is ready for implementation only when both locale trees and all required contracts are present, all paths are package-relative, source/copy hashes and the design lock verify, page/state/variant and requirement coverage are complete, each unknown points to an unresolved gap, and no blocker/major gap remains. QA requires all three evidence classes: visual, structural, and interaction. A generated skeleton is intentionally incomplete until an Agent enriches and validates it.
