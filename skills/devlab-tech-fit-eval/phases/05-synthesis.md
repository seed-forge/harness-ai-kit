# Phase 5: Synthesis & Recommendation

**目标**: 综合所有分析，产出可执行的技术选型建议报告。

## Objective

- 汇总所有阶段的发现
- 进行多角色分析（架构师、UI 设计师、产品经理视角）
- 产出技术选型建议（推荐/不推荐/有条件推荐）
- 制定实施路线图
- 产出标准化的 tech-fit-report.md

## Execution Steps

### Step 1: 汇总发现

读取前 4 个阶段的产出，提取关键发现：
- project-context.md → 项目需求和约束
- library-analysis.md → 库能力和限制
- fit-points.md → 结合点和评分
- constraints.md → 风险和缓解

### Step 2: 多角色分析

**架构师视角**:
- 技术架构影响
- 集成复杂度
- 长期维护成本

**UI 设计师视角**:
- 视觉效果影响
- 用户体验提升
- 设计一致性

**产品经理视角**:
- 业务价值
- 用户感知
- 竞争差异化

### Step 3: 产出技术选型建议

基于适配评分和多角色分析，给出明确建议：

| 总分范围 | 建议 |
|---------|------|
| 4.5 - 5.0 | 强烈推荐 |
| 3.5 - 4.4 | 推荐集成 |
| 2.5 - 3.4 | 有条件推荐 |
| 1.5 - 2.4 | 不推荐 |
| 1.0 - 1.4 | 强烈不推荐 |

### Step 4: 制定实施路线图

分阶段规划：
- Phase 1: 基础集成（核心功能）
- Phase 2: 深度定制（优化体验）
- Phase 3: 扩展应用（高级功能）

每个阶段包含：目标、任务、时间、产出。

### Step 5: 决策记录

记录所有关键决策的依据和影响。

### Step 6: 生成 tech-fit-report.md

按照 `specs/analysis-template.md` 中的结构，生成技术适配评估报告。

## Output

- **File**: `tech-fit-report.md`
- **Location**: `.workflow/.tech-fit/{timestamp}/`
- **Format**: Markdown

## Completion

所有阶段完成，产出完整的技术适配评估报告。

```
## STATUS: DONE

**Summary**: 技术适配评估完成

### Details
- Phases completed: 5/5
- Key outputs: tech-fit-report.md
```
