# Changelog — public-nl2sql-expert-base

## 0.1.3 - 2026-08-17

- 脱敏收口：0.1.0 初始草案条目中的来源会话标识匿名化（会话 ID 移除，避免具体项目/会话信息外泄）。

## 0.1.2 - 2026-08-14

- frontmatter 规范化：SKILL.md 统一 LF / 无 BOM / 单一 YAML frontmatter 块，修复 AI IDE 加载告警（missing YAML frontmatter delimited by ---）。
## 0.1.1 - 2026-08-06

- 治理清欠：结构合规修复后版本抬升（changelog_entry、changelog_missing、ref_rename:architecture.md->REFERENCE-ARCHITECTURE.md、ref_rename:correctness-eval.md->REFERENCE-CORRECTNESS-EVAL.md、ref_rename:understanding.md->REFERENCE-UNDERSTANDING.md、refs、usage_prompt）。

## 0.1.0 - 2026-08-06

- 治理清欠：补齐伴生文档与结构合规（validate 存量债务清理）。

## 0.1.0 (draft)
- 初始草案（C 类纵向）。由 base-historyminer-ops 从某 NL2SQL 会话（已脱敏）深挖提炼。
- 知识基座，模型参照 public-mysql-expert-base；含 architecture / understanding / correctness-eval 三份 reference。
- **命名说明**：定稿蓝图 v2 曾记为 `devlab-nl2sql-expert`；按 harness-ai-kit 知识基座约定（`public-*-expert-base`）对齐为 `public-nl2sql-expert-base`，最终命名待管理员确认。
- 状态：draft，待管理员评审后正式纳入并走 validate/publish；由 devlab-nl2sql-engineering 通过 extends 继承。
