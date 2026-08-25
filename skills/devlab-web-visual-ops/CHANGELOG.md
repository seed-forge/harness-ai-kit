# 变更记录

## 0.1.6 - 2026-08-25

- Public OSS metadata uses the `public` namespace and `seedforge` owner, and source resolution now uses public-registry instead of the retired private registry label.

## 0.1.5 - 2026-08-20
- 改名对齐/内容同步：harness-ai-kit → harness-ai-kit 全仓改名后未发版补发（HEAD 内容与 Nexus 制品 hash 不一致）

## 0.1.4 - 2026-08-14

- frontmatter 规范化：SKILL.md 统一 LF / 无 BOM / 单一 YAML frontmatter 块，修复 AI IDE 加载告警（missing YAML frontmatter delimited by ---）。
## 0.1.3 - 2026-08-14

- **浏览器前置条件澄清（三选一）**：`npx playwright install chromium` 自动下载 / 复用 ms-playwright 缓存 / 系统 Chrome（`channel` 或 `executablePath`）。无头模式默认可用。
- **headless shell 适用范围实证**：Playwright 与 Vision/CUA 路径支持轻量 `chromium_headless_shell`（实测 vision-locate / cua-click / vision-review 全 PASS）；**Stagehand 必须完整 Chromium**（headless 模式即可，实测全 PASS；headless shell 缺 `Extensions.loadUnpacked`，实测失败）。
- **playwright CLI 前置说明**：项目侧 `npm i -D playwright` 或全局安装；仅缓存无 CLI 时仍可 `import { chromium } from "playwright"` 直用。

## 0.1.2 - 2026-08-14

- **Vision/CUA 执行器从占位升级为已实现**（本地视觉驱动，零专用 CUA 模型依赖）：截图 + newapi 多模态模型（`vision_model`，默认 mimo-v2.5-pro → claude-sonnet-4.5 后端） + forced tool call 结构化输出。
- spike 验证三项全 PASS：视觉元素定位（误差 <1px，与 DOM 交叉验证）、CUA 坐标点击闭环（看→决策→点击→导航验证，example.com → iana.org）、视觉审查（结构化 layout_issues 输出）。
- 坐标协议：像素 [x,y] / bbox [x1,y1,x2,y2]；CUA 动作 schema `{action: click|type|scroll|done, x, y, text, reason}`；导航等待用轮询而非固定 sleep。
- 决策新增 HD-5（CUA 自动执行边界：导航/点击自动，不可逆操作必问）；配置新增 `vision_model`。

## 0.1.1 - 2026-08-14

- **Stagehand 集成 spike 验证通过**：v4.0.0 + newapi + 本机 Chromium（localBrowser.launch，零 Browserbase 依赖），observe / act / extract 三项全 PASS（目标页 example.com，模型 mimo-v2.5-pro）。
- 版本 pin：`@browserbasehq/stagehand>=1.0.0` → `==4.0.0`（v4 于 2026-08-09 发布，主版本破坏性变更：无自主 agent、无 MCP client、统一 Locator 抽象；Node >= 22.18.0）。
- 能力表修正：删除 `agent`（v4 无 autonomous agent）。
- 本地模式接入方式：v4 无 base URL 选项，必须走 generate callback（ClientLLM）；**newapi 实测忽略 `response_format`（json_schema/json_object）**，结构化请求（observe/extract）采用 forced tool call（`extract_result`）强制 JSON，失败降级提示词模式。
- 配置新增：`newapi_base_url` / `newapi_api_key`(secret) / `stagehand_model`（引用 infra-aimodel-ops）。

## 0.1.0 - 2026-08-14

- 初始版本：Web 视觉化操作 Skill。
- 三层架构：Core（Observe/Navigate/Interact/Inspect/Validate/Capture）+ Router（Playwright/Stagehand/DevTools/Vision-CUA）+ Workflows（Debug/UI Review/Visual Regression/E2E/Browser Automation）。
- Stagehand 定位为 Router 的 AI Adapter（非底座），Skill 不绑定单一框架。
- 配置治理：config.defaults.yaml（preview_base_url / preview_start_command / playwright_project_dir / stagehand_enabled / vision_fallback_enabled / artifact_dir）。
- 专题参考：REFERENCE-ROUTER-ADAPTERS.md、REFERENCE-WORKFLOWS.md。
