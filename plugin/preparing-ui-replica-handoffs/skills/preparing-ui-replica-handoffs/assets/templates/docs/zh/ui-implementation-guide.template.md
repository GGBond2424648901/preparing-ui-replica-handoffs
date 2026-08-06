---
templateId: ui-implementation-guide
locale: zh-CN
---

# UI 实施说明

sectionId: authority

## 权威顺序与证据

{{authorityOrder}}

sectionId: implementation-flow

## 实施流程

使用 `{{implementationMapPath}}` 获取页面、区域、组件、数据、交互、响应式与 Git 范围映射。

先冻结全局 UI 设计语言、Token、Shell、Logo/图标策略和共享组件，再按 `implementation-plan.json` 的顺序逐页实现。每页必须依次通过合同完整性、结构、视觉、交互和集成导航门禁，才进入下一页；最终所有路由在同一个应用、同一个开发服务器和共享端口中展示，禁止为每页创建独立端口或孤立 Demo。

sectionId: reference-classification

## 参考图分类与设计语言继承

先读取 `../../contracts/reference-inventory.json` 和 `UI设计语言.md`。全局设计语言图、组件板、品牌板、状态板与页面图分别取证；页面先继承适用的共享规则，再叠加该页直接证据。冲突时页面专属设计和用户修正优先，并记录胜出证据，不能静默覆盖。

sectionId: visual-assets

## SVG、CSS、Canvas 与装饰背景

Logo/专有图形优先 SVG，通用图标使用锁定图标库，简单几何与材质使用 CSS，精确曲线/圆环/图表优先 SVG，高密度动态图形可用 Canvas，环境装饰可用本地光栅图。登录页等允许一张完整装饰背景加真实 DOM UI；含文字、控件、数据或状态的整页截图不能充当实现。

sectionId: canvas-and-overflow

## 画布扩展与滚动

原始画布是原生像素测量基线，不是固定容器或页面、工作区、模块内容范围的最大尺寸。内容超出时保持最小组件尺寸、比例、文字和关键位置关系，并依据设计与功能证据记录换行、重排、整页滚动、模块内滚动或混合滚动；证据不足时关联 `gapId`，不得通过压缩、整体缩放或裁切来适应窗口。

sectionId: elastic-layout

## 弹性布局与浏览器缩放

逐页记录 Shell、区域、网格和组件的 `fixed`、`fluid`、`bounded-fluid`、`intrinsic` 或 `mixed` 尺寸模式，以及最小/基准/最大尺寸、Grid/Flex 轨道、伸展权重、收缩下限和溢出所有者。宽屏应按证据让主工作区利用可用宽度并分配剩余空间，避免无依据的大面积空白；窄屏或浏览器缩放产生的有效窄视口达到最小尺寸后，按合同换行、重排或滚动。禁止根节点 `transform: scale()`，有明确 `max-width` 的设计除外并须登记证据。

sectionId: desktop-web-first

## 桌面端 Web 优先顺序

默认布局策略为 `desktop-web` + `desktop-hybrid-elastic`：固定/粘性 Shell → 流式或有界流式主工作区 → 组件最小/基准/最大尺寸 → 按功能归属的整页/模块/混合滚动 → 获批重排。普通纵向内容优先整页滚动；表格、代码、流程图、画布和日志可使用专用滚动面。窄桌面窗口或浏览器放大不得自动转换为移动端单列；移动端必须使用独立 `variantId`。

sectionId: qa-and-git-safety

## QA 与 Git 安全

{{qaAndGitSafety}}
