# public-nl2sql-expert-base — Usage

## Overview
NL2SQL/Text2SQL 知识基座，供 `devlab-nl2sql-engineering` 等技能通过 extends 继承。通常隐藏于 IDE 列表，不直接触发。

## References
- `references/REFERENCE-ARCHITECTURE.md` — 两阶段架构/查询类型/规则+LLM。
- `references/REFERENCE-UNDERSTANDING.md` — 意图/检索/映射/条件/metric 抽取。
- `references/REFERENCE-CORRECTNESS-EVAL.md` — JOIN 推理/正确性/评测/错误模式速查。

## 直接使用（少见）
```text
参考 public-nl2sql-expert-base 的 correctness-eval，帮我分析这个 NL2SQL badcase 的根因
```

## 可直接复制的中文 Prompt

```text
请使用 public-nl2sql-expert-base 技能，按照其 SKILL.md 描述的标准流程执行任务；
先做 dry-run/检查，向我展示结果与风险，经确认后再正式执行。
```
