# Changelog — devlab-eval-driven-agent

## 0.3.0 - 2026-08-18

- **L0-L4 分层评测矩阵**：新增 Agent 全景测试分层（L0 确定性单测 / L1 轨迹评测 / L2 输出评测 /
  L3 生产回归 / L4 安全+成本护栏），含分层选用规则与工具/基座映射（Langfuse 平台基座 + Promptfoo 本地
  CLI + 代码级 golden session；不新增 组织内部集群 服务基座）
- **L1 轨迹评测（golden session）**：新增轨迹断言方法论——`golden-sessions/<scenario>/session.yaml`
  资产格式（expected_trace / recovery / stop_conditions / expected_terminal 断言语义表）+ replay runner
  （ToolSimulator 模式，零凭据零真实后端）+ 生产轨迹回流（Langfuse session → 人工确认 → golden session，
  经 evalctl ingest 管线）
- **L3 生产回归闭环**：新增章节，把 evalctl ingest/feedback/run/diff 串成"生产 trace → 评测集 → 回归门禁"
  闭环（复用既有命令，未新增 CLI 面）
- **章节对齐**：原「L3 数据后端（Langfuse）」更名为「L2 输出评测后端（Langfuse）」，与 L0-L4 矩阵编号一致
- **版本对齐**：SKILL.md 内容此前已含 skill-eval 0.3.0+ 与 evalctl 0.3.x 描述但 skill.json 停留在 0.2.1，
  本次抬升至 0.3.0 对齐
- frontmatter 补轨迹评测/golden session/agent 测试触发词；适用场景补多步 Agent；工作流 Phase 1 补轨迹判据

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
