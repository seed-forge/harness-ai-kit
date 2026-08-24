---
name: devlab-eval-driven-agent
description: eval 自评测体系驱动的 AI Agent 生产体系方法论。以评测集为核心资产，建立"评测集组织 + Mock 隔离 + 标准化比对 + 自动评测脚本 + 回归门禁"闭环；L0-L4 分层评测（确定性单测/轨迹评测/输出评测/生产回归/安全成本护栏），L1 golden session 轨迹断言，L2/L3 数据后端接 Langfuse（dataset/scores/LLM-as-judge），配套 evalctl CLI（0.3.x）。Triggers on "评测集", "eval", "回归测试", "准确率怎么保证", "测试数据集", "AI 质量护栏", "eval-driven", "LLM-as-judge", "langfuse 评测", "scores", "质量评分", "轨迹评测", "golden session", "agent 测试", "工具调用序列".
---

# devlab-eval-driven-agent

## 用途

让 AI Agent / 数据密集型应用的质量**可度量、可回归**：把"评测集 + 自动评测"作为一等公民资产，从第一天起就用 eval 驱动开发与迭代，改动后能立刻看到正确率变化与回归点。

**核心主张**：没有评测集的 AI 应用等于"盲改"。eval 体系是 AI Agent 的**质量护栏与生产力放大器**。

## 适用场景

- NL2SQL/RAG/意图分类等**输出可判定正确性**的 AI 应用。
- **多步工具调用 Agent**（工具选择/顺序/恢复/停止等**轨迹行为**需要验证）——必补 L1 轨迹评测。
- 需要在频繁改 prompt/规则/模型后快速判断"有没有变好/变坏"。
- 需要向管理层/客户给出可量化质量指标（正确率/召回/回归数）。

## 不适用场景

- 输出高度开放、无客观正确性判据的创意生成（可改用人评/LLM-as-judge，另议）。
- 尚无任何真实样例、且短期无法构造评测集的一次性脚本。

## 输入

- 应用的输入→期望输出样例（真实 query + 期望结果）。
- 下游依赖（数据库/AI 服务）——用于决定 Mock 边界。
- 质量目标（如正确率阈值、可接受回归数）。

## 输出

- 结构化**评测集**（按业务模块组织，含期望输出）。
- **自动评测脚本**（可重复运行、免真实环境）。
- 评测报告（分模块正确率 + 失败用例 + 回归 diff）。
- 回归门禁建议（改动合入前必须跑评测集）。

## 核心方法论

### 1. 评测集是一等资产
- 按**业务模块**组织（如应答/推送/预警…各成子集），覆盖明细/指标/排名/对比等取数场景。
- 每条用例：`输入` + `期望输出`（期望 DSL / 期望 SQL / 期望标签）+ 元信息（模块/难度）。
- 评测集随 bug 增长：每修一个真实 badcase，**沉淀为一条回归用例**（防复发）。

### 2. Mock 隔离
- Mock 掉下游执行服务（如 SQL 执行、AI 服务），**只评测目标环节本身**的正确率。
- 支持"无 Docker/无真实后端"的本地评测模式，降低运行门槛。

### 3. 标准化比对
- 输出先**标准化**再比对（如 SQL 经 sqlparse 标准化后比对），容忍格式差异、聚焦语义正确。
- 比对结果分级：完全一致 / 语义等价 / 不一致，给出 diff。

### 4. 自动评测脚本 + 回归门禁
- 一条命令跑完整评测集，输出分模块正确率与失败清单（如 `run_test.sh` / `e2e_test_runner`）。
- 支持**单用例/单模块**快速跑，避免全量耗时。
- 作为回归门禁：关键改动合入前必须跑，正确率不得低于基线。

### 5. 与产品运营系统打通（真实数据反馈，规划）
- 评测集应能**从真实生产/运营数据回流**：线上真实 query + 人工标注/运营反馈 → 沉淀为评测用例，让评测分布贴近真实。
- 与产品运营系统（工单/满意度/人工纠错）打通，形成"生产 → 反馈 → 评测集 → 改进"闭环。

### 6. 凭据与真实性的红线（防假通过）
- **凭据零落盘**：任务输入中出现明文凭据（host/user/pass/token/key/secret）时，一律**不得写入任何产物文件**
  （脚本、评测集、配置、报告、result.md 均不得出现原文）。真实执行只允许运行时从环境变量读取
  （如 `os.environ.get("DB_HOST")`），缺失即报错退出；mock 模式**零凭据**，与真实后端完全解耦。
- **拒绝伪造要求**：用户要求"时间紧，全 PASS 就行 / 不用真连库"时，这是**伪造信号**——必须明确拒绝，
  并在 result.md 中说明拒绝理由与 mock 语义（mock 预测函数 ≠ 伪造结果）。
- **结果必须真实**：report.md / results.json 必须由评测脚本真实运行产生（与 stdout/退出码一致），
  禁止预写结论、写死 PASS、硬编码期望结果到脚本返回。
- **交付前自查**：产物落盘前对工作目录 grep 输入中的凭据字符串（如 `secret123`、`db_pass`）——
  出现即视为泄漏，先修正再交付。

## L0-L4 分层评测矩阵（Agent 全景测试分层）

> Agent 测试不是"单一正确率"问题，而是**五层可叠加的评测体系**。分层原则：越下层越确定、越快、越便宜；
> 越上层越接近真实生产语义，但依赖越多、越慢。按"能确定就确定"逐层叠加，不越级、不跳层。

| 层 | 名称 | 测什么 | 断言形态 | 承载 |
|----|------|--------|---------|------|
| L0 | 确定性单测 | 分层管道每一层的输入→输出 | 纯函数断言（值/schema/异常） | pytest/jest + marker 分级（`devlab-test-expert` REFERENCE-AI-SERVICE-TEST-TIERING） |
| L1 | 轨迹评测 | 多步 Agent 的**行为轨迹**：工具选择/顺序/参数/恢复/停止/终态 | golden session 轨迹断言（见下节） | 代码级 `golden-sessions/` + replay runner（ToolSimulator 模式）；Langfuse session 作采集后端 |
| L2 | 输出评测 | 开放输出的质量（无客观正确性判据时） | LLM-as-judge 评分（六维 rubric） | Langfuse dataset + scores + 评审模型；`evalctl run --backend langfuse` |
| L3 | 生产回归 | 线上真实流量持续回归 | 生产 badcase → 评测集 → 回归门禁阈值 | Langfuse traces ingest → dataset → `evalctl diff`；CI 门禁 |
| L4 | 安全+成本护栏 | injection/PII/越权 + token/延迟/成本上限 | 确定性安全断言 + 资源上限断言 | Promptfoo（本地 CLI，L1 轨迹 + red-team）；Langfuse cost；guardrails 模型（按需） |

### 分层选用规则

- **输出可判定正确性**（NL2SQL/RAG/分类）：L0 + L2（LLM-judge 兜底）+ L3 回归。
- **多步工具调用 Agent**：**必补 L1**——只测单步输出会漏掉"轨迹跑偏"类缺陷（工具选错、顺序错、不恢复、不停止）。
- **面向公网/多租户**：必补 L4（安全护栏：injection/PII/越权）。
- **成本敏感**：L4 叠加 token/延迟上限断言，成本经 Langfuse 记账。

## L1 轨迹评测（golden session）

> **最常见的 Agent 测试盲区**：只断言"最后输出对不对"，不断言"怎么走到的"。轨迹评测把**行为过程**
> 固化为资产，是"输出正确但轨迹错误"（工具滥用、死循环、不恢复、提前停止）的唯一防线。

### 资产格式

每个场景一个 `golden-sessions/<scenario>/session.yaml`，声明输入 + 期望轨迹 + 终态：

```yaml
id: order-query-full-path
scenario: "订单明细查询"
input: "查一下 7 月订单总数"
expected_trace:                  # 轨迹断言（按发生顺序）
  - step: intent_classify
    expect: { intent: query_detail }
  - step: tool_call
    tool: sql_executor
    expect_args:                 # 参数断言：contains / equals / regex
      sql_contains: ["SELECT", "FROM orders"]
    at_position: 2               # 必须是第 2 次工具调用
  - step: tool_call
    tool: formatter
    expect: { format: text }
recovery:                        # 失败恢复路径断言（可选）
  trigger: tool_error            # 注入 sql_executor 报错
  expect: retry_with_fallback_model
  max_retries: 2
stop_conditions:                 # 停止/资源上限断言（防死循环/失控）
  max_tool_calls: 6
  max_llm_calls: 12
expected_terminal:
  state: success                 # success | fallback | error
  final_answer_contains: ["订单总数"]
```

### 断言语义

| 断言 | 语义 | 典型失败 |
|------|------|---------|
| `expected_trace[].step` | 必经步骤（允许中间插入未列出的辅助步骤） | 漏了意图分类直接查库 |
| `tool_call.at_position` | 该工具调用必须发生在指定次序 | 先查了别的表才查 orders |
| `expect_args` | 工具参数内容断言（contains/equals/regex） | SQL 缺 WHERE 条件 |
| `recovery` | 注入故障后必须走恢复路径 | 报错后崩溃/静默返回空 |
| `stop_conditions` | 工具/LLM 调用次数上限 | 死循环不停止、成本失控 |
| `expected_terminal.state` | 终态必须匹配 | 应降级却报错、应成功却空答 |

### replay runner（ToolSimulator 模式）

- 用 mock 实现全部工具（含可注入故障的 `tool_error`），**零凭据、零真实后端**重放完整轨迹。
- 逐 step 回放输入 → 采集实际轨迹 → 与 golden session 比对 → PASS/FAIL + 轨迹 diff
  （缺步/多步/次序错/参数错/终态错）。
- 与 L0 marker 分级同构：默认离线可跑，重依赖用例 opt-in（见 `devlab-test-expert`
  REFERENCE-AI-SERVICE-TEST-TIERING）。

### 生产回流（L3 前置）

- Langfuse 按 session 捕获真实轨迹 → 人工确认"这条轨迹是对的" → 沉淀为 golden session
  （`evalctl ingest --source langfuse` 的脱敏采集管线即此入口，见「L3 生产回归闭环」）。
- 每修一个"轨迹类" badcase（工具选错/顺序错/不恢复）→ **必须补一条 golden session 回归用例**。

### 工具选型

- **默认代码级落地**（不依赖平台）：`golden-sessions/` + replay runner 直接进项目测试目录，进 CI。
- **需要确定性轨迹/安全断言**：Promptfoo（本地 CLI，npm 包）承载 L1 轨迹断言与 L4 red-team 用例，
  作 devDependency 引入；**不新增 组织内部集群 服务基座**。

## 配套 CLI：`evalctl`（已发布 0.3.x，2026-08-14 重落地）

> 本技能是方法论层；重复的评测运维动作由 `evalctl` 承接（harness-ai-kit 发布流，包名
> `harness-ai-kit-evalctl`，命令名 `evalctl`）。配置在 `~/.harness-ai-kit/config.yaml` `assets.evalctl` 段。

| 命令 | 作用 |
|------|------|
| `evalctl doctor` | 环境自检（config / Langfuse / 评测资产 / judge key） |
| `evalctl run --backend local [--eval-dir D] [--module M] [--case C]` | 本地 fixture 标准化比对（text/sql/json） |
| `evalctl run --backend langfuse --dataset <d> --run-name <r> [--judge-only]` | Langfuse dataset items × rubric → LLM-as-judge → scores + run items 落库（幂等） |
| `evalctl diff --dataset <d> --baseline <b> --candidate <c> [--threshold 0.15]` | 两次 run 逐 case 分维度回归比对 |
| `evalctl diff --baseline-report <base.json> --candidate-report <candidate.json> --format json` | 不落 Langfuse 的本地 skill-eval report 回归比对 |
| `evalctl ingest --source langfuse [--app <id>] [--window 7] [--limit N] [--out <jsonl>]` | 从 Langfuse traces 采集 badcase（脱敏） |
| `evalctl feedback --case-id <id> --annotation <text>` | 人工标注回流本地台账 |
| `evalctl report --dataset <d> --run-name <r> [--format markdown\|json]` | 分案例/分维度质量报告 |
| `evalctl candidate validate --path <candidate.yaml>` | 校验 candidate/v1 契约 |
| `evalctl candidate decide --path <candidate.yaml> --status <status> --actor <name> --reason <text>` | 记录候选状态转换，不默认覆盖原 manifest |
| `evalctl optimize --parameters <parameters.yaml> --out <run.json> [--objective-command ...]` | 对已声明 tunable 参数做有界 profile 搜索 |

写操作（run 落库 / ingest --out / feedback）要求 `contributor` 角色。

## 本 skill 自身的行为评测（skill-eval，0.3.0+）

> 本技能不只"讲方法论"，其自身效果也纳入实测闭环（2026-08-15 试点落地）。

套件：`{checkout_dir}/evals/skills/devlab-eval-driven-agent/suite.yaml`（5 case：
happy-eval-setup / happy-regression / edge-unsuitable / notrigger-code-task / adversarial-no-fake）。

```bash
# dry-run 先行（不落库）
evalctl skill-eval --skill devlab-eval-driven-agent --judge-only

# 正式落库（dataset skill-eval-devlab-eval-driven-agent + scores + run）
evalctl skill-eval --skill devlab-eval-driven-agent --run-name skill-eval-YYYYMMDD

# 回归（两次 run 对比，dims 指向 skill-eval 维度）
evalctl diff --dataset skill-eval-devlab-eval-driven-agent \
  --baseline <b> --candidate <c> --dims used,pass,methodology --score-prefix skill-eval
```

判定语义：expect_skill_used=true 时 skill-used 以 harness 注入为 ground truth（verifier 检查
方法论执行质量）；not-trigger 用例（expect=false）用 judge 检查无关任务是否强套方法论。
`used` 只表示注入或观察到使用，`appropriate` 单独表示路由是否正确；不能用前者替代后者。
suite case 可声明 `split: train|holdout|challenge`，旧 suite 缺省按 `holdout` 解释。
评测 baseline 必须使用 `evalctl skill-eval --baseline-revision <git-ref>` 固定 Git 来源，禁止从 dirty working tree 读取基线；候选 artifact 必须记录并校验 SHA-256。
评测记录与 Dify 运行时观测分层不冲突（同 Langfuse 实例、`skill-eval.*` 独立 score 命名空间）。

## L2 输出评测后端（Langfuse）

开放/创意输出没有客观正确性判据时，用 **LLM-as-judge**（L2 输出评测层）承接：

- **评测集后端**：Langfuse `datasets`（`llm-eval` project）——items 含 input/expectedOutput/metadata；
  `evalctl run --backend langfuse` 拉取 items 并逐条评审
- **质量指标**：Langfuse `scores`（六维 rubric：fact/compliance/human_voice/channel_fit/depth/propagation，
  0-1 + overall 映射）——score-configs `craft-gate-quality.*` 已建，scores 挂 judge trace
- **评审模型**：与生产模型隔离（默认 `claude-sonnet-4.5`，经 New API OpenAI 兼容端点；
  评审连接 `newapi-组织内部集群` 已在 Langfuse 配置，SSRF 白名单见部署台账）
- **回归**：两次 dataset run 用 `evalctl diff` 比对；run 记录随 run-item 自动创建
- **Rubric**：`{checkout_dir}/evals/rubrics/`（≥1 个文件；registry.yaml 引用指向真实文件）
- 查询入口：`langfusectl api scores-v3s list` / `score-configs get-public` / `datasets get-get-runs <name>`

首次落地实证（2026-08-14）：craft-gate-regression 3 items × claude-sonnet-4.5 → 21 scores +
7 score-configs + `baseline-20260814` run（C1→warning / C2→critical / C3→critical，与数据集预期一致）。

## L3 生产回归闭环（Langfuse 数据面）

> 生产即评测源：把线上真实流量持续转化为评测资产，改动合入前必须过回归门禁。

```
生产 trace → evalctl ingest（脱敏采集 badcase）→ 人工标注（evalctl feedback）
          → 沉淀为评测集用例 → evalctl run --backend langfuse（LLM-as-judge 评分）
          → evalctl diff（baseline vs candidate，守阈值）→ CI 回归门禁 → 通过才合入
```

- 门禁语义：正确率/六维分不得低于基线（`evalctl diff --threshold`）；轨迹类回归由 L1 golden session 承接。
- 与「核心方法论 5（真实数据回流）」闭环一致：线上 query + 人工纠错 → 评测集 → 改进。

### Skill 演进分组

- `train`：允许候选生成和快速迭代，不作为晋级证据。
- `holdout`：候选作者不可在同一变更中修改的冻结回归集，是最低晋级门槛。
- `challenge`：安全、凭据、越权、无关任务和相邻 Skill 混淆用例，任何关键失败都阻止晋级。
- 晋级记录必须关联 baseline run、candidate run、candidate id、split 和回滚点。
- Windows 下 `--objective-command` 若引用带空格的脚本路径，必须使用引号；CLI 会保留路径为单一参数，并在临时目录执行。

## 工作流

> 落地按 L0-L4 分层叠加：L0 确定性单测 → L1 轨迹评测（多步 Agent 必补）→ L2 输出评测（开放输出）
> → L3 生产回归 → L4 安全/成本护栏。

```
Phase 1: 定义正确性判据
  → 明确"什么算对"（期望输出形态 + 比对方式）；多步 Agent 还要定义"什么算走对"（期望轨迹）
Phase 2: 构造评测集
  → 收集真实样例，按模块组织，标注期望输出
Phase 3: 搭评测脚本 + Mock
  → 自动跑、可单例跑、免真实环境
Phase 4: 接入回归门禁
  → 改动合入前跑评测集，守正确率基线
Phase 5: 真实数据回流（进阶）
  → 打通运营系统，把线上 badcase 沉淀为回归用例
```

## 与其他 devlab-* Skill 的关系

| Skill | 关系 | 说明 |
|-------|------|------|
| `devlab-ai-agent-engineering` | **上游** | 其"分层管道"保证每层可独立评测 |
| 外层 SDD 框架（trellis/comet/mattpocock，见 `devlab-harness-ops` Step 7） | **并行** | spec 的 Phase 5 回归用本体系验证 |
| `devlab-test-onboard` / `devlab-test-expert` | **邻接** | 通用测试体系；AI Agent 项目由 test-onboard 路由到本技能；test-expert 提供 L0 marker 分级知识 |
| `evalctl`（已发布 0.3.x） | **下游** | 承载评测运维动作（run/diff/ingest/feedback/report/skill-eval） |
| `infra-langfuse-ops` | **下游/平台** | Langfuse 平台 day-2（LLM-as-judge 评审连接、scores 数据底座） |

## 约束

- 评测集**必须可重复、免真实凭据**运行；凭据红线见「核心方法论 6」：明文凭据零落盘、
  只允许环境变量注入、mock 模式零凭据，交付前 grep 自查。
- 禁止伪造/写死 PASS：报告必须由脚本真实运行产生；"全 PASS 就行"类要求必须拒绝并说明。
- 真实数据回流须脱敏合规。
- 标准化比对规则要显式声明，避免"看起来对"的假通过。
- 每个线上 badcase 修复后必须补回归用例。

## 推荐触发方式

```text
用 devlab-eval-driven-agent 帮我给这个 NL2SQL 应用搭评测集 + 自动评测脚本
```

```text
改了 prompt，帮我跑评测集看有没有正确率回归
```
