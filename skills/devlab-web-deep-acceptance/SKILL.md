---
name: devlab-web-deep-acceptance
description: "存量 Web 系统深度功能验收方法论（L1-L4）。registry 功能点驱动 + 唯一入口执行器 + 假成功嗅探 + 三对齐审计，覆盖盘点建模、用例固化、失败五分类路由、多会话认领协作。与 devlab-web-test-e2e（绿field 用例生成）分工：本技能面向已有系统的全功能点深度验收与回归资产管理。实战陷阱全量清单见 references/REFERENCE-PITFALLS.md。触发词：深度测试、深度验收、功能验收、L1-L4、registry、三对齐、假成功、deep acceptance"
---

# devlab-web-deep-acceptance — 存量系统深度功能验收

## Purpose

对一个**已经存在、功能繁多、质量未知**的 Web 系统做"每个页面、每个按钮、每个接口贯通"的深度验收，
并沉淀**可重放的回归资产**（功能点 registry + 用例文件 + 报告 + 全局 dashboard）。

与 `devlab-web-test-e2e` 的分工：绿field 新项目用例从零生成走前者；存量系统"先盘点登记再分级深测"
走本技能。两者可先后衔接（先用本技能验收存量，新增功能走前者增量生成）。

**实证规模**：本方法论在某 30+ 模块微前端系统落地，登记 689 功能点（pass 64%/blocked 28%），
实战陷阱 72 条全量收录于 `references/REFERENCE-PITFALLS.md`（执行遇阻先查它）。

## 适用条件

- 被测系统有浏览器 UI + 后端 HTTP API（SPA / 微前端 / 传统 MPA 均可）；
- 可拿到前端源码（盘点要逐按钮读视图代码）与后端数据访问通道（直连 DB 或只读查询代理）；
- 执行环境可跑 Node ≥ 18 + Playwright（Chromium）；
- 允许在测试库造数（写操作前缀隔离，如 `AUTOTEST_`）。

## 核心设计（为什么是这套结构）

1. **registry 是唯一事实源**：功能点状态（todo/pass/fail/blocked）+ 根因 reason + 执行注注释全部登记在
   `registry/<module>.yaml`，执行器回写、报告生成、dashboard 聚合都从它出发。权威信息绝不写在
   会被覆盖的生成物（SUMMARY）里。
2. **唯一入口七模式**：`node run.js <module> [--dry-run|--precheck|--seed|--case|--all|--audit|--cleanup]`，
   新增模块零改执行器——只加 registry + cases。
3. **HTTP 200 ≠ 业务成功**：后端代理吞异常返 200+空/null 是存量系统最常见假成功，框架内置
   响应体六态分诊与假成功嗅探（只观测不改判定，由用例结合语义判读）。
4. **探索一次即固化**：每个 pass/fail 功能点必须有 `.case.js` 可重放，收尾 `--audit` 三对齐审计
   （status × 用例文件 × 报告）防"探索后漏固化"静默混过。
5. **blocked 是一等公民**：不可修问题不判 fail，走五分类根因 + pending-issues 闭环，registry 标
   blocked 写清解锁条件，释放执行流继续推进。

## 目录结构规范

```
test/e2e/
├── run.js                     # 唯一入口执行器（scripts/ 拷贝）
├── e2e.config.js              # 环境配置（baseUrl/凭据/API 前缀/DB 通道/豁免表）
├── registry/
│   ├── modules.yaml           # 模块总账（多会话认领制）
│   └── <module>.yaml          # 功能点唯一事实源
├── cases/<module>/<feature-id>.case.js   # 用例（探索即固化）
├── cases/<module>/_helpers.js            # 模块专属原语（噪声表/页面适配）
├── lib/                       # 框架库（browser/session/assert/report/precheck/api-common）
├── data/factory/<module>.js   # 造数工厂（--seed 调用）
├── reports/<module>/          # 功能点报告 + SUMMARY.md + PRECHECK.md
├── tools/                     # 一次性探针 probe-*（结论固化后移 _archive/）与可复用工具
└── docs/pending-issues.md     # 跨功能点问题闭环（P0-P3 分级）
```

## 七阶段工作流

### Phase 0 — 系统画像盘点（不写任何用例）

1. **范围核验（强制）**：验证范围以"实际部署的后端服务"为准（如 Git 追踪的模块清单）。
   前端有入口但后端未部署的模块标 `out_of_scope`，否则会产出永远修不好的 FAIL。
2. 摸清系统形态：SPA 还是微前端（子应用按需注册？路由挂载检测怎么做）、登录机制
   （表单/SSO/Token）、前端路由清单来源（源码 routers 目录）、后端 API 前缀
   （如 `/emas/ms/<service>/`）、DB 通道（直连 JDBC / 只读 HTTP 代理）。
3. 建立 `e2e.config.js`（从 `scripts/e2e.config.example.js` 拷贝改值）。
4. 产出：系统画像笔记 + modules.yaml 初稿（模块清单 + 路由线索 + 优先级 P0-P3）。

### Phase 1 — registry 建模（盘点 > 写码）

1. 读前端路由源码拿 route → component 映射（模块 id 与路由文件名不一定对应，找不到用中文标题 grep）。
2. **逐按钮读 Vue/React 视图源码**：每个 button/link/tab/树交互、每个 v-if 守卫、每个 API 调用
   列成功能点；不要按"表格思维"预设功能点（无表格页按真实形态等价替换）。
3. 静态排雷：盘点期跑"视图→API 模块"死调用比对（复制残留页的 mounted 死调用 L1 必炸，
   不用等运行期）；标注路由参数驱动页（`$route.params` 刷新即空，必须链式导航进入）。
4. 写入 `registry/<module>.yaml`（schema 见 `references/REFERENCE-REGISTRY-SCHEMA.md`）：
   顶层 `app:` 锚点、`backend_mappers`（预检输入）、pages[].features[]（id 带页面缩写前缀保证
   模块内全局唯一）、`# 执行注:` 注释承载关键事实。
5. **用户抽查确认后开测**——registry 质量决定全盘质量。

### Phase 2 — 预检（不拉浏览器的静态/DB 检查）

```bash
node run.js <module> --precheck
```

从 `backend_mappers` 扫 mapper/SQL 文件，四段检查（退出码 0 全过 / 3 有缺失项 / 2 通道故障）：

1. **方言静态扫描**：目标 DB 不支持的方言形态（如 PG→Oracle：`over(partition by)` 缺 order by、
   `::` 强转、`limit`、`ilike`），高置信计入退出码。空表时这些缺陷被短路不求值，造数后才爆雷。
2. **表存在性批扫**：FROM/JOIN 抽取物理表 ↔ `all_objects` 比对。缺表 → 接口呈"200+空假成功"，
   预判 blocked，**不要误判"数据空需造数"白跑造数**。
3. **自定义函数存在性**：`f_/fn_` 前缀引用 ↔ FUNCTION/PROCEDURE/PACKAGE。
4. **列存在性**：`alias.col` ↔ `all_tab_columns`（仅无歧义别名直连物理表，宁漏勿误报）。

报告落 `reports/<module>/PRECHECK.md`；DB 通道不可用时降级为仅静态段并注明。
详见 `references/REFERENCE-FALSE-SUCCESS.md` 第三节。

### Phase 3 — 分级执行

```bash
node run.js <module> --dry-run   # 必先行：登录+导航+路由挂载检测+功能点清单
node run.js <module>             # 默认执行 fail/blocked/todo（跳过 pass）
node run.js <module> --case <id> # 单点调试
node run.js <module> --all       # 全量回归（自动保护带 reason 的终态 fail 不被间歇覆写）
```

- **L1→L4 逐功能点**（分级硬条件见 `references/REFERENCE-GRADING.md`）；
- **探索一次即固化 `.case.js`**——用例文件按 `cases/<module>/<feature-id>.case.js` 映射；
- 案例级重试：`--retry N`（默认 2）仅对 fail 重跑，重试成功判 pass 并注记
  "环境重试N次后通过"（间歇抖动兜底，持续失败仍 FAIL）；
- FAIL 自动截图 `reports/<module>/<id>-fail.png`；
- 破坏性用例排在依赖它的用例之后（registry 声明顺序即执行顺序）；
- 高危操作（不可逆审批/设备下发）：硬闸拦截 + 降级到弹窗/表单层验证；🔒 HUMAN-DECISION [HD-1]
  ——只有用户显式批准后，才允许对 `AUTOTEST_` 前缀记录真实提交（细节见陷阱 26/27）。

### Phase 4 — 假成功甄别（贯穿执行全程）

- monitor 内置**假成功嗅探**：业务 API（`config.businessApiPattern` 匹配的 JSON 响应）
  HTTP 2xx 但 body `code!=200` 或 `result:null` 时记入 `collect().swallowed`，自动附到报告
  `[假成功嗅探]` 段——**只观测不改判定**（result:null 对部分写接口是合法空返回）。
- 依赖查询结果的用例必须**主动解析响应体**（六态分诊 `bodyVerdict`：
  no-hit / http:N / code:500 / result:null / empty / data），不能指望 HTTP 状态码兜底。
- 完整分诊决策树（含统计页 200+空三分法、入库断链判定）见
  `references/REFERENCE-FALSE-SUCCESS.md`。

### Phase 5 — 三对齐审计（收尾必跑）

```bash
node run.js <module> --audit     # 纯文件操作不拉浏览器；违规退出码 3
```

规则：pass/fail 必须有 `.case.js`（可重放）与报告；blocked 必须有 reason（五分类标签+解锁命令）；
todo 不查。再人工**四对齐核数**：registry 终态 × SUMMARY × 总账 progress 三方数字一致
（历史终态可能只存在于旧 SUMMARY，以带日期的 SUMMARY 为事实源回填 registry 并加执行注）。

### Phase 6 — 报告回写与全局视图

- 执行器自动**文本级回写** registry（就地替换 status/last_run/reason，**不用 yaml.dump 重写**——
  注释是经验载体；写回前 js-yaml 回验，失败放弃落盘 + 醒目告警 + 退出码 3）；
- SUMMARY 从**回写后的 registry 终态聚合**（本轮执行过的用本轮结果，未执行的用终态补齐注明来源）；
- 总账 modules.yaml 回写 progress + 释放认领；全局覆盖率看 `docs/e2e-dashboard.md`
  （`node tools/dashboard.js` 自动生成，勿手改）；
- 不可修问题登记 `docs/pending-issues.md`（格式见 `references/REFERENCE-BLOCKED-TAXONOMY.md`）。

## 失败五分类路由表

| 根因类 | 判定依据 | 处置 |
|--------|---------|------|
| 前端 | JS 报错/组件未挂载/请求体拼错 | 修视图/API 层 → 部署 → 重跑该功能点 |
| 后端-SQL | API 500 + SQL 异常（方言/缺列缺表） | 修 mapper（可配 devlab-dao-sql-compat）→ 部署 → 重跑 |
| 后端-逻辑 | 500/400 非 SQL | 修 service 或登记 pending-issues 标 blocked |
| 数据 | 200 但空/脏/缺前置 | 先按三分法甄别（断链/缺表/日期组织域）→ 造数工厂补造 |
| 环境 | 服务 down/网关不通/间歇抖动 | 停下上报等恢复；间歇重试成功入豁免表（须写明"为什么不是本页缺陷"） |

约束：同一功能点修复**最多 3 轮**，超过登记 pending-issues 标 blocked 继续下一个，不死磕。

## 用例编写模式

```js
const H = require('./_helpers');
module.exports = {
  async run({ page, monitor, assert, session, feature }) {
    await H.gotoPage(page, session, feature.page.route);
    monitor.reset();                       // 注意：L1 用例 reset 勿放在导航后，会清掉 mounted 期错误
    // ...交互与断言...
    if (!precondition) throw new Error('BLOCKED:数据类——缺XX，解锁命令：node tools/xxx.js');
    assert.noErrors(monitor.collect());
    return '一句话结论';
  },
};
```

- **BLOCKED: 协议**：`Error('BLOCKED:<五分类>——<原因+解锁命令>')` 不计失败，回写 blocked；
- 同构用例用"规格表工厂 + 薄存根"（`_specs.js` 导出 makeXxx，`.case.js` 只留一行存根），
  复杂用例（L3 写链路/探索型）单独写，别硬塞工厂；
- 依赖易耗数据的用例开头自愈补数，保证 `--all` 可重复。

## 多会话协作（modules.yaml 认领制）

- **认领**：挑 `status: todo` 且 `claimed_by: null` 的模块写 `claimed_by/claimed_at` 改 in_progress，
  commit 即抢占确认；冲突时后提交者换模块。
- **僵尸接管**：`claimed_at` 超 2 天未更新可强制接管（覆写并注明）。
- **接管前残留检查**：`ls cases/<module>/` + `git status --short` 看前会话草稿；既有 `_helpers.js`
  **禁止整文件覆盖**，用增量编辑。
- **编号防撞**：pending-issues 与陷阱追加一律"模块前缀编号/追加前重新取最大号"，禁看会话早期快照。
- 完整协议见 `references/REFERENCE-REGISTRY-SCHEMA.md` 第四节。

## 环境故障处置（固定规则）

环境故障（dev server 崩溃/后端服务 down/网关不通）🔒 HUMAN-DECISION [HD-2] ——默认
**停下上报等用户恢复，禁止会话自行重启共享服务**（多会话竞相重启已实锤互相冲突）。执行器内置前端 preflight 探活 fail-fast（退出码 2），
看到 `Fatal: 前端未就绪` 按本条处置。等待期间做不依赖环境的工作（写用例/盘点/报告）。
唯一例外：代码修复后的部署走 CI 流水线，不属于环境问题。

## Human Decisions

| ID | 决策点 | 触发条件 | 默认 |
|----|--------|----------|------|
| HD-1 | 高危写操作真实提交 | 用例涉及不可逆审批/设备下发/批量写 | 必问（默认硬闸拦截，降级到弹窗/表单层验证） |
| HD-2 | 环境故障是否协助重启 | preflight 探活失败/共享服务 down | 停下上报等恢复（禁止会话自行重启共享服务） |

结构化同源定义见 `decisions.yaml`。

## References

| 文件 | 内容 | 何时读 |
|------|------|--------|
| `references/REFERENCE-GRADING.md` | L1-L4 分级定义与硬条件、等价替换规则 | Phase 1 建模 / Phase 3 写用例 |
| `references/REFERENCE-FALSE-SUCCESS.md` | 假成功六态分诊、200+空三分法、入库断链、precheck 机制 | Phase 2/4 必读 |
| `references/REFERENCE-REGISTRY-SCHEMA.md` | registry/modules.yaml 完整 schema、回写规范、多会话协议 | Phase 1/6 |
| `references/REFERENCE-BLOCKED-TAXONOMY.md` | 五分类路由、blocked reason 规范、pending-issues 闭环 | Phase 3/6 |
| `references/REFERENCE-PITFALLS.md` | 72 条实战陷阱（五段式），按主题分组 | 执行遇阻先查 |
| `references/REFERENCE-INDEX.md` | references 导航索引 | 找文档入口 |

## Scripts 与 Templates

- `scripts/run.js` + `scripts/lib/*` + `scripts/tools/dashboard.js` + `scripts/e2e.config.example.js`：
  拷贝到项目 `test/e2e/` 即得执行器骨架（通用化版本，环境差异全部走 e2e.config.js）。
- `templates/`：registry-module / modules / case / SUMMARY / pending-issues / dashboard 六件套模板。
