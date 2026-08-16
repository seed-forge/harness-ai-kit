# Changelog

## 0.2.5 - 2026-08-14

- frontmatter 规范化：SKILL.md 统一 LF / 无 BOM / 单一 YAML frontmatter 块，修复 AI IDE 加载告警（missing YAML frontmatter delimited by ---）。
## 0.2.4 - 2026-08-06

- 治理清欠：结构合规修复后版本抬升（changelog_entry、changelog_missing、usage_prompt）。

## 0.2.3 - 2026-08-06

- 治理清欠：补齐伴生文档与结构合规（validate 存量债务清理）。

## 0.1.0 (initial)

- 办公文档通用 Inflow 编排：15+ 格式 → Markdown 统一转换入口
- extends 上游 markitdown 社区技能，不重新实现转换逻辑
- 补充本地环境适配（markitdown.cmd 包装、已验证依赖清单）
- 提供单文件转换和批量转换工作流
- 定义与 work-export / work-convert / work-dispatcher 的协作约定
