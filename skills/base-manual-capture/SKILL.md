---
name: base-manual-capture
description: Domain-neutral capture base for operation manuals. Use when the user wants an AI agent to autonomously operate an accessible system (Web now, Client later), take step-by-step screenshots with interactive user confirmation, and produce a screenshot ledger and operation trace that a manual-writing skill (e.g. pg-manual-builder) turns into a handbook. Use when 采集系统截图、生成操作手册配图、逐步走查系统流程、刷新旧手册截图.
---

# Base Manual Capture

把"打开系统、逐步操作、逐步截图、逐步确认"沉淀为域中立、工具中立的采集基座。本 Skill 只负责**采集**——产出截图与结构化操作记录；手册正文由 `pg-manual-builder` 一类写作层技能编写。

## 何时使用

- 需要为一个可访问系统（有地址+测试账号）生成带截图的操作手册
- 需要按功能描述逐步走查系统并与用户确认业务流程/概念是否符合预期（B 阶段）
- 需要刷新旧手册的截图（系统版本变化后重采）
- 需要把已确认的操作路径固化为可回放脚本（C 化）

本 Skill **不负责**：写手册正文、判断业务规则是否正确（由用户在 B 阶段确认）、桌面端采集（当前仅 Web 通道）。

## 前置输入

1. 系统访问地址
2. 测试账号（口令仅用于登录，**不落台账/记录**，见脱敏规则）
3. 功能描述（口述或简要均可）——要采哪条/哪几条流程
4. 手册目标读者（影响截图取舍与注意事项详略）
5. 输出目录：`project_root` / `manual_root`（与 `pg-manual-builder` 约定一致；截图落 `manual_root/captures/<flow>/`）

若功能描述模糊，先请用户给一句话流程目标（如"用户登录后创建工单并提交审核"），再开采。

## 工具解析优先级

按以下顺序选用任一可用的浏览器自动化工具，任一可用即可执行：

1. **Playwright MCP**（首选，可精确 selector + 稳定截图）
2. **browser-use MCP**（会话式操作，Qoder 等自带）
3. **本地 playwright CLI**（`.agents/tools/ms-playwright` 或 `playwright` 命令）

开采前先做一次探活：能打开目标地址并成功登录即视为通道可用；都不可用则停止并提示用户配置。

## 采集通道

- `capture_channel: web`（当前唯一实现）
- Client/桌面端为**预留扩展位**，本版不实现；未来新增通道时复用同一套台账/记录契约

## B 阶段主流程（核心）

### SOP-B0 采集范围确认（人工确认点，必做）

开采前先锁定“手册要覆盖哪些功能”，避免漏采：

1. 登录系统后先做一次**功能盘点**：遍历导航菜单/功能入口，列出发现的功能模块与子页面清单（含数量，如“综合查询含 5 类 20+ 子表单”）
2. 把清单交给用户**勾选确认**：哪些进手册（逐页详采）、哪些只截代表页、哪些不覆盖；未经确认不得自行裁定覆盖范围
3. 确认结果落为 **flow 清单**（写入 capture-trace 或独立 `flows.md`）：每个 flow 一行，标注 待采/已采/跳过
4. B 阶段退出条件同步收紧：**flow 清单全部处理完毕**（而非单条流程走完）才算采集完成，交给写作层前再向用户报一次覆盖对账（已采 N/应采 M）

### SOP-B1 环境确认

1. 用选定工具打开地址并登录，确认进入目标系统首页
2. 固定视口 `1920×1080`（保证截图尺寸一致，详见截图规范）
3. 显式确认 `project_root` / `manual_root`，建立 `manual_root/captures/<flow>/` 目录
4. 初始化空的 `capture-ledger.md` 与 `capture-trace.yaml`（字段见契约）

### SOP-B2 逐步采集循环（每步都做全）

对流程的每一步：

1. 执行一个操作（点击/输入/选择/提交等）——**一步只做一个动作**
2. `take_screenshot` 落盘到 `captures/<flow>/<step_id>-<页面名>.png`
3. 记录四要素：入口（菜单路径/按钮位置）、动作、预期结果、注意事项
4. **向用户播报本步理解并请求确认/纠偏**：用一两句话复述"我在做什么、看到什么"，等待用户确认或纠正后再进入下一步
5. 把该步写入 `capture-ledger`（含用户确认状态）与 `capture-trace`（含 selector/action 供 C 化）

### SOP-B3 分支与异常路径

正常路径走完后，按用户指点补采异常分支（权限不足、校验失败、数据为空、提交失败等），同样逐步截图+确认。异常步在台账中标注所属分支。

### SOP-B4 阶段产物落盘

一条流程采完，确保产出齐全：

- 截图文件（`captures/<flow>/`）
- `capture-ledger.md`（截图台账，四要素+确认状态已填）
- `capture-trace.yaml`（操作路径记录，供 C 化）
- 草稿手册骨架（可选）：按 flow 生成"章节+步骤占位"的 md，方便用户即时审查

### SOP-B5 B 阶段退出门禁

当用户确认 **SOP-B0 flow 清单全部处理完毕**且每条 flow 的全部步骤（含异常分支）都正确时，在 `capture-trace` 中把该 flow 标记为 `status: C-ready`。只有 C-ready 的流程才允许进入 C 化。

## C 化章节（本版只定规则，不实现 CLI）

- C-ready 的 flow 可固化为 Playwright 回放脚本，存 `manual_root/replay/<flow>.py`（或团队约定的脚本形态）
- 回放脚本严格依据 `capture-trace` 的 selector/action/wait 顺序生成，凭据用占位符从环境注入
- 系统版本更新时：回放脚本重跑 → 生成新截图 → 与旧截图做 **diff 对照清单**（哪些步骤截图变化）→ 只更新变化步骤的手册配图与文字
- 回放脚本的正式实现（CLI 化）不在本版范围；本版负责保证 `capture-trace` 字段足以支撑后续生成

## 与写作层的交接

- 采集完成后，把 `capture-ledger.md` 交给 `pg-manual-builder`：台账即其截图清单，四要素已预填，写作层按图文绑定规则直接回填正文
- `capture-trace.yaml` 不进手册正文，仅供 C 化
- 若沉淀出通用规则（新的截图约定、脱敏项、易缺步骤），先更新本 harness-ai-kit Skill，再同步项目副本

## 推荐输出格式

执行完毕后按以下结构输出：

**状态**：✅ 成功 / ⚠️ 部分成功 / ❌ 失败

| 产出物 | 位置/格式 | 说明 |
|-------|----------|------|
| 截图文件 | `manual_root/captures/<flow>/` .png | 步骤号+页面名命名 |
| 截图台账 | `<path>/capture-ledger.md` | 四要素+用户确认状态 |
| 操作路径记录 | `<path>/capture-trace.yaml` | 供 C 化，凭据脱敏 |
| 草稿手册骨架 | `<path>` .md（可选） | 章节+步骤占位 |

**采集通道**：web
**流程状态**：<in-progress / C-ready>
**下一步**：<交 pg-manual-builder 成稿 / 补采异常分支 / C 化回放>

## 参考文件

- 契约字段定义：`references/REFERENCE-CAPTURE-CONTRACT.md`
- 截图与命名规范：`references/REFERENCE-SCREENSHOT-SPEC.md`
- 脱敏规则：`references/REFERENCE-REDACTION-RULES.md`

参考文档：
- references/REFERENCE-CAPTURE-PITFALLS.md
