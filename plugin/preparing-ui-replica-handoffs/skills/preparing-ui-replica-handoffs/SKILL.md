---
name: preparing-ui-replica-handoffs
description: "Use when screenshots, Figma exports, generated mockups, UI design-language boards, component/brand/state/motion boards, or approved UI images must become precise bilingual, evidence-bounded, desktop-Web-first UI replica handoff contracts for a downstream Agent."
---

# Preparing UI Replica Handoffs / UI 复刻交付准备

Create a self-contained, bilingual handoff package that lets a downstream UI Agent implement what the design proves without inventing missing facts. 本技能把设计图片整理为可追溯、可验证、可失败关闭的中英双语 UI 复刻合同。

This skill is independent. Do not call, require, or route work through `design-image-to-web-replica`; ordinary image inspection, document, browser, and filesystem tools may be used when available. 本技能不依赖其他 UI 复刻技能。

## Non-negotiables / 不可协商规则

- Treat the input as read-only: never modify the original design directory. 输入只读：只扫描并复制字节，不重命名、移动、转码或改写源文件。
- Write only beneath the approved output root. Store relative paths; reject absolute paths, URI targets, and traversal. 只写入已批准输出根目录，所有路径使用相对路径并拒绝绝对路径、URI 和越界路径。
- Produce Chinese and English human-readable documents plus one English-keyed machine-contract set. 生成人读中英文双版本，以及一套英文稳定键名的机器合同。
- Classify every input before freezing pages. Keep page references, UI design-language boards, component boards, brand boards, state/motion references, decorative backgrounds, and content assets as distinct evidence roles with explicit authority and scope. 冻结页面前先分类全部输入；页面图、UI 设计语言图、组件板、品牌板、状态/动效参考、装饰背景与内容资产必须分角色记录权威和作用域。
- Treat visibly written titles such as “UI 设计语言”, “Design Language”, “Design System”, “视觉规范”, or an equivalent product-specific title as direct role evidence. Read titles with the multimodal model and record title bounds; filenames are clues only. There may be multiple design-language boards: group them into one or more `DLS###` sets, preserve every source, merge complementary rules, scope theme/module/version variants, and resolve conflicts explicitly. 将图片中明确写出的“UI 设计语言”等标题作为直接角色证据，由多模态模型读取并记录标题坐标；文件名仅是线索。设计语言图可以有多张，必须组成一个或多个 `DLS###` 集合，保留全部来源，合并互补规则，区分主题/模块/版本，并显式解决冲突。
- Reconcile and freeze navigation before page implementation. Inventory every observed label, icon, order, hierarchy, route, and visibility/permission rule across references; resolve missing, extra, or mismatched entries into one canonical navigation tree. 逐页实施前先汇总并冻结导航；跨参考图核对标题、图标、顺序、层级、路由和权限，所有漏项、多项与不一致都必须形成唯一规范导航树及解决记录。
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
3. Run `scripts/build_contact_sheet.py`. Inspect every source image at readable resolution, using the contact sheet for inventory—not as a replacement for full-resolution inspection. First complete `reference-inventory.json`: identify design-language, component, brand, state/motion, decorative, and actual page references; remove non-page references from provisional page candidates while preserving their `REF###` lineage. 生成联系表并逐张查看原图；先完成参考资料分类，将设计语言、组件、品牌、状态/动效、装饰和真实页面图分开，非页面图从临时页面候选移除但保留 `REF###` 血缘。
4. Build the evidence graph before page implementation: reference relationships, source-to-viewport calibration, presentation-vs-real-UI regions, one or more multi-board design-language sets, rule cascade, inconsistency ledger, deterministic fixtures, navigation reconciliation, motion contracts, semantic visual encodings, and end-to-end traceability. Then extract principles, named visual style (for example Apple-like, premium glass, translucent frosted material), tokens, shell, Logo/icon strategy, charts, motion/states, scope, exceptions, and conflicts. 逐页实施前先建立证据图谱：参考图关系、源图到真实 UI 视口校准、说明性内容与真实 UI 分离、多图设计语言集合、规则级联、不一致台账、稳定数据、导航对齐、动效、语义视觉编码和端到端追溯；再提取主体风格、材质、Token、Shell、Logo/图标、图表、状态、作用域、例外与冲突。
5. Assign stable `pageId + stateId + variantId` identities and enrich every page contract under the rules below, including a feature-level micro-visual contract. 分配稳定页面/状态/变体身份，并富化每份逐页合同及特征级微视觉合同。
   - [中文：页面、状态与交互合同](references/zh/page-and-state-contract.md)
   - [English: page, state, and interaction contract](references/en/page-and-state-contract.md)
6. Extract global tokens, shells, components, icons, copy, data classifications, rendering strategies, and reuse decisions. Bind buttons, search, inputs, radio/checkbox/multi-select, navigation, tables, tabs, dialogs, and every interactive state to the governing visual-language material and motion rules. Keep page-local candidates local until evidence supports sharing. 提取全局 Token、Shell、组件、图标、文案、数据分类、渲染策略和复用决策；按钮、搜索、输入、单选/多选、导航、表格、Tab、弹窗及全部交互状态必须继承主体视觉语言的材质与动效规则。
   - [中文：组件与样式合同](references/zh/component-and-style-contract.md)
   - [English: component and style contract](references/en/component-and-style-contract.md)
7. Complete the package tree, bilingual documents, reference/style/micro-visual/application contracts, requirement ledger, gap register, page-by-page implementation plan, capture profile, diff regions, and QA matrix. 补齐固定目录、中英双语文档、参考/样式/微视觉/单应用合同、需求台账、缺口、逐页计划、采集环境、Diff 区域和 QA 矩阵。
   - [中文：交付包规格](references/zh/delivery-package-spec.md)
   - [English: delivery package specification](references/en/delivery-package-spec.md)
8. Run `scripts/check_bilingual_parity.py`, then `scripts/validate_handoff.py`. Resolve findings or leave them explicitly open; do not edit a validation report to manufacture success. 依次运行双语和完整验证；解决问题或明确保留，不得编辑报告伪造通过。
9. Implement and accept pages in one routed application, one shared development server/port, page by page. Apply contract-completeness, visual, structural, interaction, integrated-navigation, and Git-scope gates. 在一个路由应用和共享开发服务器/端口中逐页实施，执行合同完整性、视觉、结构、交互、集成导航与 Git 范围门禁。
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
├── contracts/reference-inventory.json
├── contracts/reference-relationships.json
├── contracts/viewport-calibration.json
├── contracts/design-rule-cascade.json
├── contracts/design-inconsistencies.json
├── contracts/page-inventory.json
├── contracts/ui-style-contract.json
├── contracts/micro-visual-contract.json
├── contracts/motion-contract.json
├── contracts/semantic-visual-encoding.json
├── contracts/component-registry.json
├── contracts/navigation-reconciliation.json
├── contracts/deterministic-fixtures.json
├── contracts/traceability-map.json
├── contracts/application-system.json
├── contracts/implementation-map.json
├── contracts/implementation-plan.json
├── contracts/capture-profile.json
├── contracts/diff-regions.json
├── contracts/visual-qa-matrix.csv
├── contracts/design-lock.json
├── reports/contact-sheet.png
├── reports/validation-report.json
└── tools/validate-command.txt
```

The locale trees contain four top-level guides, including a dedicated UI design-language authority document, and one page contract per target. The initial skeleton assigns provisional stable `P###-S01-V01` identities and `REF###` references with linked gaps. Before freezing, an Agent classifies every reference, removes non-page boards from page candidates, and may merge/refine pages from evidence while retaining aliases and source mappings; after freezing, IDs are immutable. Preparation may compute an initial design lock, but it is not approval or completion. 双语目录各含四份总文档（包括独立 UI 设计语言权威文档）和逐页合同；初始骨架分配临时 `P###-S01-V01` 与 `REF###`。冻结前必须分类参考图、将非页面板从页面候选移除，并保留别名与来源；冻结后 ID 不可变。初始设计锁不代表批准或完成。

Identity merge or refinement is allowed only before freezing; after freezing every `REF###`, `P###`, `S##`, and `V##` is immutable. 身份合并与调整仅冻结前允许；冻结后所有参考图、页面、状态和变体 ID 均不可变。

## Decision rules / 决策规则

- If a visible fact is unambiguous, record it as `direct` with source coordinates. 明确可见事实标为 `direct` 并记录坐标。
- If a relationship is calculated from visible facts, record it as `derived` and include the derivation. 由可见事实计算的关系标为 `derived` 并写明推导。
- If text is clear, transcribe it. If unreadable, use business-appropriate, similar-length inferred copy only when needed for layout, mark it `inferred`, and link the crop/coordinates and `gapId`. 清晰文案照录；仅在布局占位需要时使用长度相近的推断文案，标 `inferred` 并关联裁图/坐标和 `gapId`。
- If the design shows example records or metrics, classify them as `sample`; do not invent APIs, formulas, permissions, or production truth. 示例记录/指标标为 `sample`，不得据此虚构 API、公式、权限或生产事实。
- If a route, state, breakpoint, interaction result, icon identity, asset, or component reuse decision is not evidenced or approved, keep it unresolved. 路由、状态、断点、交互结果、图标、资产和复用没有证据或批准时保持未解决。
- If an input contains design-language authority, extract it into the dedicated global contract with scope and exceptions before applying it to pages. A page-specific design or user correction wins a documented conflict. 输入含设计语言权威时，先独立提取全局合同及作用域/例外，再应用到页面；页面专属设计或用户修正在已登记冲突中优先。
- Never reduce several design-language boards to a single chosen screenshot. Preserve all boards in evidence sets; identical rules retain multiple citations, complementary rules merge, scoped rules coexist, explicit newer versions may supersede, and unresolved conflicts block approval. 禁止把多张设计语言图简化成“选一张”；相同规则保留多来源，互补规则合并，有作用域差异的规则并存，明确新版可覆盖旧版，未解决冲突阻止批准。
- Treat named visual-language descriptions as enforceable decomposable rules: material, backdrop blur, translucency, saturation, tint, inner/outer highlight, border, shadow, noise, background, depth, and forbidden combinations. Apply them through `styleTokenRefs`, `sourceRuleIds`, and component-state contracts, not as vague prose. 将“苹果风格、磨砂玻璃、高级玻璃、透明磨砂”等主体描述拆成可执行材质规则，并通过 Token、规则和组件状态映射落地，不能只写成形容词。
- A motion is not “add a transition.” Contract trigger, initial/final states, animated properties, duration, delay, easing, transform origin, stacking/pointer/focus behavior, state-frame evidence, and Reduced Motion fallback. Static evidence that does not prove motion remains `candidate` or `unknown`. 动效不能只写“加过渡”；必须记录触发、起止状态、属性、时长、延迟、缓动、变换原点、层级/指针/焦点行为、状态帧证据和 Reduced Motion 降级；静态图无法证明的动效保持候选或未知。
- Treat priority, workflow status, evidence grade, feedback, approval, risk, sync, presence, permission, AI state, data freshness, and validation as independent semantic dimensions. For every visible value record label/code/meaning, text/background/border/dot/icon colors, shape, geometry, typography, interaction states, source Bounds, and contrast. Equal hues never imply equal semantics; P0 red is not automatically an error token. 优先级、流程状态、证据等级、反馈、审批、风险、同步、在线状态、权限、AI 状态、数据新鲜度和校验结果必须分维度建模；逐值记录文案/编码/含义、文字/背景/边框/圆点/图标颜色、形状、尺寸、字体、交互状态、来源坐标与对比度。同色不等于同义，P0 红色不能自动当作错误色。
- Record visible micro geometry and paint—not only large regions—including icon strokes, curves, rings, cylinders, borders, radii, shadows, opacity, gradients, clipping, and layering, with feature-level Diff targets. 除大区块外还要记录图标描边、曲线、圆环、圆柱、边框、圆角、阴影、透明度、渐变、裁切和层级，并建立特征级 Diff。
- Prefer SVG/CSS/library icons for crisp UI geometry and use Canvas/raster only where their functional or decorative role supports it. A full-canvas decorative background is allowed only with real DOM UI over it; a screenshot containing UI is forbidden. 清晰 UI 几何优先 SVG/CSS/图标库；Canvas/光栅仅按功能或装饰角色使用。完整装饰背景可叠加真实 DOM UI，但含 UI 的截图式实现禁止。
- When viewport extent or scroll ownership is not evidenced, preserve the original geometry and record page, region, or hybrid overflow as unresolved with a `gapId`; do not impose a common breakpoint or a single scroll owner. Prefer expansion and scrolling over compression. 视口范围或滚动所有者没有证据时，保持原始几何，并将整页、模块或混合溢出策略以 `gapId` 标为未解决；不得擅自套用常见断点或强制单一滚动所有者，优先扩展和滚动而不是压缩。
- For desktop Web, apply this order: fixed/sticky shell → fluid or bounded-fluid workspace → component minimum dimensions → function-owned page/region/hybrid scrolling → approved reflow. Do not silently turn a desktop page into a mobile single-column layout. 桌面端 Web 固定执行顺序为：固定/粘性 Shell → 流式或有界流式主工作区 → 组件最小尺寸 → 按功能归属的整页/模块/混合滚动 → 获批重排；不得静默把桌面页面改成移动端单列布局。
- If references conflict, apply the documented authority order and log the conflict and winning evidence. 证据冲突时执行权威顺序并记录冲突与胜出证据。
- If any required evidence changes after preparation, rebuild the lock from source; never hand-edit hashes. 必需证据变化后从源重建锁，禁止手改哈希。

## Completion gate / 完成门禁

A handoff is ready for implementation only when both locale trees and all required contracts are present and substantive, all paths are package-relative, the original source is supplied and source/copy hashes plus the design lock verify, page/state/variant/component/requirement coverage is complete, each unknown points to an unresolved gap, and no blocker/major gap remains. QA requires validated evidence records for all three classes: computed visual comparison, structural mappings, and replayable interaction cases. A declared `pass` or arbitrary evidence file is insufficient. A generated skeleton is intentionally incomplete until an Agent enriches and validates it. 只有双语文档与合同内容实质完整、相对路径正确、验证时提供原始源目录且源/副本哈希和设计锁通过、页面/状态/变体/组件/需求覆盖完整、未知项均关联未解决缺口且无 blocker/major 时才可实施；视觉必须计算比对，结构必须映射，交互必须可重放，单纯填写 `pass` 或放置任意证据文件无效，生成骨架本身永远不等于完成。
