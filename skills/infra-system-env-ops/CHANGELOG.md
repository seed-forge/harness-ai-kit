# 变更记录

## 0.2.4 - 2026-08-25

- Public OSS metadata uses the `public` namespace and `seedforge` owner, and source resolution now uses public-registry instead of the retired private registry label.

## 0.2.3 - 2026-08-20
- 改名对齐/内容同步：harness-ai-kit → harness-ai-kit 全仓改名后未发版补发（HEAD 内容与 Nexus 制品 hash 不一致）

## 0.2.2 - 2026-08-14

- frontmatter 规范化：SKILL.md 统一 LF / 无 BOM / 单一 YAML frontmatter 块，修复 AI IDE 加载告警（missing YAML frontmatter delimited by ---）。
## 0.2.1 - 2026-08-06

- 治理清欠：结构合规修复后版本抬升（changelog_drift、changelog_entry、ref_link、ref_rename:README.md->REFERENCE-README.md、refs）。

## 0.2.0 - 2026-08-06

- 治理清欠：补齐伴生文档与结构合规（validate 存量债务清理）。

## 0.1.0 - 2026-05-14

- 将项目级 `infra-system-env-ops` 共享为 `infra-system-env-ops`。
- 统一纳入 组织内部集群 网络访问链路技能命名体系。
- 保留 iptables、DNAT、FORWARD、MASQUERADE、持久化与回滚四段式输出规则。
