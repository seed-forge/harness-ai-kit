# DevLab Web Visual Ops — Usage

## When To Use
- Web 应用的视觉化操作：视觉走查、UI 审查、页面调试、控制台/网络排查、截图对比、视觉回归、浏览器自动化。
- 需要在"确定性执行（Playwright）+ AI 增强（Stagehand）+ 调试检查（DevTools）+ 视觉兜底（Vision/CUA）"之间按需选路时。

## Inputs
- 目标 URL 或预览地址（preview_base_url，可配置）。
- 任务意图（属于哪个 Workflow）与可选的页面/路由清单、基线、用例规格。

## Output
- 标准化报告（SKILL.md 输出模板）+ 产物（截图/trace/har/diff/用例）。
- Router 使用记录与降级原因。

## Prerequisites
- Node ≥ 18 + `npx playwright install chromium`。
- 项目侧配置 `assets.devlab-web-visual-ops`（preview_base_url / preview_start_command / stagehand_enabled 等），详见 config.defaults.yaml。
- Stagehand 本地模式（可选）：Node ≥ 22.18.0 + `newapi_base_url` / `newapi_api_key`(secret) / `stagehand_model` 配置；零 Browserbase 依赖（localBrowser + generate callback，spike 2026-08-14 验证）。
- Vision/CUA 视觉兜底（可选）：`vision_model`（默认 mimo-v2.5-pro）复用同一 newapi 消费配置；截图 + 视觉模型 + forced tool call 实现元素定位/坐标点击/视觉审查（spike 2026-08-14 验证，误差 <1px）。

## 可直接复制的中文 Prompt

### 场景 1：直接调用技能
```text
请使用 `devlab-web-visual-ops` 技能处理我的任务。
输入材料：<在这里补充 URL、页面清单、基线、问题描述或项目背景>。
目标：<在这里补充你要完成的视觉操作/排查/回归/自动化结果>。
要求：先判定属于哪个 Workflow（Debug / UI Review / Visual Regression / E2E / Browser Automation）并按 Router 规则选执行器；缺失关键输入先列出缺口；执行时遵循 SKILL.md 的约束（写操作与基线更新需确认）；输出最终报告、关键证据产物路径、还需要我补充的内容。
```

### 场景 2：页面调试（Debug）
```text
使用 `devlab-web-visual-ops` 排查这个页面的问题：<URL 或复现步骤>。
现象：<报错/白屏/请求失败/交互异常>。期望：<正常行为>。
请先抓 Console 与 Network 证据，录制 trace 复现，输出根因结论、可复现步骤与修复建议。
```

### 场景 3：视觉回归
```text
使用 `devlab-web-visual-ops` 对 <变更范围> 做视觉回归。
基线位于 .visual-ops/artifacts/baselines/（如无则先建立基线）。
请对比当前页面与基线，输出 diff 报告；如需更新基线，先向我确认（HD-3）。
```
