# 变更记录

## 0.1.6 - 2026-08-25

- Public OSS metadata uses the `public` namespace and `seedforge` owner, and source resolution now uses public-registry instead of the retired private registry label.

## 0.1.5 - 2026-08-21

- Replaced the instruction-only `drawio-skill` dependency with
  `drawioctl >= 0.1.3` and its tested `inspect --json` contract for D7.
- Kept patent-specific consistency and blocking rules in the D7 reference.

## 0.1.4 - 2026-08-14

- frontmatter 规范化：SKILL.md 统一 LF / 无 BOM / 单一 YAML frontmatter 块，修复 AI IDE 加载告警（missing YAML frontmatter delimited by ---）。
## 0.1.3 - 2026-08-06

- 治理清欠：结构合规修复后版本抬升（ref_link、ref_rename:README.md->REFERENCE-README.md、ref_rename:REFERENCE-review-dimensions.md->REFERENCE-REFERENCE-REVIEW-DIMENSIONS.md、refs、usage_prompt）。

## 0.1.2 - 2026-07-24

- 补全 Human Decision 结构（Skill 组织规范 §5）：新增 `decisions.yaml`（HD-1 --fix 模式的自动修改确认）+ SKILL.md `## Human Decisions` 汇总表。（harness-ai-kit-audit-ops HD 治理 P2 批）

## 0.1.1 - 2026-06-07

- 新增 drawio-skill 可选依赖（feature: diagram-consistency）
- D7 图文一致性维度升级：由 drawio-skill 驱动解析附图
- 修复 skill.json companion_docs 字段格式，移除不支持的嵌套结构

## 0.1.0 - 2026-06-07

- 初始版本
- 支持7维审查：D1数据流闭合、D2术语一致性、D3状态迁移、D4公式完整性、D5错误代码分流、D6实施例一致性、D7图文一致性
- 多轮循环审查机制，连续3轮无阻塞问题自动停止
- 默认 dry-run 模式（仅输出问题清单）
- --fix 模式支持自动修复（阻塞问题需人工确认）
- 跨文档接口一致性检查
