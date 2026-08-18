# RAGFlow parser_config 全参数参考与 chunk method×场景矩阵

> 基线：<host> v0.26.4 实测 schema（`dataset create` 返回的完整 parser_config）。
> 定位：知识库建库/调优时的参数决策底账。chunk method 决定**解析管线**，parser_config 决定**增强算法开关**。

## 1. chunk method 场景矩阵

| chunk_method | 适用文档 | 管线行为 | 典型场景 |
|--------------|----------|----------|----------|
| `naive` | 通用文本（md/txt/docx/pdf） | 按 delimiter+chunk_token_num 切 | 绝大多数知识库（默认） |
| `paper` | 学术论文 PDF | 版面分栏识别、摘要/引用结构 | 论文库 |
| `book` | 长书稿 | 章节结构感知 | 书籍 |
| `laws` | 法律法规 | 条款（第 X 条）结构切分 | 法规库 |
| `manual` | 产品手册 | 小节结构 | 说明书 |
| `resume` | 简历 | 简历字段结构化 | HR 简历库 |
| `qa` | 问答对文档 | Q/A 成对切分 | FAQ 库 |
| `table` | 表格类（xlsx/csv） | 行级切分，表头保留 | 数据表 |
| `presentation` | PPT | 页级切分 | 幻灯片 |
| `picture` | 图片 | **VLM（img2txt）描述入库** | 截图/照片/扫描图 |
| `one` | 小文档 | 整篇一 chunk | 短通知/单页 |
| `email` | 邮件 | 邮件头+正文结构 | 邮件归档 |
| `knowledge_graph` | 任意（配合 GraphRAG） | 切分后实体关系抽取建图 | GRAPH 库（<host> 在用 2 个） |
| `tag` | 标签体系文档 | 按标签匹配增强 | 标签知识库 |

注意：**视频文件（mp4/avi/mkv/mov）归 VISUAL 类型走 VLM 路径**，无独立 chunk method；视频解析质量取决于 img2txt 模型（当前 grok-chat-fast）。

## 2. parser_config 全参数（v0.26.4 实测 schema）

### 2.1 通用切分

| 参数 | 默认 | 说明 |
|------|------|------|
| `chunk_token_num` | 512 | 单 chunk token 上限；法律/长叙述调大（1024），FAQ 调小 |
| `delimiter` | `\n` | 切分隔符 |
| `layout_recognize` | `DeepDOC` | 版面解析引擎（PDF 表格/分栏识别） |
| `html4excel` | false | xlsx 转 HTML 保留表格结构（table 场景建议 true） |
| `image_context_size` | 0 | 图片 chunk 携带的上下文窗口 |
| `table_context_size` | 0 | 表格 chunk 携带的上下文窗口 |

### 2.2 LLM 增强（都消耗 token，默认关）

| 参数 | 默认 | 说明 |
|------|------|------|
| `auto_keywords` | 0 | chunk 自动提取关键词条数（0=关；建议 3-5，提升 keyword 召回） |
| `auto_questions` | 0 | chunk 自动生成问题条数（0=关；FAQ 场景建议 2-3） |
| `topn_tags` | 3 | 标签匹配增强的标签数 |
| `llm_id` | 租户 chat 默认 | 增强任务专用模型（三段式引用；GraphRAG/auto_* 用它） |

### 2.3 RAPTOR（递归摘要树）

```json
"raptor": {"use_raptor": true, "max_cluster": 64, "max_token": 256, "threshold": 0.1, "random_seed": 0, "prompt": "..."}
```

- 长文档库建议开（默认 on）；小 FAQ 库可关省 token。
- 手动触发/追踪：`ragflowctl graph run-raptor|trace-raptor`。

### 2.4 GraphRAG（实体关系图谱）

| 参数 | 默认 | 说明 |
|------|------|------|
| `use_graphrag` | true | 总开关（chunk method=knowledge_graph 时才有意义） |
| `method` | `light` | light=轻量快速；general=全量（贵） |
| `entity_types` | organization/person/geo/event/category | 抽取实体类型，可按域裁剪（如加 product） |
| `batch_chunk_token_size` | 4096 | 抽取批大小 |
| `community_timeout_seconds` | 1800 | 社区报告生成超时（大库调大） |
| `build_subgraph_min_timeout_seconds` | 600 | 子图构建最短超时 |
| `merge_timeout_seconds` / `resolution_timeout_seconds` | 180 / 1800 | 实体合并/消解超时 |
| `retry_attempts` / `retry_backoff_seconds` / `retry_backoff_max_seconds` | 2 / 2.0 / 60 | 抽取重试 |
| `lock_acquire_timeout_seconds` | 600 | 并发锁等待 |

- 手动触发/追踪：`ragflowctl graph run-graphrag|trace-graphrag`。
- **成本警告**：GraphRAG 抽取耗 LLM token 与 chunks 成正比；15704 chunks 大库跑一次 general 图构建费用可观，先用 light 或子集试。

### 2.5 parent_child（父子块）

```json
"parent_child": {"use_parent_child": false, "children_delimiter": "\n"}
```

开启后小块（child）做检索命中、大块（parent）喂 LLM——长上下文保真场景（法律条文/技术规范）建议开。

### 2.6 TOC / 元数据

- `toc_enhance`（目录增强）：长书/规范开启，提升章节级定位。
- metadata 自定义字段（source_path/content_description/topic/year/document_type/publisher）经入库写入，检索可按 metadata-condition 过滤（见能力地图 §2.2 入库纪律）。

## 3. 场景推荐配置

| 场景 | chunk_method | 关键 parser_config |
|------|--------------|--------------------|
| 企业制度/常识库 | naive | chunk_token_num=512，auto_keywords=3，RAPTOR on |
| 技术规范/标准 | naive 或 laws | chunk_token_num=1024，parent_child on，TOC on |
| 论文/研报 | paper | layout_recognize=DeepDOC，RAPTOR on |
| 深研/图谱问答 | knowledge_graph | use_graphrag=true，method=light 起步，entity_types 按域裁剪 |
| FAQ/客服 | qa | chunk_token_num=256，auto_questions=2 |
| 数据表问答 | table | html4excel=true，table_context_size=2 |
| 截图/扫描件库 | picture | 租户 img2txt 已配（grok-chat-fast），image_context_size=1 |
| 营销2.0类业务库（<host> 现状） | naive + 姊妹 GRAPH 库 | 主库 naive，GRAPH 库 knowledge_graph（light） |

## 4. 修改路径

- 建库指定：`ragflowctl dataset create --name X --chunk-method <m>`（parser_config 细参数走 UI 或 API `PUT /datasets/{id}` 的 `parser_config` 字段）。
- 改库配置：`PUT /api/v1/datasets/{id}` body `{"parser_config": {...}}`（改后需对存量文档重跑 parse 生效）。
- 修改 chunk method 会触发**全库重解析**（不同于 set-embedding 的零重建）。
