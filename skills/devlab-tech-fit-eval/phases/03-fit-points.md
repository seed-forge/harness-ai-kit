# Phase 3: Fit Point Identification

**目标**: 识别库能力与项目需求的结合点，产出适配点清单。

## Objective

- 将项目需求映射到库的能力矩阵
- 识别高价值结合点
- 识别潜在冲突
- 进行适配评分
- 产出标准化的 fit-points.md

## Execution Steps

### Step 1: 需求-能力映射

将 project-context.md 中的项目需求逐条映射到 library-analysis.md 中的库能力：

```
项目需求 → 库能力 → 匹配度评估
```

### Step 2: 识别高价值结合点

筛选条件：
- 项目核心需求被库核心能力覆盖
- 结合后能显著提升项目价值
- 实现复杂度可控

### Step 3: 识别潜在冲突

检查维度：
- 技术栈不兼容（如 SSR vs Client-only）
- 性能瓶颈（如包体积过大、渲染开销）
- API 设计差异（如状态管理方式不同）

### Step 4: 识别机会点

库的独特能力可能带来：
- 竞争对手没有的差异化特性
- 用户体验的显著提升
- 技术展示的新维度

### Step 5: 适配评分

按照 `specs/fit-criteria.md` 中的维度和权重，逐项评分并计算加权总分。

### Step 6: 生成 fit-points.md

按照 `specs/analysis-template.md` 中的结构，生成适配点清单。

## Output

- **File**: `fit-points.md`
- **Location**: `.workflow/.tech-fit/{timestamp}/`
- **Format**: Markdown

## Next Phase

Proceed to [Phase 4: Constraint Definition](04-constraints.md) with the generated fit-points.md.
