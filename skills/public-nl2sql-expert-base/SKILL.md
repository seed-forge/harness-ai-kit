---
name: public-nl2sql-expert-base
description: NL2SQL/Text2SQL 知识基座（供 extends 继承）。聚合两阶段架构、查询类型分类、字段/术语映射、条件与 metric 抽取、多表 JOIN 推理、SQL 正确性与评测的深度知识与踩坑。通常被 devlab-nl2sql-engineering 继承，不直接面向用户触发。
---

# public-nl2sql-expert-base

> **知识基座**：本技能不做流程编排，只提供 NL2SQL 领域的深度知识与判据，供 `devlab-nl2sql-engineering` 等技能通过 extends 继承。

## 覆盖主题

| 主题 | reference |
|------|-----------|
| 架构与管道 | `references/REFERENCE-ARCHITECTURE.md` — NL2DSL2SQL 两阶段、DSL 中间表示、查询类型分类、strategy-per-type |
| 理解与抽取 | `references/REFERENCE-UNDERSTANDING.md` — 意图识别、知识增强检索、字段/术语映射、条件/metric/时间/实体抽取 |
| 正确性与评测 | `references/REFERENCE-CORRECTNESS-EVAL.md` — 多表 JOIN 推理、SQL 标准化比对、评测集组织、常见错误模式 |

## 使用原则

- **证据优先**：以评测集正确率、EXPLAIN、日志为依据，而非拍脑袋规则。
- **区分表象与根因**：修一个 badcase 要定位根因并沉淀回归用例，避免只压症状。
- **可解释可追溯**：DSL 中间表示保留完整语义链路，便于审计与调试。
- **破坏性变更同步调用侧**。

## 与其他 Skill 的关系
- 被 `devlab-nl2sql-engineering` 通过 extends 继承（提供知识，流程由其编排）。
- 与 `public-mysql-expert-base` 互补（后者聚焦 DB 侧 schema/索引/事务）。
- 评测细节交 `devlab-eval-driven-agent`。
