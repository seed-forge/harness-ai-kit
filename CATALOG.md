# harness-ai-kit Asset Catalog

One-line descriptions of every skill, CLI, and plugin bundled in this repo.
Install any with `harness-ai-kit add skill <id>` (skills) or `pip install <pkg>` / `harness-ai-kit add cli <id>` (CLIs).

- **Skills: 56** across 8 categories
- **CLIs: 6** (pip-installable, published to PyPI as `sf-*`)
- **Plugins: 1** (AI-harness plugins)

> Build Less, Compose More — the **REMIX** methodology (Reuse · Extend · Mix · Integrate · eXecute): these assets compose open-source tools and community skills rather than reimplement them.

## Skills (56)

### Database & Middleware Expertise (11)

| Skill | Version | Description |
|-------|---------|-------------|
| `devlab-dao-sql-compat` | 0.4.4 | DAO 层通用 SQL 方言兼容性检查 + 系统性修复工作流。支持 MyBatis/JPA/MyBatis-Plus/SQLAlchemy 四种持久层框架，扫描源码识别 Oracle/PostgreSQL/MySQL 方言混用风险，自动修复 80% 常见陷阱，剩余 20% 由 Agent 辅助人工确认。七阶段流程 + adapter 模式框架适配。 |
| `devlab-db-data-migration` | 0.1.5 | Database data-layer safe migration: backup -> idempotent check -> migrate -> verify -> rollback. SQLite/MySQL dialect branches, rebuild-table path for constraint changes. Complements devlab-dao-sql-compat (syntax layer). |
| `public-git-workflow-expert-base` | 0.1.4 | Git 工作流知识基座：extends netresearch/git-workflow-skill 上游通用 Git 知识，叠加团队 commit 规范、分支策略、Gitea 工作流、CI/CD 集成、镜像同步经验。供下游技能通过 extends 继承。 |
| `public-kafka-expert-base` | 0.1.2 | Kafka 知识基座：Topics/Partitions、Consumer Groups、Producer Config、Serialization、Exactly-Once、Rebalancing。供 devlab-middleware-expert 通过 extends 继承。借鉴自 confluentinc/agent-skills。 |
| `public-mongodb-expert-base` | 0.1.2 | MongoDB 知识基座：Document Model、Aggregation Pipeline、Indexes、Replica Sets、Change Streams。供 devlab-middleware-expert 通过 extends 继承。借鉴自 mongodb/agent-skills。 |
| `public-mysql-expert-base` | 0.1.3 | MySQL/InnoDB 知识基座：schema 设计、索引策略、查询调优、事务与锁、运维操作。供 devlab-middleware-expert 技能通过 extends 继承。借鉴自 planetscale/database-skills，去除 PlanetScale 特有内容。 |
| `public-nl2sql-expert-base` | 0.1.4 | NL2SQL/Text2SQL 知识基座：两阶段架构(NL2DSL2SQL)、查询类型分类、字段/术语映射、条件与 metric 抽取、多表 JOIN 推理、SQL 正确性与评测。供 devlab-nl2sql-engineering 通过 extends 继承。 |
| `public-oracle-expert-base` | 0.1.2 | Oracle 知识基座：Connection Types（SID/ServiceName/TNS）、JDBC Driver、Connection Pool、LOB Handling、Character Set。供 devlab-middleware-expert 通过 extends 继承。 |
| `public-postgres-expert-base` | 0.1.2 | PostgreSQL 知识基座：Schema Design、Indexing（B-Tree/GIN/GiST/BRIN）、JSONB、Partitioning、Extensions。供 devlab-middleware-expert 通过 extends 继承。借鉴自 planetscale/database-skills。 |
| `public-rabbitmq-expert-base` | 0.1.2 | RabbitMQ 知识基座：Exchange Types、Queue & Routing、Durability、Dead Letter、Confirmations。供 devlab-middleware-expert 通过 extends 继承。借鉴自 mindrally/skills。 |
| `public-redis-expert-base` | 0.1.3 | Redis 知识基座：数据结构选型、Key 命名、连接池/Pipeline、集群/副本读取、TTL 与淘汰。供 devlab-middleware-expert 通过 extends 继承。借鉴自 redis/agent-skills。 |

### Diagnostics & Troubleshooting (7)

| Skill | Version | Description |
|-------|---------|-------------|
| `diag-container-oom` | 0.1.3 | 容器 OOM 全链排查：dmesg → cgroup limits → compose memory → swap → 应用内存分析，输出结构化报告与修复建议。 |
| `diag-k8s-node-pressure` | 0.1.3 | K8s 节点资源压力排查：CPU/Memory/Disk/PID pressure 全链诊断，kubectl top → describe node → eviction → 调度分析，输出结构化报告。 |
| `diag-k8s-pod-crashloop` | 0.1.3 | K8s Pod CrashLoopBackOff 全链排查：kubectl describe → events → logs → restart policy → resource limits → liveness probe，输出结构化报告与修复建议。 |
| `diag-mysql-deadlock` | 0.1.3 | MySQL 死锁全链诊断：捕获 InnoDB 状态、解析锁链、分类模式（AB-BA/Gap Lock/FK/Auto-Inc）、查找长事务，输出结构化报告与三级修复建议。 |
| `diag-mysql-replication` | 0.1.3 | MySQL 主从延迟全链诊断：检查 replication 状态、定位延迟根因（大事务/网络/从库负载/binlog 格式/并行复制），输出结构化报告与修复建议。 |
| `diag-mysql-slow-query` | 0.1.3 | MySQL 慢查询全链诊断：开启/分析 slow query log、定位 Top-N 慢 SQL、EXPLAIN 检查执行计划、识别缺失索引与全表扫描，输出结构化报告与优化建议。 |
| `diag-network-port-unreach` | 0.1.3 | 端口不可达全链诊断：DNS → TCP connect → iptables/firewalld → 服务监听 → 路由，输出结构化报告与修复建议。 |

### AI / LLM Engineering (3)

| Skill | Version | Description |
|-------|---------|-------------|
| `devlab-ai-agent-engineering` | 0.1.3 | AI Agent / LLM 应用工程化方法论：分层管道、规则优先+LLM兜底、多模型触点路由、Prompt 统一治理、超时/缓存/降级、评测闭环、多厂商 SDK 适配。各领域（NL2SQL/RPA/数字人语音）作为独立 reference。 |
| `devlab-ai-kit-miner` | 0.4.6 | 研发会话后复盘提炼：分析已完成的研发会话，判断哪些经验值得沉淀为 Skill/CLI/MCP/Loop/Subagent/知识卡片，输出最小规格草案。基于 base-session-ai-kit-miner 二次定制，覆盖全资产类型决策和 devlab-* 命名规范。 |
| `devlab-eval-driven-agent` | 0.3.1 | eval 自评测体系驱动的 AI Agent 生产体系：评测集组织、Mock 隔离、标准化比对、自动评测脚本与回归；L3 数据后端接 Langfuse（dataset/scores/LLM-as-judge），配套 evalctl CLI（0.2.x 已发布）承接 run/diff/ingest/feedback/report。 |

### Software Engineering Methodology (7)

| Skill | Version | Description |
|-------|---------|-------------|
| `devlab-contract-web-server` | 0.1.3 | 前后端契约规范技能（contract 技能簇首个，介于 srv 与 web 之间）：接口/序列化契约、字段类型一致性、配置分层与不过度设计，配契约校验与联调防错清单。 |
| `devlab-cicd-onboard` | 0.10.6 | Provider-neutral CI/CD onboarding: repository assessment, pipeline design, configuration and secret boundaries, quality gates, and release verification. |
| `devlab-integration-fullstack` | 0.1.6 | 全栈集成测试专家技能。支持多服务 Docker Compose 部署场景，基于 Testcontainers + Mock Server 实现端到端集成测试。 |
| `devlab-srv-test-api` | 0.1.4 | 后端 API 测试专家技能。支持 Java（JUnit）/ Python（pytest）/ Node.js（supertest + jest）后端项目的接口测试、Mock 服务、测试数据管理。 |
| `devlab-tech-debt-ops` | 0.1.3 | 技术债清理/重构编排方法论（非业务债，侧重技术债）：现状梳理→拆分设计→引用清零安全移除→回归验证；附设计模式清单与典型模式示意性伪代码（点到即止，实操由 AI 给选项）。 |
| `devlab-test-expert` | 0.3.2 | 测试专家知识库。包含测试最佳实践、故障排查指南、测试策略设计、性能优化建议、属性测试（property-based testing）模式等专家级知识，供其他测试技能引用。 |
| `devlab-test-onboard` | 0.1.6 | AI 驱动的分层测试体系顶层路由编排。根据项目特征（前端/后端/全栈/微服务）智能识别测试需求，路由到对应子技能（devlab-web-test-e2e / devlab-srv-test-api / devlab-integration-fullstack）。 |

### Web & Frontend (9)

| Skill | Version | Description |
|-------|---------|-------------|
| `devlab-web-context` | 0.1.2 | 前端项目上下文理解规则资产（<domain>-context 家族首个成员）：双模式（模式 A 规则包被 devlab-context-bootstrap 文件契约委托 / 模式 B 独立四步渐进式理解），产出前端 context 画像（7 固定键 + 置信度标注），供 bootstrap 消费填五件套台账。 |
| `devlab-web-deep-acceptance` | 0.1.3 | 存量 Web 系统深度功能验收方法论：registry 功能点驱动 + 唯一入口执行器 + 假成功嗅探 + 三对齐审计 + L1-L4 分级 + 失败五分类路由，沉淀可重放回归资产。 |
| `devlab-web-echarts-usage` | 1.0.3 | ECharts 在 Astro/前端项目中的完整集成指南，包含 tree-shaking、IntersectionObserver 按需加载、自定义系列集成、拓扑图实现、雷达图配置、Astro Islands 数据传递、调试经验。 |
| `devlab-web-engineering` | 0.2.1 | Web / 前端工程化能力层。语言无关覆盖六域：Project Bootstrap、Build、Dependency、Packaging、Runtime/Environment、Engineering Convention。路由键 = 语言 × 框架 双维：TS 主线 / JS 兼容 / 语言维度扩展位 → 框架路由 profiles/vue（实战级：Vite 主线/Webpack 兼容 + 微前端场景层）、profiles/react（模板级），其余框架走 references 引用层。Capability Layer：原则沉淀 + 能力编排 + Profile + 工程质量要求；由 devlab-web-bootstrap 吸收升级而来。 |
| `devlab-web-extension-bootstrap` | 0.1.2 | 浏览器扩展（WebExtension/MV3）从零构建的团队工作流：可行性→逆向目标站点数据通道→WXT+Vue+MV3 选型→content/background/popup 三面架构→单测+Chrome-for-Testing 真实浏览器 e2e。尤其适用于从已有 Web 应用提取/下载/增强内容的扩展。 |
| `devlab-web-skywalking-rum-usage` | 0.1.7 | 前端 SkyWalking RUM 接入指南（框架无关）：skywalking-client-js 初始化、全局错误捕获、Web Vitals 采集、SPA 路由感知、前后端 trace 关联。 |
| `devlab-web-test-e2e` | 0.1.6 | Web E2E 测试专家技能。专注 Vue/React 前端项目的浏览器端到端测试能力，基于 Playwright + AI Agent 实现测试计划生成 → 代码生成 → 失败修复的完整闭环。 |
| `devlab-web-visual-ops` | 0.1.6 | Web 视觉化操作手册：Core（Observe/Navigate/Interact/Inspect/Validate/Capture）+ Router（Playwright/Stagehand/DevTools/Vision-CUA）+ Workflows（Debug/UI Review/Visual Regression/E2E/Browser Automation）。Stagehand 作为 Router 的 AI Adapter 而非底座，避免绑定单一框架。 |
| `devlab-web-xyflow-usage` | 0.1.4 | @xyflow/react 使用指南：核心概念、自定义节点、Astro Islands 集成、6 条踩坑经验。 |

### Infrastructure Ops (6)

| Skill | Version | Description |
|-------|---------|-------------|
| `infra-dify-ops` | 0.6.4 | Dify 平台使用层运维 Skill：DSL 创作/校验/双轨导入（Console API 优先，Playwright 兜底）、DSL 导出、app 检查、本地资源沉淀、workflow 草稿、模型 provider 配置与生产验收；不负责部署层。配套 CLI difyctl。 |
| `infra-harbor-ops` | 0.1.5 | Harbor 平台运维：project/robot/proxy cache/registry token/runtime health；OCI 预热消费链仍归 infra-artifact-readiness-ops。 |
| `infra-nexus-ops` | 0.3.7 | Nexus 平台运维：仓库 CRUD + update、blobstore 管理、cleanup-policy 查询、inventory 导出/漂移检测；消费预热归 infra-artifact-readiness-ops。 |
| `infra-ragflow-ops` | 0.2.6 | RAGFlow 平台运维：服务健康、模型/向量库/对象存储依赖、知识库 API 探活与数据源消费边界。 |
| `infra-sonarqube-ops` | 0.1.5 | SonarQube 代码质量平台 day-2 运维：探活、项目管理、质量门禁、扫描触发与结果解读、Token 管理。配套 CLI sonarqubectl。 |
| `infra-system-env-ops` | 0.2.4 | 基础设施系统环境运维 Skill。v1 覆盖端口转发/iptables/portproxy/SSH tunnel，v2 扩展 Monit 统一看门狗、服务崩溃自愈、系统资源监控和 Mattermost 告警集成。 |

### Documents & Office (11)

| Skill | Version | Description |
|-------|---------|-------------|
| `markitdown` | 0.1.2 | 调用已安装的 MarkItDown，把 docx、pdf、pptx、xlsx、图片、html、csv 等资料稳定转换为 markdown。 |
| `patent-disclosure-workflow` | 0.1.5 | 面向中文专利技术交底编写、补强、预审和按需导出的团队共享工作流 Skill。 |
| `patent-review` | 0.1.6 | 专利技术交底书多轮循环严格审查。支持多维审查（数据流闭合、术语一致、状态迁移、公式完整、错误代码分流、图文一致性（集成drawio-skill））、逐轮收敛、可选自动修复（默认关闭需人工确认）。 |
| `patent-specification-writer` | 0.1.2 | 面向中文专利说明书与技术交底主体内容编写的团队共享基础写作 Skill。 |
| `work-convert` | 0.2.8 | 办公文档格式互转编排：文件 → 文件格式转换（docx→pdf, pptx→pdf 等），依赖 soffice 和社区上游技能。 |
| `work-export` | 0.2.8 | 办公文档通用 Outflow 编排：从内容（Markdown/数据/大纲）调度社区上游技能生成目标格式文档（docx/pdf/xlsx/pptx）。 |
| `work-markitdown` | 0.2.7 | 办公文档通用 Inflow 编排：15+ 格式 → Markdown 统一转换入口，extends 上游 markitdown，补充本地环境适配和批量转换工作流。 |
| `work-sc-document-sop-builder` | 0.2.9 | 参考文档 SOP 提取：从参考文件中提取结构/内容/格式/导出规则，沉淀为可复用文档编制 SOP。 |
| `work-sc-docx-comment-reply` | 0.2.8 | Word 批注回复：提取批注上下文，生成回复并以 threaded replies 写回 docx。 |
| `work-sc-patent-specification-writer` | 0.2.8 | 专利说明书撰写：起草发明/实用新型/外观专利说明书主体章节。 |
| `work-sc-software-copyright-writer` | 0.1.4 | 软件著作权申请材料撰写：软件说明书（≥5000字）+ 源程序示例（≥2000行），含软著审查专家自查。与 work-sc-patent-specification-writer 同簇。 |

### General & Base (2)

| Skill | Version | Description |
|-------|---------|-------------|
| `base-cn-registry-mirror-strategy` | 0.1.10 | 国内镜像源与代理分层策略：覆盖 Docker 拉取、Debian/Alpine 包管理、Node/npm、Python/pip、Maven/Gradle 与 Go 模块，便于 Dockerfile 与 CI 统一维护。 |
| `base-manual-capture` | 0.1.5 | Domain-neutral capture base for operation manuals: browser-driven flow capture, screenshots, user confirmation, and structured operation traces. |

## Companion CLIs (6)

| PyPI package | Command | Description |
|--------------|---------|-------------|
| `sf-difyctl` | `difyctl` | Dify usage-layer ops CLI: dual-track DSL import (Console API + Playwright), DSL version detect, DSL authoring/validation, provider config, resource ledger. |
| `sf-evalctl` | `evalctl` | Eval CLI for AI / data apps: run eval sets, diff regressions, ingest real-world samples, collect feedback, generate reports. |
| `sf-loopctl` | `loopctl` | Loop asset lifecycle CLI (list, validate, run, status, extract, promote) for harness-ai-kit loop assets. |
| `sf-mineructl` | `mineructl` | MinerU document-parsing service ops CLI: doctor, probe, version, submit, status, result, tasks. |
| `sf-nexusctl` | `nexusctl` | Nexus repository ops CLI: repo CRUD, blobstore, cleanup-policy, inventory export/diff, presets, user/role management. |
| `sf-ragflowctl` | `ragflowctl` | RAGFlow ops CLI: doctor, dataset/document/ingest/retrieval, LLM model provider governance (v0.26 HTTP API). Companion of infra-ragflow-ops. |

Each CLI depends on `harness-ai-kit`. Publication is controlled by the explicit `docs/oss-public-release.yaml` allowlist and `.github/workflows/release.yml`; a directory is never auto-published.

## Plugins (1)

| Plugin | Description |
|--------|-------------|
| `harness-ai-kit-plugin` | harness-ai-kit 的 dsh 宿主插件（工具 + 随包技能） |

---
*Generated from each asset's `skill.json` / `cli.json` / `asset.json`.*
