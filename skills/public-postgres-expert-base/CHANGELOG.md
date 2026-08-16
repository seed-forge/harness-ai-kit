# CHANGELOG — public-postgres-expert-base

## 0.1.1 - 2026-08-14

- frontmatter 规范化：SKILL.md 统一 LF / 无 BOM / 单一 YAML frontmatter 块，修复 AI IDE 加载告警（missing YAML frontmatter delimited by ---）。
## 0.1.0 - 2026-07-09

- 初始版本。借鉴自 planetscale/database-skills PostgreSQL skill
- 覆盖 Schema Design、Indexing、JSONB、Partitioning、Extensions、Connection Management
- 定位为 extends 知识基座，供 devlab-postgres-usage 继承
