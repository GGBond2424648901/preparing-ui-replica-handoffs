---
templateId: component-specification
locale: zh-CN
---

# 组件规范

sectionId: component-registry

## 组件注册表

{{componentRegistry}}

sectionId: style-tokens

## 样式令牌

{{styleTokens}}

sectionId: states-and-variants

## 状态与变体

{{componentStatesAndVariants}}

按钮、图标按钮、搜索、输入框、单选、多选、开关、下拉、多选标签、Tab、分页、表格操作、导航项、卡片、弹窗和抽屉必须逐状态引用主体视觉语言的 `DR###` 与 `styleTokenRefs`，并列出局部覆盖。组件库默认样式不能绕过主体材质。

sectionId: semantic-visual-components

## 语义标签、圆点与等级组件

{{semanticVisualEncoding}}

优先级、流程状态、证据等级、反馈、审批、风险、同步、权限和 AI 状态不得共用一个“万能 Badge”。组件按 `SEM###` 维度和 `SEMVAL###` 值绑定含义，并记录文字/背景/边框/圆点/图标颜色、胶囊几何、字体、长文案、多语言、对比度及默认/hover/focus-visible/selected/disabled 状态。视觉颜色近似但业务含义错误视为失败。

sectionId: motion-and-focus

## 动效、Hover 与焦点

每个 `MOT###` 记录触发、起止视觉、时长、延迟、缓动、动画属性、变换原点、层级、指针/焦点行为、状态帧证据和 Reduced Motion。鼠标 Hover 必须有键盘 focus-visible 的等价可见反馈。

sectionId: rendering-strategy

## 渲染与素材策略

每个组件记录 `renderingStrategy` 与资产引用：真实内容/控件使用 DOM，正式 Logo/专有图形使用本地 SVG，通用图标使用锁定图标库，简单几何与材质使用 CSS，精确曲线/圆环/图表优先 SVG，高密度动态图形可用 Canvas，环境装饰可使用本地光栅图。登录页允许纯装饰整图加 DOM 交互层，但禁止截图式 UI。

sectionId: micro-visual-reuse

## 微视觉与复用

共享组件仍需记录图标描边、边框、圆角、阴影、透明度、渐变、裁切和层级；页面特例保持局部覆盖。每个复用决定链接设计语言 `referenceId`、页面证据和微视觉特征 ID。

sectionId: elastic-sizing

## 弹性尺寸

每个 Shell、区域和组件必须记录宽度模式、桌面角色、窄桌面行为、最小/基准/最大宽高、Grid/Flex 轨道或伸缩权重、换行/重排条件、宽屏剩余空间分配和溢出所有者。`fixed-shell`、`flexible-workspace`、`bounded-content`、`scroll-surface` 与 `intrinsic` 可在同一页面并存；不得把统一拉伸或统一滚动强加给全部组件。浏览器缩放按有效 CSS 视口变化处理，不得对页面根节点整体缩放。
