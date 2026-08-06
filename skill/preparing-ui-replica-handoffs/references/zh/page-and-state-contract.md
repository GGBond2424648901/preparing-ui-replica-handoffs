# 页面、状态与交互合同

sectionId: identity

## 稳定身份

ruleId: PS-001

每个可验收目标由 `pageId + stateId + variantId` 唯一标识，格式为 `P###-S##-V##`。文件顺序、截图序号或路由不能替代身份；名称变化不得改变已冻结 ID。

ruleId: PS-002

每张源图必须一对一映射到交付副本和至少一个目标身份。重复图片仍保留各自来源记录并声明重复组，不能静默丢弃。

sectionId: canvas-shell

## 画布与 Shell

ruleId: PS-003

记录原始画布宽高、像素密度（已知时）、背景、内容起点、Sidebar/TopBar/底栏尺寸、固定/粘性层级、裁剪边界，以及页面级和区域级滚动所有者、方向与触发条件。原始画布是截图/设计视口证据，不自动等于最终内容范围或最大页面尺寸。未知项写 `unknown` 并登记 `gapId`。

ruleId: PS-004

原始画布是 1:1 测量基线，不是固定容器或页面/工作区尺寸上限。有效视口更宽时，主工作区应按证据利用可用宽度，并按列比例、伸展权重或有界流式规则分配剩余空间，不能因照抄截图像素宽度而留下设计中没有的大面积空白；有直接证据的 `max-width` 例外。空间不足时保持最小卡片宽度、列比例、文字尺寸和关键位置关系，依据证据选择换行、重排、扩展整页/模块内容范围，以及整页纵向滚动、浏览器页面水平滚动、模块内滚动或混合滚动。禁止用全页 `transform: scale()`，也不得为了塞入窗口而任意压缩、移动或裁切。

sectionId: regions

## 区域与几何

ruleId: PS-005

为每个可见区域记录唯一 region ID、`x/y/width/height` 参考边界、父容器、上下左右邻接、对齐、列比例、间距、内边距、层级和溢出行为；同时记录 `fixed`、`fluid`、`bounded-fluid`、`intrinsic` 或 `mixed` 尺寸模式，最小/基准/最大尺寸、Grid/Flex 轨道公式、伸展权重、收缩下限和宽/窄视口行为。明确溢出由浏览器页面、具体区域或两者共同承担，并记录滚动轴、固定尺寸依据和滚动链关系。坐标是测量基线，不是要求全页绝对定位。

ruleId: PS-006

同时描述适合实现的布局模型（正常流、Grid、Flex、叠层）、固定 Shell 与弹性工作区的边界、锚定关系、伸缩规则和滚动所有者。只有设计或功能约束能证明固定视口时，才把滚动限制在模块内部；证据不足时以 `unknown` + `gapId` 保留页面级、区域级和混合策略候选。不得用截图整体缩放代替真实布局；若像素测量存在误差，记录容差和测量方法，不伪造整数精度。

sectionId: visible-content

## 可见组件、文案、图标与数据

ruleId: PS-007

逐区列出组件实例、可见文案、按钮、输入、表格列、卡片、图表、AI 对话、文件、工作流、Diff、日志、徽标和反馈。每项引用组件 ID 或标记为页面局部 `candidate`。

ruleId: PS-008

图标记录库/资产来源、候选名称、尺寸、线宽、颜色、位置和证据等级。无法确认具体图标时使用 `unknown` + `gapId`，不得用随意 Emoji 或错误图标充数。

sectionId: interactions

## 交互合同

ruleId: PS-009

每个可操作元素记录初始状态、触发方式、前置条件、动作、立即反馈、成功结果、失败结果、焦点变化、数据变化、弹窗/抽屉/菜单、路由目标和返回行为。未展示的结果保持 `unknown`。

ruleId: PS-010

路由使用建议值与证据等级；除非产品资料批准，不把建议路由视为事实。外链、下载、复制、上传、删除和权限动作必须说明副作用与确认机制。

sectionId: states

## 页面状态

ruleId: PS-011

默认截图只证明当时可见状态。Loading、Empty、Error、Forbidden、Disabled、Hover、Focus、Selected、Expanded、Modal、Drawer、Toast、长内容和极端数据必须分别标为 `direct`、`approved`、`proposed` 或 `unknown`。

ruleId: PS-012

任何 `unknown` 状态都必须引用未解决的 `gapId`；不要复制通用状态来假装设计存在。`proposed` 状态必须与原设计基线分离，等待批准后才能升级为 `approved`。

sectionId: responsive

## 响应式变体

ruleId: PS-013

只有设计图、正式资料或用户批准能建立响应式 `variantId`。记录断点证据、容器宽度模式、最小/基准/最大尺寸、Grid/Flex 轨道与伸缩变化、顺序变化、隐藏/替换元素、换行/重排和滚动策略；不得默认套用常见断点，也不得仅凭一次浏览器缩放创造新布局。

ruleId: PS-014

未批准的视口变化继承原始视觉关系和最小几何，不把原始画布当作固定宽高。宽屏默认候选是保持列数与顺序、由弹性工作区按证据吸收剩余宽度；窄屏或浏览器缩放形成的有效窄视口，则在达到最小尺寸后依据证据选择换行、重排、页面级、区域级或混合溢出。证据不足时标为 `candidate`/`proposed` 并关联 `gapId`。每个原始、宽屏、窄屏和缩放采集配置单独验收，不能覆盖原生像素基线。

sectionId: page-acceptance

## 逐页完成条件

ruleId: PS-015

逐页合同必须覆盖身份、来源、画布、Shell、区域、布局、组件、文案、图标、数据、交互、状态、响应式、实现映射、QA 与缺口。缺少任何一项时状态是 incomplete，不得写“无需推断”。

sectionId: desktop-web-first

## 桌面端 Web 优先合同

ruleId: PS-016

桌面页面逐区执行以下顺序并写入合同：固定/粘性 Shell 与工具区；流式或有界流式主工作区；卡片、表格、编辑器、画布等组件的最小/基准/最大尺寸；页面级、区域级或混合滚动所有者；最后才是获得证据或批准的换行/重排。`baseline-elastic` 表示按此顺序优先利用空间，不表示所有区域无条件拉伸。

ruleId: PS-017

窄桌面窗口和浏览器放大不得自动触发移动端单列。组件先按合同收缩到最小尺寸；普通纵向内容优先由页面滚动，表格、代码、流程图、画布、日志等二维或连续内容可由功能区域滚动。只有移动稿、正式资料或用户批准才能建立移动端导航替换、隐藏元素或单列重排。

sectionId: micro-visual-and-integration

## 微视觉与系统集成

ruleId: PS-018

逐页合同除区域 Bounds 外，还必须枚举该页可见微视觉特征：图标/Logo、曲线、圆环、圆柱/装置、边框、圆角、阴影、透明度、渐变、裁切/Mask 与层级。每项关联 `MV###`、来源 `REF###`、区域、渲染策略、响应式行为和 Diff 容差。

ruleId: PS-019

逐页合同必须声明其统一应用路由、Shell、导航入口、共享状态/组件、前后页依赖和集成验收。页面可单独开发和截屏验收，但最终不能保留为独立端口或脱离统一 Router 的孤立 Demo。

sectionId: page-evidence-graph

## 页面证据图谱绑定

ruleId: PS-020

每个页面身份必须列出 `referenceRelationshipIds`、`calibrationIds`、`inheritedDesignRuleIds`、`inconsistencyIds`、`fixtureIds`、`traceabilityIds`、`navigationSystemIds` 和 `motionIds`。页面区域坐标使用校准后的真实 UI 视口，不得把源图外框、红线、说明文字或设备框算入组件 Bounds。

ruleId: PS-021

页面先继承适用的主体设计语言，再叠加页面直接证据。按钮、搜索、单选/多选、导航、卡片等每个实例都要能追溯到组件、Token 和 `DR###`；页面特例必须写明覆盖字段和来源，禁止通过复制整套局部样式绕过共享语言。

sectionId: page-navigation-and-motion

## 页面导航与动效状态

ruleId: PS-022

页面只引用已对齐的规范导航项，并明确该页选中项、展开父级、权限可见项、导航标题/图标和目标路由。截图中偶发缺少或增加的导航项不得直接变成页面专属导航，必须先在导航差异合同中解决。

ruleId: PS-023

页面的 hover、focus-visible、pressed、selected、loading、展开/收起和浮层进出状态引用 `MOT###`。交互验收除结果状态外，还要覆盖动效起点、中间关键状态、终点、时间参数和 Reduced Motion；静态截图不能替代可重放状态验收。

sectionId: page-semantic-visuals

## 页面语义视觉使用合同

ruleId: PS-024

页面通过 `semanticDimensionIds` 声明使用哪些语义维度，并用 `semanticValueIds` 精确列出当前页面/状态/变体可见的值。表格列、筛选项、详情标签、统计卡和弹窗不得各自复制一套近似颜色；都引用同一 `SEMVAL###`，页面专属例外必须有直接证据。

ruleId: PS-025

语义标签需同时覆盖默认视图、选中/筛选、hover、focus-visible、禁用、长文案、多语言、深浅背景和高对比环境。优先级、工作流状态、证据等级等不同维度即使同色也不得互换含义；批准页面的每个可见 `SEMVAL###` 必须有 `semanticTargets` Diff。
