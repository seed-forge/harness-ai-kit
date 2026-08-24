# Changelog

## 0.2.8 - 2026-08-20
- 改名对齐/内容同步：harness-ai-kit → harness-ai-kit 全仓改名后未发版补发（HEAD 内容与 Nexus 制品 hash 不一致）

## 0.2.7 - 2026-08-14

- frontmatter 规范化：SKILL.md 统一 LF / 无 BOM / 单一 YAML frontmatter 块，修复 AI IDE 加载告警（missing YAML frontmatter delimited by ---）。
## 0.2.6 - 2026-08-06

- 治理清欠：结构合规修复后版本抬升（ref_link、ref_rename:README.md->REFERENCE-README.md、refs）。

## 0.2.5 - 2026-07-24

- 补全 Human Decision 结构（Skill 组织规范 §5）：新增 `decisions.yaml`（HD-1 文档导出确认）+ SKILL.md `## Human Decisions` 汇总表。（harness-ai-kit-audit-ops HD 治理 P2 批）

## 0.1.0 (migrated)

- 从 03 空间 `document-reference-sop-builder` 迁移到 harness-ai-kit 并重命名为 `work-sc-document-sop-builder`
- 归属 work-sc 命名空间，声明 depends on docx + pdf
# Changelog

## 0.1.0 - 2026-05-09

- onboarded `document-reference-sop-builder` into `harness-ai-kit`
- added team metadata and dependency declarations for companion skills
- bundled the reference checklist used to extract reusable document rules

