---
name: devlab-web-xyflow-usage
description: "@xyflow/react (React Flow) 使用指南：核心概念、自定义节点、Astro Islands 集成、踩坑经验。适用于需要可交互节点-边画布的前端项目。"
argument-hint: "<具体问题或使用场景>"
---

# devlab-web-xyflow-usage

## 库信息

| 项 | 值 |
|---|---|
| 名称 | @xyflow/react (React Flow) |
| GitHub | https://github.com/xyflow/xyflow |
| 官方文档 | https://reactflow.dev |
| 当前版本 | ^12.11.1 |
| 体积 | ~150KB (react + xyflow) |

## 适用场景

- 需要可交互的节点-边画布（流程图、拓扑图、生命周期地图等）
- 节点需要完全自定义 DOM 结构
- 需要 zoom/pan/fitView 画布控制
- 需要节点展开/折叠、点击交互

## 不适用场景

- 简单时间线/甘特图 → vis-timeline 或纯 CSS
- 纯静态流程图 → SVG/Canvas
- 亚像素级精度图表 → ECharts/D3

## 核心概念

### 节点 (Node)

```typescript
interface Node {
  id: string;           // 唯一标识
  type: string;         // 对应 nodeTypes 中的组件名
  position: { x: number; y: number };  // 画布坐标
  data: Record<string, unknown>;       // 传递给自定义节点的数据
}
```

### 边 (Edge)

```typescript
interface Edge {
  id: string;
  source: string;       // 源节点 id
  target: string;       // 目标节点 id
  type?: string;        // 对应 edgeTypes 中的组件名
  animated?: boolean;
  style?: CSSProperties;
}
```

### 自定义节点

```tsx
import { Handle, Position, type NodeProps } from "@xyflow/react";

function MyNode({ data }: NodeProps) {
  return (
    <div className="my-node">
      <Handle type="target" position={Position.Left} />
      {/* 自定义内容 */}
      <Handle type="source" position={Position.Right} />
    </div>
  );
}

> 更多细节见 references/REFERENCE-USAGE-DETAIL.md

## 可直接复制的中文 Prompt

```text
请使用 devlab-web-xyflow-usage 技能，按照其 SKILL.md 描述的标准流程执行任务；
先做 dry-run/检查，向我展示结果与风险，经确认后再正式执行。
```
