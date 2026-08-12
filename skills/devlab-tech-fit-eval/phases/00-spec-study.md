# Phase 0: Specification Study

**目标**: 研读设计规范，确保后续产出符合质量标准。

## Objective

在执行任何分析之前，必须完整阅读以下规范文档，确保理解评估维度、产出结构和质量标准。

## Execution Steps

### Step 1: 阅读适配评估维度

```
Read: specs/fit-criteria.md
```

理解 6 个评估维度的定义、评分标准和加权公式：
- 功能匹配度 (30%)
- 技术兼容性 (25%)
- 性能影响 (15%)
- 集成复杂度 (15%)
- 维护成本 (10%)
- 生态成熟度 (5%)

### Step 2: 阅读产出结构规范

```
Read: specs/analysis-template.md
```

理解 5 个产出文件的标准结构：
- project-context.md
- library-analysis.md
- fit-points.md
- constraints.md
- tech-fit-report.md

### Step 3: 确认参数

从用户输入中提取：
- **项目路径**: 待评估项目的位置
- **技术库**: 待评估的库/框架名称
- **评估重点**: 用户关注的核心维度（如有）

## Output

- **变量**: `project_path`, `library_name`, `focus_dimensions`
- **状态**: 规范已研读，准备进入 Phase 1

## Next Phase

Proceed to [Phase 1: Project Exploration](01-project-exploration.md) with the readied specifications.
