# 变更记录

## 0.5.1 - 2026-08-17

- 修 `chat ask` 误导性 code=109：`POST /chat/completions` 对「不存在/非本 token 所属的 chat_id（含误传 dataset id）」返回 `109 No authorization`，易误判为鉴权问题。CLI 现在预检 `--chat`（支持 id 或名称解析，同 `_dataset_id` 习惯），无效时给出明确指引（run `chat list`；--chat 要 chat 助手 id/name 非 dataset id）。`sessions`/`new-session`/`delete` 同步支持名称解析。

## 0.5.0 - 2026-08-17

- 新增四大命令组（知识库半径智能体，范围经用户确认）：
  - `chat`：list/create/sessions/new-session/ask（非流式）/delete——dataset-backed 持续问答助手，脚本化回归与评测基础。
  - `agent`：list/templates（26 个内置模板 i18n 标题展示）/create（--dsl @path，create 后按 title 反查 id）/sessions/new-session/ask/delete——画布智能体脚本化。
  - `graph`：run-graphrag/trace-graphrag/run-raptor/trace-raptor——走 `/datasets/{id}/index?type=graph|raptor` 新路径（deprecated run_*/trace_* 在 API token 下 code=102）。
  - `chunk`：list/add/update/expand（±N 邻块上下文，三级召回支撑）/delete。
- **HD 确认门**：全部 delete/rm 类命令（含存量 dataset rm / document delete）默认交互输入 `yes` 确认，`--yes` 跳过；非交互 stdin（EOF）fail-closed 拒绝。
- 兼容修复：list 端点包装结构归一化（`{chats|canvas|sessions:[...],total}` → 裸 list）；Windows GBK 控制台非 GBK 字符输出崩溃（stdout utf-8 reconfigure）。
- USAGE.md 补四命令组用法与关键约束（--json 位置、中文 argv 编码、HD 门、index?type 路径）。

## 0.4.1 - 2026-08-13

- DX 改善（消费者反馈，无功能变更）：为 `api_client` 的 `dataset_list`/`dataset_create`/`dataset_update`/`dataset_delete`/`dataset_find`/`document_list`/`retrieval` 补齐 docstring，明确返回形态——多数方法返回**已拆包的 `data`**（如 retrieval 的 `{chunks, doc_aggs, total}`、document_list 的 `{docs, total}`）；明确标注 `dataset_update`/`dataset_delete` 返回**完整响应包络**（成功已由 `_request` 的 code==0 检查保证，调用方通常忽略返回值）。
- 治理修复：`cli.json` 版本由 0.3.0 补正至与包一致（0.4.0 发布时漏 bump）。

## 0.4.0 - 2026-08-11

- 新增 `document delete` 子命令：按 `--doc`（可重复）/ `--name`（fnmatch 名称模式，如 `*.md`）/ `--failed`（清 run=FAIL 残档）/ `--all` 选择删除文档；对接 `DELETE /api/v1/datasets/{id}/documents`（body `{"ids":[...]}`）；无匹配时安全报错不误删。

## 0.3.0 - 2026-08-10

- 新增 `llm` 命令组对接 v0.26 模型治理 API（provider_api + models_api）：`providers` / `factories` / `verify` / `add-instance` / `add-model` / `models` / `remote-models` / `default` / `set-default`（租户默认模型）。
- v0.26 兼容修复：`/datasets` 与 `/documents` 的 `page_size` 由 200/500 降为 100（v0.26.0 起服务端封顶 100，#15292，否则报 code=101）。
- `list` 类命令默认输出明细行（`data` 中 name/id/status/type 等关键字段），遵循 harness-ai-kit CLI 增强候选标准。
- 实测认证：ragflow- API token 对 v0.26.4 `login_required` 端点（含 `/providers`、`/models/default`）有效。

## 0.2.0 - 2026-08-10

- 重构对接 RAGFlow v0.24 HTTP API（/api/v1，Bearer auth）：新增 `api_client.py` 纯标准库统一客户端（code==0 响应包络）。
- cli.py 命令面重写（datasets/documents/ingest/retrieval，+200/-68）。
- 新增 `data/config.defaults.yaml`（harness-ai-kit 配置治理规范：base_url/api_key 清单）并随 wheel 打包。

## 0.1.1 - 2026-08-06

- 治理清欠：结构合规修复后版本抬升（usage_missing）。

