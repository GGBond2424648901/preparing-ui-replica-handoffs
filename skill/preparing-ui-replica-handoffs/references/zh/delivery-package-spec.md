# 交付包规格

sectionId: package-tree

## 固定目录

ruleId: DP-001

标准根目录包含 `README.md`、`assets/designs/<design-version>/`、`docs/zh/`、`docs/en/`、`contracts/`、`reports/` 和 `tools/`。不得增加对创建机器、外部技能或远程资源的运行时依赖。

ruleId: DP-002

中文文档至少包含 `设计稿总目录.md`、`UI实施说明.md`、`组件规范.md` 与 `pages/<page-state-variant>.md`；英文镜像为 `Design-Catalog.md`、`UI-Implementation-Guide.md`、`Component-Specification.md` 和同 ID pages 文档。

sectionId: catalog

## 总目录职责

ruleId: DP-003

设计稿总目录记录页面/状态/变体 ID、名称、模块、来源与副本图片、原始画布、SHA-256、建议路由及证据、状态、优先级、Shell 类型、资产、逐页合同链接和缺口。它是导航索引，不替代逐页合同。

sectionId: implementation-guide

## 实施说明职责

ruleId: DP-004

UI 实施说明定义全局工作流、权威顺序、原生像素基线、滚动策略、实施顺序和每个 `P###-S##-V##` 的区域、几何、组件、文案、图标、数据、交互、状态、响应式、映射与验收合同。

ruleId: DP-005

逐页文档必须能让下游 Agent 区分直接证据、推导、候选、批准和未知；任何仍需决策的信息引用 `gapId`，不得隐藏在散文措辞中。

sectionId: component-spec

## 组件规范职责

ruleId: DP-006

组件规范记录精确 token、Shell、Logo、图标映射、组件 anatomy/尺寸/状态/交互/内容边界/可访问性，以及页面复用矩阵；复杂组件至少覆盖设计中出现的导航、卡片、按钮、表格、AI 对话、文件、工作流、Diff 和日志。

sectionId: contracts

## 机器合同

ruleId: DP-007

`contracts/` 必须包含 requirement ledger、gap register、asset manifest、page inventory、UI style contract、component registry、implementation map、capture profile、diff regions、visual QA matrix 和 design lock。稳定键名使用英文，可读字段提供 `zh-CN`/`en-US`。

ruleId: DP-008

requirement ledger 把每项需求映射到页面、区域、组件、交互和 QA；implementation map 把同一目标映射到建议代码位置但不虚构真实文件；gap register 保存未知项及审批生命周期。

ruleId: DP-009

design lock 由脚本根据交付文件集与哈希计算。禁止手写、复制旧锁或把 validation report 当锁输入；任何锁覆盖文件变化都必须失败并重新冻结。

sectionId: paths-links

## 路径与链接

ruleId: DP-010

所有存储路径和 Markdown 图片/文档链接均使用相对路径并保持在交付根目录内。拒绝盘符路径、UNC、根路径、`file:`/HTTP URI、路径穿越、链接目录和别名覆盖。

ruleId: DP-011

每个整理图片副本必须与源图一对一、字节哈希一致，并使用 Agent 易识别的稳定英文编号名称。语义未知时用 `unclassified`，不得由脚本看文件名猜页面业务。

sectionId: generation

## 生成与人工富化

ruleId: DP-012

`prepare_handoff.py` 生成确定性初始骨架；`build_contact_sheet.py` 生成索引。随后 Agent 必须查看原分辨率图片并富化所有合同。初始骨架有未解决 `blocker`/`major`，因此预期验证失败关闭。

ruleId: DP-013

更新只能作用于有明确所有权标记的交付目录，并采用无覆盖冲突的安全发布；并发冲突、非法恢复目录或所有权不明时保留证据并停止，不递归删除未知内容。

sectionId: bilingual

## 双语一致性

ruleId: DP-014

中英文档自然语言可不同，但文件配对、页面 ID、section ID、rule ID、占位符和图片引用集合必须一致。运行 `check_bilingual_parity.py`；不得只翻译标题而遗漏规则。

sectionId: completion

## 完成定义

ruleId: DP-015

只有源图不变、双语覆盖完整、机器合同非空且互相引用有效、所有图片/文档/QA 路径可解析、设计锁通过、三类 QA 完成、无未解决 `blocker`/`major`、可选 Git 白名单通过时，才可声明可实施。

ruleId: DP-016

若仍有未知项，交付包仍可作为“初始交付”提供，但必须在 README 和 validation report 明确写 incomplete/failed、列出 `gapId` 和下一步；禁止使用“已完全还原”“无需推断”等声明。

ruleId: DP-017

可实施验证必须由调用方提供原始设计目录，并重新核对来源集合与每张源图哈希；交付包只保存相对来源路径，不保存创建机器绝对路径。未提供源目录时验证失败，不得作为“离线豁免”。

ruleId: DP-018

批准页面的逐页机器合同和双语页面文档必须有实质内容：区域、布局、文案、组件、数据和交互互相引用，组件实例可解析到非空注册表。确实不存在的类别必须由该页引用的已解决缺口明确标记 `[absence:<field>]`，不能以空数组默认通过。

ruleId: DP-019

逐页文档按 section ID 验证语义归属：身份/来源只能在身份段完成，Shell/区域在画布段，布局/文案/图标/数据在对应段，组件/交互/响应式在行为段，QA/缺口在验收段。把全部 ID 附加到任意一段不能满足覆盖率。
