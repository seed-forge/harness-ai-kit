# Changelog — devlab-spec-driven-dev

## 0.1.2 - 2026-08-14

- frontmatter 规范化：SKILL.md 统一 LF / 无 BOM / 单一 YAML frontmatter 块，修复 AI IDE 加载告警（missing YAML frontmatter delimited by ---）。
## 0.1.1 - 2026-08-06

- 治理清欠：结构合规修复后版本抬升（changelog_entry、changelog_missing、ref_rename:kiro-spec-example.md->REFERENCE-KIRO-SPEC-EXAMPLE.md、refs）。

## 0.1.0 - 2026-08-06

- 治理清欠：补齐伴生文档与结构合规（validate 存量债务清理）。

## 0.1.0 (draft)
- 初始草案。由 base-historyminer-ops 从本机 Kiro 528 会话深挖提炼（spec 命中最高频，跨三条产品线通用）。
- 抽象为**工具无关**的通用 spec 驱动 AI 协作开发方法论；Kiro spec 降为 `references/kiro-spec-example.md` 示例。
- 固化提案质量四约束 + G1/G2/G3 human-on-the-loop 决策门禁。
- 状态：draft，待管理员评审后正式纳入并走 validate/publish。
