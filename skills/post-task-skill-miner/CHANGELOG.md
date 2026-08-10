# Changelog

## 0.2.2 - 2026-08-06

- 治理清欠：结构合规修复后版本抬升（ref_link、ref_rename:README.md->REFERENCE-README.md、refs）。

## 0.2.1 - 2026-07-24

- 补全 Human Decision 结构（Skill 组织规范 §5）：新增 `decisions.yaml`（HD-1 提炼资产是否推进创建）+ SKILL.md `## Human Decisions` 汇总表。（ai-kit-audit-ops HD 治理 P2 批）

## 0.2.0 - 2026-07-12

- 合并 `session-to-loop` 技能：内置 6 信号评分模型、Skill→Loop 字段映射 Rubric、多 Skill 组合策略、Loop 草案模板。
- 工作流新增 Step 9：Loop 提炼候选输出。
- 输出新增 Loop 资产提炼区块（loop.json + LOOP.md + CHECK.md + USAGE.md）。
- 新增「专题引用」章节，指向 references/ 和 templates/。
- 新增 Loop 提炼触发示例。
- tags 增加 `loop`、`distillation`。

## 0.1.0 - 2026-05-10

- added `post-task-skill-miner` as a shared retrospective skill for Codex and Claude Code style AI IDE workflows
- defined a reusable rubric for deciding between knowledge-card only, project-level skill, and team-shared skill outcomes
- aligned the deliverable shape with `ai-kit` skill packaging and governance expectations
