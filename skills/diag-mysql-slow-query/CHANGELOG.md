# 变更记录

## 0.1.3 - 2026-08-25

- Public OSS metadata uses the `public` namespace and `seedforge` owner, and source resolution now uses public-registry instead of the retired private registry label.

## 0.1.2 - 2026-08-20
- 改名对齐/内容同步：harness-ai-kit → harness-ai-kit 全仓改名后未发版补发（HEAD 内容与 Nexus 制品 hash 不一致）

## 0.1.1 - 2026-08-14

- frontmatter 规范化：SKILL.md 统一 LF / 无 BOM / 单一 YAML frontmatter 块，修复 AI IDE 加载告警（missing YAML frontmatter delimited by ---）。
## 0.1.0 - 2026-07-08

- 初始化 diag-mysql-slow-query。
- 5 步诊断链：配置检查 → Top-N 慢 SQL → EXPLAIN → 缺失索引 → 统计信息。
- 参考 OpenOcta openocta_skills mysql-slow-query-diagnose 结构设计，内容适配 harness-ai-kit 规范。
