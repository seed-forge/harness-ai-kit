# REFERENCE-WORKFLOWS.md — 五类 Workflow 步骤细则

> 与 `SKILL.md` 的 Workflows 表格配套。每个 Workflow：触发、步骤序列、判定规则、产物规范。

## 1. Debug（页面问题排查）

**触发**：控制台报错、白屏、请求失败、交互异常、性能劣化。
**步骤**：
1. 意图解析：收集问题描述、URL、复现条件、期望行为。
2. Inspect(DevTools)：抓 Console 错误（分级）、Network 失败请求、`pageerror`、性能指标。
3. 复现：Playwright 走一遍复现路径（无稳定复现时切 Stagehand 语义触发），录制 trace。
4. 根因定位：按"前端异常 → 请求失败 → 后端/数据"三分支收敛；HTTP 200 ≠ 业务成功（检查响应体）。
5. 产出 Debug 报告：根因结论 + 复现步骤 + 修复建议 + 证据（trace/har/截图）。
**判定**：修复建议必须可执行；证据必须可回放（trace 或截图 + 步骤日志）。
**产物**：`artifacts/reports/debug-{ts}/`（report.md + trace.zip + har + 截图）。

## 2. UI Review（视觉走查）

**触发**：设计还原检查、上线前走查、UI 回归、风格一致性审查。
**步骤**：
1. 输入页面/路由清单（来自路由源码或用户提供）。
2. Capture：逐页全页截图 + 关键区域截图（桌面/移动断点）。
3. 对照：设计规范（间距/色彩/字体/a11y）逐项核对；引用 `devlab-ui-taste-ops` 的规则库。
4. 分级输出问题清单（P0 阻断 / P1 明显 / P2 建议）。
5. 产出报告 + 截图集（before/after 后续由 devlab-ui-taste-ops 承接）。
**判定**：每个问题必须带截图证据与规范依据；P0 必须阻断发布。
**产物**：`artifacts/reports/ui-review-{ts}/`（report.md + shots/ + issue-list.md）。

## 3. Visual Regression（视觉回归）

**触发**：前端变更后需确认无视觉回归；样式/组件库升级。
**步骤**：
1. 基线管理：首次建立 `baselines/`（每页全页/关键区域截图 + 元数据 yaml）。
2. 对比：当前截图 vs 基线（像素 diff + 结构 diff），忽略动态区域（时间/数据）。
3. 判定：diff 阈值 → PASS / FAIL；FAIL 时输出 diff 标注图。
4. 基线更新：确认是无意回归还是有意变更 → `🔔 HUMAN-DECISION [HD-3]` 后才覆盖基线。
**判定**：动态区域必须 mask；失败必须有人工复核记录。
**产物**：`artifacts/reports/regression-{ts}/`（report.md + diff-*.png + mask-list.yaml）。

## 4. E2E（端到端）

**触发**：关键链路回归、发布前验证、用例沉淀。
**步骤**：
1. 用例规格 → 衔接 `devlab-web-test-e2e` 的用例生成约定（feature 文件/规格）。
2. Interact + Validate 执行；失败自动截图 + trace。
3. 结果回写用例状态；与 devlab-web-deep-acceptance 的 registry 对齐。
**判定**：失败必须区分"用例问题 / 环境问题 / 产品缺陷"。
**产物**：用例文件 + `artifacts/reports/e2e-{ts}/`。

## 5. Browser Automation（浏览器自动化）

**触发**：重复性浏览器操作（批量下载、报表导出、巡检、数据采集）。
**步骤**：
1. 描述重复操作 → 脚本化编排 Core 原语（Playwright 脚本为主）。
2. 参数化输入/输出；异常重试与超时策略。
3. 落盘运行日志；支持定时/触发（外部调度器）。
**判定**：脚本必须可重入（幂等）；不得硬编码凭据（走 config governance）。
**产物**：脚本 + 运行日志 + 导出产物。

## 通用收尾（所有 Workflow）

- 汇总 `router:` 使用记录与降级原因；
- 产物统一落 `artifacts/` 并给出相对路径；
- 报告按 `SKILL.md` 输出模板填写。
