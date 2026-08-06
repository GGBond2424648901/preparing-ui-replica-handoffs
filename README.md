# preparing-ui-replica-handoffs

我自己制作的 Codex Skill：把设计稿图片、UI 设计语言图、组件板、品牌板、状态图和动效参考，整理成可供下游 UI Agent 使用的中英双语 UI 复刻交付包。

An evidence-driven, bilingual Codex Skill that turns UI screenshots, design-language boards, component and brand boards, state references, and motion references into precise handoff contracts for downstream UI-replica Agents.

`preparing-ui-replica-handoffs` 面向桌面端 Web 和单一软件系统，重点解决设计稿复刻中的信息遗漏与无依据猜测问题。它会保留原始设计稿不动，并生成页面、状态、变体、导航、布局、组件、视觉 Token、动效、语义状态、微视觉和 Diff 验收合同。

> 当前版本：`1.0.0+codex.20260806040539` · 中英双语 · 桌面端 Web 优先 · 192 项测试

## 能做什么

- 识别并区分页面图、UI 设计语言图、组件图、品牌图、状态/动效图和装饰背景。
- 支持多张设计语言权威图，记录版本、主题、模块、作用域、互补规则和冲突。
- 先对齐并冻结规范导航，再进行逐页 UI 复刻。
- 支持桌面端 Web 混合布局：固定 Shell、弹性工作区、原生尺寸基线、页面/模块/混合滚动和必要的宽度扩展。
- 记录按钮、搜索、多选、表格、AI 对话、文件、工作流、Diff、日志等组件规范。
- 记录优先级、流程状态、证据等级、审批、风险、同步和 AI 状态的颜色与几何语义。
- 记录 Hover、Focus、Pressed、Selected、展开、加载和 Reduced Motion 动效。
- 输出中英文文档、机器合同、逐页实施合同和 Reference/Current/Overlay/Diff 验收目标。

## 输出内容

运行 Skill 后会生成：

- `docs/zh/`、`docs/en/`：中英双语设计稿目录、UI 设计语言、实施说明、组件规范和逐页合同。
- `assets/designs/`：英文编号的设计稿副本，使用相对路径和 SHA-256 追溯。
- `contracts/`：页面、设计语言、Token、组件、导航、动效、语义状态、微视觉、布局、实施计划和 Diff 等机器可读合同。
- `reports/`：联系表和验证报告。
- `tools/validate-command.txt`：标准验证命令。

这些文件共同构成“证据可追溯的实施合同”，不是只靠文件名和图片尺寸生成的空壳。多模态 Agent 需要先读取原始设计证据，补全设计语言、逐页布局、交互、状态和微视觉信息，再运行验证器。只有证据补全且验证通过的交付包，才能作为下游 UI Agent 的正式实施输入。

## 快速开始 / Quick Start

### 方式一：安装发布包（推荐）

1. 从 [`v1.0.0` Release](https://github.com/GGBond2424648901/preparing-ui-replica-handoffs/releases/tag/v1.0.0) 下载 `preparing-ui-replica-handoffs-plugin.zip`。
2. 解压后使用其中同时包含 `.codex-plugin/` 和 `skills/` 的 `preparing-ui-replica-handoffs` 插件目录。
3. 在 Codex 中启用插件，然后把原始设计稿图片目录交给 Skill。

直接下载地址：[preparing-ui-replica-handoffs-plugin.zip](https://github.com/GGBond2424648901/preparing-ui-replica-handoffs/releases/download/v1.0.0/preparing-ui-replica-handoffs-plugin.zip)

### 方式二：从源码使用

仓库中的 [`plugin/preparing-ui-replica-handoffs/`](plugin/preparing-ui-replica-handoffs/) 是可分发的 Codex 插件目录；[`skill/preparing-ui-replica-handoffs/`](skill/preparing-ui-replica-handoffs/) 是独立 Skill 源码目录。

### 调用方式

在 Codex 中安装插件后，将设计稿图片目录交给：

```text
$preparing-ui-replica-handoffs
```

建议先让 Skill 生成并完善交付包，再让 UI Agent 按页面编号逐页实施。所有页面应进入同一个 Router、同一个开发服务器和同一个软件系统；不是每张设计稿各自启动一个端口。

Typical workflow: provide the original image directory, let a multimodal Agent enrich the generated bilingual contracts from visual evidence, run the included validation command, and then hand the validated package to the implementation Agent.

## 复刻示例

下面的两张图是使用 GPT-5.6 Luna Max、在本 Skill 完善前生成的早期示例，用于展示“设计稿参考 → 实际 UI 复刻”的效果。它们不是当前最终版本的质量上限。

当前版本已经补充多张设计语言权威图、规则作用域与冲突处理、导航冻结、逐页微视觉、语义状态、动效、证据图谱和 Diff 验收合同。使用当前版本配合 SoI 模型时，预计可以获得更完整、更稳定的复刻效果。

The following pair is an early GPT-5.6 Luna Max example created before the current Skill improvements. The present release records substantially more visual evidence and contract detail; SoI models are expected to improve fidelity further.

### 设计稿参考图

![设计稿参考图](examples/reference-design.png)

### 实际 UI 复刻图

![实际 UI 复刻图](examples/gpt5.6-luna-max-replica.png)

## 目录说明

| 目录 | 作用 |
|---|---|
| `plugin/preparing-ui-replica-handoffs/` | Codex 插件目录，包含插件清单和嵌入式 Skill。 |
| `skill/preparing-ui-replica-handoffs/` | Skill 源码目录。 |
| `examples/` | 复刻示例图片。 |
| `tests/` | 合同、生成器、验证器和插件结构测试。 |

## 当前状态

当前版本为 `1.0.0+codex.20260806040539`。完整测试套件为 192/192 通过。公开发行版使用语义版本标签 `v1.0.0`。

## 开源许可证 / License

本项目采用 [MIT License](LICENSE) 开源。允许使用、复制、修改和再分发，但必须保留原始版权与许可声明。

This project is licensed under the [MIT License](LICENSE).
