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

sectionId: elastic-sizing

## 弹性尺寸

每个 Shell、区域和组件必须记录宽度模式、桌面角色、窄桌面行为、最小/基准/最大宽高、Grid/Flex 轨道或伸缩权重、换行/重排条件、宽屏剩余空间分配和溢出所有者。`fixed-shell`、`flexible-workspace`、`bounded-content`、`scroll-surface` 与 `intrinsic` 可在同一页面并存；不得把统一拉伸或统一滚动强加给全部组件。浏览器缩放按有效 CSS 视口变化处理，不得对页面根节点整体缩放。
