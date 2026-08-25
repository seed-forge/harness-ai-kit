# CHANGELOG — public-rabbitmq-expert-base

## 0.1.2 - 2026-08-25

- Public OSS metadata uses the `public` namespace and `seedforge` owner, and source resolution now uses public-registry instead of the retired private registry label.

## 0.1.1 - 2026-08-14

- frontmatter 规范化：SKILL.md 统一 LF / 无 BOM / 单一 YAML frontmatter 块，修复 AI IDE 加载告警（missing YAML frontmatter delimited by ---）。
## 0.1.0 - 2026-07-09

- 初始版本。借鉴自 mindrally/skills rabbitmq-development + RabbitMQ 官方文档
- 覆盖 Exchange Types、Queue/Routing、Durability、Dead Letter、Confirmations
- 定位为 extends 知识基座，供 devlab-rabbitmq-usage 继承
