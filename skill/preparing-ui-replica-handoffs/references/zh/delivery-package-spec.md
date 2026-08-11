# 交付包规格

sectionId: package-tree

## 固定目录

ruleId: DP-001

标准根目录包含 `README.md`、`assets/designs/<design-version>/`、`docs/zh/`、`docs/en/`、`contracts/`、`reports/` 和 `tools/`。不得增加对创建机器、外部技能或远程资源的运行时依赖。

ruleId: DP-002

中文文档至少包含 `设计稿总目录.md`、`UI设计语言.md`、`UI实施说明.md`、`组件规范.md` 与 `pages/<page-state-variant>.md`；英文镜像为 `Design-Catalog.md`、`UI-Design-Language.md`、`UI-Implementation-Guide.md`、`Component-Specification.md` 和同 ID pages 文档。

sectionId: catalog

## 总目录职责

ruleId: DP-003

设计稿总目录记录页面/状态/变体 ID、名称、模块、来源与副本图片、原始画布、SHA-256、建议路由及证据、状态、优先级、Shell 类型、资产、逐页合同链接和缺口。它是导航索引，不替代逐页合同。

sectionId: implementation-guide

## 实施说明职责

ruleId: DP-004

UI 实施说明定义全局工作流、权威顺序、原生像素基线、画布与内容范围的区别、固定/流式/有界流式尺寸模式、最小/基准/最大尺寸、Grid/Flex 伸缩与剩余空间分配、宽屏/窄屏/浏览器缩放行为、页面/区域/混合滚动策略、实施顺序和每个 `P###-S##-V##` 的区域、几何、组件、文案、图标、数据、交互、状态、响应式、映射与验收合同。

ruleId: DP-005

逐页文档必须能让下游 Agent 区分直接证据、推导、候选、批准和未知；任何仍需决策的信息引用 `gapId`，不得隐藏在散文措辞中。

sectionId: component-spec

## 组件规范职责

ruleId: DP-006

组件规范记录精确 token、Shell、Logo、图标映射、组件 anatomy/尺寸/状态/交互/内容边界/可访问性，以及页面复用矩阵；复杂组件至少覆盖设计中出现的导航、卡片、按钮、表格、AI 对话、文件、工作流、Diff 和日志。

sectionId: contracts

## 机器合同

ruleId: DP-007

`contracts/` 必须包含 requirement ledger、gap register、asset manifest、reference inventory、page inventory、UI style contract、micro visual contract、component registry、application system、implementation map、implementation plan、capture profile、diff regions、visual QA matrix 和 design lock。稳定键名使用英文，可读字段提供 `zh-CN`/`en-US`。

ruleId: DP-008

requirement ledger 把每项需求映射到页面、区域、组件、交互和 QA；implementation map 把同一目标映射到建议代码位置但不虚构真实文件；gap register 保存未知项及审批生命周期。

ruleId: DP-009

design lock 由脚本根据交付文件集与哈希计算。禁止手写、复制旧锁或把 validation report 当锁输入；任何锁覆盖文件变化都必须失败并重新冻结。

sectionId: paths-links

## 路径与链接

ruleId: DP-010

所有存储路径和 Markdown 图片/文档链接均使用相对路径并保持在交付根目录内。拒绝盘符路径、UNC、根路径、`file:`/HTTP URI、路径穿越、链接目录和别名覆盖。

ruleId: DP-011

每个整理图片副本必须与源图一对一、字节哈希一致，并使用 Agent 易识别的稳定英文编号名称。语义未知时用 `unclassified`，不得由脚本看文件名猜页面业务。

sectionId: generation

## 生成与人工富化

ruleId: DP-012

`prepare_handoff.py` 生成确定性初始骨架；`build_contact_sheet.py` 生成索引。随后 Agent 必须查看原分辨率图片并富化所有合同。初始骨架有未解决 `blocker`/`major`，因此预期验证失败关闭。

ruleId: DP-013

更新只能作用于有明确所有权标记的交付目录，并采用无覆盖冲突的安全发布；并发冲突、非法恢复目录或所有权不明时保留证据并停止，不递归删除未知内容。

sectionId: bilingual

## 双语一致性

ruleId: DP-014

中英文档自然语言可不同，但文件配对、页面 ID、section ID、rule ID、占位符和图片引用集合必须一致。运行 `check_bilingual_parity.py`；不得只翻译标题而遗漏规则。

sectionId: completion

## 完成定义

ruleId: DP-015

只有源图不变、双语覆盖完整、机器合同非空且互相引用有效、所有图片/文档/QA 路径可解析、设计锁通过、三类 QA 完成、无未解决 `blocker`/`major`、可选 Git 白名单通过时，才可声明可实施。

ruleId: DP-016

若仍有未知项，交付包仍可作为“初始交付”提供，但必须在 README 和 validation report 明确写 incomplete/failed、列出 `gapId` 和下一步；禁止使用“已完全还原”“无需推断”等声明。

ruleId: DP-017

可实施验证必须由调用方提供原始设计目录，并重新核对来源集合与每张源图哈希；交付包只保存相对来源路径，不保存创建机器绝对路径。未提供源目录时验证失败，不得作为“离线豁免”。

ruleId: DP-018

批准页面的逐页机器合同和双语页面文档必须有实质内容：区域、布局、文案、组件、数据和交互互相引用，组件实例可解析到非空注册表。确实不存在的类别必须由该页引用的已解决缺口明确标记 `[absence:<field>]`，不能以空数组默认通过。

ruleId: DP-019

逐页文档按 section ID 验证语义归属：身份/来源只能在身份段完成，Shell/区域在画布段，布局/文案/图标/数据在对应段，组件/交互/响应式在行为段，QA/缺口在验收段。把全部 ID 附加到任意一段不能满足覆盖率。

ruleId: DP-020

批准页面的每个逐页章节都必须包含由该章节机器合同子集计算的 `contractHash: sha256:<hex>`，并有该语言的实质说明；纯 ID/哈希列表不能通过。文案、数据形状、组件名称和交互结果须出现在语义对应章节。

sectionId: desktop-web-profile

## 桌面端 Web 交付配置

ruleId: DP-021

配置、逐页合同、组件注册表、实施映射和 QA profile 必须共同声明目标平台与布局策略。默认交付值为 `desktop-web` 与 `desktop-hybrid-elastic`；每个区域还要记录桌面角色和窄桌面行为。移动端或原生桌面端必须使用独立平台值和变体，不能静默继承桌面 Web 合同。

sectionId: reference-authority

## 参考资料角色与设计语言

ruleId: DP-022

每个输入资产必须先获得稳定 `REF###`，并分类为页面图、UI 设计语言图、组件板、品牌板、交互状态板、动效参考、装饰背景、内容资产或 unknown。非页面参考不得冻结为业务页面；若初始骨架暂列为页面候选，富化阶段必须先重分类、移除候选页面并保留别名与来源映射。

ruleId: DP-023

`UI设计语言.md` 是共享视觉权威，不是页面目录。它必须逐条记录设计原则、层次/材质、Token、Shell、组件、Logo/图标、图表、微视觉、背景策略、动效/状态、适用范围、例外和冲突，并与 `reference-inventory.json`、`ui-style-contract.json` 和 `micro-visual-contract.json` 互相引用。

sectionId: integrated-application

## 单应用逐页实施

ruleId: DP-024

`application-system.json` 必须定义一个软件系统、一个应用入口、一个开发服务器/共享端口、统一 Router、Shell 家族、导航与共享状态。所有页面通过路由集成展示，不得默认为每页创建单独工程、端口或孤立 Demo；微前端例外必须有用户批准。

ruleId: DP-025

`implementation-plan.json` 按“全局设计语言/Token/Shell/共享组件 → 页面逐页实现 → 系统集成”的顺序组织。每页只有通过合同完整性、结构、视觉、交互和集成导航门禁后才能验收，微视觉特征必须进入该页验收。

sectionId: evidence-graph-contracts

## 证据图谱机器合同

ruleId: DP-026

交付包必须包含 `reference-relationships.json`、`viewport-calibration.json`、`design-rule-cascade.json`、`design-inconsistencies.json`、`deterministic-fixtures.json`、`traceability-map.json`、`navigation-reconciliation.json` 和 `motion-contract.json`。这些文件与页面、参考图、规则、组件、实现目标和 QA ID 互相解析，禁止孤立记录或悬空 ID。

ruleId: DP-027

`design-rule-cascade.json` 支持多个 `DLS###` 设计语言集合及每集合多张参考图。每个 `DR###` 必须至少有一段来源坐标；同一规则可保留多来源。冲突、版本覆盖、主题/模块作用域和页面例外必须机器可读，不能只散落在说明文字中。

ruleId: DP-028

`navigation-reconciliation.json` 在逐页实施前汇总全部导航观察并冻结唯一规范树。遗漏、多余、标题、图标、顺序、层级、路由和权限差异必须逐项解决；未达到 `freezeStatus: approved` 时，相关页面不得批准。

ruleId: DP-029

`motion-contract.json` 保存交互状态和动效的证据、起止帧、时间参数、层级/焦点行为与 Reduced Motion；`deterministic-fixtures.json` 固定角色权限、数据、时钟、时区、随机种子、网络、动画、光标和滚动位置，确保 Reference/Current/Overlay/Diff 可重复。

ruleId: DP-030

`traceability-map.json` 必须形成“参考图区域 → 设计规则/Token → 组件/微视觉/动效 → 页面身份 → 实现文件/符号 → QA”的闭环。批准页面引用的校准、导航、稳定数据、追溯和动效合同必须同样获批。

ruleId: DP-031

`semantic-visual-encoding.json` 按 `SEM###` 维度和 `SEMVAL###` 值保存状态/等级语法。每个值必须有来源参考图和 Bounds，并完整记录颜色角色、形状、几何、字体、交互状态、对比度、证据等级与缺口。逐页合同和 Diff 目标必须可解析到这些 ID。

sectionId: system-first-shell-contracts

## 系统优先的 Shell 与验收合同

ruleId: DP-032

`application-system.json` 是运行时组装的权威合同。它必须按证据记录前台、中台、后台和公开/认证范围的实质 Shell 家族；每个 Shell 包含规范导航、路由前缀、布局/导航实现目标、复用方式、几何 Token、全局偏移所有者、滚动、缩放行为和状态。批准应用不得保留 `null` 或 `unclassified`。

ruleId: DP-033

`navigation-reconciliation.json` 按 Shell 家族汇总观察，而不是按截图建立系统。准备骨架只生成一个待分类的共享证据池；视觉分类可以将其拆分为不同 Shell，但每个获批 Shell 最多只有一棵规范导航树，且始终禁止页面本地导航副本。

ruleId: DP-034

`implementation-plan.json` 必须先安排四个系统工作项：Shell 分类、规范导航冻结、统一 Router/共享 Shell/导航注册表建设，以及每个 Shell 代表路由验证。所有页面工作项都依赖该门禁，并声明 `implementationBoundary: page-content-only`。

ruleId: DP-035

`capture-profile.json` 必须区分用于复刻评分的锁定基准 profile，以及必需的 `wide`、`narrow`、`zoom` 稳定性 profile。基准环境锁定视口、缩放比例、DPR、浏览器/版本、语言环境、主题和字体；稳定性 profile 不得影响复刻百分比。

ruleId: DP-036

`diff-regions.json` 支持锚点化的 `shell-navigation`、`shell-topbar` 和 `page-content` 区域。生成式证据不确定时，导航可以设置明确的参考几何容差，但已接受偏移不得传导到内容区 Diff，运行时跨路由 Shell 漂移仍为零。
