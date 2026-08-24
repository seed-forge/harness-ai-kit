# Changelog

## 0.2.5 - 2026-08-20
- 环境值占位符抽取：组织内部集群 IP/域名改为 {<host>_host}/{<host>_host}/{<host>_host}/{base_domain}/{service_domain}/{root_domain} config 占位符（docs/config-governance.md §12）

## 0.2.4 - 2026-08-17

- 配套 ragflowctl 0.5.0（依赖升至 >=0.5.0）：新增 chat（dataset-backed 问答助手）/ agent（画布智能体 create+ask）/ graph（GraphRAG/RAPTOR run-trace）/ chunk（含 expand 邻块上下文）四命令组与 HD 确认门（delete 类默认交互确认，--yes 跳过，EOF fail-closed）。
- 新增 references/REFERENCE-PARSER-CONFIG.md：parser_config 全参数（v0.26.4 实测 schema）+ 14 种 chunk method×场景矩阵 + 场景推荐配置 + 修改路径；SKILL.md 参考文档链接补齐（validate ref_link 要求）。

## 0.2.3 - 2026-08-16

- 能力地图 §3 分工补第三形态：自研代码 agent（LangGraph/自研框架）经 `POST /api/v1/retrieval` 把 RAGFlow 当检索后端（hybrid+rerank 一站式，`ragflowctl retrieval` 可作接入冒烟/回归工具）；补「画布表达不了的状态机才走自研代码」选型判断。

## 0.2.2 - 2026-08-16

- 新增 references/REFERENCE-RAGFLOW-AGENT-AND-ALGORITHMS.md（能力地图）：v0.26 agent 编排引擎（21 组件/25 内置模板含 deep_research）、Agent DSL 编写要点、RAG 算法速查（GraphRAG/RAPTOR/hybrid/VLM/parent_child）、三级召回方法论与入库纪律、与 Dify 分工选型、ragflowctl 扩展 backlog（RAPTOR-GraphRAG run-trace / chat sessions / agent CRUD / connector / embed / system）。SKILL.md 补「能力地图」指引段。
- 借鉴致谢（practice-first 研读未整体引入）：LunarCache/ragflow-skill（DSL 要点与命令全景）、cclyfblink/ragflow_skill-zhlx（召回方法论与入库纪律）。
- 评估未采纳：LiuChenyangSHU/ragflow-kb-skill — 极简 chat 查询，对已有 ragflowctl chat/retrieval 能力无增量。

## 0.2.1 - 2026-08-14

- frontmatter 规范化：SKILL.md 统一 LF / 无 BOM / 单一 YAML frontmatter 块，修复 AI IDE 加载告警（missing YAML frontmatter delimited by ---）。
## 0.2.0 - 2026-08-11

- 新增「模型治理」章节：v0.26 三级模型体系（provider/instance/model）全量经 `ragflowctl llm` 命令组操作（依赖 ragflowctl >=0.3.0）。
- 明确存量知识库 embedding 重绑方法（`dataset set-embedding`，同模型换后端无需重建索引）与 newapi 统一入口口径。

## 0.1.2 - 2026-08-06

- 治理清欠：结构合规修复后版本抬升（changelog_drift、changelog_entry、ref_link、refs）。

## 0.1.1 - 2026-08-06

- 治理清欠：补齐伴生文档与结构合规（validate 存量债务清理）。

## 0.1.0

- 初始发布：新增 RAGFlow 平台运维 Skill。
