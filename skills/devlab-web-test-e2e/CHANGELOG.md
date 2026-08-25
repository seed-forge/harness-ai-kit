# Changelog

## 0.1.6 - 2026-08-25

- Public OSS metadata uses the `public` namespace and `seedforge` owner, and source resolution now uses public-registry instead of the retired private registry label.

## 0.1.5 - 2026-08-20
- 改名对齐/内容同步：harness-ai-kit → harness-ai-kit 全仓改名后未发版补发（HEAD 内容与 Nexus 制品 hash 不一致）

## 0.1.4 - 2026-08-14

- frontmatter 规范化：SKILL.md 统一 LF / 无 BOM / 单一 YAML frontmatter 块，修复 AI IDE 加载告警（missing YAML frontmatter delimited by ---）。
## 0.1.3 - 2026-08-06

- 治理清欠：结构合规修复后版本抬升（usage_missing）。

## 0.1.2 - 2026-07-26

- **Bug Fix**: 修复 `runtime_requirements` 的 schema 格式错误
  - 从对象数组改为字符串数组格式（pkg>=version）
  - 符合 harness-ai-kit 官方规范
  - 解决 `publish-skill` 时报错 "Input should be a valid string"
  
## 0.1.1 - 2026-07-24

- Initial release (trial status)
- Web E2E 测试专家技能
- 基于 Playwright + AI Agent 实现测试闭环
