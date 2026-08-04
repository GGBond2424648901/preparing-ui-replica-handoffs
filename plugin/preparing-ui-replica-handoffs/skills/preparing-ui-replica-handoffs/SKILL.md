---
name: preparing-ui-replica-handoffs
description: "Prepare bilingual, evidence-bounded UI replica handoff packages from design images. Use when screenshots, Figma exports, generated mockups, or approved UI images must become precise Chinese-English implementation contracts for a downstream Agent."
---

# Preparing UI Replica Handoffs / UI 复刻交付准备

Create a self-contained, bilingual handoff package that lets a downstream UI Agent implement what the design proves without inventing missing facts. 本技能把设计图片整理为可追溯、可验证、可失败关闭的中英双语 UI 复刻合同。

This skill is independent. Do not call, require, or route work through `design-image-to-web-replica`; ordinary image inspection, document, browser, and filesystem tools may be used when available. 本技能不依赖其他 UI 复刻技能。

## Non-negotiables / 不可协商规则

- Treat the input as read-only: never modify the original design directory. 输入只读：只扫描并复制字节，不重命名、移动、转码或改写源文件。
- Write only beneath the approved output root. Store relative paths; reject absolute paths, URI targets, and traversal. 只写入已批准输出根目录，所有路径使用相对路径并拒绝绝对路径、URI 和越界路径。
- Produce Chinese and English human-readable documents plus one English-keyed machine-contract set. 生成人读中英文双版本，以及一套英文稳定键名的机器合同。
- Separate evidence from inference. Unknowns stay `unknown`, `candidate`, or `proposed` and reference a `gapId`. 证据与推断分离；未知项保持相应状态并关联 `gapId`。
- Preserve the original canvas as the baseline. If it does not fit, retain geometry and use horizontal scrolling; do not compress or rearrange it without evidenced or approved responsive variants. 以原始画布为基线；显示不下时保持几何并水平滚动，没有证据或批准不得压缩重排。
- Scripts do not initialize, stage, commit, push, or create a worktree. They may only inspect Git and report an allowlist result. 脚本只读检查 Git，不初始化、暂存、提交、推送或创建 worktree。
- Validation must fail closed. Never claim implementation-ready or complete while blocker/major gaps, missing evidence classes, drift, unsafe paths, or validation errors remain. 验证必须失败关闭；存在 blocker/major、证据缺失、漂移、不安全路径或错误时不得宣称可实施或完成。

## Workflow / 工作流

1. Read both intake references and establish source, output, authority order, languages, version, optional product evidence, environment, and Git allowlist. Do not silently fill missing optional inputs. 阅读双语输入规则，确定源、输出、权威顺序、语言、版本、产品证据、环境与 Git 白名单；缺失项不得静默补全。
   - [中文：输入与权威顺序](references/zh/intake-and-authority.md)
   - [English: intake and authority](references/en/intake-and-authority.md)
2. Run `scripts/prepare_handoff.py` first with `--dry-run`, review its plan, then create the skeleton. The script only scans and copies; it does not visually infer page meaning. 先 dry-run，确认计划后生成骨架；脚本只扫描复制，不从视觉猜页面语义。
3. Run `scripts/build_contact_sheet.py`. Inspect every source image at readable resolution, using the contact sheet for inventory—not as a replacement for full-resolution inspection. 生成联系表并逐张查看可读分辨率原图；联系表只用于清点，不能替代原图检查。
4. Assign stable `pageId + stateId + variantId` identities and enrich every page contract under the rules below. 分配稳定页面/状态/变体身份，并按规则富化每份逐页合同。
   - [中文：页面、状态与交互合同](references/zh/page-and-state-contract.md)
   - [English: page, state, and interaction contract](references/en/page-and-state-contract.md)
5. Extract global tokens, shells, components, icons, copy, data classifications, and reuse decisions. Keep page-local candidates local until evidence supports sharing. 提取全局 token、Shell、组件、图标、文案、数据分类和复用决策；证据不足的候选保持页面局部。
   - [中文：组件与样式合同](references/zh/component-and-style-contract.md)
   - [English: component and style contract](references/en/component-and-style-contract.md)
6. Complete the package tree, bilingual documents, machine contracts, requirement ledger, gap register, implementation map, capture profile, diff regions, and QA matrix. 补齐固定目录、中英双语文档、机器合同、需求台账、缺口、实施映射、采集环境、Diff 区域和 QA 矩阵。
   - [中文：交付包规格](references/zh/delivery-package-spec.md)
   - [English: delivery package specification](references/en/delivery-package-spec.md)
7. Run `scripts/check_bilingual_parity.py`, then `scripts/validate_handoff.py`. Resolve findings or leave them explicitly open; do not edit a validation report to manufacture success. 依次运行双语和完整验证；解决问题或明确保留，不得编辑报告伪造通过。
8. Apply visual, structural, and interaction acceptance plus Git-scope checks. 完成视觉、结构、交互三类验收和 Git 范围检查。
   - [中文：视觉验收与 Git 安全](references/zh/visual-qa-and-git-safety.md)
   - [English: visual QA and Git safety](references/en/visual-qa-and-git-safety.md)

## Canonical package / 固定交付树

Do not substitute another handoff convention or add unapproved top-level trees. Use this package shape. 不得替换为其他交付约定或添加未批准的顶层目录，固定使用以下结构：

```text
<output>/
├── README.md
├── assets/designs/<design-version>/
├── docs/zh/
├── docs/en/
├── contracts/requirement-ledger.csv
├── contracts/gap-register.csv
├── contracts/asset-manifest.json
├── contracts/page-inventory.json
├── contracts/ui-style-contract.json
├── contracts/component-registry.json
├── contracts/implementation-map.json
├── contracts/capture-profile.json
├── contracts/diff-regions.json
├── contracts/visual-qa-matrix.csv
├── contracts/design-lock.json
├── reports/contact-sheet.png
├── reports/validation-report.json
└── tools/validate-command.txt
```

The locale trees contain three top-level guides and one page contract per target. The initial skeleton assigns provisional stable `P###-S01-V01` identities with `unclassified` semantics and linked gaps. An Agent may merge or refine them from evidence only before freezing, retaining aliases and source mappings; after freezing, IDs are immutable. Preparation may compute an initial design lock over the copied sources and contracts, but that lock is not an approval or completion claim. Validation remains failed/incomplete until semantic enrichment, gap resolution, and all QA classes are real. 双语目录各含三份总文档和每目标一份逐页合同；初始 `P###-S01-V01`/`unclassified` 是带缺口的可追溯临时身份，只能在冻结前依据证据合并或调整，并保留别名与来源映射；冻结后 ID 不可变。初始设计锁只冻结副本与合同，不代表批准或完成；语义、缺口和三类 QA 未完成前验证保持失败或 incomplete。

## Decision rules / 决策规则

- If a visible fact is unambiguous, record it as `direct` with source coordinates. 明确可见事实标为 `direct` 并记录坐标。
- If a relationship is calculated from visible facts, record it as `derived` and include the derivation. 由可见事实计算的关系标为 `derived` 并写明推导。
- If text is clear, transcribe it. If unreadable, use business-appropriate, similar-length inferred copy only when needed for layout, mark it `inferred`, and link the crop/coordinates and `gapId`. 清晰文案照录；仅在布局占位需要时使用长度相近的推断文案，标 `inferred` 并关联裁图/坐标和 `gapId`。
- If the design shows example records or metrics, classify them as `sample`; do not invent APIs, formulas, permissions, or production truth. 示例记录/指标标为 `sample`，不得据此虚构 API、公式、权限或生产事实。
- If a route, state, breakpoint, interaction result, icon identity, asset, or component reuse decision is not evidenced or approved, keep it unresolved. 路由、状态、断点、交互结果、图标、资产和复用没有证据或批准时保持未解决。
- For an unevidenced narrow viewport, preserve the original canvas geometry and require horizontal scrolling; do not merely say responsiveness is unknown. 未证实的窄屏必须保持原始几何并水平滚动，不能只写“响应式未知”。
- If references conflict, apply the documented authority order and log the conflict and winning evidence. 证据冲突时执行权威顺序并记录冲突与胜出证据。
- If any required evidence changes after preparation, rebuild the lock from source; never hand-edit hashes. 必需证据变化后从源重建锁，禁止手改哈希。

## Completion gate / 完成门禁

A handoff is ready for implementation only when both locale trees and all required contracts are present, all paths are package-relative, source/copy hashes and the design lock verify, page/state/variant and requirement coverage are complete, each unknown points to an unresolved gap, and no blocker/major gap remains. QA requires all three evidence classes: visual, structural, and interaction. A generated skeleton is intentionally incomplete until an Agent enriches and validates it. 只有双语文档与合同齐全、相对路径/哈希/设计锁通过、页面与需求覆盖完整、未知项均关联未解决缺口且无 blocker/major 时才可实施；视觉、结构、交互三类 QA 缺一不可，生成骨架本身永远不等于完成。
