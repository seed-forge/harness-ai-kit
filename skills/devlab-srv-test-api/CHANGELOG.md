# Changelog

## 0.1.4 - 2026-08-25

- Public OSS metadata uses the `public` namespace and `seedforge` owner, and source resolution now uses public-registry instead of the retired private registry label.

## 0.1.3 - 2026-08-14

- frontmatter 规范化：SKILL.md 统一 LF / 无 BOM / 单一 YAML frontmatter 块，修复 AI IDE 加载告警（missing YAML frontmatter delimited by ---）。
## 0.1.2 - 2026-08-06

- 治理清欠：结构合规修复后版本抬升（usage_missing）。

## 0.1.1 - 2026-07-26

- **Bug Fix**: 修复 `runtime_requirements` 依赖声明缺失
  - 补全 7 个 npm/Python 包声明（jest/supertest/msw/@faker-js/faker/zod/pytest/requests-mock）
  - 使用字符串数组格式（pkg>=version），符合 harness-ai-kit 官方规范
  - 移除冗余的 post_install_hints 安装命令（由 runtime_requirements 正式声明替代）

## 0.1.0 - 2026-07-24

- Initial release (trial status)
- 后端 API 测试专家技能
- 支持 Java（JUnit）/ Python（pytest）/ Node.js（supertest + jest）
