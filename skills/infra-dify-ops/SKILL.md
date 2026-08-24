---
name: infra-dify-ops
description: Dify 平台使用层运维 Skill：DSL 创作/校验/双轨导入（Console API 优先，Playwright 兜底）、DSL 导出、app 检查、本地资源沉淀、workflow 草稿、模型 provider 配置与生产验收；不负责部署层。配套 CLI difyctl。
---

# infra-dify-ops

> 配套 CLI `difyctl`（`difyresctl` 旧包与 shim 已下线）。

## 用途

用于在 组织内部集群 场景中做 Dify 平台的使用层资源运维与 workflow DSL 创作，而不是处理部署层。它作为 AI 平台基础设施治理的一部分纳入 `infra-*`，但不接管 Dify Compose、数据库或容器生命周期。

这个 Skill 主要覆盖：

- Dify app / workflow / chatflow / agent 等资源的本地归档
- **DSL 创作**：从业务需求生成 import-ready DSL（`workflow-create` + spec v2）、本地校验（`dsl validate`）
- **双轨 DSL 导入**：优先 Console API（`dsl import --via auto`），5xx/网络错误自动降级 Playwright；不再默认依赖 RPA
- **DSL 导出**：经 Console API 拉取现网 app 的 DSL（`dsl export`）
- 导出的 DSL 文件校验、摘要、快照与 current 版本维护
- 基于 app API key 的使用层检查
- 模型 provider 配置（`openai_api_compatible` 加模型，联动 newapictl 消费）
- Dify 1.13.x workflow DSL / graph 兼容性排障与生产验收
- Studio 导入后 graph 损坏、未发布 app、输出结构漂移等使用层救援
- 资源清单 `resources.yml` 的登记与批量筛选计划
- 把后续新 workflow 及时沉淀到统一资源目录

## DSL 创作与导入（0.2.0 新增）

### 三步创作流程

1. `difyctl workflow-create intake ... --spec-out ./specs/x.yml`：从业务需求生成结构化 spec（默认 v2）
2. `difyctl workflow-create scaffold --spec ./specs/x.yml --output ./drafts/x.dify.yml`：产出 **import-ready DSL**（含 `app`/`kind: app`/`version: "0.6.0"`/`workflow.features`/完整 graph node wrapper + position + edges）
3. `difyctl dsl validate ./drafts/x.dify.yml`：本地校验（version/mode、图端点可达性、环检测、edge 引用、LLM 必填字段、变量引用语法、if-else handle）

### 双轨导入决策

- `difyctl dsl import --dsl ./drafts/x.dify.yml --via auto`（推荐）：
  - Console API 成功 → 返回 `app_id` + `app_url`
  - Console API 返回 5xx 或网络错误 → 自动降级 Playwright 浏览器导入
  - Console API 返回 4xx（配置/鉴权错误）→ 直接报错，不降级
- `--via api`：只走 Console API，失败即报错（CI / 无 GUI 环境）
- `--via browser`：只走 Playwright（现网 API 不可用时的兜底）

导入前默认自动跑一次 `dsl validate`；用 `--skip-validate` 跳过。

详细 DSL 结构、节点 schema、布局与踩坑见：
- `references/REFERENCE-DSL-AUTHORING.md`
- `references/REFERENCE-DSL-GOTCHAS.md`

## 输入

- 当前资源目标，例如 `app`、`workflow`、`chatflow`
- 本地 DSL 导出文件路径
- Dify app base URL 与 app API key（如需远端检查）
- 资源 ID、标题、标签、app_id、app_name
- 当前项目的资源工作区目录

## 输出

- 规范化的资源目录
- `resource.json` 元数据
- `dsl/current.*` 与 `dsl/snapshots/*` 快照
- 远端 app 信息或参数检查结果
- 对后续沉淀方式的明确建议

## 工作流

1. 先判断这是“远端 app 检查”还是“本地资源沉淀”。
2. 若需要远端检查：
   - 优先使用 `difyctl app info`
   - 必要时再用 `difyctl app parameters`
   - 如需补充环境描述，可再用 `difyctl app meta`
   - 若任务涉及命名、描述、发布对象或 Studio 卡片展示，先确认 live app 事实，再讨论本地 DSL 或 registry
3. 若需要沉淀资源：
   - 先用 `difyctl resource init <resource_id> --mode ...`
   - 再把导出的 DSL 用 `difyctl resource capture ...` 归档
   - 默认维护 `dsl/current.*` 与时间戳快照
4. 若要维护项目级资源清单：
   - 先用 `difyctl registry init`
   - 再用 `difyctl registry upsert ...`
   - 批量筛选时用 `difyctl batch plan ...`
5. 若需要从零生成一个业务需求对应的 workflow：
   - 先用 `difyctl workflow-create intake ...` 或 `draft --from-demand ...`
   - 再用 `difyctl workflow-create validate-spec ...`
   - 然后用 `difyctl workflow-create scaffold ...` 产出 DSL 草稿
6. 若需要把本地资源同步回 Dify Studio：
   - 先用 `difyctl studio create-plan ...`
   - 或对已有资源用 `difyctl studio export-plan ...`
   - 或用 `difyctl studio duplicate-plan ...`
7. 若准备切到真实浏览器自动化执行：
   - 先用 `difyctl studio browser-doctor`
   - 再用 `difyctl studio import-dsl-run --dsl ...`
   - 当前阶段要预期登录页和按钮选择器仍需现场微调
8. 若只想快速理解一个 DSL：
   - 先用 `difyctl dsl summarize <path>`
9. 每次新增或明显改造 workflow 后，都要判断是否应该：
   - 继续补当前资源目录
   - 新增一个独立资源目录
   - 回填到项目级知识卡片或 SOP
10. 若导入后的 workflow 在 Dify 1.13.x 中无法运行或 Studio 无法正常打开：
   - 先把问题分层为 `graph schema`、`publish state`、`runtime invoke` 三类
   - 优先用黑盒 app API 调用和只读数据库检查定位，不要一上来就改库
   - 确认是旧 DSL 兼容性问题后，再决定是“最小字段补丁”还是“整图原生重建”
11. 若需要做生产救援：
   - 先确认 draft graph、published workflow、apps.workflow_id、api_tokens 四个对象是否齐全
   - 再确认 `start`、`llm`、`end` 三类节点是否符合当前 Dify 原生 schema
   - 最后用真实样例做健康路径与异常路径双验证，结果通过后再宣布可用
12. 若任务同时涉及 Git 台账、本地 DSL、Studio 页面和 live app：
   - 先把四层对象分开看，不要假设它们天然一致
   - 优先核对 live app，再核对 `resources.yml` / `resource.json` / `dsl/current.*`
   - 若只是 Studio 资产漂移，先修正 Studio，再把本地台账回写到一致状态
13. 若需要查询/新增 Dify 模型提供商下的模型（模型台账）：
   - 先 `difyctl provider login --username-env ... --password-env ... --headed` 取 Console 会话，用返回的 `full_cookie_header`（含 `csrf_token`，纯 `session_cookie` 会 401）作为 `--console-key`
   - 用 `difyctl provider models --provider <full-path>` 查某提供商已配置模型（台账视图），随时看清现状
   - 用 `difyctl provider add-model --provider <full-path> --model <name> --endpoint-url <base>/v1 --api-key <key>` 给 openai_api_compatible 类可自定义模型的提供商加单个模型；先 `--dry-run` 预览 payload（无需 Console 会话）
   - newapi 消费 key 无法经 Admin API 读取（服务端全程脱敏、忽略客户端传入 key），必须从 newapi Web UI 复制或由用户提供；获取后 `newapi/v1/chat/completions` 冒烟测试确认模型可用再注册
14. 若需要改某 workflow 的 LLM 节点模型：
   - `GET /console/api/apps` 定位 app_id → `GET .../workflows/draft` 取 graph
   - 改 `data.type=="llm"` 节点的 `model.provider` 与 `model.name` → `POST .../workflows/draft` 保存 → `POST .../workflows/publish` 发布
   - 用 `POST .../workflows/draft/run`（SSE 流）跑一次，确认 `node_finished`/`workflow_finished` 均 `status=succeeded` 且 `error=None`

## 一致性校验与命名漂移

### 四层事实源

处理 Dify 使用层问题时，至少区分以下四层：

- live app：`/v1/info`、`/v1/parameters`、`/v1/meta` 实际返回的对象
- Studio asset：`/apps` 卡片、应用标题、描述、发布态和可见名称
- local registry：`resources.yml`、`resource.json` 中登记的 `resource_id`、`title`、`app_id`、`app_name`
- local DSL：`dsl/current.*`、`dsl/snapshots/*`、`drafts/*` 中沉淀的 graph 与元数据

不要因为其中一层已经更新，就推断其他三层也已经同步。

### 推荐校验顺序

1. 先确认当前问题属于 live app、Studio asset、local registry、local DSL 中的哪一层，或是否多层叠加。
2. 只要任务涉及 app 名称、描述、默认 workflow 绑定或“页面显示不对”，优先执行 `difyctl app info`。
3. 若 组织内部集群 本地网络、代理或浏览器自动化环境不稳定，优先以内网可达机器上的 live app 检查结果为准。
4. 确认 live app 事实后，再决定是：
   - 更新本地 registry / DSL
   - 更新 Studio app 信息
   - 同时做两边对齐
5. 完成修改后，至少做一次双验证：
   - live app 验证
   - 本地资源验证

### 命名治理规则

> **命名格式的权威真源在 `fleet-platform/resources/dify/README.md`「资源命名规范」章节**（resource_id 正则 `^[a-z][a-z0-9]*(-[a-z0-9]+)*$`、文件布局、扩展名、ledger v2 schema）。本节只讲**漂移治理**，不重复定义命名格式；`difyctl` 亦在代码/`--help` 内置同一正则并硬校验非法 id。

- `resource_id` 是稳定标识，优先保持稳定，不要因为展示名称变化就频繁改动。
- `title` 和 `app_name` 可以随业务语义演进，但改名后要主动检查 Studio 与 live app 是否同步。
- `drafts/*` 与 `dsl/snapshots/*` 允许保留历史名称，但不能拿历史快照代表当前现网事实。
- 浏览器自动化如果按名称查找 app，默认要警惕 registry 名称与现网名称已经漂移。

### 处理顺序建议

遇到“代码里已经叫新名字，但 Dify 页面还是旧名字”这类问题时，默认按下面顺序处理：

1. 用 app API 先确认现网 `name` / `description` / `mode`
2. 再核对 `resources.yml`、`resource.json`、`dsl/current.*`
3. 若只是 Studio / live app 漂移，先修正 Studio
4. 再把本地 registry 和 README 等元数据回写到最终一致状态
5. 最后保留一次可追溯验证结果，避免下次会话重新猜

## Dify 1.13.x 修复策略

### 故障分层

- `graph schema`：Studio 打不开、运行前即报 `validation errors`，通常是旧 DSL 与当前 `start` / `llm` / `end` 节点 schema 不兼容。
- `publish state`：app 存在但不可调用，常见特征是 `apps.workflow_id` 为空、未指向 published workflow，或只有 draft 没有 published 版本。
- `runtime invoke`：API 可进业务层但 blocking 运行异常、超时、输出漂移，通常需要看 workflow runs 和 API logs。

### 推荐排查顺序

1. 先做黑盒调用，确认错误是在鉴权、参数校验、graph 校验还是节点执行阶段。
2. 再检查 app 发布态是否完整：
   - `apps.workflow_id` 应指向 published workflow，而不是 draft
   - 同一个 app 通常至少有一条 `draft` workflow 和一条带时间戳版本号的 published workflow
   - 若需要使用 service API，还要确认存在 `api_tokens.type = app`
3. 再检查 graph 结构是否是当前 Dify 原生格式：
   - `start.variables` 应是 `variable` / `label` / `type: text-input` 这类 `VariableEntity`
   - `llm` 节点至少要有 `model`、`context`、`vision`
   - `end.outputs` 应是 `variable` + `value_selector` + `value_type`
4. 只有在 Studio 已不可用、且黑盒与只读检查都证明是元数据损坏时，才进入 break-glass 数据层修复。

### Break-Glass 原则

- 这类修复属于使用层资源救援，不是常规路径，必须有明确授权。
- 优先做“可回滚的最小改动”，例如先补齐缺失字段，再验证是否足够。
- 若旧 graph 与当前 Dify 版本差异过大，不要持续缝补，直接重建成当前原生 graph。
- 不在总结里扩散完整 API token、数据库密码等凭证；验证时只汇报是否成功与关键输出形状。

### 生产可用判定

- `published workflow` 已存在，且 `apps.workflow_id` 已切到该 published 版本。
- app API 黑盒调用成功，不再停留在 schema 校验或参数缺失报错。
- 至少完成两类验证：
  - 健康样例：应返回稳定的 `title`、`markdown_body`、`plain_text_body`
  - 异常样例：正文必须贴合输入事实，不能复用历史样例或编造新数字
- 最新 `workflow_runs` 记录应能落库并收敛到 `succeeded`，必要时辅以 API logs 核对。

## Dify 1.13.x Graph 约定

### 优先选择

- 对监控日报、通知封装、结构化摘要这类场景，优先用 `start -> 单个 llm(structured_output) -> end`。
- 不要默认串多个自由文本 LLM 节点再靠 end 兜底拆字段，这样更容易产生幻觉和字段漂移。

### 原生字段约定

- `start.variables` 使用当前 `VariableEntity` 结构，例如 `variable`、`label`、`type: text-input`。
- `llm` 节点在 Dify 1.13.x 下应显式带上：
  - `model`
  - `context`
  - `vision`
  - `retry_config`（`difyctl` scaffold 默认注入 3 次重试）
  - `error_strategy`（`difyctl` scaffold 默认注入 `default_value` fallback）
  - 需要结构化结果时加 `structured_output_enabled` 与 `structured_output.schema`
- 新建 workflow 的默认 LLM 模型使用 `langgenius/deepseek/deepseek` / `deepseek-v4-flash`，`mode: chat`，`temperature: 0.1`。
- `end.outputs` 直接映射到上游 `structured_output` 字段，例如：
  - `["llm_node", "structured_output", "title"]`
  - `["llm_node", "structured_output", "markdown_body"]`
  - `["llm_node", "structured_output", "plain_text_body"]`

### 提示词约束

- 明确写出“只能依据 snapshot_json 中已有事实，不允许猜测、补造、外推”。
- 明确要求空区块输出“未观测到异常”或“无数据”。
- 对正文结构写死章节名，而不是依赖模型自行发挥。
- 若需要多语言，只让 `language` 影响表述语言，不影响事实本身。

### LLM 节点容错默认行为（0.4.0 新增）

`difyctl workflow-create scaffold` 默认为每个 LLM 节点注入两层容错：

1. **`retry_config`**：`{retry_enabled: true, max_retries: 3, retry_interval: 1000}`
   - 触发条件：模型返回 429 / 5xx / 超时
   - 与 newapi 侧的 proxy 重试 + 渠道 fallback 互补：newapi 处理上游不可用，Dify 侧处理模型响应本身的异常
   - 传 `retry_config=None` 可禁用（仅限调试）

2. **`error_strategy`**：`{type: default_value, default_value: ""}`
   - 触发条件：重试全部耗尽后
   - 效果：输出空值让下游节点继续执行，而非整个 workflow 崩溃
   - 对于 `structured_output` 节点，`default_value` 应是一个含全部必填字段的空对象，例如 `{"title":"","markdown_body":"","plain_text_body":""}`
   - 传 `error_strategy=None` 可禁用（不推荐用于生产）

`difyctl dsl validate` 会对缺失这两项的 LLM 节点发出 warning，提示手动补齐。

手写或从 Dify 导出的 DSL 如果缺少 `retry_config` / `error_strategy`，建议用 `difyctl dsl lint` 检查后再导入。

## App 服务密钥 / 调用 / 运维（0.7.0 新增）

创建工作流后「取 key → 调用」现已在 CLI 内闭环，覆盖各类应用：

```bash
# 1) 取 app 的 service API key（Console API）：完整 token 仅打印一次 + 存 config.yaml assets.difyctl.app_keys
difyctl app keys create --app-id <app_id>
difyctl app keys list --app-id <app_id>        # 只显示掩码前缀
difyctl app keys delete --app-id <app_id> --key-id <kid>

# 2) 调用应用（mode 自动从 ledger/--mode 解析，覆盖全类型）
difyctl app run --app-id <app_id> --inputs '{"text":"hi"}'          # workflow -> /v1/workflows/run (blocking)
difyctl app run --app-id <app_id> --query "你好"                     # chat/advanced-chat/chatflow -> /v1/chat-messages (blocking)
difyctl app run --app-id <app_id> --mode agent-chat --query "你好"    # agent-chat -> /v1/chat-messages (streaming，Dify 拒绝 blocking，自动改流式聚合)
difyctl app run --app-id <app_id> --mode completion --query "写首诗"  # completion -> /v1/completion-messages

# 3) 导入即可用（opt-in 闭环）
difyctl dsl import --dsl draft.dify.yml --via api --resource-id my-wf --create-key --smoke --smoke-inputs '{"text":"hi"}'
# 导入默认带重名去重守卫：现网已存在同名 app 时 block（列出 existing app_id）；确需重复用 --allow-duplicate。
# 排查现网重复：difyctl registry audit 的 duplicate_names 段列出同名 app 分组。

# 3b) 渐进式：原地更新已有 app（不产生副本）
difyctl dsl export --app-id <app_id> --output cur.dify.yml   # 拉当前线上 DSL
difyctl dsl diff --app-id <app_id> --dsl new.dify.yml        # 推送前预览差异
difyctl dsl import --dsl new.dify.yml --via api --app-id <app_id>   # 原地更新（同 app_id，无副本）
difyctl dsl import --dsl new.dify.yml --via api --update-if-exists  # 或按同名自动定位单个 app 更新
difyctl app publish --app-id <app_id>                        # workflow/advanced-chat 更新后需 publish 才能 /v1 run
difyctl dsl lint --dsl new.dify.yml                          # 推送前静态检查：硬编码密钥/悬空变量/空模型
difyctl dsl retarget --dsl new.dify.yml --provider <p> --model <m>  # 批量改绑模型
difyctl dsl apply --dir ./dify-apps --dry-run                # 声明式：目录 DSL 幂等同步（新建/原地更新/歧义跳过）
difyctl dsl apply --dir ./dify-apps --publish                # 执行同步并发布

# 3c) 长期治理：台账回填 + 重复清理
difyctl registry sync --dry-run          # 预览把未登记的线上 app 回填进台账（分页全量）
difyctl registry sync                     # 执行回填
difyctl registry prune-duplicates         # dry-run：列出同名冗余 app 的删除计划（保留最新）
difyctl registry prune-duplicates --apply # 执行删除（破坏性，保留 --keep newest/oldest 之一）

# 3d) 知识库（RAG 数据集）+ 全量备份
difyctl dataset list                                   # 列出所有知识库（分页全量）
difyctl dataset list --name 营销                        # 按名称子串过滤
difyctl dataset documents --dataset-id <id>            # 某知识库的文档列表
difyctl dataset create --name "KB" --indexing-technique high_quality   # 建库（high_quality 需 embedding 模型）
difyctl dataset add-doc --dataset-id <id> --name doc --text "..."      # 加文本文档（/v1 + 自动取 dataset key）
difyctl dataset add-doc --dataset-id <id> --name doc --file ./a.md     # 或从文件读入
difyctl dataset delete --dataset-id <id> --yes         # 删库（破坏性，需 --yes）
difyctl app annotations --app-id <id>                  # 列出 app 标注（问答缓存）
difyctl dsl export --all --output-dir ./dify-backup    # 全量备份每个 app 的 DSL（灾备）

# 输出约定：stdout 恒为纯 JSON（可直接管道消费）；人类可读的错误/告警走 stderr。全局 --quiet 静默 stderr、--verbose 追踪、-q 简写。

# 4) 运维车队
difyctl app rename --app-id <app_id> --name "New Name"    # Console PUT + 同步 ledger
difyctl app delete --app-id <app_id>                       # Console 删除 + ledger status→deprecated
difyctl registry audit                                     # live apps vs ledger：僵尸/未登记/漂移

# 5) /v1 运行时全覆盖（0.8.0，均用 app-* service token）
difyctl app run --app-id <id> --mode agent-chat --query "你好" --stream   # 强制流式聚合
difyctl app run-status --app-id <id> --run-id <workflow_run_id>           # 运行明细/状态
difyctl app stop --app-id <id> --task-id <task_id> --user <u>            # 中止流式任务
difyctl app upload --app-id <id> --file ./a.png --user <u>               # 文件/图片输入
difyctl app logs --app-id <id> --limit 20                                 # 运行日志/审计
difyctl app conversations --app-id <id> --user <u>                        # 会话列表
difyctl app messages --app-id <id> --conversation-id <cid> --user <u>     # 会话消息
difyctl app conversation-rename --app-id <id> --conversation-id <cid> --name "X" --user <u>
difyctl app conversation-delete --app-id <id> --conversation-id <cid> --user <u>
difyctl app feedback --app-id <id> --message-id <mid> --rating like --user <u>   # 点赞/踩
difyctl app suggested --app-id <id> --message-id <mid> --user <u>         # 追问建议
difyctl app audio-to-text --app-id <id> --file ./a.wav --user <u>         # 语音转文字
difyctl app text-to-audio --app-id <id> --text "你好" --output ./o.mp3 --user <u>  # 文字转语音
```

**安全红线**：完整 `app-*` token 只存本地 `~/.harness-ai-kit/config.yaml`（app_keys 映射，禁入 Git）；`app keys create` 完整 token 仅一次性打印，其余输出与 ledger 一律掩码（prefix+`****`）。key 解析优先级：`--app-key` > config.yaml app_keys[app_id] > app_api_key。

## 配置上下文

本技能依赖以下配置，AI 在运行时按如下优先级解析：

1. 用户对话中明确提供的值（最高优先级）
2. `~/.harness-ai-kit/config.yaml` 中 `assets.difyctl`（配套 CLI 配置段）或 `global` 段
3. `config.defaults.yaml` 中的默认值

如用户未提供且无默认值的 required 字段，**必须主动询问用户**。
禁止从 AGENTS.md 或脚本中读取硬编码配置值。

## 推荐输出格式

执行完毕后按以下结构输出：

**状态**：✅ / ⚠️ / ❌

| 资源ID | 类型(app/workflow/chatflow) | 动作(init/capture/reconcile/validate) | DSL 快照 / live 校验结果 |
|--------|----------------------------|--------------------------------------|------------------------|

（漂移排查场景补充四层事实源对照：live app / Studio asset / local registry / local DSL 的一致性结论；生产救援场景注明 published workflow、apps.workflow_id、健康/异常双验证是否通过。）

## 约束

- 这个 Skill 不负责 Docker、Compose、Nginx、容器启停与 Dify 升级。
- 优先把 Dify 资源沉淀为项目内可跟踪文件，而不是只留在 Dify UI 中。
- 公开稳定的使用层入口先以 app API key 与导出 DSL 为主，不默认依赖不稳定的控制台私有接口。
- 数据库直修只作为 break-glass 救援手段，不作为常规导入、发布或编辑路径。
- 当前已对齐中文 Dify Studio 登录页与 `/apps` -> `创建空白应用` / `导入 DSL 文件` / `更多 -> 导出 DSL / 复制 / 编辑信息` 流程。
- 新资源命名应稳定、可检索、可长期复用，不要使用一次性临时名称。
- 不要把本地 `drafts/*`、历史 snapshot 名称或 `.env` 中的展示名，直接当成现网 app 事实；涉及展示层问题时必须再做 live app 校验。

## 命令约定

初始化本地配置：

```bash
difyctl config init --base-url https://dify.example.com --workspace-dir ./fleet-platform/resources/dify
```

推荐最小环境变量：

```bash
DIFY_BASE_URL=https://dify.example.com
DIFY_STUDIO_USERNAME=you@example.com
DIFY_STUDIO_PASSWORD=your-password
```

远端检查解析顺序：

1. 显式命令参数 `--base-url` / `--app-api-key`
2. `difyctl` 已保存配置
3. 环境变量 `DIFY_BASE_URL`
4. `workspace_dir` 附近 `.env` 中的 `DIFY_BASE_URL`、`DIFY_API_KEY` 或 `DIFY_APP_API_KEY`

若 `DIFY_BASE_URL` 以 `/v1` 结尾，CLI 会自动收口到站点根地址。

检查 readiness：

```bash
difyctl doctor
```

远端 app 检查：

```bash
difyctl app info
difyctl app parameters
difyctl app meta
```

命名或描述漂移校验：

```bash
difyctl app info
difyctl reconcile diff-only sales-intake
difyctl reconcile show sales-intake
difyctl registry show sales-intake
difyctl resource show sales-intake
```

本地资源沉淀：

```bash
difyctl resource init my-workflow --mode workflow --title "My Workflow" --dsl ./exports/my-workflow.yml
difyctl resource capture my-workflow --dsl ./exports/my-workflow-v2.yml --label exported-2026-05-11
difyctl resource list
difyctl resource show my-workflow
```

DSL 快速摘要：

```bash
difyctl dsl summarize ./exports/my-workflow.yml
```

资源清单与批量计划：

```bash
difyctl registry init
difyctl registry upsert sales-intake --mode workflow --title "Sales Intake" --tag sales --dsl-path resources/sales-intake/dsl/current.yml
difyctl batch plan --mode workflow --tag sales
```

从零生成 workflow 草稿：

```bash
difyctl workflow-create intake --name "Sales Intake" --mode workflow --goal "Triage inbound leads" --input lead_text --output final_reply --step "Classify intent" --step "Generate reply" --spec-out ./specs/sales-intake.yml
difyctl workflow-create validate-spec --spec ./specs/sales-intake.yml
difyctl workflow-create scaffold --spec ./specs/sales-intake.yml --output ./drafts/sales-intake.dify.yml
```

Studio 操作计划：

```bash
difyctl studio create-plan --name "Sales Intake" --mode workflow --dsl ./drafts/sales-intake.dify.yml
difyctl studio export-plan sales-intake
difyctl studio duplicate-plan sales-intake
```

浏览器自动化入口：

```bash
difyctl studio browser-doctor
difyctl studio import-dsl-run --dsl ./drafts/sales-intake.dify.yml --headed
```

生产验收建议：

```bash
curl -X POST "$DIFY_BASE_URL/v1/workflows/run" \
  -H "Authorization: Bearer $DIFY_APP_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": {
      "snapshot_json": "{\"summary\":{\"overall_status\":\"healthy\"},\"hosts\":[],\"containers\":[],\"entrypoints\":[],\"alerts\":[],\"links\":[]}",
      "period_label": "2026-05-12",
      "audience": "ops-oncall",
      "language": "zh-CN"
    },
    "response_mode": "blocking",
    "user": "smoke-test"
  }'
```

## 示例

示例 1：刚从 Dify 导出一个 workflow DSL，想立即沉淀

1. `difyctl resource init sales-intake --mode workflow --title "Sales Intake" --dsl ./exports/sales-intake.yml`
2. 确认 `resource.json`、`dsl/current.yml` 与首个 snapshot 已生成
3. 后续版本继续用 `capture` 累积快照

示例 2：想先看当前 app 的运行参数

1. 配置 `base_url` 与 `app_api_key`
2. 运行 `difyctl app parameters`
3. 把结果作为后续资源整理和比对依据

示例 3：从业务需求直接起一个 workflow 草稿

1. 用 `workflow-create intake` 生成结构化 spec
2. 用 `validate-spec` 校验 spec
3. 用 `scaffold` 生成 starter DSL
4. 再进入 `resource init / capture` 与后续 Studio 导入流程

示例 4：对已登记资源生成 Dify Studio 操作计划

1. 先确认该资源已存在于 `resources.yml`
2. 运行 `difyctl studio export-plan sales-intake`
3. 按计划把导出的 DSL 回填到本地资源目录

示例 5：导入后的 workflow 在 Dify 1.13.x 中无法运行

1. 先用 app API 做黑盒调用，记录它卡在鉴权、参数校验、graph 校验还是节点执行
2. 对照一个正常 app，检查 draft / published workflow、`apps.workflow_id` 和 app token 是否齐全
3. 若报 `VariableEntity`、`EndNodeData` 或 `LLMNodeData` 校验错误，优先按当前原生 schema 重建 graph
4. 修复后至少跑一条健康样例和一条异常样例，再确认 `workflow_runs` 已 `succeeded`

示例 6：本地 registry 已改名，但 Studio 页面仍显示旧名称

1. 先运行 `difyctl app info`，确认 live app 当前 `name` 和 `description`
2. 再核对 `resources.yml`、`resource.json` 和 `dsl/current.*` 是否已经切到新语义
3. 若确认只是 Studio asset 漂移，再执行 `studio edit-info-run`
4. 修改完成后重新做一次 live app 校验，不要只看 Studio 页面标题

示例 7：新开会话时想先快速确认是否存在漂移

1. 先运行 `difyctl reconcile diff-only sales-intake`
2. 若只有 live app 网络错误，优先切到内网可达环境复核
3. 若存在 `observations`，再运行 `difyctl reconcile show sales-intake` 看完整上下文

## 给 LLM 应用加"联网搜索/工具"能力（Dify 1.x 插件版）

**关键事实**：Dify 的 **LLM 节点本身没有内置"联网搜索"开关**。联网搜索通过**工具（1.x 里是插件）**提供，两种接法：

- **Agent 应用 / Agent 节点**：把搜索工具挂到 Agent，由模型自主决定何时搜（依赖模型 function-calling 能力，不够确定）。
- **Chatflow/Workflow 的 Tool 节点**（推荐，确定性）：显式放一个搜索 Tool 节点在 LLM 节点前，把检索结果通过 `context` 拼进 LLM 上下文。不依赖模型 tool-calling，最稳。

**可用 web-search 工具（本实例，`GET /console/api/workspaces/current/tools/builtin` 探测）**：

| 工具 | provider（1.x 全名）| tool_name | 授权/密钥 |
|------|--------------------|-----------|-----------|
| Wikipedia | `langgenius/wikipedia/wikipedia` | `wikipedia_search`（query+language 必填）| 已授权·免密钥·**稳定** |
| DuckDuckGo | `langgenius/duckduckgo/duckduckgo` | `ddgo_search`（query 必填，max_results 必填）| 已授权·免密钥·**免费端点常被限流(202 Ratelimit)** |
| Tavily | `langgenius/tavily/tavily` | tavily search | 已授权·**需 key**·生产推荐 |
| Google/Bing/SearchApi/Brave/Jina | 对应插件 | — | **需各自 API key** |

**工具节点 DSL 关键 schema（1.x，workflow.graph.nodes[].data）**：

```yaml
type: tool
provider_id: langgenius/wikipedia/wikipedia      # 与 provider_name 一致，用插件全名
provider_name: langgenius/wikipedia/wikipedia
provider_type: builtin
tool_name: wikipedia_search
tool_configurations: {}                           # provider 级配置（proxy 等）
tool_parameters:
  query:    {type: mixed,    value: "{{#<start_node_id>.query#}}"}   # 变量引用
  language: {type: constant, value: zh}                              # 常量
retry_config: {max_retries: 2, retry_enabled: true, retry_interval: 1000}
```

LLM 节点消费工具输出：`context.enabled: true` + `context.variable_selector: [<tool_node_id>, "text"]`，prompt 里引用 `{{#<tool_node_id>.text#}}`。节点外壳统一 `type: custom`，真实类型在 `data.type`。

**CLI 一键运维闭环（已真机验证 GREEN）**：

```bash
# 1) 作者一个 start -> tool(wikipedia_search) -> llm(ollama) -> end 的 workflow DSL（见上 schema）
# 2) 导入(带重名去重) + 建 key
difyctl dsl import --dsl websearch.dify.yml --via api --resource-id web-search-pilot-wiki --create-key
# 3) 发布（workflow 必须 publish 才能 /v1 run）
difyctl app publish --app-id <app_id>
# 4) 试点跑通：联网检索 -> LLM 汇总
difyctl app run --app-id <app_id> --mode workflow --inputs @q.json   # q.json: {"query":"..."}
# 排错：run_status=failed 时看 error（如 DuckDuckGo 202 Ratelimit 即免费端点限流，非配置错误）
```

**踩坑与选型**：DuckDuckGo 免费端点在服务器 IP 上常返回 `202 Ratelimit`（节点结构正确、确实发起了真实搜索，但被限流）；生产联网搜索优先 **Tavily / SearchApi（配 key）** 或给 DDG 配 `proxy_server`。零成本试点/演示用 **Wikipedia** 最稳（`wikipedia_search`，免密钥、无限流）。

### Tool 节点参数放置（关键坑，已真机踩过 3 次）

- **运行时输入**（`form: llm`，如 `query`）→ 放 `tool_parameters`，**必须包裹** `{type: mixed|variable|constant, value: ...}`。
- **静态配置项**（`form: form`，如 `max_results`/`search_depth`/`include_answer`）→ 放 `tool_configurations`，**用原始值、不要包裹**（写成 `{max_results: 5, include_answer: "advanced"}`；写成 `{type:constant,value:...}` 会报 `value {...} not in options`）。
- **`select` 型但默认值是布尔**的配置项（Tavily 的 `include_answer`/`include_raw_content`）**必须显式赋一个合法字符串选项**（如 `include_answer: "advanced"`、`include_raw_content: "false"`），否则默认 `False` 触发 `value False not in options`。

### 本实例 web-search 现状（探测结论，随时可复查）

- **Tavily 已授权且已配 key**（`tavily_api_key: <set>`），5 个工具 `tavily_search/tavily_extract/tavily_crawl/tavily_map/tavily_research` → **search+read 开箱即用**，已真机 GREEN（`tavily_search`→LLM 返回带来源 URL 的实时答案）。生产联网搜索首选它。
- **SearXNG 插件未安装**（无 provider）：自托管要先装 marketplace 插件 + 部署 SearXNG 容器 + 配 base_url + 上游引擎国际出口代理。
- **Firecrawl 插件在册但未配**（`base_url`/`api_key` 空）：需云端 key 或自托管 `base_url`；旧 app 里 `provider_id: firecrawl` 短名是遗留写法，新建用插件全名 `langgenius/firecrawl/firecrawl`。

### 自托管 SearXNG + Firecrawl 接入（已真机 GREEN）

**CLI/API 授权 tool provider**（difyctl 暂无此命令，走 Console API）：
```
POST /console/api/workspaces/current/tool-provider/builtin/<provider>/add
body: {"credentials": {...}, "type": "api-key", "name": "self-hosted"}
```
- **坑**：该接口常返回 400 `Cannot release a lock that's no longer owned`，但**凭据其实已保存**——以 `GET tools/builtin` 的 `is_team_authorization=True` 为准，**别盲目重试**（会建重复凭据）。

**SearXNG**（`langgenius/searxng/searxng`，cred 字段 `searxng_base_url`，免密钥）：
- 搜索工具 `searxng_search`：`query`(llm) + `search_type`(form，**必填**，options: general/images/videos/news/map/music/it/science/files/social_media) + `time_range`(form,可选)。
- **关键坑**：SearXNG 节点结果只在 **`json`**（array[object]，含 title/url/content）里，**`text` 为空**！prompt 必须引用 `{{#节点.json#}}`（非 `text`），context 关掉或指 json。真机 GREEN：MCP 查询→9501 tokens、带来源 URL。
- 直连自检：`GET http://<searxng>/search?q=...&format=json` 返回 `results[]` + `unresponsive_engines`（本实例 google cse+duckduckgo 正常、brave 挂）。

**Firecrawl**（`langgenius/firecrawl/firecrawl`，creds `base_url`+`firecrawl_api_key`，自托管 key 任意非空）：
- `scrape`：`url`(llm) + `formats`/`onlyMainContent`/`timeout`(form)。输出走 `text`（与 SearXNG 不同）。真机 GREEN：抓 runoob 页→摘要。

### 联网搜索 workflow spec 模板库（一键脚手架）

技能自带 3 个可直接脚手架的 spec（`references/specs/`），`difyctl workflow-create scaffold --spec <spec> --output x.dify.yml` 一键生成 DSL：

| spec | 拓扑 | 特点 | 适用 |
|------|------|------|------|
| `web-search-searxng.spec.yml` | `start→tool(SearXNG)→llm→end` | 自托管、快、无需 sandbox（json 含 content 摘要）| 多数联网问答 |
| `web-search-tavily.spec.yml` | `start→tool(Tavily)→llm→end` | 托管兜底、结果已 LLM 清洗、带来源 | 快速接入/无自托管时 |
| `deep-research-websearch.spec.yml` | `start→tool(SearXNG)→template(取URL)→tool(Firecrawl)→llm→end` | 两段式、读全文、最扎实（50-73s）| 深研/需全文落地引用 |

均真机验证 scaffold→import→run 全绿。导入+运行通用流程：
```bash
difyctl workflow-create scaffold --spec <skill>/references/specs/<spec>.spec.yml --output x.dify.yml
difyctl dsl import --dsl x.dify.yml --via api --resource-id <rid> --create-key
difyctl app publish --app-id <id>
difyctl app run --app-id <id> --mode workflow --inputs '{"query":"..."}'
```
注意各自的输出变量与参数坑（SearXNG 在 `json` 非 `text`；Tavily `include_answer` 等 select-with-bool-default 必须显式赋合法字符串；工具节点静态配置进 `tool_configurations` 原始值、运行时输入进 `tool_parameters` 包裹）。

### 两段式深研（SearXNG搜索→取URL→Firecrawl读→LLM）—— 已真机 GREEN

- **一键脚手架（推荐）**：技能自带 spec `references/specs/deep-research-websearch.spec.yml`，直接生成两段式 DSL：
  ```bash
  difyctl workflow-create scaffold --spec <skill>/references/specs/deep-research-websearch.spec.yml --output dr.dify.yml
  difyctl dsl validate dr.dify.yml
  difyctl dsl import --dsl dr.dify.yml --via api --resource-id deep-research-websearch --create-key
  difyctl app publish --app-id <id>
  difyctl app run --app-id <id> --mode workflow --inputs '{"query":"..."}'
  ```
  `workflow-create scaffold`（difyctl 0.13.0+）支持 `tool` step 与跨节点引用重映射：spec 里用稳定 step-id（`start`/`searxng`/`pick_url`/…）互引 `{{#id.field#}}` 与 `value_selector`，scaffold 自动改写为生成的 node-id。
- 拓扑：`start → searxng_search → 取首条url(template-transform) → firecrawl scrape → llm → end`。取 URL 也可用 **Code 节点**（`def main(arg1)->{"url":...}`）。
- **依赖 dify-sandbox**：Code 与 Template-Transform 节点都在 `dify-sandbox` 里执行；曾遇 `-500 fork/exec /usr/local/bin/python3`（sandbox 缺 python3，拖垮所有含 Code/Template 的 workflow），修复 sandbox 后恢复。
- **超时**：全链 50-65s；difyctl 默认超时已调到 **120s**（0.12.2+），或 `app run --timeout` 单次覆盖。真机 GREEN：56-73s、带来源 URL。
- 规避：单段 `SearXNG→LLM`（json 已含 content 摘要）无需 sandbox、更快，适合多数问答；两段式用于需要读全文的深研。


## 参考文档

- [REFERENCE-DSL-AUTHORING.md](references/REFERENCE-DSL-AUTHORING.md)
- [REFERENCE-DSL-GOTCHAS.md](references/REFERENCE-DSL-GOTCHAS.md)
