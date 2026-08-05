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

原始画布是原生像素测量基线，不是页面、工作区或模块内容范围的最大尺寸。内容超出时保持组件尺寸、比例、文字和位置关系，并依据设计与功能证据记录整页滚动、模块内滚动或混合滚动；证据不足时关联 `gapId`，不得通过压缩、缩小、重排或裁切来适应窗口。

sectionId: qa-and-git-safety

## QA 与 Git 安全

{{qaAndGitSafety}}
