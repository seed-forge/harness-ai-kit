---
name: devlab-web-visual-ops
description: "Web 视觉化操作（Web Visual Operations）：对 Web 应用做 Observe/Navigate/Interact/Inspect/Validate/Capture 的 day-2 操作手册。Router 层统一编排 Playwright（确定性）、Stagehand（AI 增强）、DevTools（Console/Network/Runtime）、Vision/CUA（视觉兜底）四类执行器，覆盖 Debug / UI Review / Visual Regression / E2E / Browser Automation 五类 Workflow。Stagehand 定位为 Router 的 AI Adapter 而非底座，Skill 不绑定单一框架。触发词：视觉走查、UI 审查、页面调试、控制台报错、网络请求排查、截图对比、视觉回归、浏览器自动化、visual ops、stagehand、playwright"
---

# DevLab Web Visual Ops — Web 视觉化操作

## Purpose

对 **Web 应用**做可重复的视觉化操作：观察页面、导航、交互、检查（Console/Network/Runtime）、验证、截图捕获，并沉淀为 Debug / UI Review / Visual Regression / E2E / Browser Automation 五类 Workflow 的标准化产物。

**定位边界（与 Stagehand 的关系）**：Stagehand 本质是 AI Browser Automation；本技能是范围更大的 Web Visual Operations。因此 **Stagehand 是 Router 层的 AI Adapter 之一，不是 Skill 底座**。Console/Network/Trace/截图/视觉回归/UI Review 是 Skill 自己的核心能力，不抽象成"Stagehand 能力"，避免被具体框架绑死。

## 适用条件

- 目标是有浏览器 UI 的 Web 应用（SPA / 微前端 / MPA 均可）；
- 需要浏览器端到端执行的操作：视觉走查、UI 审查、页面调试、截图对比、视觉回归、浏览器自动化；
- 执行环境可运行 Node ≥ 18 + Playwright。**浏览器获取方式可选（三选一）**：① `npx playwright install chromium` 自动下载到 ms-playwright 缓存；② 复用已有 ms-playwright 缓存；③ 系统 Chrome/Edge（`executablePath` 或 `channel`）。**无头模式默认可用**：Playwright 与 Vision/CUA 路径还可用更轻的 `chromium_headless_shell`（实测三项全 PASS）。
- Stagehand AI 增强路径需 Node ≥ 22.18.0 + newapi 消费 key（`chat_default` 模型，见 infra-aimodel-ops）；**必须完整 Chromium（headless 模式即可，实测全 PASS），headless shell 不支持扩展注入（实测失败）**；
- 无 DOM 或 DOM 不可靠的场景（canvas / 复杂 iframe / 纯视觉渲染）走 Vision/CUA 兜底。

## 核心设计：三层架构

```
devlab-web-visual-ops
│
├── Core      能力原语（Observe / Navigate / Interact / Inspect / Validate / Capture）
├── Router    执行路由（Playwright / Stagehand / DevTools / Vision-CUA）
└── Workflows 业务闭环（Debug / UI Review / Visual Regression / E2E / Browser Automation）
```

1. **Core 定义"做什么"**，与具体执行器解耦；所有 Workflow 只调用 Core 原语。
2. **Router 决定"用谁执行"**：默认确定性执行（Playwright）；AI 增强/非确定性页面切 Stagehand；Console/Network/Runtime 检查走 DevTools；无 DOM 走 Vision/CUA。统一输入 `task + page`，统一输出 `action / observation / extraction` 协议，保证执行器可替换。
3. **Workflows 组装"业务闭环"**：每个 Workflow 是 Core 原语 + Router 选路的固定编排，输出标准化产物。

## 资产结构

```
.visual-ops/
├── artifacts/          # 产物：screenshots/ traces/ hars/ 报告/ 视频
│   ├── baselines/      # 视觉回归基线（更新需用户确认 HD-3）
│   └── reports/        # Debug / UI Review / Regression 报告
├── cases/              # E2E / 自动化用例（复用 devlab-web-test-e2e 约定）
└── config.local.*      # 项目侧本地覆盖（不入库）
```

## 工作流

### 0. 入口：意图解析与 Router 判定

1. 读取 `~/.harness-ai-kit/config.yaml` 的 `assets.devlab-web-visual-ops` 段（preview_base_url / preview_start_command / stagehand_enabled 等）；缺失时按项目探测。
2. 按用户意图归类到 Workflow（Debug / UI Review / Visual Regression / E2E / Browser Automation）；意图不明确时询问用户。
3. 按下表选择 Router 执行器；执行器不可用时按降级路径切换并记录原因。

### Router 选择规则

| 场景 | 首选执行器 | 降级路径 |
|------|-----------|---------|
| 有稳定 selector 的确定性操作 | Playwright | Stagehand（selector 失效需语义定位） |
| 自然语言指令 / 非确定性页面 | Stagehand（前置：newapi 消费 key + chat_default 模型，Node ≥ 22.18.0；缺失时视作不可用） | Playwright + 显式选择器，或 Vision/CUA |
| Console / Network / Runtime 检查 | DevTools（CDP） | 无 CDP 时降级为截图 + 静态分析 |
| 无 DOM / canvas / 复杂 iframe | Vision/CUA（前置：newapi 多模态模型 `vision_model`；缺失时仅出截图） | 截图 + 视觉模型分析，标注置信度 |
| 截图 / 录制 / trace | Capture（任意执行器） | — |

> 切换执行器时在报告中记录 `router: 切换原因`。详细适配器操作见 `references/REFERENCE-ROUTER-ADAPTERS.md`。

### Core 能力原语

| 原语 | 职责 | 典型输出 |
|------|------|---------|
| Observe | 页面状态观察：DOM 快照、可见性、样式、a11y 树 | 状态快照 JSON |
| Navigate | 导航：URL、前进/后退、hash、多标签页、iframe 上下文 | 导航记录 |
| Interact | 交互：点击/输入/滚动/拖拽/表单/上传 | 操作回放日志 |
| Inspect | 检查：Console 错误、Network 请求、Runtime 状态、元素属性 | 检查报告 |
| Validate | 验证：断言、视觉对比、a11y、响应式断点 | 验证结果（PASS/FAIL） |
| Capture | 捕获：截图、trace、har、视频、DOM 快照 | 产物文件集 |

### Workflows

| Workflow | 输入 | 关键步骤 | 产物 |
|----------|------|---------|------|
| Debug | 问题描述 / URL | Inspect(Console/Network) → 复现路径 Capture → 根因定位 → 修复建议 | Debug 报告 + trace/har |
| UI Review | 页面/路由清单 | Capture 截图 → 设计规范对照 → 问题分级清单 | UI Review 报告 + 截图集 |
| Visual Regression | 基线 + 变更描述 | Capture 基线/当前 → 像素/结构对比 → diff 标注 | 回归报告 + diff 图 |
| E2E | 用例规格 | 用例生成（衔接 devlab-web-test-e2e）→ Interact 执行 → Validate | 用例 + 执行报告 |
| Browser Automation | 重复操作描述 | 脚本化编排 Core 原语 → 定时/触发执行 | 自动化脚本 + 运行日志 |

> 各 Workflow 详细步骤与判定规则见 `references/REFERENCE-WORKFLOWS.md`。

## Integration Points

| 目标资产 | 类型 | 方向 | 契约（输入→输出） |
|---------|------|------|-----------------|
| devlab-web-test-e2e | skill | outbound | E2E 用例生成/失败修复闭环；本技能提供执行层 |
| devlab-web-deep-acceptance | skill | outbound | 深度验收浏览器执行层；registry 用例由 Observe/Interact 驱动 |
| devlab-ui-taste-ops | skill | outbound | 视觉走查截图/问题清单 → UI 精修定调与修复 |
| harness-ai-kit-maintainer | skill | outbound | 发布/废弃/同步、bump 版本、lock 刷新 |

## 约束

- **不绑定单一框架**：Stagehand 只作为 Router 的 AI Adapter；新增/替换执行器不改 Skill 骨架，只改 Router 插槽与 REFERENCE-ROUTER-ADAPTERS.md。
- **Stagehand 依赖 pin `==4.0.0`**（v4 破坏性变更：无 agent、无 MCP client；Node ≥ 22.18.0）；本地模式走 `localBrowser.launch` + generate callback，无需 Browserbase key；newapi 结构化请求用 forced tool call（HD-4）。
- **Vision/CUA 已实现（v0.1.2）**：本地视觉驱动（截图 + newapi 多模态模型 + forced tool call），无需专用 CUA 模型；CUA 执行闭环中**导航/点击类自动执行，不可逆操作（表单提交/删除/数据修改）必须 HD-1 确认**（HD-5）。
- **写操作默认拦截**：表单提交、删除、修改数据等不可逆操作前必须 `🔔 HUMAN-DECISION [HD-1]`。
- **基线更新必须确认**：视觉回归基线覆盖前必须 `🔔 HUMAN-DECISION [HD-3]`。
- 依赖版本 pinned；外部公开依赖统一写入 `skill.json` 的 `environment` / `runtime_requirements`，不在正文硬编码版本。
- 产物默认落 `.visual-ops/`；缓存、临时文件、凭据不入库、不入正式文档。
- Router 切换需记录原因，禁止静默降级。

## 专题引用

- `references/REFERENCE-ROUTER-ADAPTERS.md` — Router 四类执行器的启用条件、典型命令/API、降级路径。
- `references/REFERENCE-WORKFLOWS.md` — 五类 Workflow 的步骤序列、判定规则与产物规范。
- `references/REFERENCE-INDEX.md` — 专题文档导航。

## 输出模板

```
DevLab Web Visual Ops 报告
════════════════════════════════════════
Target: {preview_base_url | URL}
Router: {playwright | stagehand | devtools | vision}
Workflow: {debug | ui-review | visual-regression | e2e | automation}
Time:   {timestamp}

[执行摘要]
  操作数: {n}
  验证结果: {PASS | FAIL | BLOCKED}

[发现]
  - {severity}: {finding} (证据: {artifact 路径})

[产物]
  - {artifact 类型}: {路径}

结论: {conclusion}

建议:
  1. {recommendation_1}
  2. {recommendation_2}
```

## 示例

**场景**：前端项目反馈"列表页偶发白屏，控制台有报错，但本地复现不稳定"。
调用本技能 Debug Workflow：
1. Router 判定：Console/Network 检查 → DevTools；复现交互 → Playwright。
2. Inspect：抓 Console 错误与 Network 失败请求，定位疑似未捕获的 API 异常。
3. Capture：录制 trace + 截图，标记失败时间点。
4. 输出 Debug 报告：根因、复现步骤、修复建议、trace 产物。
**合格输出**：报告包含根因结论、可复现路径、证据产物路径。

## Human Decisions

| # | 决策点 | 触发条件 | 选项 | 默认行为 |
|---|--------|---------|------|---------|
| HD-1 | 写操作放行 | 表单提交/删除/修改数据等不可逆操作前 | 放行 / 仅截图 / 取消 | 必问 |
| HD-2 | Router 降级切换 | Playwright 确定性路径失败需 AI 推断（切 Stagehand/Vision） | 允许 / 停止并报告 | 默认允许，记录原因 |
| HD-3 | 视觉基线更新 | 覆盖 baselines/ 中已有基线 | 更新 / 保留旧基线 | 必问 |
| HD-4 | Stagehand 结构化输出模式 | Stagehand observe/extract 需要结构化 JSON 时 | forced tool call（默认）/ response_format json_schema / 提示词降级 | forced tool call（newapi 忽略 response_format，spike 已验证） |
| HD-5 | CUA 自动执行边界 | Vision/CUA 执行器准备在页面上执行动作时 | 导航/点击类自动执行 / 不可逆操作必须 HD-1 确认 | 导航/点击自动；不可逆操作必问（spike 2026-08-14 验证坐标闭环） |
