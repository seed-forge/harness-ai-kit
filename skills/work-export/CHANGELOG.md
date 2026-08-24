# Changelog

## 0.2.7 - 2026-08-20
- 改名对齐/内容同步：harness-ai-kit → harness-ai-kit 全仓改名后未发版补发（HEAD 内容与 Nexus 制品 hash 不一致）

## 0.2.6 - 2026-08-14

- frontmatter 规范化：SKILL.md 统一 LF / 无 BOM / 单一 YAML frontmatter 块，修复 AI IDE 加载告警（missing YAML frontmatter delimited by ---）。
## 0.2.5 - 2026-08-06

- 治理清欠：结构合规修复后版本抬升（changelog_entry、changelog_missing、usage_prompt）。

## 0.2.4 - 2026-08-06

- 治理清欠：补齐伴生文档与结构合规（validate 存量债务清理）。

## 0.1.0 (initial)

- 办公文档通用 Outflow 编排：内容 → 目标格式统一导出管线
- depends on docx, pdf, xlsx, pptx 社区上游技能
- 提供格式选择决策树和统一输出校验流程
- 与 work-markitdown（Inflow）形成闭环
