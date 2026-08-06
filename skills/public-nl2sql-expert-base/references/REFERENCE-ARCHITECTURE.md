# NL2SQL 架构与管道

## 两阶段架构（NL2DSL2SQL）
```
自然语言 → [NL2DSL] → DSL(中间表示) → [DSL2SQL] → SQL → (执行/校验)
```
- **为何要 DSL 中间层**：解耦 NLP 理解与工程实现；一份 DSL 可编译到多种 SQL 方言（MySQL/PostgreSQL/Oracle），查询方案跨库复用；保留完整语义链路，可解释、可审计。
- **NL2DSL（理解侧）**：意图识别 → 知识增强检索 → 术语/字段映射 → 条件/metric 抽取 → 关系推断/JOIN → DSL 构建与校验。
- **DSL2SQL（编译侧）**：DSL 标准化 → 方言适配 → JOIN/聚合生成 → 语法+语义校验。

## 查询类型分类 + strategy-per-type
先分类后分策略，避免巨型分支：
| 类型 | 特征 | 策略要点 |
|------|------|---------|
| 明细(DETAIL) | 取原始记录 | 主表识别 + 字段选择 + 过滤条件 |
| 指标(METRIC) | 聚合/衍生指标 | metric 抽取 + 衍生指标生成（有此能力的策略才承接） |
| 排名(RANKING) | order+limit | 排序指标 + topN；**勿承接多指标查询** |
| 对比(COMPARISON) | 多维度对比 | 维度拆解 + 分组 |

> 坑：多汇总指标/衍生指标查询若误路由到 ranking 策略 → 指标缺失。稳定分类是前提。

## 规则优先 + LLM 兜底
- 默认 rule_first：可确定的走确定性路径（快/稳/可解释/零成本）。
- 规则置信度低或产出不足 → LLM 兜底（慢路径）。策略：rule_first/llm_first/parallel/adaptive。
- 触点分模型：归一化/意图路由用便宜模型，复杂条件抽取用强模型。
- 配置分层：LLM 配置在 `llm_fallback.touchpoints.*`，非 LLM（排序/裁剪）在 `ranking.*`。
