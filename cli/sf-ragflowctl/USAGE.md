# ragflowctl 用法

RAGFlow day-2 运维 CLI：dataset/document/ingest/retrieval + v0.26 模型治理（llm）+ 知识库半径智能体（chat/agent/graph/chunk）。
配置来源：`~/.harness-ai-kit/config.yaml` → `assets.ragflowctl`（`base_url`、`api_key`）。

## 健康检查与知识库

```bash
ragflowctl doctor                          # 认证体检（连通 + token 有效）
ragflowctl dataset list                    # 知识库清单（id/name/docs/chunks）
ragflowctl dataset create --name <名称>     # 建库（默认继承租户默认 embedding）
ragflowctl dataset rm --dataset <id|名称> [--yes]   # 删库（HD 确认门，逗号分隔多个）
ragflowctl retrieval --dataset <id|名称> --question "..." --top-k 8
```

## 文档与解析

```bash
ragflowctl document list --dataset <id|名称>
ragflowctl document upload --dataset <id|名称> <file...>
ragflowctl document parse --dataset <id|名称> [--all | --doc <id>]
ragflowctl ingest --dataset <名称> --dir <目录> [--create] [--glob "*.md"] [--no-parse]
```

## 知识库半径智能体（0.5.0 新增）

```bash
# chat assistant（带知识库的持续问答）：list / create --name X --dataset <ids> / ask --chat <id> --question "..." [--session]
ragflowctl chat list|create|sessions|new-session|ask|delete   # ask 非流式，省略 session 自动新建；delete 需 HD 确认
# canvas agent（deep_research 等模板）：templates 列 26 内置模板；create --title X --dsl @file（按 title 反查 id）
ragflowctl agent list|templates|create|sessions|new-session|ask|delete
# GraphRAG / RAPTOR 任务（走 /datasets/{id}/index?type=graph|raptor）
ragflowctl graph run-graphrag|trace-graphrag|run-raptor|trace-raptor --dataset <id|名称>
# chunk 级操作（三级召回支撑）：expand=±N 邻块上下文
ragflowctl chunk list|add|update|expand|delete --dataset <id|名称> --doc <doc_id> [--chunk <id>] [--content "..."]
```

## 模型治理（llm 命令组，v0.26 模型体系）

```bash
ragflowctl llm providers|factories|models|default   # 只读盘点（models 需 --provider/--instance）
ragflowctl llm remote-models --provider OpenAI-API-Compatible --api-key <k> --base-url <url>  # 远端可拉模型
ragflowctl llm add-instance --provider OpenAI-API-Compatible --name newapi --api-key <k> --models bge-m3:embedding
ragflowctl llm add-model --provider OpenAI-API-Compatible --instance newapi --name mimo-v2.5-pro --type chat
ragflowctl llm set-default --provider OpenAI-API-Compatible --instance newapi --model mimo-v2.5-pro --type chat  # --type 可重复
ragflowctl llm remove-provider --provider Ollama   # 连实例/模型一起删
```

## 关键约束与坑

- **HD 确认门（0.5.0）**：所有 delete/rm 类命令默认要求交互输入 `yes`；脚本显式 `--yes` 跳过；非交互 stdin（EOF）fail-closed。
- **`--json` 是全局参数，必须放子命令前**：`ragflowctl --json document list ...`。
- **中文库名传参**：PowerShell 传中文 argv 有 GBK 编码风险，脚本里优先用 id（ASCII）。
- list 端点服务端返回包装结构（`{chats|canvas|sessions:[...],total}`），CLI 已归一化为裸列表。
- GraphRAG/RAPTOR 的 deprecated run_*/trace_* 路径在 API token 下报 code=102，必须用 `/index?type=`。
- agent create 成功只返回 `true`（不回新 id），CLI 自动按 title 反查。
- **`--api-key`/`--base-url` 在 `llm` 子命令里指「被配置 provider 的」凭据**（dest 已隔离），顶部全局参数才是 RAGFlow 自身的。
- `add-instance --models` 至少给一个 `name:type`（服务端创建时强制探测）。
- `add-model --type asr/vision` 映射为内部类型 `speech2text/image2text`。
- `set-default` 模型引用格式 `model@instance@provider`（三段）；两段式按「唯一 active 实例」回退。
- `/datasets`、`/documents` 的 `page_size` 服务端封顶 100（#15292），CLI 已适配。
- 重绑 embedding（`dataset set-embedding`）只换服务后端引用：**同模型换 provider 向量兼容免重建，换模型必须重建**。
- 模型消费选型统一走任一 OpenAI 兼容网关（provider=`OpenAI-API-Compatible`）。

## 可直接复制的中文 Prompt

```text
请使用 ragflowctl 技能，按照其 SKILL.md 描述的标准流程执行任务；
先做 dry-run/检查，向我展示结果与风险，经确认后再正式执行。
```
