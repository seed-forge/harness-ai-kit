# REFERENCE: Dify DSL 创作

> 面向 `difyctl workflow-create` / `dsl validate` / `dsl import`。规范事实源自 Dify 官方
> `api/services/app_dsl_service.py` 与 `api/constants/dsl_version.py`；节点模板与布局算法
> 改编自 MIT 许可的 yoloyolo8/dify-workflow-writer 与 LingyiChen-AI/workflow-skill。

## 版本策略

| Target | version | 能力 |
|--------|---------|------|
| Dify 1.13.x–1.15.x（当前生产） | `"0.6.0"` | Workflow / Chatflow / 传统 model-config / 传统 Agent 节点 |
| Dify 1.16.x | `"0.7.0"` | 以上 + 顶层 Agent App package + 可移植 Agent v2 节点 |

- `version` 必须是**带引号的字符串**。
- `difyctl` 默认产出 `"0.6.0"`（贴合当前 组织内部集群 Dify 1.13.x）。
- 不要仅改版本字符串来"升级"；0.7.0 的 Agent App 需要额外 package 结构（当前不生成）。

## 顶层结构

```yaml
app:
  name: "App name"
  mode: workflow            # workflow | advanced-chat | chat | completion | agent-chat | agent(0.7.0)
  icon: "🤖"
  icon_type: emoji
  icon_background: "#FFEAD5"
  description: "What it does"
  use_icon_as_answer_icon: false
kind: app
version: "0.6.0"
dependencies: []            # 每个引用的 marketplace/plugin 都要登记
workflow:
  environment_variables: []
  conversation_variables: []
  features: { ... }         # file_upload / tts / stt / opening_statement 等
  graph:
    nodes: [ ... ]
    edges: [ ... ]
    viewport: { x: 0, y: 0, zoom: 1 }
```

## 节点 wrapper 与 edge

- 节点外层 `type: custom`，运行时类型在 `data.type`；`custom-note` 不可执行。
- 节点带 `id`（13 位毫秒时间戳字符串，加引号，唯一）、`position{x,y}`、`width`/`height`。
- edge id 格式：`{sourceId}-{sourceHandle}-{targetId}-target`，`type: custom`，`data.sourceType`/`data.targetType` 必填。
- 普通节点出边 `sourceHandle: source`；if-else 用 case id 或 `false`；question-classifier 用 class id。

## 常用节点关键字段

| 节点 | data.type | 关键字段 |
|------|-----------|---------|
| Start | `start` | `variables[]`（variable/label/type=text-input/required/max_length/options） |
| End | `end` | `outputs[]`（variable + value_selector=[node_id, field]） |
| Answer（advanced-chat） | `answer` | `answer`（含 `{{#node.field#}}`） |
| LLM | `llm` | `model`/`prompt_template[]`/`context{enabled,variable_selector}`/`vision`/`retry_config{retry_enabled,max_retries,retry_interval}`/`error_strategy{type,default_value}` |
| Code | `code` | `code_language`/`code`/`variables[]`/`outputs{}`（每个返回字段都要声明） |
| HTTP Request | `http-request` | `method`/`url`/`headers`/`params`/`body`/`authorization`/`timeout`/`retry_config` |
| If/Else | `if-else` | `cases[]`（case_id/logical_operator/conditions[]） |
| Template Transform | `template-transform` | `template`（Jinja2）/`variables[]` |

- **LLM 节点即使不启用检索也必须带 `context: {enabled: false, variable_selector: []}`**（Dify 节点模型要求该对象）。
- 新建 workflow 默认 LLM 模型：`langgenius/deepseek/deepseek` / `deepseek-v4-flash`，`mode: chat`，`temperature: 0.1`。
- **`difyctl` scaffold 默认为 LLM 节点注入 `retry_config` 和 `error_strategy`**：
  - `retry_config`: `{retry_enabled: true, max_retries: 3, retry_interval: 1000}`（429/5xx/超时自动重试 3 次，间隔 1s）
  - `error_strategy`: `{type: default_value, default_value: ""}`（重试耗尽后输出空值，让下游继续而非崩溃）
  - newapi 侧已有 proxy 级重试 + 渠道 fallback；Dify 侧 retry 是第二道安全网，处理模型响应本身的异常
  - 传 `retry_config=None` 或 `error_strategy=None` 可禁用（仅限明确不需要的调试场景）

## 变量引用

- 语法：`{{#node_id.field#}}`（双 `#`）。
- 运行时 node-id 部分限 1–50 位字母/数字/下划线；`sys`/`env`/`conversation` 为系统前缀。
- selector 数组形如 `["node_id", "text"]`；`["node_id", "structured_output", "title"]` 指向结构化输出字段。

## 布局算法

- Start 起点 `{x: 80, y: 282}`；横向步进 300px（节点宽 244 + gap 56）。
- 并行分支纵向间隔 200px。
- `difyctl` 自动按 step 顺序分配 col，线性 workflow 直接左到右排布。

## 图约定（监控日报类场景）

- 优先 `start -> 单个 llm(structured_output) -> end`，不要串多个自由文本 LLM 再靠 end 兜底拆字段。
- `end.outputs` 直接映射上游 `structured_output` 字段。
- 提示词写死章节名、明确"只依据已有事实、空区块输出无数据"。
