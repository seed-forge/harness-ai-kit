# Skill → Loop 字段映射 Rubric

定义从 Skill（或 session 经验）到 Loop 资产的结构化字段映射规则。所有字段按自动提取能力分为三级：**自动**、**半自动**、**需人工**。

---

## 字段映射矩阵（14 个字段）

| # | Loop 字段 | 来源 | 提取级别 | 提取策略 | 备注 |
|---|-----------|------|----------|----------|------|
| 1 | `loop.id` | 命名约定 | 自动 | 从 session topic 或第一个 Skill name 派生 kebab-case ID | 如 `ci-auto-fix-loop` |
| 2 | `loop.name` | session topic / skill name | 自动 | 取 session topic 或主导 skill 的 name 字段 | 中文或英文均可 |
| 3 | `loop.summary` | session summaries | 半自动 | 汇总 `.summaries/` 中 IMPL 总结的首段描述 | 需人工确认精简 |
| 4 | `loop.description` | planning-notes + summaries | 半自动 | 从规划笔记提取目的和范围描述 | 需人工确认边界 |
| 5 | `loop.tags` | session topic + skill tags | 半自动 | 从 session topic 关键词 + 相关 skill tags 聚合去重 | 需人工筛选 |
| 6 | `loop.dependencies` | SKILL.md references | 自动 | 从 session 中涉及的其他 skill 的 name/ID 提取 | 版本范围需人工确认 |
| 7 | `loop.maker.entry` | 固定 | 自动 | 固定为 `LOOP.md` | — |
| 8 | `loop.maker.description` | workflow + summaries | 半自动 | 从 session workflow 步骤中提取核心动作描述 | 需人工确认范围 |
| 9 | `loop.checker.entry` | 固定 | 自动 | 固定为 `CHECK.md` | — |
| 10 | `loop.checker.description` | acceptance criteria | 半自动 | 从 session 验收标准中提取验证目标 | 需人工确认 |
| 11 | `loop.checker.rubric.dimensions` | acceptance criteria + verification | 需人工 | 根据验收标准设计 rubric 维度和权重 | 必须人工审核 |
| 12 | `loop.stop_conditions.success` | acceptance criteria | 半自动 | 从验收标准推导成功谓词 | 阈值需人工确认 |
| 13 | `loop.stop_conditions.failure` | error patterns in session | 半自动 | 从 session 失败模式推导失败谓词 | 需人工确认严重性 |
| 14 | `loop.convergence_metric` | iteration patterns | 需人工 | 根据 Loop 性质选择主指标和收敛方向 | 必须人工审核 |

### 提取级别定义

- **自动**：模式匹配直接填充，无需人工干预。
- **半自动**：语义分类可推断候选值，但需人工确认或微调。
- **需人工**：无法可靠自动推导，必须由用户或领域专家填写。

---

## Rubric 自动提取三层策略

### 第一层：模式匹配

当 session 资产中出现明确的结构化信号时，直接映射：

| 信号模式 | 映射目标 | 示例 |
|----------|----------|------|
| `tests_pass_rate` 出现在总结中 | `stop_conditions.success` 谓词 | `tests_pass_rate == 1.0` |
| `error_count` 出现在总结中 | `stop_conditions.failure` 谓词 | `error_count >= 3` |
| `coverage_pct` 出现在总结中 | `rubric.dimension` | 覆盖率维度 |
| `iteration_count` 出现在总结中 | `stop_conditions.budget` 谓词 | `iteration_count >= 10` |
| SKILL.md 中有 `input` / `output` 章节 | `maker.description` | 输入输出描述 |
| SKILL.md 中有 `约束` 章节 | `maker.description` 补充约束 | 约束条件 |

### 第二层：语义分类

当没有直接模式匹配时，对文本做语义分类：

| 语义类别 | 映射目标 | 判定方法 |
|----------|----------|----------|
| 验收标准文本 | `stop_conditions.success` | 提取"通过""成功""完成"等关键词后的条件 |
| 失败描述文本 | `stop_conditions.failure` | 提取"失败""错误""异常"等关键词后的条件 |
| 迭代次数记录 | `stop_conditions.budget` | 统计 session 中最大迭代次数 + 20% 余量 |
| 验证步骤描述 | `checker.rubric.dimensions` | 每个独立验证步骤作为一个维度 |
| 主目标描述 | `convergence_metric.primary` | 选择最频繁出现的验证指标 |

### 第三层：通用兜底

当以上两层均无法提取时，使用默认值：

| 字段 | 默认值 |
|------|--------|
| `stop_conditions.success` | `[{identifier: "rubric_pass", predicate: "checker_score >= 0.8"}]` |
| `stop_conditions.failure` | `[{identifier: "max_errors", predicate: "error_count >= 3"}]` |
| `stop_conditions.budget` | `[{identifier: "max_iterations", predicate: "iteration_count >= 10"}]` |
| `checker.rubric.dimensions` | `[{name: "output_quality", weight: 1.0, severity: "must_pass"}]` |
| `convergence_metric` | `{primary: "checker_score", direction: "increase", stagnation_threshold: 3}` |

---

## 多 Skill 组合策略

当一个 Loop 由多个 Skill 组合而成时，按以下三种模式处理：

### 串联模式（Pipeline）

多个 Skill 按固定顺序依次执行，前一个 Skill 的输出是后一个 Skill 的输入。

```
Skill A → Skill B → Skill C
```

**映射规则**：
- `loop.maker.description`：按顺序描述完整流水线
- `loop.checker.rubric.dimensions`：每个 Skill 的输出质量各占一个维度
- `loop.stop_conditions.success`：最后一个 Skill 的验收标准
- `loop.dependencies`：列出所有参与 Skill

**示例**：需求分析 → 代码生成 → 测试验证 → 发布部署

### 并联模式（Parallel）

多个 Skill 独立执行，各自产出独立结果，最终汇总。

```
      → Skill A →
Session → Skill B → Aggregate
      → Skill C →
```

**映射规则**：
- `loop.maker.description`：描述并行执行和聚合逻辑
- `loop.checker.rubric.dimensions`：每个 Skill 一个维度 + 聚合质量一个维度
- `loop.stop_conditions.success`：所有 Skill 均通过
- `loop.dependencies`：列出所有参与 Skill

**示例**：前端审查 + 后端审查 + 安全审查 → 综合报告

### 选择模式（Conditional）

根据触发条件或输入特征，选择不同的 Skill 路径。

```
Session → 判断条件 → Skill A (条件1)
                   → Skill B (条件2)
                   → Skill C (条件3)
```

**映射规则**：
- `loop.maker.description`：描述判断逻辑和分支路径
- `loop.checker.rubric.dimensions`：各分支共享核心维度 + 各自特有维度
- `loop.stop_conditions.success`：所选分支的验收标准
- `loop.stop_conditions.failure`：判断失败或无匹配分支
- `loop.dependencies`：列出所有可能的 Skill

**示例**：根据错误类型选择修复策略（编译错误 → 编译修复 Skill / 运行时错误 → 运行时修复 Skill）

---

## 组合模式判定方法

| 判定信号 | 模式 |
|----------|------|
| session 中步骤严格按 A→B→C 顺序重复 | 串联 |
| session 中多个独立任务并行执行后汇总 | 并联 |
| session 中有 if/else 分支判断后再选择执行 | 选择 |
| 信号不明确 | 默认串联，标注需人工确认 |
