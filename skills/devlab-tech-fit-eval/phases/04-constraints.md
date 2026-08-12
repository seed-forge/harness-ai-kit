# Phase 4: Constraint Definition

**目标**: 明确集成约束、风险和缓解措施，产出约束与风险清单。

## Objective

- 定义技术约束（版本兼容、构建工具、运行时限制）
- 定义性能约束（包体积、渲染性能、内存占用）
- 定义维护约束（依赖版本、社区支持、迁移成本）
- 制定风险缓解措施
- 产出标准化的 constraints.md

## Execution Steps

### Step 1: 技术约束分析

检查维度：
- 库版本与项目技术栈的兼容性
- 构建工具支持（Vite/Webpack/Rollup）
- 运行时限制（浏览器支持、Node 版本）
- SSR/CSR/SSG 兼容性

### Step 2: 性能约束分析

评估指标：
- 包体积（gzipped）及对首屏加载的影响
- 运行时性能（渲染时间、内存占用）
- 降级策略（数据量阈值、移动端降级）

### Step 3: 集成约束分析

确定：
- 推荐的集成方式（直接引入、适配器、封装层）
- 与现有状态管理的集成方案
- 与现有主题系统的集成方案

### Step 4: 维护约束分析

评估：
- 库的版本更新策略
- 未来迁移的潜在成本
- 库不可用时的替代方案

### Step 5: 风险矩阵

为每个风险评估：
- 概率（高/中/低）
- 影响（高/中/低）
- 缓解措施

### Step 6: 定义 Non-Goals

明确排除的范围，避免过度分析。

### Step 7: 生成 constraints.md

按照 `specs/analysis-template.md` 中的结构，生成约束与风险清单。

## Output

- **File**: `constraints.md`
- **Location**: `.workflow/.tech-fit/{timestamp}/`
- **Format**: Markdown

## Next Phase

Proceed to [Phase 5: Synthesis & Recommendation](05-synthesis.md) with the generated constraints.md.
