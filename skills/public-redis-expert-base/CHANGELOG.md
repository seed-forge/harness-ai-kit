# CHANGELOG — public-redis-expert-base

## 0.1.2 - 2026-08-14

- frontmatter 规范化：SKILL.md 统一 LF / 无 BOM / 单一 YAML frontmatter 块，修复 AI IDE 加载告警（missing YAML frontmatter delimited by ---）。
## 0.1.1 - 2026-08-06

- 治理清欠：结构合规修复后版本抬升（ref_link、ref_rename:README.md->REFERENCE-README.md、refs）。

## 0.1.0 - 2026-07-09

- 初始版本。借鉴自 redis/agent-skills（redis-core + redis-connections + redis-clustering）
- 覆盖数据结构选型、Key 命名、连接池/Pipeline、集群/副本、TTL 淘汰
- 8 个参考文档（references/）
- 定位为 extends 知识基座，供 devlab-redis-usage 继承
