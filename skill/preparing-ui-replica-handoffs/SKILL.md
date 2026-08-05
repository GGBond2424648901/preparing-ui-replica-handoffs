---
name: preparing-ui-replica-handoffs
description: "Prepare bilingual, evidence-bounded, desktop-Web-first UI replica handoff packages from design images. Use when screenshots, Figma exports, generated mockups, or approved UI images must become precise Chinese-English implementation contracts with mixed fixed, fluid, bounded, and scrollable layout behavior for a downstream Agent."
---

# Preparing UI Replica Handoffs / UI 复刻交付准备

Create a self-contained, bilingual handoff package that lets a downstream UI Agent implement what the design proves without inventing missing facts. 本技能把设计图片整理为可追溯、可验证、可失败关闭的中英双语 UI 复刻合同。

This skill is independent. Do not call, require, or route work through `design-image-to-web-replica`; ordinary image inspection, document, browser, and filesystem tools may be used when available. 本技能不依赖其他 UI 复刻技能。

## Non-negotiables / 不可协商规则

- Treat the input as read-only: never modify the original design directory. 输入只读：只扫描并复制字节，不重命名、移动、转码或改写源文件。
- Write only beneath the approved output root. Store relative paths; reject absolute paths, URI targets, and traversal. 只写入已批准输出根目录，所有路径使用相对路径并拒绝绝对路径、URI 和越界路径。
- Produce Chinese and English human-readable documents plus one English-keyed machine-contract set. 生成人读中英文双版本，以及一套英文稳定键名的机器合同。
- Separate evidence from inference. Unknowns stay `unknown`, `candidate`, or `proposed` and reference a `gapId`. 证据与推断分离；未知项保持相应状态并关联 `gapId`。
- Treat the original canvas as a native-pixel measurement baseline, not a fixed container or maximum page/workspace size. Use a desktop-Web-first mixed layout unless stronger evidence or an explicit user choice establishes another platform: keep shell/navigation/tool regions fixed or sticky where evidenced; make the primary workspace fluid or bounded-fluid; preserve component min/base/max geometry; assign page, region, or hybrid scrolling by function; and create reflow/mobile variants only from evidence or approval. Record fixed/fluid/bounded/intrinsic sizing, grow/shrink rules, track ratios, and wide/narrow/zoom behavior for every shell, region, grid, and component. On wider effective viewports, consume available workspace width without unboundedly stretching text or sparse cards. On narrow desktop viewports or browser zoom, shrink to contracted minima, then scroll or use an approved reflow. Never use whole-page `transform: scale()` or compress, rearrange, or crop merely to fit. 将原始画布视为原生像素测量基线，而不是固定容器或页面/工作区的最大尺寸。除非更高权威证据或用户明确指定其他平台，采用桌面端 Web 优先的混合布局：有证据的 Shell、导航和工具区保持固定或粘性；主工作区使用流式或有界流式；保留组件最小/基准/最大几何；按功能分配整页、模块或混合滚动；只有获得证据或批准才建立重排/移动端变体。逐一记录尺寸模式、伸缩规则、轨道比例和宽屏/窄屏/缩放行为。有效视口变宽时利用可用空间，但不得无限拉长文本或稀释卡片；窄桌面视口或浏览器放大时先收缩至合同下限，再滚动或执行获批重排。禁止使用全页 `transform: scale()`，也不得仅为塞入窗口而压缩、重排或裁切。
- Scripts do not initialize, stage, commit, push, or create a worktree. They may only inspect Git and report an allowlist result. 脚本只读检查 Git，不初始化、暂存、提交、推送或创建 worktree。
- Validation must fail closed. Never claim implementation-ready or complete while blocker/major gaps, missing evidence classes, drift, unsafe paths, or validation errors remain. 验证必须失败关闭；存在 blocker/major、证据缺失、漂移、不安全路径或错误时不得宣称可实施或完成。
- Readiness validation requires the original source directory. Omitting `--source-root` is an error, never a waiver. 可实施验证必须提供原始源目录；省略 `--source-root` 是错误，不能视为豁免。

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
- When viewport extent or scroll ownership is not evidenced, preserve the original geometry and record page, region, or hybrid overflow as unresolved with a `gapId`; do not impose a common breakpoint or a single scroll owner. Prefer expansion and scrolling over compression. 视口范围或滚动所有者没有证据时，保持原始几何，并将整页、模块或混合溢出策略以 `gapId` 标为未解决；不得擅自套用常见断点或强制单一滚动所有者，优先扩展和滚动而不是压缩。
- For desktop Web, apply this order: fixed/sticky shell → fluid or bounded-fluid workspace → component minimum dimensions → function-owned page/region/hybrid scrolling → approved reflow. Do not silently turn a desktop page into a mobile single-column layout. 桌面端 Web 固定执行顺序为：固定/粘性 Shell → 流式或有界流式主工作区 → 组件最小尺寸 → 按功能归属的整页/模块/混合滚动 → 获批重排；不得静默把桌面页面改成移动端单列布局。
- If references conflict, apply the documented authority order and log the conflict and winning evidence. 证据冲突时执行权威顺序并记录冲突与胜出证据。
- If any required evidence changes after preparation, rebuild the lock from source; never hand-edit hashes. 必需证据变化后从源重建锁，禁止手改哈希。

## Completion gate / 完成门禁

A handoff is ready for implementation only when both locale trees and all required contracts are present and substantive, all paths are package-relative, the original source is supplied and source/copy hashes plus the design lock verify, page/state/variant/component/requirement coverage is complete, each unknown points to an unresolved gap, and no blocker/major gap remains. QA requires validated evidence records for all three classes: computed visual comparison, structural mappings, and replayable interaction cases. A declared `pass` or arbitrary evidence file is insufficient. A generated skeleton is intentionally incomplete until an Agent enriches and validates it. 只有双语文档与合同内容实质完整、相对路径正确、验证时提供原始源目录且源/副本哈希和设计锁通过、页面/状态/变体/组件/需求覆盖完整、未知项均关联未解决缺口且无 blocker/major 时才可实施；视觉必须计算比对，结构必须映射，交互必须可重放，单纯填写 `pass` 或放置任意证据文件无效，生成骨架本身永远不等于完成。
