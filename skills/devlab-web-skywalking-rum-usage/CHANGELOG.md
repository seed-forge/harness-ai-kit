# Changelog

## 0.1.6 - 2026-08-22
- 移除成员侧不可解析的维护者仓路径，改为自包含的 RUM/错误追踪边界说明。

## 0.1.5 - 2026-08-22
- 对齐统一可观测性矩阵，明确 RUM/Web Vitals 与 GlitchTip 前端错误追踪的边界。

## 0.1.4 - 2026-08-20
- 环境值占位符抽取：组织内部集群 IP/域名改为 {<host>_host}/{<host>_host}/{<host>_host}/{base_domain}/{service_domain}/{root_domain} config 占位符（docs/config-governance.md §12）

## 0.1.3 - 2026-08-14

- frontmatter 规范化：SKILL.md 统一 LF / 无 BOM / 单一 YAML frontmatter 块，修复 AI IDE 加载告警（missing YAML frontmatter delimited by ---）。
## 0.1.2 - 2026-08-06

- 治理清欠二轮：USAGE 精简/结构合规收尾（config_schema）。

## 0.1.1 - 2026-08-06

- 治理清欠：结构合规修复后版本抬升（changelog_entry、changelog_missing、usage_prompt）。

## 0.1.0 - 2026-08-06

- 治理清欠：补齐伴生文档与结构合规（validate 存量债务清理）。

## 0.1.0 (2026-07-21)

- Initial draft: skywalking-client-js 前端 RUM 接入指南
- 框架无关设计：覆盖 Vue/React/Angular/原生 JS 错误捕获示例
- 覆盖 Web Vitals、SPA 路由感知、分布式 trace 关联
