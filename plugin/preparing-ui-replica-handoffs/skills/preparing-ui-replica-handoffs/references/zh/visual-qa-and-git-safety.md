# 视觉验收与 Git 安全

sectionId: capture-profile

## 可重复采集环境

ruleId: QG-001

每个 QA 目标必须引用 capture profile，记录浏览器/版本、操作系统、CSS 视口、DPR、Locale、时区、主题、浏览器缩放、字体及加载等待条件。原始基线、宽屏、窄屏和缩放场景使用独立 profile；未知环境字段保持 `unknown` 并登记 `gapId`，不能用本机默认值冒充设计环境。

ruleId: QG-002

采集前固定路由、初始数据/夹具、权限、滚动位置、动画/光标策略和网络稳定条件。reference 与 current 必须使用兼容环境和同一区域定义。

sectionId: evidence-files

## 四类视觉证据

ruleId: QG-003

每个目标保存独立相对路径的 `reference/current/overlay/diff` 文件；文件路径不能互相别名。像素完全一致时内容哈希可以相同，但文件身份、来源和生成步骤仍需可追溯。

ruleId: QG-004

Diff 区域引用真实 region ID，记录裁剪边界、阈值、允许差异、忽略区域和理由。不得用高阈值、模糊或大面积遮罩隐藏结构错误。

sectionId: acceptance-classes

## 三类验收

ruleId: QG-005

视觉验收检查画布、内容占用宽度、剩余空间分配、列比例、最小尺寸、颜色、字体、间距、尺寸、边框、圆角、阴影、图标、图像、层级、溢出和 reference/current/overlay/diff。宽屏出现设计无依据的大面积空白，或窄屏出现压扁、裁切、错位，均视为布局失败；每个失败关联页面、区域、严重度和修复证据。

ruleId: QG-006

结构验收检查 DOM/组件/区域/需求/实现映射、页面与状态覆盖、可访问语义、固定/流式/有界流式尺寸模式、最小/基准/最大尺寸、Grid/Flex 伸缩规则、滚动所有权和相对路径完整性。视觉相近不能替代结构验收。

ruleId: QG-007

交互验收按用例验证初始状态、动作、反馈、成功/失败、弹窗/抽屉、路由、键盘、焦点和数据变化。静态截图通过不能替代交互验收。

ruleId: QG-008

完成声明必须同时具备视觉验收、结构验收和交互验收。任一类为 not-run、incomplete 或 failed，整体均不得通过。

sectionId: severity

## 严重度与失败关闭

ruleId: QG-009

`blocker` 表示无法可靠实施/验收或有安全与证据完整性风险；`major` 表示关键布局、状态、交互或资产缺失；`minor` 表示不阻断的局部偏差。`blocker`/`major` 必须解决或由有权用户明确批准例外。

ruleId: QG-010

验证器只依据实际合同和文件计算结论。禁止手工把 validation report 改成 passed；报告是派生产物，不是权威输入。原始输入、合同或锁变化后必须重新验证。

sectionId: git-safety

## Git 范围

ruleId: QG-011

Git 检查是只读的。脚本不得初始化仓库、创建/删除 worktree、暂存、提交、推送、重置、清理或改写用户已有变更；无仓库时明确报告 skipped。

ruleId: QG-012

只有用户提供仓库和允许相对前缀时，检查已暂存路径是否都在白名单内。发现越界文件即失败并列出路径，不自动取消暂存或移动文件。

ruleId: QG-013

准备提交前人工确认 `git status`、目标分支、diff 和文件清单，只包含本次新增/修改的交付包或插件文件。用户已有未提交变更保持原样；提交/推送需要独立授权。

sectionId: release-gate

## 发布门禁

ruleId: QG-014

发布前运行双语、结构、Schema、路径、哈希、设计锁、覆盖率、QA、缺口和可选 Git 白名单检查。结果、命令、时间、工具版本和未解决项写入报告；报告不得泄漏创建机器绝对路径。

ruleId: QG-015

每条通过的 QA 行必须引用带 SHA-256 的机器可读 evidence record。记录必须绑定 qa/page/state/variant/证据类型、工具、可重放命令、实际工件路径与哈希及逐项检查；任意图片或手填 `pass` 不能构成通过证据。

ruleId: QG-016

视觉通过由验证器解码 reference/current、重算 overlay/diff 与像素差异率并对照区域容差；结构通过必须把需求、区域和组件映射到真实合同；交互通过必须引用页面已登记 interaction ID 的可重放测试用例。三类结果均从证据推导，不信任声明状态。

ruleId: QG-017

reference 必须绑定该页面资产清单中的已验证设计副本。每条通过记录还必须绑定带哈希的 runner result，包含工具/版本/命令、起止时间、退出码 0、非空且全部通过的断言及工件哈希；验证器不执行交付包中的不可信命令。

ruleId: QG-018

结构 runner 必须绑定 DOM 快照与实施快照，并把 region/component/target file 与机器合同交叉验证；交互 runner 必须逐用例绑定已登记 interaction ID 与非空断言。JSON 中 `NaN`、正负无穷及任何非有限阈值/指标均为无效输入。

ruleId: QG-019

结构映射采用精确全集校验：需求、区域、组件、DOM 节点和实施目标不得缺失、重复或多出。合法 `[absence:components]` 时对应集合必须为空，并由绑定已解决缺口的 absence 断言证明。

ruleId: QG-020

合法 `[absence:interactions]` 页面可没有交互用例，但 runner 必须提供绑定已解决缺口的 absence-check 与“没有交互 ID/用例”的通过断言；没有该证据时空用例仍然失败。

sectionId: elastic-layout-acceptance

## 弹性布局验收

ruleId: QG-021

宽屏 profile 必须验证固定 Shell 保持合同尺寸、主工作区利用可用宽度、卡片与列按合同权重分配剩余空间，且不通过放大字体、图标或整体缩放填充。若设计明确存在居中上限，验收该 `max-width` 和两侧留白；否则大面积单侧死空白不得通过。

ruleId: QG-022

窄屏与缩放 profile 必须验证有效 CSS 视口、最小组件尺寸、换行/重排条件及页面/区域/混合滚动所有权。不得以根节点 `transform: scale()`、额外 zoom 或修改 token 尺寸制造“适配”；任何横向裁切、重叠、固定区域漂移或无法触达内容均失败。

sectionId: desktop-web-acceptance

## 桌面端 Web 验收

ruleId: QG-023

桌面端至少分别验收原始基线、宽屏、窄桌面窗口和浏览器缩放 profile。检查固定 Shell、主工作区占用、有界内容上限、组件最小尺寸和滚动所有者；移动端单列不能代替窄桌面验收，也不能用宽屏截图证明缩放场景。

ruleId: QG-024

滚动验收必须验证一个主要纵向滚动链，以及每个专用滚动面的必要性、轴向、边界、滚轮转交和全部内容可达性。无功能依据的嵌套纵向滚动、滚轮被困、Sticky 边界漂移、固定区覆盖内容或宽屏无限拉伸均失败。

sectionId: micro-visual-acceptance

## 微视觉与集成验收

ruleId: QG-025

每个 `MV###` 都要在原始基线 profile 下进行 reference/current/overlay/diff 比对，验证几何、描边、颜色、透明度、裁切和层级容差。仅整页像素比对不能替代曲线控制点、圆环/圆柱比例、Logo 留白和图标描边等特征级检查。

ruleId: QG-026

每页验收还要证明其在统一应用和共享端口中可由路由/导航到达、复用正确 Shell/Token/组件且不会破坏已通过页面。单页截图通过但集成导航失败时，该页不能标记 accepted。
