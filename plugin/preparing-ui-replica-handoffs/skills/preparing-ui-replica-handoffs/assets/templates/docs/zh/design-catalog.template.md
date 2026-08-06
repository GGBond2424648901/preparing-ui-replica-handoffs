---
templateId: design-catalog
locale: zh-CN
---

# 设计稿总目录

sectionId: overview

## 总览

- 设计版本：`{{designVersion}}`
- 来源集合哈希：`{{sourceSetHash}}`

sectionId: page-index

## 页面、状态与变体索引

本索引在骨架阶段只是页面候选。先依据 `../../contracts/reference-inventory.json` 区分页面图、设计语言图、组件板、品牌板、状态/动效板和装饰背景；非页面资产不得保留为正式 `P###` 页面。

{{pageInventoryTable}}

sectionId: reference-index

## 参考资料角色索引

每个 `REF###` 必须记录角色、权威类别、全局/模块/组件/页面作用域、适用页面、提取规则、冲突和缺口。全局视觉规则详见 [UI设计语言](UI设计语言.md)。

sectionId: evidence-and-gaps

## 证据与缺口

{{gapSummary}}
