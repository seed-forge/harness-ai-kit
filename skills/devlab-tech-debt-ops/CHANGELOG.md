# Changelog — devlab-tech-debt-refactor

## 0.1.2 - 2026-08-20
- 改名对齐/内容同步：harness-ai-kit → harness-ai-kit 全仓改名后未发版补发（HEAD 内容与 Nexus 制品 hash 不一致）

## 0.1.1 - 2026-08-06

- 治理清欠：结构合规修复后版本抬升（ref_rename:design-patterns.md->REFERENCE-DESIGN-PATTERNS.md、refs）。

## 0.1.0 (draft)
- 初始草案。由 base-historyminer-ops 从本机 Kiro 528 会话深挖提炼（RPA/NL2SQL 引擎 god-class 拆分反复出现）。
- 抽象为技术债（非业务债）重构编排方法论：现状固化 → 安全网 → 拆分设计 → 引用清零安全移除 → 回归。
- 附 `references/design-patterns.md`：设计模式清单 + 示意性伪代码（点到即止，实操由 AI 给选项）。
- 状态：draft，待管理员评审后正式纳入并走 validate/publish。
