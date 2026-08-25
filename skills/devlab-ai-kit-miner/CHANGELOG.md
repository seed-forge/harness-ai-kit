# Changelog

## 0.4.6 - 2026-08-25

- Public OSS metadata uses the `public` namespace and `seedforge` owner, and source resolution now uses public-registry instead of the retired private registry label.

## 0.4.5 - 2026-08-17

- 来源脱敏纪律：复盘产出草案（SKILL.md/CHANGELOG/元数据）不得深度包含具体项目名、产品名、会话 ID、内部域名或路径；来源统一匿名化（如"某上游产品二开项目（已脱敏）"），量化锚点可保留。沉淀自 2026-08-17 首跑反哺批次审查（来源项目已脱敏）。

## 0.4.4 - 2026-08-14

- frontmatter 规范化：SKILL.md 统一 LF / 无 BOM / 单一 YAML frontmatter 块，修复 AI IDE 加载告警（missing YAML frontmatter delimited by ---）。
## 0.4.3 - 2026-08-06

- 治理清欠：结构合规修复后版本抬升（ref_link、ref_rename:README.md->REFERENCE-README.md、refs）。

## 0.4.2 - 2026-07-25

- 新增「八、与审查流水线的关系」：沉淀候选经 historyminerctl push 进草稿队列，由 harness-ai-kit-review-ops 审查后融合，不直提交。

## 0.4.1 - 2026-07-24

- 补全 Human Decision 结构（Skill 组织规范 §5）：新增 `decisions.yaml`（HD-1 提炼资产是否推进创建/发布）+ SKILL.md `## Human Decisions` 汇总表。（harness-ai-kit-audit-ops HD 治理 P2 批）

## 0.4.0 - 2026-07-19

- 命名规范表新增 `devlab-cicd-*` 前缀（CI/CD 编排领域，如 `devlab-cicd-onboard`）
- 判定规则补充 CI/CD → `cicd` 分支

## 0.3.0 - 2026-07-13

- 从 `devlab-skill-miner` 重命名为 `devlab-ai-kit-miner`，准确反映多资产类型覆盖能力（Skill/CLI/MCP/Loop/Subagent/知识卡片）。
- 重构 SKILL.md：从 375 行精简到 ~155 行，各资产类型规范拆分到独立 references。
- 新增 references：REFERENCE-ASSET-SKILL.md、REFERENCE-ASSET-CLI.md、REFERENCE-ASSET-LOOP.md、REFERENCE-ASSET-MCP-SUBAGENT.md、REFERENCE-DISTILLATION-RULES.md。
- 新增"与 harness-ai-kit-forge 的接力"章节，明确复盘→创建的无缝链路。

## 0.2.0 - 2026-07-12

- （继承自 devlab-skill-miner）升级命名规范：devlab-srv/web/tool 二级体系。
- 增加对 post-task-skill-miner 的显式依赖声明。
- 状态从 draft 升级到 trial。

## 0.1.0 - 2026-06-30

- （继承自 devlab-skill-miner）初始版本，基于 post-task-skill-miner 二次定制。
