---
name: infra-ragflow-ops
description: RAGFlow 平台运维技能。凡是用户提到 RAGFlow、ragflowctl、知识库、dataset、RAGFlow 模型/向量库/对象存储依赖或 RAGFlow 健康检查时触发。
---

# infra-ragflow-ops

用于 RAGFlow 平台 day-2 运维。RAGFlow 是 AI/RAG 平台型应用，本轮作为基础设施纳入治理。

## 配置上下文

本技能依赖以下配置，AI 在运行时按如下优先级解析：

1. 用户对话中明确提供的值（最高优先级）
2. `~/.harness-ai-kit/config.yaml` 中 `assets.ragflowctl` 或 `global` 段
3. `config.defaults.yaml` 中的默认值

如用户未提供且无默认值的 required 字段，**必须主动询问用户**。
禁止从 AGENTS.md 或脚本中读取硬编码配置值。

| 配置项 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `ragflow_url` | string | ✅ | RAGFlow 服务 URL（默认 `http://<service-url>:11281`） |

配套 CLI：`ragflowctl`（配置来源：`~/.harness-ai-kit/config.yaml` → `assets.ragflowctl`）

## 边界

- 本 skill 负责：RAGFlow 服务健康、dataset/知识库 API 探活、模型/向量库/对象存储依赖检查、运行台账。
- 模型消费统一走任一 OpenAI 兼容网关（provider=`OpenAI-API-Compatible`）。
- 数据库/向量库/对象存储连接由你自有的数据源与对象存储（MinIO/S3）提供。


## 推荐输出格式

执行完毕后输出极简回执：**状态**（✅ 成功 / ⚠️ 部分成功 / ❌ 失败）+ **关键结果**（1-2 行，如操作对象、产出位置、下一步）。无需强制套用大表格。
## 操作顺序

1. 运行 `ragflowctl doctor --profile default --json`。
2. 检查依赖：模型 endpoint、数据库、向量库、对象存储。
3. 只读列 dataset/知识库，再评估是否需要变更。
4. 变更前输出 dry-run 计划。

## 模型治理（ragflowctl ≥0.3.0，v0.26 模型体系）

v0.26 起 RAGFlow 模型管理重构为 provider/instance/model 三级（`tenant_model_*` 表），一律经 `ragflowctl llm` 命令组操作，不开 UI、不手写 SQL：

- `llm providers|factories|models|remote-models|default`：只读盘点
- `llm add-instance --models <name:type>`：创建实例（服务端强制真实探测，--models 至少一项）
- `llm add-model`：追加模型（纯登记不探测；`--type asr/vision` 自动映射 `speech2text/image2text`）
- `llm set-default --type chat|embedding|rerank|asr|tts`：设租户默认模型（引用格式 `model@instance@provider`）
- `llm remove-provider`：连实例/模型整体删除
- `dataset set-embedding`：存量库 embedding 引用重绑（同模型换服务后端向量兼容，无需重建索引）

模型选型与消费统一走任一 OpenAI 兼容网关（provider=`OpenAI-API-Compatible`）。

## 能力地图（v0.26：不止是知识库 RAG）

v0.26 的 RAGFlow 是 **RAG-native 智能体平台**：知识库底座 + agent 编排引擎（21 组件 / 25 内置模板，含 deep_research 交叉核实综述、web_search_assistant、ingestion_pipeline 系列）。分工：知识库半径内智能体放 RAGFlow Agent，业务半径编排留 Dify，自研代码 agent（LangGraph 等）经 `POST /api/v1/retrieval` 把 RAGFlow 当检索后端（hybrid+rerank 一站式），模型统一走 newapi。RAG 算法（GraphRAG/RAPTOR/hybrid/VLM/parent_child）、三级召回方法论、入库纪律、ragflowctl 扩展 backlog 见参考文档。

参考文档：
- references/REFERENCE-RAGFLOW-AGENT-AND-ALGORITHMS.md（能力地图：agent 组件/模板、RAG 算法速查、召回与入库纪律、Dify/自研 agent 分工、扩展 backlog）
- references/REFERENCE-PARSER-CONFIG.md（parser_config 全参数 + chunk method×场景矩阵 + 场景推荐配置）
- references/REFERENCE-RAGFLOWCTL-CLI.md
