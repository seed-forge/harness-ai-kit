# REFERENCE-ROUTER-ADAPTERS.md — Router 适配器操作细则

> 与 `SKILL.md` 的 Router 选择规则配套。每个执行器：启用条件、典型命令/API、输出协议、降级路径。

## 统一协议

- 输入：`task`（自然语言或结构化指令）+ `page`（Playwright Page 或等价上下文）
- 输出：`action[]`（已执行操作）、`observation`（状态快照）、`extraction`（结构化抽取结果）
- 所有适配器必须支持 Core 六原语：Observe / Navigate / Interact / Inspect / Validate / Capture（能力矩阵见下）。

## 1. Playwright（默认确定性执行器）

- **启用条件**：有稳定 selector；操作可确定性复现；无需语义推断。
- **环境**：Node ≥ 18；`@playwright/test` pinned；**浏览器三选一**：`npx playwright install chromium` 自动下载 / 复用 ms-playwright 缓存 / 系统 Chrome（`channel: "chrome"` 或 `executablePath`）。
- **无头模式**：`headless: true` 默认可用；更轻的 `chromium_headless_shell` 亦支持（Vision/CUA 路径实测三项全 PASS；体积约为完整 Chromium 1/3）。
- **playwright CLI**：项目侧 `npm i -D playwright` 或全局安装后可用（`npx playwright --version`）；仅浏览器缓存而无 CLI 时，Node 代码仍可直接 `import { chromium } from "playwright"`。
- **典型用法**：
  ```bash
  npx playwright test --project=chromium      # 测试执行
  npx playwright codegen <url>                # 录制选择器
  npx playwright show-trace trace.zip         # 回放 trace
  ```
- **输出协议**：DOM 快照（`page.content()` / aria snapshot）、操作回放日志、`locator` 定位。
- **降级路径**：selector 失效 → Stagehand 语义定位；无 DOM → Vision/CUA。

## 2. Stagehand（AI 增强执行器）

- **启用条件**：自然语言指令；页面非确定性（动态内容、无稳定 selector）；需要语义理解/抽取。
- **定位**：AI Browser Adapter，**不是底座**。与 Playwright Page 混用（官方支持）。
- **版本事实（v4.0.0，2026-08-09 发布）**：主版本破坏性变更；**无 autonomous agent、无 MCP client**；统一 Locator 抽象；engines 要求 Node >= 22.18.0。依赖必须 pin `==4.0.0`（`>=1.0.0` 无意义，v3→v4 API 已变）。
- **能力**：`act`（自然语言操作）、`observe`（可操作元素观察）、`extract`（结构化抽取）。~~`agent`~~（v4 已移除）。
- **本地模式（零 Browserbase 依赖，spike 已验证 2026-08-14）**：
  - 浏览器：`localBrowser.launch({ headless: true, executablePath })`，复用本机 Chromium（ms-playwright 缓存或系统 Chrome），无需 `BROWSERBASE_API_KEY`。
  - **浏览器要求：必须完整 Chromium**（headless 模式即可）；`chromium_headless_shell` 不支持扩展注入（实测 `'Extensions.loadUnpacked' wasn't found`，2026-08-14）。
  - LLM：v4 无 base URL 选项，自定义端点必须走 **generate callback**（ClientLLM）：`Stagehand.create({ browser, model: { generate } })`。
  - 回调契约：入参 `{ messages, systemPrompt?, temperature?, stopSequences?, responseFormat? }`；返回 `{ role: "assistant", content, outputFormat: "text" | "json_schema", structuredContent? }`（strict 校验，勿带多余字段）。
  - **newapi 结构化强制**：`response_format`（json_schema/json_object）对 mimo-v2.5-pro 渠道实测被忽略 → 结构化请求用 forced tool call（函数名 `extract_result`，`tool_choice` 强制），从 `tool_calls[0].function.arguments` 取 JSON；失败降级"提示词内嵌 schema + 手动解析"。工具调用消息双向转换：assistant `tool_use` ↔ OpenAI `tool_calls`；`tool_result` ↔ OpenAI `tool` role。
- **配置**：`assets.devlab-web-visual-ops` 段：`stagehand_enabled` / `newapi_base_url` / `newapi_api_key`（secret）/ `stagehand_model`。LLM 选型与 key 引用 **infra-aimodel-ops**（scenario `chat_default`，默认 `mimo-v2.5-pro`）。
- **输出协议**：操作意图 → 已执行操作 + 置信度；抽取结果按 schema 返回。
- **降级路径**：LLM 不可用 → Playwright 显式选择器 + 静态分析；仍失败 → Vision 兜底。

## 3. DevTools（Console / Network / Runtime）

- **启用条件**：需要检查 Console 错误、Network 请求链路、Runtime 状态、性能指标。
- **实现**：CDP 协议（Playwright 内置 `page.on('console'|'requestfailed'|'response')`，或独立 CDP 会话）。
- **典型采集**：
  - Console：`console` 事件 → 错误堆栈分级；
  - Network：`request` / `response` / `requestfailed` → 状态码、耗时、失败原因；
  - Runtime：`performance` 指标、`window` 状态、全局异常 `pageerror`。
- **输出协议**：结构化日志（severity/url/stack/timing）。
- **降级路径**：无 CDP 环境 → 截图 + 服务端日志交叉分析。

## 4. Vision / CUA（视觉兜底执行器）— **已实现（v0.1.2，spike 2026-08-14 验证）**

- **启用条件**：无 DOM 或 DOM 不可靠（canvas 渲染、复杂 iframe、图片型页面、深 Shadow DOM）；或需要纯视觉验证；或 Playwright/Stagehand 均不可用。
- **实现（本地视觉驱动，零专用 CUA 模型依赖）**：
  - 视觉模型：newapi 多模态（`vision_model`，默认 `mimo-v2.5-pro` → claude-sonnet-4.5 后端，图片理解实测通过；备选 `grok-chat-fast`）。选型与 key 引用 **infra-aimodel-ops**。
  - 浏览器：Playwright Chromium，**支持完整 Chromium 与轻量 `chromium_headless_shell`**（实测两项均全 PASS；headless shell 体积更小，适合 CI/无头环境）。
  - 输入：viewport 截图（PNG → `image_url` data URL）+ 任务提示。
  - 结构化输出：newapi 忽略 `response_format` → **必须 forced tool call（`vision_result`，机制同 HD-4）**；失败降级"提示词内嵌 schema + 手动解析"。
  - 坐标协议：像素 `[x,y]`（默认 1280x800 viewport；deviceScaleFactor=1 时与 CSS 像素/鼠标坐标一致），bbox `[x1,y1,x2,y2]`。
- **Vision 面（纯分析）**：
  - 元素定位：截图 → `{ elements: [{ label, center, bbox, reason }] }`（实测与 DOM 中心误差 <1px）。
  - 视觉审查：截图 → `{ layout_issues: [{ severity, issue, location }], overall }`（UI Review / Debug 复用）。
- **CUA 面（执行闭环）**：
  - 循环：截图 → 模型决策 `{ action: click|type|scroll|done, x, y, text, reason }` → Playwright 坐标执行（`page.mouse.click` / `keyboard.type` / `mouse.wheel`）→ 轮询验证（URL/DOM 变化，非固定 sleep）→ 重复至 `done` 或超时（默认 max_steps 5）。
  - 点击前可做 `elementFromPoint` 命中验证（日志留痕）；坐标点击命中精度实测 <2px。
  - **不可逆操作仍受 HD-1 约束**（表单提交/删除/数据修改必须人工确认），导航/点击类自动执行（HD-5）。
- **输出协议**：截图集 + 结构化分析/动作记录 + 置信度；与 DOM 结论冲突时标注"视觉推断"。
- **降级路径**：视觉模型不可用 → 仅产出截图供人工复核。

## 能力矩阵

| 适配器 | Observe | Navigate | Interact | Inspect | Validate | Capture |
|--------|---------|----------|----------|---------|----------|---------|
| Playwright | ✅ | ✅ | ✅ | ⚠️ 部分(CDP) | ✅ | ✅ |
| Stagehand | ✅ | ✅ | ✅ | ⚠️ 部分 | ✅ | ✅ |
| DevTools | ⚠️ | ❌ | ❌ | ✅ | ⚠️ | ⚠️ |
| Vision/CUA | ✅(视觉定位) | ⚠️(坐标点击) | ✅(坐标点击/输入/滚动) | ❌ | ✅(视觉审查) | ✅(截图) |

> ⚠️ = 需配合其他执行器。执行器新增/替换时：更新本矩阵 + SKILL.md Router 规则表 + Router 判定代码（如有）。
