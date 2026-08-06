---
templateId: ui-design-language
locale: zh-CN
---

# UI 设计语言

sectionId: authority-references

## 权威参考图与适用范围

{{referenceAuthority}}

每张输入图必须先在 `../../contracts/reference-inventory.json` 中分类。`design-language-reference`、`component-board`、`brand-reference`、`interaction-state-board` 与 `page-reference` 分别建档，不得把设计语言总览误当成业务页面，也不得把单页特例升级为全局规则。每条共享规则都要写明来源 `referenceId`、裁图区间、作用域、冲突优先级和适用/不适用页面。

可见标题明确写有“UI 设计语言”等专名时，记录标题文字和 Bounds 作为直接证据。设计语言图可以有多张：在 `design-rule-cascade.json` 中按产品/版本/主题/模块组成一个或多个 `DLS###`，保留每张来源并分别记录互补、覆盖与冲突。

sectionId: principles-and-materials

## 设计原则、层次与材质

记录设计原则、信息密度、8px/其他网格、背景层/内容层/浮层、玻璃/磨砂/实色材质、Blur、饱和度、透明度、边框、阴影、发光与层级。数值未知时保留 `unknown + gapId`，不得套用常见 SaaS 默认值。

“苹果风格、磨砂质感、高级玻璃、透明磨砂”等主体描述必须拆成背景、Blur、透明度、色调/饱和度、边框/高光、阴影、纹理、层级和禁止组合，不能只保留形容词。

sectionId: tokens

## 精确视觉 Token

{{styleContract}}

颜色、渐变、字体、字重、字号、行高、字距、间距、圆角、边框、阴影、透明度、模糊、层级、动效、密度和背景分别记录原始测量值、归一化 Token、来源与容差。相近值不自动合并。

sectionId: shell-components

## Shell、组件与复用语言

逐一描述 Sidebar、TopBar、导航选中态、工作区、卡片、按钮、输入框、Tab、标签、表格、图表、弹窗、抽屉、Toast、Tooltip、AI 状态等的 anatomy、尺寸、材质、状态和复用边界。给出“共享规则 → Shell/组件 → 使用页面”的复用矩阵。

按钮、搜索、输入、单选/多选、开关、下拉、导航项等全部控件必须给出“设计规则/Token → 组件 → 默认/hover/focus-visible/pressed/selected/disabled/loading/error → 页面”的继承矩阵。

sectionId: semantic-status-grammar

## 语义颜色、状态与等级语法

{{semanticVisualEncoding}}

按优先级、流程状态、证据等级、反馈、审批、风险、同步、在线状态、权限、AI 状态、数据新鲜度、校验结果分别建立 `SEM###`。逐个 `SEMVAL###` 记录编码/文案/含义、胶囊或圆点形式、文字/底色/边框/指示点/图标颜色、尺寸、字体、交互状态、来源 Bounds 和对比度。相同颜色不得跨维度自动合并；未在设计稿出现的值保持缺口。

sectionId: brand-icons-assets

## Logo、图标与素材实现策略

正式 Logo 优先使用交付包内 SVG；通用图标使用已锁定版本和精确名称的图标库；专有图形使用本地 SVG；简单色块、圆点、胶囊、边框和渐变使用 CSS；曲线、连线、圆环与精确图表标记优先 SVG，海量动态图形才使用 Canvas；环境插画和纹理可使用本地光栅图。禁止 Emoji、字体字符冒充图标、远程热链和来源不明素材。

sectionId: micro-visual-language

## 微视觉语言

{{microVisualContract}}

图标尺寸/描边、Logo 留白、装置与圆柱比例、曲线控制点、圆环直径/环宽/起止角、边框、四角半径、阴影、透明度、渐变停止点、裁切、Mask、层级和溢出均进入微视觉合同，并纳入结构与分区 Diff。

sectionId: decorative-backgrounds

## 装饰背景策略

登录页、Hero 或环境场景可将纯装饰背景先生成/导出为一张完整画布，再由真实 DOM 在其上实现 Logo、标题、表单、按钮、错误、动态数据和交互。背景合同必须记录来源/生成状态、原始尺寸、比例、`cover/contain/position`、焦点、安全区、裁切和宽窄变体。禁止把含控件、文字、数据或状态的整页截图当成交互 UI 背景；普通业务页只能在有证据时局部采用该策略。

sectionId: motion-states-accessibility

## 动效、状态与可访问性

记录默认、Hover、Focus、Pressed、Disabled、Loading、Empty、Error、权限和 AI 运行状态；记录持续时间、缓动、位移/透明度变化和 reduced-motion。设计未展示的状态标 `proposed`，不能伪装成直接证据。

所有有证据的微交互进入 `motion-contract.json`，记录触发、起止状态、动画属性、时长、延迟、缓动、层级/指针/焦点行为、状态帧来源和 Reduced Motion；仅有静态图时不推断动效事实。

sectionId: forbidden-and-gaps

## 禁止项与缺口

禁止截图式实现、全页 `transform: scale()`、无证据压缩/重排/裁切、随意替换 Logo/图标、把页面特例全局化、忽略微细节以及隐去冲突或未知。所有未决项必须关联 `gapId`。
