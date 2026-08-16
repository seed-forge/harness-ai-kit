# 变更记录

## 0.6.1 - 2026-08-14

- frontmatter 规范化：SKILL.md 统一 LF / 无 BOM / 单一 YAML frontmatter 块，修复 AI IDE 加载告警（missing YAML frontmatter delimited by ---）。
## 0.6.0 - 2026-08-06

- 新增 **「LLM 节点容错默认行为」** 章节（SKILL.md）：`difyctl workflow-create scaffold` 默认为每个 LLM 节点注入 `retry_config`（3 次重试，间隔 1s）和 `error_strategy`（`default_value` fallback），确保模型返回 429/5xx/超时时 workflow 不直接崩溃。
- 更新 Graph 约定：LLM 节点应显式带上 `retry_config` 和 `error_strategy`，与 `model`/`context`/`vision` 同级。
- 更新 REFERENCE-DSL-AUTHORING.md：LLM 节点关键字段表补充 `retry_config` 和 `error_strategy`。
- 更新 REFERENCE-DSL-GOTCHAS.md：新增 gotcha #9（缺 retry_config）和 #10（缺 error_strategy）；校验维度表补充两条 warning 级检查。
- 配套 CLI 依赖 floor 抬到 `difyctl>=0.14.0`（scaffold 默认注入 retry + error strategy）。

## 0.5.2 - 2026-08-06

- 治理清欠：结构合规修复后版本抬升（changelog_drift、changelog_entry）。

## 0.5.1 - 2026-08-06

- 治理清欠：补齐伴生文档与结构合规（validate 存量债务清理）。

## 0.5.0 - 2026-08-01

- 新增单段联网搜索 spec 模板：`references/specs/web-search-searxng.spec.yml`（SearXNG→LLM，自托管/快/免 sandbox）与 `references/specs/web-search-tavily.spec.yml`（Tavily→LLM，托管兜底/带来源）。连同两段式 `deep-research-websearch.spec.yml` 形成三档 spec 模板库。均真机验证 scaffold→import→run 全绿。SKILL 增加 spec 模板库选型表与通用导入流程。

## 0.4.0 - 2026-08-01

- 新增可复用资产 `references/specs/deep-research-websearch.spec.yml`：两段式联网深研 workflow spec，`difyctl workflow-create scaffold` 一键生成 `SearXNG搜索→取URL→Firecrawl读全文→LLM` DSL。真机验证：scaffold→validate→import→run 全绿（73s、带来源）。
- 依赖 difyctl `>=0.13.0`（新增 `tool` step 脚手架 + 跨节点引用重映射）。SKILL 补充脚手架用法。

## 0.3.3 - 2026-08-01

- 两段式深研 `SearXNG搜索→Template取URL→Firecrawl读全文→LLM` **修复 sandbox 后真机 GREEN**（56s、5467 tokens、带来源 URL）。
- 记录**超时坑**：全链 50-65s，超 difyctl 默认 20s → 用 `difyctl app run --timeout 150`（difyctl 0.12.1+ 新增 `--timeout`）。CLI 依赖 floor 抬到 `>=0.12.1`。

## 0.3.2 - 2026-07-30

- 自托管 SearXNG + Firecrawl 接入实录（真机 GREEN）：Console API `tool-provider/builtin/<provider>/add`（type=api-key）授权；`Cannot release a lock` 400 为假失败（凭据已存，勿重试）。
- **关键坑**：SearXNG 节点结果只在 `json`（`text` 为空）→ prompt 引用 `{{#节点.json#}}`；Firecrawl scrape 输出走 `text`。
- **基础设施阻断**：本实例 `dify-sandbox` 缺 python3，Code 与 Template-Transform 节点均报 `-500 fork/exec /usr/local/bin/python3`，含转换节点的 workflow 全部跑不了 → 两段式 SearXNG→Firecrawl→LLM 待修 sandbox；单段 SearXNG→LLM 已 GREEN。
- `app delete` 需 `--yes` 确认门（破坏性门禁）。

## 0.3.1 - 2026-07-30

- 补充 **Tool 节点参数放置坑**：运行时输入放 `tool_parameters`（包裹 `{type,value}`），静态配置放 `tool_configurations`（原始值不包裹）；`select` 型且默认布尔的配置项（Tavily `include_answer`/`include_raw_content`）必须显式赋合法字符串，否则默认 `False` 触发 `value False not in options`。
- 记录本实例 web-search 现状：**Tavily 已授权已配 key（search+extract 开箱即用，真机 GREEN，返回带来源 URL 的实时答案）**；SearXNG 插件未安装；Firecrawl 插件在册未配。生产联网搜索首选 Tavily。

## 0.3.0 - 2026-07-30

- 新增章节 **「给 LLM 应用加联网搜索/工具能力（Dify 1.x 插件版）」**：说明 LLM 节点本身无内置联网搜索开关，联网搜索经 Tool 节点（插件）实现；给出本实例可用 web-search 工具矩阵（Wikipedia/DuckDuckGo 免密钥、Tavily/Google/Bing 需 key）、Tool 节点 1.x DSL schema、以及 `dsl import→app publish→app run` 的 CLI 运维闭环。
- 记录真机结论：Wikipedia（`wikipedia_search`）零成本试点 GREEN；DuckDuckGo 免费端点常 `202 Ratelimit`（节点结构正确但被限流），生产联网搜索推荐 Tavily/SearchApi 或 DDG 配 proxy。
- CLI 依赖floor 抬到 `difyctl>=0.8.1`（联网搜索闭环用到 app publish/run + import 去重）。

## 0.2.0 - 2026-07-29

- **Skill 更名 `infra-dify-resource-ops` → `infra-dify-ops`**（保留 alias），配套 CLI 依赖切到 `difyctl>=0.5.0`（原 `difyresctl`）。
- 新增 **DSL 创作与双轨导入**能力文档：`difyctl dsl validate/import/export`，import 优先 Console API（`POST /console/api/apps/imports`），5xx/网络错误自动降级 Playwright；不再默认依赖 RPA。
- 新增两份 references：`REFERENCE-DSL-AUTHORING.md`（DSL 结构/节点 schema/布局/模式）与 `REFERENCE-DSL-GOTCHAS.md`（Top gotchas + 校验维度清单），借鉴自 yzmw123/dify-workflow-dsl-skill（规范重述）、yoloyolo8/dify-workflow-writer（MIT）、LingyiChen-AI/workflow-skill（MIT）。
- `workflow-create scaffold` 产出升级为 import-ready DSL（app/kind/version/features/完整 graph），spec 支持 v2（多节点类型）。

## 0.1.3 - 2026-07-29

- Config governance 修正：config.defaults.yaml 键名对齐 difyresctl 实际读取的 config.yaml assets.difyresctl 键（base_url/studio_username/studio_password/app_api_key/workspace_dir/timeout_seconds），移除不匹配的 dify_base_url/dify_api_key 与 env_var 引用；studio 登录凭据以 ~/.harness-ai-kit/config.yaml 为真源。配套 difyresctl 0.4.2（配置真源统一）。

## 0.1.2 - 2026-07-16

- Config governance: add config.defaults.yaml + inject config context paragraph.


## 0.1.1 - 2026-05-29

- 将配套 CLI 依赖提升到 `dify-resource-ops==0.2.6`。
- 明确新建 workflow 的 LLM 节点默认使用 `deepseek-v4-flash`。

## 0.1.0 - 2026-05-14

- 由 `difyresctl` 重命名为 `infra-dify-resource-ops`，统一纳入 组织内部集群 运维 skill 命名体系。
- 继承 app 检查、DSL 摘要、本地资源沉淀、registry/batch/workflow-create、Studio 自动化，以及 Dify `1.13.x` workflow 兼容性修复经验。
- 保持对配套 CLI `dify-resource-ops==0.2.4` 的必需依赖。
