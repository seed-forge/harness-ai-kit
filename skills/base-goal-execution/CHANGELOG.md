# Changelog

## 0.1.2 - 2026-08-14

- Retired with no replacement.
- frontmatter 规范化：SKILL.md 统一 LF / 无 BOM / 单一 YAML frontmatter 块，修复 AI IDE 加载告警（missing YAML frontmatter delimited by ---）。
## 0.1.1 - 2026-07-24

- 补全 Human Decision 结构（Skill 组织规范 §5）：新增 `decisions.yaml`（HD-1 交付确认（Phase 4） / HD-2 超出原计划范围的变更）+ SKILL.md `## Human Decisions` 汇总表。（team-ai-kit-audit-ops HD 治理 P2 批）

## 0.1.0 - 2026-07-12

- 初始版本：从本地 `.agents/skills/goal-driven-execution` 迁移至 SSOT，重命名为 `base-goal-execution`
- 新增 `agents_md_inject` 字段：安装时自动向 AGENTS.md 注入「Goal 驱动执行」章节
- 完整执行框架：Phase 0（Goal 定义）→ Phase 1（前置检查）→ Phase 2（逐步执行）→ Phase 3（质量门禁）→ Phase 4（交付确认）
- 结构化错误恢复策略表（7 类错误，带重试上限）
- 断点恢复机制：支持从中间状态继续执行
