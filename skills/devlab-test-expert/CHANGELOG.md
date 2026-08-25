# 变更记录

## 0.3.2 - 2026-08-25

- Public OSS metadata uses the `public` namespace and `seedforge` owner, and source resolution now uses public-registry instead of the retired private registry label.

## 0.3.1 - 2026-08-18

- `references/REFERENCE-AI-SERVICE-TEST-TIERING.md` 末尾新增「延伸：Agent 测试的 L0-L4 分层（指针）」：
  明确本模式 = L0 确定性单测落地形态，L1-L4 由 `devlab-eval-driven-agent` 承载、路由见 `devlab-test-onboard`。

## 0.3.0 - 2026-08-17

- 新增 `references/REFERENCE-AI-SERVICE-TEST-TIERING.md`：AI 服务测试分级隔离模式（9 级 marker + opt-in 开关 + fake key 注入 + mock_env + 全局超时 + 目录镜像 + 落地清单）。来源 devlab-spec-miner 对某 NL2DSL 服务（已脱敏）的 measure-first 挖掘（40 条规范，2026-08-17）
- SKILL.md 索引表/尾部 references 列表与 references/REFERENCE-README.md 同步加行。

## 0.2.0 - 2026-08-15

- 新增 `references/REFERENCE-PROPERTY-BASED-TESTING.md`：属性测试模式索引（roundtrip / inverse / idempotence / stateful / shrink / precondition），映射 fast-check / Hypothesis / jqwik / FsCheck 与官方文档。
- SKILL.md 测试方法论索引表增加属性测试一行；references 根目录索引同步。
- skill.json：version 0.2.0，tags 增加 `property-based-testing`，summary 补属性测试。

## 0.1.2 - 2026-08-14

- frontmatter 规范化：SKILL.md 统一 LF / 无 BOM / 单一 YAML frontmatter 块，修复 AI IDE 加载告警（missing YAML frontmatter delimited by ---）。
## 0.1.1 - 2026-08-06

- 治理清欠：结构合规修复后版本抬升（changelog_entry、changelog_missing、ref_link、ref_rename:README.md->REFERENCE-README.md、refs、usage_missing）。

## 0.1.0 - 2026-08-06

- 治理清欠：补齐伴生文档与结构合规（validate 存量债务清理）。

## 0.1.0 - 2026-08-06

- 治理清欠：补齐伴生文档与结构合规（validate 存量债务清理）。
