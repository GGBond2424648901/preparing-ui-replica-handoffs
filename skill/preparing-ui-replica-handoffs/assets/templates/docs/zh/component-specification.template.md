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

sectionId: rendering-strategy

## 渲染与素材策略

每个组件记录 `renderingStrategy` 与资产引用：真实内容/控件使用 DOM，正式 Logo/专有图形使用本地 SVG，通用图标使用锁定图标库，简单几何与材质使用 CSS，精确曲线/圆环/图表优先 SVG，高密度动态图形可用 Canvas，环境装饰可使用本地光栅图。登录页允许纯装饰整图加 DOM 交互层，但禁止截图式 UI。

sectionId: micro-visual-reuse

## 微视觉与复用

共享组件仍需记录图标描边、边框、圆角、阴影、透明度、渐变、裁切和层级；页面特例保持局部覆盖。每个复用决定链接设计语言 `referenceId`、页面证据和微视觉特征 ID。

sectionId: elastic-sizing

## 弹性尺寸

每个 Shell、区域和组件必须记录宽度模式、桌面角色、窄桌面行为、最小/基准/最大宽高、Grid/Flex 轨道或伸缩权重、换行/重排条件、宽屏剩余空间分配和溢出所有者。`fixed-shell`、`flexible-workspace`、`bounded-content`、`scroll-surface` 与 `intrinsic` 可在同一页面并存；不得把统一拉伸或统一滚动强加给全部组件。浏览器缩放按有效 CSS 视口变化处理，不得对页面根节点整体缩放。
