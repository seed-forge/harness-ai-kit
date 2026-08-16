# 变更记录

## 0.1.4 - 2026-08-14

- 依赖修复：word-export 依赖从旧 ID patent-docx-exporter 改指 work-sc-patent-docx-exporter。

## 0.1.3 - 2026-08-14

- frontmatter 规范化：SKILL.md 统一 LF / 无 BOM / 单一 YAML frontmatter 块，修复 AI IDE 加载告警（missing YAML frontmatter delimited by ---）。
## 0.1.2 - 2026-08-06

- 治理清欠：结构合规修复后版本抬升（ref_link、ref_rename:README.md->REFERENCE-README.md、refs）。

## 0.1.1 - 2026-07-24

- 补全 Human Decision 结构（Skill 组织规范 §5）：新增 `decisions.yaml`（HD-1 导出 Word 文档）+ SKILL.md `## Human Decisions` 汇总表。（team-ai-kit-audit-ops HD 治理 P2 批）

## 0.1.0 - 2026-05-14

- 从 03 工作空间迁入 patent-disclosure-workflow，补齐 team-ai-kit 元数据，明确与写作层、导出层 Skill 的依赖关系。
