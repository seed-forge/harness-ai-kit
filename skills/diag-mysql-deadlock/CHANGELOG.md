# 变更记录

## 0.1.1 - 2026-08-14

- frontmatter 规范化：SKILL.md 统一 LF / 无 BOM / 单一 YAML frontmatter 块，修复 AI IDE 加载告警（missing YAML frontmatter delimited by ---）。
## 0.1.0 - 2026-07-08

- 初始化 diag-mysql-deadlock。
- 参考 OpenOcta openocta_skills mysql-deadlock-analyzer 结构设计，内容全部重写适配 team-ai-kit 规范。
- 包含 5 步诊断链、模式分类表、输出模板、告警阈值表、Quick Reference。
- skill_type: diagnostic（首个 diag-* namespace 技能）。
