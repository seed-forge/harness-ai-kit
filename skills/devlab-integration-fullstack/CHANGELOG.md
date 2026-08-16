# Changelog

## 0.1.4 - 2026-08-14

- frontmatter 规范化：SKILL.md 统一 LF / 无 BOM / 单一 YAML frontmatter 块，修复 AI IDE 加载告警（missing YAML frontmatter delimited by ---）。
## 0.1.3 - 2026-08-06

- 治理清欠：结构合规修复后版本抬升（usage_missing）。

## 0.1.2 - 2026-07-26

- **Bug Fix**: 修复依赖声明元数据缺陷
  - `testcontainers` 从 dependencies（错误的 cli 类型）迁移到 runtime_requirements
  - 补全 @playwright/test / jest / supertest 的 npm 包声明
  - 使用字符串数组格式（pkg>=version），符合 harness-ai-kit 官方规范
  - post_install_hints 仅保留 Docker 运行提示（系统级依赖）

## 0.1.1 - 2026-07-24

- Initial release (trial status)
- 全栈集成测试专家技能
- 基于 Testcontainers + Mock Server 实现端到端集成测试
