# Changelog — devlab-contract-web-server

## 0.1.3 - 2026-08-25

- Public release metadata now uses the `public` namespace and `seedforge` owner; private registry labels and source references are removed from the OSS bundle.

## 0.1.2 - 2026-08-14

- frontmatter 规范化：SKILL.md 统一 LF / 无 BOM / 单一 YAML frontmatter 块，修复 AI IDE 加载告警（missing YAML frontmatter delimited by ---）。
## 0.1.1 - 2026-08-06

- 治理清欠：结构合规修复后版本抬升（changelog_entry、changelog_missing）。

## 0.1.0 - 2026-08-06

- 治理清欠：补齐伴生文档与结构合规（validate 存量债务清理）。

## 0.1.0 - 2026-08-06

- 治理清欠：补齐伴生文档与结构合规（validate 存量债务清理）。

## 0.1.0 (draft)
- 初始草案。由 base-historyminer-ops 从本机 Kiro 528 会话深挖提炼（NL2SQL/数字人前后端契约类坑反复出现）。
- 定位为 `devlab-contract-*` 技能簇首个成员，介于 devlab-srv-* 与 devlab-web-* 之间。
- 覆盖字段类型/序列化/错误码/配置分层契约 + schema 校验落点 + 联调防错清单。
- 状态：draft，待管理员评审后正式纳入并走 validate/publish；contract 技能簇命名需管理员确认。
