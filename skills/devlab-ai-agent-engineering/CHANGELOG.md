# Changelog — devlab-ai-agent-engineering

## 0.1.2 - 2026-08-14

- frontmatter 规范化：SKILL.md 统一 LF / 无 BOM / 单一 YAML frontmatter 块，修复 AI IDE 加载告警（missing YAML frontmatter delimited by ---）。
## 0.1.1 - 2026-08-06

- 治理清欠：结构合规修复后版本抬升（changelog_entry、changelog_missing、ref_rename:digitalhuman.md->REFERENCE-DIGITALHUMAN.md、ref_rename:nl2sql.md->REFERENCE-NL2SQL.md、ref_rename:rpa.md->REFERENCE-RPA.md、refs）。

## 0.1.0 - 2026-08-06

- 治理清欠：补齐伴生文档与结构合规（validate 存量债务清理）。

## 0.1.0 - 2026-08-06

- 治理清欠：补齐伴生文档与结构合规（validate 存量债务清理）。

## 0.1.0 (draft)
- 初始草案。由 base-historyminer-ops 从本机 Kiro 528 会话深挖（NL2SQL/RPA/数字人语音三条线）提炼。
- 建立 7 条核心方法论：分层管道、规则优先+LLM兜底、多模型触点路由、Prompt 统一治理、超时/缓存/降级、多厂商 SDK 适配、评测闭环。
- 附 3 个领域 reference：nl2sql / rpa / digitalhuman。
- 状态：draft，待管理员评审后正式纳入并走 validate/publish。
