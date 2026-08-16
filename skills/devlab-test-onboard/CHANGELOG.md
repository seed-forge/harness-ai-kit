# Changelog

## 0.1.4 - 2026-08-14

- frontmatter 规范化：SKILL.md 统一 LF / 无 BOM / 单一 YAML frontmatter 块，修复 AI IDE 加载告警（missing YAML frontmatter delimited by ---）。
## 0.1.3 - 2026-08-11

- 场景识别矩阵新增「性能/容量需求」档，路由到新子技能 `devlab-app-test-perf`；补齐矩阵仅覆盖功能测试的缺口。
- 子技能说明新增第 4 节（应用级性能测试），明确与功能测试的正交关系及与 cicd-onboard quality-gate 的职责分工。

## 0.1.2 - 2026-08-06

- 治理清欠：结构合规修复后版本抬升（usage_missing）。

## 0.1.1 - 2026-07-24

- 补全 Human Decision 结构（Skill 组织规范 §5）：新增 `decisions.yaml`（HD-1 测试框架初始化执行）+ SKILL.md `## Human Decisions` 汇总表。（harness-ai-kit-audit-ops HD 治理 P2 批）

## 0.1.0

- 初始版本：测试框架 onboard 编排。
