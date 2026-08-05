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

sectionId: canvas-and-overflow

## 画布扩展与滚动

原始画布是原生像素测量基线，不是固定容器或页面、工作区、模块内容范围的最大尺寸。内容超出时保持最小组件尺寸、比例、文字和关键位置关系，并依据设计与功能证据记录换行、重排、整页滚动、模块内滚动或混合滚动；证据不足时关联 `gapId`，不得通过压缩、整体缩放或裁切来适应窗口。

sectionId: elastic-layout

## 弹性布局与浏览器缩放

逐页记录 Shell、区域、网格和组件的 `fixed`、`fluid`、`bounded-fluid`、`intrinsic` 或 `mixed` 尺寸模式，以及最小/基准/最大尺寸、Grid/Flex 轨道、伸展权重、收缩下限和溢出所有者。宽屏应按证据让主工作区利用可用宽度并分配剩余空间，避免无依据的大面积空白；窄屏或浏览器缩放产生的有效窄视口达到最小尺寸后，按合同换行、重排或滚动。禁止根节点 `transform: scale()`，有明确 `max-width` 的设计除外并须登记证据。

sectionId: qa-and-git-safety

## QA 与 Git 安全

{{qaAndGitSafety}}
