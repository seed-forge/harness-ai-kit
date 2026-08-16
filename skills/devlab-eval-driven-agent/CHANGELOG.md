# Changelog — devlab-eval-driven-agent

## 0.2.0 - 2026-08-14

- **draft → released**：evalctl CLI 已发布（0.2.x），本技能从"规划"转"已落地"
  - 新增「L3 数据后端（Langfuse）」章节：dataset 评测集后端、scores 质量指标（六维 rubric）、
    LLM-as-judge 执行方法（评审模型隔离、SSRF 白名单）、evalctl 命令映射表
  - frontmatter description 补 langfuse/LLM-as-judge/scores 触发词
  - 首次落地实证记录：craft-gate-regression 3 items × claude-sonnet-4.5（21 scores / 7 configs / baseline run）

## 0.1.2 - 2026-08-14

- frontmatter 规范化：SKILL.md 统一 LF / 无 BOM / 单一 YAML frontmatter 块，修复 AI IDE 加载告警（missing YAML frontmatter delimited by ---）。
## 0.1.1 - 2026-08-06

- 治理清欠：结构合规修复后版本抬升（changelog_entry、changelog_missing）。

## 0.1.0 - 2026-08-06

- 治理清欠：补齐伴生文档与结构合规（validate 存量债务清理）。

## 0.1.0 - 2026-08-06

- 治理清欠：补齐伴生文档与结构合规（validate 存量债务清理）。

## 0.1.0 (draft)
- 初始草案。由 base-historyminer-ops 从本机 Kiro 528 会话深挖提炼（三条产品线均有评测集/测试框架实践）。
- 建立 eval 闭环：评测集组织 + Mock 隔离 + 标准化比对 + 自动评测脚本 + 回归门禁。
- 预留与产品运营系统打通（真实数据反馈），规划配套 `evalctl` CLI（run/diff/ingest/feedback/report）。
- 状态：draft，待管理员评审后正式纳入并走 validate/publish；evalctl CLI 需另行立项。
