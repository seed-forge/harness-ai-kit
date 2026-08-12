---
name: devlab-tech-fit-eval
description: 评估技术库/框架与项目需求的适配度，识别结合点、约束和集成方案。适用于技术选型决策、库集成可行性分析、框架迁移评估。 Triggers on "tech fit", "技术适配", "库评估", "framework evaluation", "library fit", "技术选型评估".
allowed-tools: Agent, AskUserQuestion, Read, Bash, Glob, Grep, Write, WebSearch
---

# devlab-tech-fit-eval

技术库/框架与项目需求的适配度评估 Skill。通过结构化的 6 阶段流程，分析技术库的能力边界、项目的需求匹配度、集成约束和风险，产出可执行的技术选型建议。

## Architecture Overview

```
Phase 0: Specification Study (Mandatory prerequisite)
         ↓
Phase 1: Project Exploration    → project-context.md
         ↓
Phase 2: Library Research       → library-analysis.md
         ↓
Phase 3: Fit Point Identification → fit-points.md
         ↓
Phase 4: Constraint Definition  → constraints.md
         ↓
Phase 5: Synthesis & Recommendation → tech-fit-report.md
```

## Key Design Principles

1. **Evidence-Based**: 所有结论必须有代码/配置/文档证据支撑
2. **Structured Analysis**: 按固定流程分析，避免遗漏关键维度
3. **Actionable Output**: 产出必须包含具体的集成方案和风险缓解措施
4. **Role-Diverse**: 支持多角色视角（架构师、UI 设计师、产品经理等）的并行分析
5. **Boundary-Aware**: 明确界定「不做」的范围，避免过度分析

---

## Mandatory Prerequisites

> **Do NOT skip**: Before performing any operations, you **must** completely read the following documents.

### Specification Documents (Required Reading)

| Document | Purpose | Priority |
|----------|---------|----------|
| [specs/fit-criteria.md](specs/fit-criteria.md) | 适配评估维度和评分标准 | **P0 - Must read** |
| [specs/analysis-template.md](specs/analysis-template.md) | 分析产出的标准结构 | **P0 - Must read** |

---

## Execution Flow

### Phase 1: Project Exploration

**目标**: 理解项目的定位、技术栈、需求和约束

**步骤**:
1. 读取项目根目录的关键文件：`package.json`, `README.md`, `CLAUDE.md`, 配置文件
2. 扫描项目结构，识别技术栈（框架、构建工具、测试框架）
3. 提取项目的业务定位和核心需求
4. 识别项目的设计语言（主题系统、颜色方案、组件库）

**输出**: `project-context.md` — 项目上下文包

### Phase 2: Library Research

**目标**: 深入理解技术库的能力、限制和生态

**步骤**:
1. 研究库的官方文档、GitHub README、API 参考
2. 分析库的核心能力、支持的平台、性能特征
3. 研究库的生态（框架集成、社区活跃度、维护状态）
4. 识别库的限制和已知问题

**输出**: `library-analysis.md` — 技术库分析报告

### Phase 3: Fit Point Identification

**目标**: 识别库能力与项目需求的结合点

**步骤**:
1. 将项目需求映射到库的能力矩阵
2. 识别高价值结合点（核心需求匹配）
3. 识别潜在冲突（技术栈不兼容、性能瓶颈）
4. 识别机会点（库的独特能力可以提升项目）

**输出**: `fit-points.md` — 适配点清单

### Phase 4: Constraint Definition

**目标**: 明确集成约束、风险和缓解措施

**步骤**:
1. 定义技术约束（版本兼容、构建工具、运行时限制）
2. 定义性能约束（包体积、渲染性能、内存占用）
3. 定义维护约束（依赖版本、社区支持、迁移成本）
4. 制定风险缓解措施

**输出**: `constraints.md` — 约束与风险清单

### Phase 5: Synthesis & Recommendation

**目标**: 综合所有分析，产出可执行的技术选型建议

**步骤**:
1. 汇总所有阶段的发现
2. 进行多角色分析（架构师、UI 设计师、产品经理视角）
3. 产出技术选型建议（推荐/不推荐/有条件推荐）
4. 制定实施路线图（分阶段、优先级）

**输出**: `tech-fit-report.md` — 技术适配评估报告

---

## Directory Setup

```javascript
const workDir = `.devlab/tech-fit-eval`;

Bash(`mkdir -p "${workDir}"`);
```

## Output Structure

```
.devlab/
├── tech-fit-eval/
│   ├── project-context.md       # 项目上下文包
│   ├── library-analysis.md      # 技术库分析报告
│   ├── fit-points.md            # 适配点清单
│   ├── constraints.md           # 约束与风险清单
│   └── tech-fit-report.md       # 技术适配评估报告（最终产出）
```

---

## Completion Protocol

Follow [Completion Status Protocol](../_shared/SKILL-DESIGN-SPEC.md#13) and [Escalation Protocol](../_shared/SKILL-DESIGN-SPEC.md#14).

---

## Reference Documents by Phase

### Phase 1: Project Exploration

| Document | Purpose | When to Use |
|----------|---------|-------------|
| [specs/fit-criteria.md](specs/fit-criteria.md) | 适配评估维度 | 确定需要收集哪些项目信息 |

### Phase 2: Library Research

| Document | Purpose | When to Use |
|----------|---------|-------------|
| [specs/analysis-template.md](specs/analysis-template.md) | 分析产出结构 | 确保库分析报告的完整性 |

### Phase 3-4: Fit & Constraints

| Document | Purpose | When to Use |
|----------|---------|-------------|
| [specs/fit-criteria.md](specs/fit-criteria.md) | 适配评分标准 | 评估结合点的价值和风险 |

### Phase 5: Synthesis

| Document | Purpose | When to Use |
|----------|---------|-------------|
| [specs/analysis-template.md](specs/analysis-template.md) | 最终报告结构 | 确保技术选型报告的完整性 |

### Debugging & Troubleshooting

| Issue | Solution Document |
|-------|-------------------|
| 项目探索不充分 | [specs/fit-criteria.md](specs/fit-criteria.md) — 检查评估维度是否覆盖 |
| 库研究不深入 | [specs/analysis-template.md](specs/analysis-template.md) — 检查分析结构是否完整 |
| 结合点识别不准确 | 回到 Phase 3 重新映射需求到能力矩阵 |

---


## 推荐输出格式

执行完毕后按以下结构输出：

**状态**：✅ 成功 / ⚠️ 部分成功 / ❌ 失败

| <评估/选型结论/推荐> | <值/状态> | 说明 |
|------|------|------|

**下一步**：<可执行动作>

## Example

**场景**: 评估 rough.js 库与 personal-brand-showcase 项目的适配度

**输入**:
- 项目路径: `C:\Users\Working\Documents\02-工程工作空间\personal-brand-showcase`
- 技术库: rough.js (手绘风格 SVG/Canvas 渲染库)

**合格输出应包含**:
1. 项目上下文：Astro 5.x SSG、chalkboard 主题、ECharts 雷达图、Cytoscape 拓扑图
2. 库分析：rough.js 核心能力、SVG/Canvas 双渲染、手绘风格参数
3. 适配点：Tech Radar 手绘化、Skill Topology 手绘边框、rough-annotation 标注
4. 约束：Astro 集成方式、性能影响、暗色主题适配
5. 建议：推荐集成、分阶段实施、优先级排序
