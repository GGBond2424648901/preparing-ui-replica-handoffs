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

记录原始画布宽高、像素密度（已知时）、背景、内容起点、Sidebar/TopBar/底栏尺寸、固定/粘性/滚动层级和裁剪边界。未知尺寸写 `unknown` 并登记 `gapId`。

ruleId: PS-004

原始画布是 1:1 基线。视口不足时保持卡片宽度、列比例、文字尺寸和模块位置，通过扩展工作区或水平滚动展示；不得为了塞入浏览器而压缩、重排、移动或裁切。

sectionId: regions

## 区域与几何

ruleId: PS-005

为每个可见区域记录唯一 region ID、`x/y/width/height` 参考边界、父容器、上下左右邻接、对齐、列比例、间距、内边距、最小/最大尺寸、层级和溢出行为。坐标是测量基线，不是要求全页绝对定位。

ruleId: PS-006

同时描述适合实现的布局模型（正常流、Grid、Flex、叠层）、锚定关系和滚动所有者。若像素测量存在误差，记录容差和测量方法，不伪造整数精度。

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

只有设计图、正式资料或用户批准能建立响应式 `variantId`。记录断点证据、容器变化、顺序变化、隐藏/替换元素和滚动策略；不得默认套用常见断点。

ruleId: PS-014

未批准的窄屏默认继承原始几何并水平滚动。若必须提出适配方案，标为 `candidate`/`proposed`，单独验收，不能覆盖原生像素基线。

sectionId: page-acceptance

## 逐页完成条件

ruleId: PS-015

逐页合同必须覆盖身份、来源、画布、Shell、区域、布局、组件、文案、图标、数据、交互、状态、响应式、实现映射、QA 与缺口。缺少任何一项时状态是 incomplete，不得写“无需推断”。

