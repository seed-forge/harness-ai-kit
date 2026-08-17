---
name: devlab-web-extension-bootstrap
description: Use when building a browser/web extension from scratch, especially one that extracts, downloads, or enhances data from an existing web app. Covers feasibility, reverse-engineering the target site's data channels, tech-stack selection (WXT + framework + Manifest V3), content/background/popup architecture, and a real-browser e2e testing strategy. Hand off open-source packaging and release to devlab-github-oss-ops.
---

# DevLab Web Extension Bootstrap

## 用途

从零构建一个浏览器扩展（WebExtension / Manifest V3）的团队标准工作流，尤其适用于"**从某个已有 Web 应用里提取、下载或增强内容**"这类扩展。

核心原则：**这类扩展的成败取决于检测层（detection layer），而不是 UI。** 按钮谁都会写；难的是在多种页面形态（应用页 / SSR 分享页 / 未登录页）和登录态下都能稳定定位到目标资产。所以**先逆向、验证能拿到资产，再写 UI**。

把扩展当作有生命周期的产品来做：可行性 → 逆向工程 → 技术选型 → 架构 → 测试。代码验证通过后，开源与发布交给 `devlab-github-oss-ops`。

## 适用场景

- 新建浏览器扩展（Chrome/Edge/Firefox，MV3）
- 需要从特定 Web 应用读取 / 下载 / 增强内容的扩展
- 必须兼容多种页面类型（应用页、SSR 分享页、登出态）的扩展
- 把"网站能加载但不给我保存"变成一个可用工具

**不适用**：
- 纯 Web 应用或无需打包的 userscript
- 一次性的 DevTools console 片段
- 开源打包 / GitHub 发布阶段（用 `devlab-github-oss-ops`）

## 输入

| 输入项 | 是否必须 | 来源 |
|--------|----------|------|
| 目标 Web 应用 URL + 要提取的内容 | 是 | 用户描述 |
| 需覆盖的页面类型清单 | 是 | 逆向阶段枚举（应用页/分享页/登出页） |
| 目标浏览器 | 交互确认 | 默认 Chrome MV3 |

## 输出

- 一个可加载的 MV3 扩展（content script + background + popup）
- 一个纯函数、可注入、可单测的检测层
- 单元测试 + 真实浏览器 e2e 闭环
- 交接给 `devlab-github-oss-ops` 的就绪代码

## 工作流

调用本技能时的标准顺序：

1. 判定是否真的需要扩展（§1）
2. 逆向目标站点的数据通道（§2）—— 成败关键
3. 选型并脚手架（§3）
4. 搭建三面架构（§4）
5. 单测 + 真实浏览器 e2e 证明（§5）
6. 过验收门禁，交接 `devlab-github-oss-ops` 做开源与发布

配合 `brainstorming`（§1 前，新点子）、`writing-plans`（§4 前，多步实现）、`test-driven-development`（§5）、`verification-before-completion`（宣称就绪前）。

### §1 可行性与范围

动手前确认：

- 你要的内容在你浏览查看时**已经**被加载进浏览器（扩展只能保存页面在你会话下已能访问的内容）
- 你提取的是**你自己的**内容、走平台**自己的**端点（不破解/绕过付费墙——这既是合规红线也是维护陷阱）
- 目标有可识别的数据通道（见 §2），而非纯 canvas/WebGL 不可解析渲染
- **提前枚举必须支持的页面类型**：应用/编辑器页、公开分享页、登出页。每种暴露数据的方式可能不同。

产出：一句话问题陈述 + 需覆盖的页面类型清单。

### §2 逆向目标站点（关键阶段）

目标：找出页面暴露资产 URL / 标识符的**所有**途径，然后实现一个**按可靠性排序、逐级兜底的多通道检测器**。

按优先级排查（`🔒 HUMAN-DECISION [HD-1]` 通道优先级由实证确定）：

1. **SSR 注入的初始状态** —— 现代 React/Next.js 应用把初始数据内嵌在 HTML 里。找 `self.__next_f.push(...)`、`__NEXT_DATA__`、`window.__INITIAL_STATE__` 或内联 `<script>` JSON。这是最丰富最稳定的来源，且在分享页登出态也有效。
2. **同源 API / 代理** —— 前端常调自己的 `/api/...`（有时是 `/api/proxy?url=<backend>` 模式）。用 `credentials: 'include'` 复用，自动携带用户会话。
3. **由路径标识符构造 URL** —— 若分享 URL 如 `/e/<hash>` 能确定性映射到公开资产端点，则无需任何页面数据即可构造下载 URL。
4. **被动资源观察** —— `performance.getEntriesByType('resource')`（或 `PerformanceObserver`）暴露页面已加载的资产 URL。作为最后兜底。

检测层设计规则（均经生产验证）：

- 按可靠性排序，`detect()` 命中第一个可用资产即返回
- 检测器做成**纯函数、可注入**（传入 `{ pathname, scripts, entries, fetcher }`），无需浏览器即可单测——这是 §5 快的前提
- content script 运行在**隔离世界（isolated world）**：读不到页面 JS 全局（如 `window.__next_f`），但**能**读 DOM 里 `<script>` 文本并解析。从大字符串里抠 JSON 对象时用**括号匹配**而非脆弱正则。
- 放宽框架变体匹配（如匹配 `push([<任意数字>, ...])`，别写死 chunk 索引）
- **导出时始终重新查询最新资产**——资产 URL 可能带时效签名会过期
- 验证登出页产出**零**匹配（不误注入按钮）

尽早用浏览器在真实站点探测：把候选检测逻辑内联到页面 console / 或用自动化 subagent 跑，确认能解析真实数据，并记录字节级证据（JPEG 魔数 `FF D8 FF`、`SOF0` 取尺寸、`FF D9` EOI 判完整）。检测层骨架见 `references/REFERENCE-DETECTION-AND-E2E.md`。

### §3 技术选型

团队默认栈（经验证、快、MV3 原生）：

- **WXT**（`wxt.dev`）—— 扩展框架：HMR 开发、MV3 构建、`zip`/`submit` target、多浏览器开箱即用
- **Vue 3 + TypeScript** 做 popup（或团队当前框架）经 `@wxt-dev/module-vue`
- **Manifest V3** —— 声明最窄 `permissions`（如 `downloads`）与具体 `host_permissions`；除非确需，绝不用 `<all_urls>`
- **vitest** 单测，**puppeteer-core** + Chrome for Testing 做 e2e

用 WXT Vue 模板脚手架。保持 `entrypoints/`（content/background/popup）、`utils/`（纯逻辑 + 测试）、`e2e/` 结构。

### §4 架构 —— 三个面

严格分离职责：

- **content script**（`entrypoints/content.ts`）：跑在页面里，做检测（§2）、注入 UI（浮动按钮/FAB）、把选中的资产发给 background。隔离世界——仅同源 `fetch`。
- **background service worker**（`entrypoints/background.ts`）：拥有 `chrome.downloads`、跨域 fetch、以及 content script 源做不了的事。经 `browser.runtime` 消息通信。
- **popup**（`entrypoints/popup/`）：小 Vue 应用，展示当前检测项（缩略图/标题/状态）并提供相同操作。挂载时查询当前活动标签页。

已验证有效的模式：

- 在一个带类型的资产模型接口里集中定义（所有面共享）
- 下载走 background 的 `chrome.downloads.download`，文件名用内容标题清洗（替换 `\ / : * ? " < > |`）
- 防止轮询循环覆盖用户可见的反馈文本
- 任何本地处理（裁剪、格式转换）在浏览器上下文用 `createImageBitmap` + canvas；变换做成纯函数、可单测

### §5 测试策略

三层，对应已验证的交付：

1. **单元测试（vitest）** 覆盖纯检测 + 处理逻辑。因为检测器可注入，喂合成的 `scripts`/`entries`/`pathname`，断言通道优先级、去重、错误路径、文件名清洗、裁剪矩形。快、确定、覆盖大头。
2. **e2e 闭环**：**mock 站点 + 真实 Chrome**。起一个极小本地 HTTP 服务复现每种页面类型（调代理 API 的应用页、带注入 payload 的 SSR 分享页、资产字节）。用 **Chrome for Testing** 加载真实构建的扩展，puppeteer-core 驱动，断言下载与所供文件**字节级一致**。覆盖主页 + popup + 分享页。
3. **真实站点探测**：把检测器内联到真实站点跑（登出态、可能的话登录态），确认真实数据可解析、全量资产按最高分辨率下载。

关键 e2e 陷阱（已实测踩过）：

- **Chrome 137+ 品牌版移除了 `--load-extension`**。扩展 e2e 用 **Chrome for Testing**（经 `@puppeteer/browsers` / Playwright 的 chromium），别用系统 Chrome。
- e2e 需要显示器：headless Linux 上用 `xvfb-run -a`。
- MV3 用 background **service worker** 而非 page —— 等 SW target，别等 background page。

mock 站点 + CfT harness 骨架见 `references/REFERENCE-DETECTION-AND-E2E.md`。

## Integration Points

| 目标资产 | 类型 | 方向 | 契约（输入→输出） |
|---------|------|------|-----------------|
| devlab-github-oss-ops | skill | outbound | 验证就绪的扩展代码 → 开源打包 + GitHub 发布自动化 |
| harness-ai-kit-maintainer | skill | outbound | 发布/废弃/同步、bump 版本、lock 刷新 |

## 约束

- 检测先于装饰：先证明能定位资产，再建按钮。
- 合规姿态从第一天守住：只处理用户自有内容、只走官方端点、不绕付费墙。
- 声明最窄权限；不请求 `<all_urls>` 除非确需。
- 外部公开依赖（wxt/vue/vitest/puppeteer-core）统一写进 `skill.json` 的 `environment`。
- 不写死个人路径 / 账号 / 具体站点内幕；本技能是方法论，站点特定细节留给具体项目。

## 专题引用

- [`references/REFERENCE-DETECTION-AND-E2E.md`](references/REFERENCE-DETECTION-AND-E2E.md)：多通道检测器骨架、`wxt.config` 基线、mock 站点 + Chrome-for-Testing e2e harness、合规检查清单。

## 示例

用户说："帮我做个 Chrome 扩展，把我在 X 站生成的图导出原图，免费账号没有下载按钮。"

合格执行：① 确认内容已在浏览器加载、走官方端点（§1）；② 逆向发现 X 站分享页用 SSR `initialData`、应用页用 `/api/proxy`，实现四通道检测器并单测（§2）；③ WXT+Vue+MV3 脚手架、最窄权限（§3）；④ content 检测注入、background 下载、popup 卡片（§4）；⑤ 31 单测 + mock 站点 + Chrome-for-Testing e2e 字节级一致 + 真实站点探测（§5）；⑥ 过门禁，交 `devlab-github-oss-ops`。

## Human Decisions

| # | 决策点 | 触发条件 | 选项 | 默认行为 |
|---|--------|---------|------|---------|
| HD-1 | 检测通道优先级 | §2 发现多个可用数据通道时 | 按实证可靠性排序 / 用户指定优先通道 | 必问（影响稳定性） |
| HD-2 | 目标浏览器与框架 | §3 选型 | Chrome MV3 + Vue（默认）/ 其他浏览器 / 其他框架 | 默认 Chrome+Vue，可改 |
