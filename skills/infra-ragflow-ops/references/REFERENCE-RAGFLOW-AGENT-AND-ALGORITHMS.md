# RAGFlow v0.26 能力地图：Agent 编排引擎 + RAG 算法速查

> 定位纠偏（2026-08-16）：RAGFlow 不只是「知识库 RAG 服务」。v0.26 起它是 **RAG-native 智能体平台**：
> 知识库解析/检索是原生底座，`agent` 模块提供完整 DAG 编排引擎（画布 + 组件 + 沙箱 + 内置模板）。
> 本文是 infra-ragflow-ops 的能力参考底账，源码实证于 <host> v0.26.4 容器（`/ragflow/agent/`）。
>
> 借鉴致谢（practice-first 研读，部分采纳）：
> - [LunarCache/ragflow-skill](https://github.com/LunarCache/ragflow-skill)（v0.26.4 命令面全景 + AGENT_GUIDE）→ 采纳：§1.4 DSL 要点、§4 backlog
> - [cclyfblink/ragflow_skill-zhlx](https://github.com/cclyfblink/ragflow_skill-zhlx)（知识库查询/入库纪律）→ 采纳：§2.1 三级召回、§2.2 入库纪律

## 1. Agent 编排引擎（内嵌智能体 pipeline）

### 组件清单（`agent/component/`，21 个，实测）

| 类别 | 组件 | 用途 |
|------|------|------|
| 交互 | begin / message / fillup | 会话入口、消息、表单收集 |
| 生成 | llm | LLM 生成（可接检索结果） |
| 路由 | categorize / switch | 意图分类、条件分支 |
| 循环 | loop / loopitem / exit_loop / iteration / iterationitem | 迭代与循环控制 |
| 数据操作 | variable_aggregator / variable_assigner / data_operations / list_operations / string_transform | 变量与列表处理 |
| 联网 | **browser** | 浏览器组件（联网检索/页面访问） |
| 文档 | excel_processor / docs_generator | Excel 处理、文档生成 |
| 智能体 | **agent_with_tools** | 带工具调用的 agent 节点（多工具编排） |
| 扩展 | invoke | 调用外部服务/组件 |

### 内置画布模板（`agent/templates/`，25 个，实测）

- **deep_research.json**：深度研究——多轮检索 → 联网 → 交叉核实 → 综述报告，**「交叉联网核实 + 总结」的现成范式**，改知识库与模型即可用。
- **web_search_assistant.json**：联网搜索助手。
- **ingestion_pipeline_*.json**（9 个）：book/general/laws/manual/one/paper/resume 等文档类型的摄入管线（v0.26 把 chunk/解析也管线化了）。
- 业务类：text2sql_data_expert / stock_market_research_assistant / seo_article_writer / market_seo_article_writer / trip_planner / smart_customer_service_specialist / customer_feedback_dispatcher / cv_analysis_and_candidate_evaluation / photo_text_translator / reflective_academic_paper_generator / chunk_summary / title_chunker / user_interaction / data_analysis_beginner_assistant / cajal_scientific_paper_agent / advanced_ingestion_pipeline。

### 「交叉联网核实 / 总结」怎么落

1. **拿来即用**：从 `deep_research` 模板建 agent，把 Retrieval 组件指向目标知识库，browser/搜索配好出口，LLM 组件用租户默认 chat 模型。
2. **自己组装**：Retrieval（知识库证据）→ browser（联网证据）→ LLM（对比核实 prompt：「证据一致不扣分 / 直接矛盾才 critical / 未覆盖仅 warning」，与 craft-gate 同纪律）→ 输出。
3. Code 组件（自定义 Python/JS 处理）需要 Sandbox，默认未启用——启用路径见 knowledge-cards `ragflow-v026-upgrade-pitfalls-L1.md` 坑 #13（当前 <host> 零消费者，按需开）。

### 1.4 手写/调试 Agent DSL 要点（借鉴 LunarCache AGENT_GUIDE）

不要从空 JSON 起手：从内置模板或最小示例改，只换 `llm_id`/`kb_ids`/凭据/prompt，保留运行时字段原样：

- 顶层必须同时含 `components`（运行时结构）与 `graph`（画布结构），**两边 node id 必须对齐**；另有 `history`/`path`/`retrieval`/`variables`/`globals`。
- `globals` 显式保留系统变量（`sys.query`/`sys.user_id`/`sys.conversation_turns`/`sys.files`/`sys.history`/`sys.date`）。
- 循环流必须 **Iteration + IterationItem 双组件**成对；工具调用型 agent 的工具挂在 `Agent.params.tools` 下。
- `create-agent` API 成功只返回 `true`（不回新 id），需按 title 反查；再 `create-agent-session` → `agent-chat`（默认流式，`--stream false` 取整包）。
- 深度参考：<https://github.com/LunarCache/ragflow-skill/blob/main/skill-for-ragflow/references/AGENT_GUIDE.md>（v0.26.4 DSL schema + 5 个最小示例 + 失败模式）。

## 2. RAG 算法速查（运维视角）

### 2.1 三级召回方法论（借鉴 zhlx）

把知识库查询当「远端文件检索」分级使用，避免只见孤立片段：

| 级别 | 类比 | 动作 | 适用 |
|------|------|------|------|
| 检索 | 远端 `rg` | `retrieval`（hybrid：vector+term） | 先找证据；低置信时放宽阈值或换 keyword 思路重查 |
| 上下文展开 | `rg -C` | 对关键 chunk 拉前后相邻 chunk | 引用前核实语义完整性 |
| 整篇通读 | 远端 `cat` | 按 document 拉全部已解析 chunk 合并文本 | 某文档被确认是核心来源后通读/核对多章节 |

纪律：先结论后来源；政策/标准按**原始发布主体**表述（知识库名≠发布主体）；未检索到明说「未检索到」，不编造；RAGFlow 结果与本地文件冲突时本地为实现事实、知识库为背景资料。

### 2.2 入库纪律（借鉴 zhlx）

- 文档名自带来源：`资料分类-年份-文件名.pdf` 式拼接，杜绝 `报告.pdf`/`扫描件.pdf` 这类无法溯源的名。
- 批量上传用 metadata 写资料说明：`source_path`/`content_description`/`topic`/`year`/`document_type`/`publisher`；不同主题的文件不共用同一段笼统描述。
- 分批入库：一个资料夹一批 → 解析完成 → 召回验证通过 → 再传下一批。
- 格式白名单 `pdf/doc/docx/xlsx/txt`（旧 `xls` 先转 `xlsx`）；跳过同名文档（默认去重）；大文件先限量试解析稳定再放宽。
- 上传前 dry-run 确认数量与跳过项。

### 2.3 算法参数速查

| 能力 | 说明 | 操作入口 |
|------|------|----------|
| chunk method | naive/paper/book/laws(law)/manual/resume/one/qa/table/picture/email/knowledge_graph 等，按文档类型选；枚举以 `dataset create --chunk-method` 与 UI 为准 | ragflowctl dataset create / UI |
| DeepDOC 版面解析 | `layout_recognize: DeepDOC`，PDF 版面/表格识别 | parser_config |
| **GraphRAG** | 实体关系图谱 + 社区报告（knowledge_graph chunk method + graphrag 配置段）；<host> 已有 2 个 GRAPH 库在用 | parser_config.graphrag |
| **RAPTOR** | 递归聚类摘要树，增强长文档检索 | parser_config.raptor（默认 on） |
| auto_keywords / auto_questions | chunk 级自动关键词/问题增强（耗 LLM token，默认 0） | parser_config |
| hybrid 检索 | vector + term 双路相似度，`vector_similarity_weight`（默认 0.3） | retrieval 参数 |
| rerank | 检索后重排（bge-reranker-v2-m3 已配默认） | retrieval 参数/租户默认模型 |
| **VLM 图片理解** | picture chunk method 用 img2txt 模型（grok-chat-fast 已配）描述图片入库；视频文件同走 VLM（VISUAL 类型） | 租户默认 img2txt |
| parent_child | 父子块（小块检索、大块喂 LLM） | parser_config.parent_child |
| tag | topn_tags 标签匹配增强 | parser_config |
| TOC 增强 | 目录结构增强长文档 | parser_config（toc_enhance） |

## 3. 与 Dify / 自研 agent 的分工（组织内部集群 选型纪律）

| 场景 | 放哪 | 理由 |
|------|------|------|
| 以知识库为中心的智能体（问答/深研/文档核实） | **RAGFlow Agent** | Retrieval 原生直连 dataset，DeepDOC/GraphRAG 质量底座，deep_research 现成 |
| 通用业务编排（内容工厂/外部集成/发布渠道） | **Dify workflow** | 现有 DSL 资产全部沉淀在 Dify（craft-share/gate/工厂） |
| **自研代码 agent（LangGraph/自研框架）** | **RAGFlow retrieval API 作检索后端** | `POST /api/v1/retrieval` 一站式 hybrid+rerank，免自建向量库/解析运维；`ragflowctl retrieval` 即该 API 的 CLI 封装，可作接入冒烟与回归工具 |
| 联网核查 | Dify craft-gate（已有） | 不重复建设；RAGFlow 侧仅做「面向知识库内容的核实/深研」 |
| 模型治理/消费 | 统一 newapi | 各平台/自研代码均经 `OpenAI-API-Compatible` 入口消费，模型台账归 infra-aimodel-ops |

**自研 agent 选型判断**：画布类（RAGFlow Agent / Dify）表达力覆盖不了的状态机——如 LangGraph 的 checkpoint 续跑、精细人机协同、复杂工具链与自研中间件——就走自研代码；此时 RAGFlow 退位为「检索后端」一类基础设施（与 ES/MinIO 同层），通过 retrieval API 消费，不要为用它而硬套画布。

**一句话**：RAGFlow 管「知识库半径内的智能体」并向外提供「检索后端即服务」；Dify 管「业务半径内的编排」；自研代码管「画布表达不了的状态机」；模型统一走 newapi，各自的能力 reference 各自沉淀。

## 4. ragflowctl 命令面：当前覆盖 vs 社区全景（扩展 backlog）

对照 LunarCache skill-for-ragflow 的命令全景，ragflowctl 0.4.x 已覆盖：doctor/probe、dataset CRUD+set-embedding、document list/upload/parse/delete、ingest、retrieval、llm 模型治理全组。

未覆盖（按价值排序的扩展候选，需要时再做）：

| 候选方向 | 价值场景 |
|----------|----------|
| RAPTOR / GraphRAG `run-*`/`trace-*`/`get-knowledge-graph` | 大库手动触发图构建/摘要树、任务追踪 |
| chat assistant / sessions（create-chat/session/chat-session） | 脚本化问答回归测试、批量评测 |
| agent CRUD + agent-session/agent-chat | deep_research 等模板 agent 的脚本化创建与调用（配合 §1.4） |
| connector 管理 | 外部源同步进知识库 |
| embed/system-token | 知识库嵌入外部站点 |
| system version/health/log-level | 巡检增强 |

原则：ragflowctl 只做 day-2 高频刚需，低频面先记录不实现；需要某方向时单独提版本实现。

## 5. 关联

- 运维操作：SKILL.md + `ragflowctl`（USAGE.md / REFERENCE-RAGFLOWCTL-CLI.md）
- 升级与排障经验：组织内部集群/knowledge-cards/ragflow-v026-upgrade-pitfalls-L1.md（坑 #1-#13）
- 模型消费台账：<host>/ai模型/模型笔记.md（RAGFlow 行）
