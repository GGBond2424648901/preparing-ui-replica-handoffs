# Preparing UI Replica Handoffs Skill 设计规格

## 1. 目标

创建一个独立、自包含、可自动发现的 Codex Skill：`preparing-ui-replica-handoffs`。

用户提供 UI 设计稿图片、截图、Figma 导出图或 AI 生成稿后，Skill 将其整理为中英双语、机器可读、可冻结、可验证的 UI 复刻交付包，使后续开发 Agent 能在明确证据边界内实施页面，而不需要自行猜测页面、状态、布局、文案、组件、路由、交互或验收规则。

最终分发形态为个人 Codex 插件，插件内只携带本 Skill，不增加 MCP、App 或 Hook。

插件源码/安装位置：`C:\Users\PC\plugins\preparing-ui-replica-handoffs`。

个人 marketplace：`C:\Users\PC\.agents\plugins\marketplace.json`。

可分发备份：`D:\AI_Demo\Result\preparing-ui-replica-handoffs-plugin.zip`。

## 2. 非目标

- 不依赖、调用或要求安装 `design-image-to-web-replica`。
- 不负责实现 React、Vue 或其他 Web 页面。
- 不把整张设计图作为最终页面背景或热点交互层。
- 不把不可辨认或未展示的信息伪装成设计事实。
- 不承诺跨浏览器、跨系统、跨字体、跨 DPR 的无条件像素一致。
- 不自动提交、推送或修改用户现有 Git 变更。

## 3. 核心原则

1. 原始设计目录只读；所有整理、重命名和注释只作用于交付副本。
2. 冲突顺序为：用户最新明确修正 > 已批准参考图 > 已批准资产 > 已验证产品资料 > 需求 > 当前实现 > 已记录假设。
3. 页面身份使用 `pageId + stateId + variantId`，文件顺序不能代替稳定身份。
4. 每项结论都记录证据级别：`direct`、`derived`、`candidate`、`approved`、`unknown`。
5. 清晰文案照录；业务已确认文案引用正式资料；无法识别文案使用长度相近的推断文案并标记 `inferred`，同时保留原图坐标与缺口编号。
6. 设计稿示例数据默认分类为 `sample`，不能据此虚构 API、公式、权限或生产事实。
7. 坐标是参考边界，不是全页面绝对定位指令；必须同时记录容器、Grid/Flex、比例、间距、最小尺寸和滚动关系。
8. 原始画布基线与弹性布局、响应式变体分离。默认采用 `desktop-web` + `desktop-hybrid-elastic`：固定/粘性 Shell → 流式或有界流式主工作区 → 组件最小/基准/最大尺寸 → 按功能归属的整页/模块/混合滚动 → 获批重排。原始画布是测量基线而非固定容器或尺寸上限；宽屏按证据利用空间但不无限拉伸文本和卡片，窄桌面/浏览器放大先收缩到下限再滚动或执行获批重排。移动端单列必须是独立变体，禁止根节点整体缩放以及任意压缩或裁切。
9. 未展示状态必须登记为 `unknown` 或 `proposed`，不能默认复制通用 Loading、Empty、Error、Forbidden、Modal 或 Drawer。
10. 验收使用 reference/current/overlay/diff、DOM/区域/功能映射和交互用例三类证据；缺一类不能宣称完整通过。
11. 验收失败关闭；存在未解决的 blocker/major 缺口时不得生成“已完成”声明。
12. Git 操作只生成安全建议和白名单检查；是否创建 worktree、提交或推送取决于真实仓库状态和用户授权。

## 4. 双语策略

- `SKILL.md` 使用精简的中英双语入口和统一工作流。
- 详细规则分别位于 `references/zh/` 与 `references/en/`，章节和规则 ID 一一对应。
- 交付包同时生成 `docs/zh/` 与 `docs/en/`。
- JSON/CSV 合同只维护一份，稳定键名使用英文；可读字段提供 `zh-CN` 和 `en-US` 值。
- 双语校验器检查参考文件配对、标题 ID、规则 ID、模板字段和交付文档数量，防止两种语言漂移。

## 5. Skill 包结构

```text
preparing-ui-replica-handoffs/
├── SKILL.md
├── agents/openai.yaml
├── scripts/
│   ├── prepare_handoff.py
│   ├── validate_handoff.py
│   ├── build_contact_sheet.py
│   └── check_bilingual_parity.py
├── references/
│   ├── zh/
│   │   ├── intake-and-authority.md
│   │   ├── page-and-state-contract.md
│   │   ├── component-and-style-contract.md
│   │   ├── visual-qa-and-git-safety.md
│   │   └── delivery-package-spec.md
│   └── en/
│       └── 与中文文件一一对应
└── assets/
    ├── schemas/
    │   ├── handoff-config.schema.json
    │   ├── asset-manifest.schema.json
    │   ├── page-inventory.schema.json
    │   ├── ui-style-contract.schema.json
    │   ├── component-registry.schema.json
    │   ├── implementation-map.schema.json
    │   ├── capture-profile.schema.json
    │   ├── diff-regions.schema.json
    │   └── design-lock.schema.json
    └── templates/
        ├── handoff-config.template.json
        ├── requirement-ledger.template.csv
        ├── gap-register.template.csv
        ├── visual-qa-matrix.template.csv
        └── docs/zh 与 docs/en 文档模板
```

## 6. 输入

最小输入：

- 设计图片目录；
- 交付输出目录；
- 设计版本；
- 交付语言，默认 `zh-CN,en-US`。

可选输入：

- 产品目标、用户角色和模块清单；
- 正式需求、路由、数据结构和交互说明；
- Logo、图标、字体及品牌资产；
- 目标技术栈；
- 已批准的页面、状态和响应式变体；
- 浏览器、视口、DPR、Locale、时区、主题和字体环境；
- Git 仓库路径与允许新增的相对路径。

缺少可选输入时，Skill 必须登记缺口，不能静默猜测。

## 7. 标准交付包

```text
ui-replica-handoff/
├── README.md
├── assets/designs/<design-version>/
├── docs/
│   ├── zh/
│   │   ├── 设计稿总目录.md
│   │   ├── UI实施说明.md
│   │   ├── 组件规范.md
│   │   └── pages/<page-state-variant>.md
│   └── en/
│       ├── Design-Catalog.md
│       ├── UI-Implementation-Guide.md
│       ├── Component-Specification.md
│       └── pages/<page-state-variant>.md
├── contracts/
│   ├── requirement-ledger.csv
│   ├── gap-register.csv
│   ├── asset-manifest.json
│   ├── page-inventory.json
│   ├── ui-style-contract.json
│   ├── component-registry.json
│   ├── implementation-map.json
│   ├── capture-profile.json
│   ├── diff-regions.json
│   ├── visual-qa-matrix.csv
│   └── design-lock.json
├── reports/
│   ├── contact-sheet.png
│   └── validation-report.json
└── tools/
    └── validate-command.txt
```

所有 Markdown 中的图片链接必须是相对于交付包的路径。交付包不得依赖创建机器的绝对路径。

## 8. 生成流程

1. 只读扫描输入图片，记录相对路径、格式、字节数、尺寸、SHA-256、重复组和来源集合哈希。
2. 生成规范化英文副本名称；原文件保持不动。无法识别页面语义时使用稳定的 `unclassified` slug，不猜名称。
3. 生成联系表供人工确认页面顺序、重复图和模块归属。
4. 创建初始页面、状态和视口清单；默认图只证明默认状态。
5. 检查产品资料并建立权威顺序、需求台账和缺口登记。
6. 对每个目标生成逐页合同，包含身份、来源、画布、Shell、区域、布局关系、组件、文案、图标、数据分类、交互、状态、响应式和验收项。
7. 建立全局样式和组件合同；相似组件先标记 `candidate`，批准后才进入共享组件。
8. 生成双语人读文档和单份机器合同。
9. 生成设计锁；锁由脚本根据源图片和合同计算，不能手写为通过。
10. 运行结构、路径、哈希、覆盖率、双语一致性和 Git 白名单验证。
11. 未满足的项目进入验证报告并保持失败状态。

## 9. 脚本职责

### `prepare_handoff.py`

- 初始化交付目录；
- 只读扫描和复制图片；
- 获取尺寸、哈希和重复组；
- 生成稳定 ID、英文文件名草案、合同模板和双语文档骨架；
- 支持 `--dry-run`；
- 若输出目录位于输入目录内部则拒绝运行；
- 不覆盖非本工具生成的文件，除非显式使用安全更新模式。

### `validate_handoff.py`

- 校验 JSON/CSV、Schema、相对路径和图片哈希；
- 校验源图与副本一一映射；
- 校验页面/状态/变体唯一性与逐页文档覆盖；
- 校验必需状态已登记，未知状态有 gap ID；
- 校验机器合同与中英文文档引用一致；
- 校验设计锁、环境字段、Diff 策略和 QA 矩阵；
- 可选校验 Git 暂存文件是否全部位于允许路径；
- 输出失败关闭的 JSON 报告。

### `build_contact_sheet.py`

- 依据资产清单生成带稳定 ID、尺寸和文件名的联系表；
- 不修改输入图片。

### `check_bilingual_parity.py`

- 校验中英文参考文件和模板一一配对；
- 校验规则 ID、章节 ID 和占位字段集合一致；
- 不要求自然语言逐字等长。

## 10. 错误处理

- 输入目录不存在、无支持图片、输出目录嵌套输入目录、哈希变化、重复 ID、路径越界或 Schema 无效时立即失败。
- 不支持的图片格式登记为缺口，不擅自转码。
- 发现损坏图片时保留来源记录并标记 blocker，不复制成已批准资产。
- 发现原图在扫描与冻结之间变化时拒绝生成设计锁。
- 发现绝对路径泄漏到交付文档时验证失败。
- 无 Git 仓库时跳过 Git 状态检查并明确报告；不得假设或自动创建 worktree。

## 11. 基线测试发现

无 Skill 的三个 Agent 都能提出部分正确原则，但产物不稳定：

- 一个 Agent 只生成三份合并双语 Markdown，缺少逐页双语合同、组件注册表、实施映射和完整状态矩阵。
- 一个 Agent 生成十层重型目录、PDF 签署基线及大量拆分 CSV，超出本任务的必要复杂度。
- 一个 Agent 把固定响应式断点和 Git worktree 当成默认事实，而没有先根据项目证据和仓库状态判断。
- 三个 Agent 使用不同编号、证据等级、目录、文件名和完成声明，无法形成可重复流程。

新 Skill 的价值是固定最小完整交付形态，同时允许通过配置扩展，而不是重复普通 Agent 已经知道的原则。

## 12. 验证计划

1. 用 3 张小型测试图片验证初始化、命名、哈希、重复检测、双语生成和失败关闭。
2. 验证输出目录嵌套、损坏图片、绝对路径、哈希漂移、重复 ID 和中英文缺页等失败场景。
3. 使用当前 16 张 UI 设计稿的只读副本前向验证，输出到临时目录，不修改现有交付包。
4. 运行 `quick_validate.py` 验证 Skill 元数据和结构。
5. 用新鲜 Agent 加载 Skill 运行同一场景，检查输出结构收敛、未知项不被猜测、Git 不被误操作。
6. 通过后打包 ZIP 并保留安装目录。

## 13. 完成定义

- Skill 可被 Codex 自动发现并有正确的 `agents/openai.yaml`。
- `SKILL.md` 和所有必需参考均为中英双语且通过配对检查。
- 生成器、联系表、验证器和双语检查脚本有先失败后通过的自动化测试证据。
- 模板和 Schema 能覆盖原图、页面、状态、变体、组件、文案、数据、布局、交互、响应式、环境、Diff、Git 范围和缺口审批。
- 真实 16 图样例可生成完整初始交付包，现有源图和原交付包哈希不变。
- 前向测试 Agent 按统一结构执行，不依赖任何外部 UI 复刻 Skill。
- 插件包含有效的 `.codex-plugin/plugin.json`，其 `skills` 指向内置的 `./skills/`，不声明不存在的 MCP、App 或 Hook。
- 个人 marketplace 以追加方式登记本插件，不修改已有插件条目。
- 插件通过官方插件校验，内置 Skill 通过官方 Skill 校验。
- ZIP 与个人插件安装目录内容一致。

## 14. 设计语言权威与逐页精确升级

设计输入不再被假定为“全部都是页面截图”。每个资产先获得 `REF###`，并分类为页面参考图、UI 设计语言图、组件板、品牌板、交互状态板、动效参考、装饰背景、内容资产或 unknown。设计语言图单独形成中英双语 `UI设计语言.md` / `UI-Design-Language.md`，逐条记录原则、材质、Token、Shell、Logo/图标、图表、动效、状态、作用域、例外和冲突。页面继承适用的共享规则，再叠加页面直接证据；用户修正和页面专属设计优先。

新增 `micro-visual-contract.json`，按特征记录图标描边、Logo 留白、曲线控制点、圆环和圆柱比例、边框/圆角/阴影/透明度、渐变、裁切、Mask、层级、渲染策略、响应式行为和 Diff 容差。Logo/专有图形优先 SVG，普通图标使用锁定图标库，简单材质使用 CSS，精确曲线/图表优先 SVG，高密度动态图形可使用 Canvas，环境装饰可使用本地光栅图。登录页可使用一张纯装饰完整背景加真实 DOM 交互层，但禁止将含控件、文字、数据或状态的整页截图当成实现。

新增 `application-system.json` 与 `implementation-plan.json`，固定“共享视觉基础 → 逐页复刻 → 系统集成”的交付顺序。最终页面必须通过统一 Router 运行在一个应用、一个开发服务器和共享端口中；每页执行合同完整性、结构、视觉、交互与集成导航五类门禁，不能以独立端口 Demo 作为最终交付。
