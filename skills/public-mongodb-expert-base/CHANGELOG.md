# CHANGELOG — public-mongodb-expert-base

## 0.1.1 - 2026-08-14

- frontmatter 规范化：SKILL.md 统一 LF / 无 BOM / 单一 YAML frontmatter 块，修复 AI IDE 加载告警（missing YAML frontmatter delimited by ---）。
## 0.1.0 - 2026-07-09

- 初始版本。借鉴自 mongodb/agent-skills（schema-design + query-optimizer + connection）
- 覆盖 Document Model、Schema Patterns、Indexing、Aggregation、Replica Sets、Change Streams
- 定位为 extends 知识基座，供 devlab-mongodb-usage 继承
