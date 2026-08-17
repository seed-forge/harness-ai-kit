---
name: devlab-web-xyflow-usage
description: "@xyflow/react 使用指南：核心概念、自定义节点、Astro Islands 集成、6 条踩坑经验。"
---

# devlab-web-xyflow-usage

## 库信息

| 项 | 值 |
|---|---|
| 名称 | @xyflow/react (React Flow) |
| GitHub | https://github.com/xyflow/xyflow |
| 官方文档 | https://reactflow.dev |
| npm | https://www.npmjs.com/package/@xyflow/react |
| 当前版本 | ^12.11.1 |
| 核心能力 | 节点-边画布、自定义节点/边类型、zoom/pan、拖拽、连线、子流程 |
| 体积 | ~150KB (react + xyflow) |

## 适用场景

- 需要可交互的节点-边画布（流程图、拓扑图、生命周期地图等）
- 节点需要完全自定义 DOM 结构
- 需要 zoom/pan/fitView 画布控制
- 需要节点展开/折叠、点击交互
- 已有 React 19 环境

## 不适用场景

- 简单的时间线/甘特图 → 用 vis-timeline 或纯 CSS
- 纯静态的流程图展示 → 用 SVG/Canvas 直接画
- 需要亚像素级精度的图表 → 用 ECharts/D3

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

const nodeTypes = { my: MyNode };
```

### 画布配置

```tsx
<ReactFlow
  nodes={nodes}
  edges={edges}
  nodeTypes={nodeTypes}
  colorMode="dark"         // 暗色主题
  fitView                  // 自动适配视口
  nodesDraggable={false}   // 禁止拖拽节点
  nodesConnectable={false} // 禁止连线
  elementsSelectable={false}
  panOnDrag={false}        // 禁止画布平移
  preventScrolling={false} // 允许页面滚动
/>
```

## Astro + React Islands 集成

### 包装组件

```astro
---
// Wrapper.astro
import FlowComponent from "./FlowComponent.tsx";
---

<!-- client:only 跳过 SSR，适合需要确定尺寸的组件 -->
<FlowComponent client:only="react" />

<!-- client:visible 延迟加载，适合首屏不需要的组件 -->
<FlowComponent client:visible />
```

### 选型规则

| 场景 | 用 `client:visible` | 用 `client:only="react"` |
|------|---------------------|--------------------------|
| 组件需要确定的容器尺寸 | ❌ SSR 后尺寸为 0 | ✅ 跳过 SSR |
| 首屏不需要展示 | ✅ 延迟加载 | ❌ 首屏加载 |
| 依赖浏览器 API | ❌ SSR 会报错 | ✅ 只在浏览器执行 |

### @astrojs/react 版本兼容矩阵

Astro 大版本与 `@astrojs/react` 存在**强绑定**关系，选错版本会导致 Vite 主版本冲突。

| Astro | @astrojs/react | Vite | @vitejs/plugin-react |
|-------|---------------|------|---------------------|
| 5.x   | **4.x**       | 6.x  | 4.x                 |
| 6.x   | **6.x**       | 8.x  | 5.x                 |

**错误组合症状链**（Astro 5 + `@astrojs/react@6`）：

```
@astrojs/react@6 → @vitejs/plugin-react@5 → Vite 8
Astro 5.x 内置 Vite 6
两个 Vite 主版本在同一进程中冲突
  → "Missing field 'moduleType'" (builtin:vite-react-refresh-wrapper)
  → 模块图状态不一致
  → 连锁 "No cached compile metadata"（看似缓存问题，实为版本冲突）
```

**验证方法**：`npm ls vite` 检查是否只有一个 Vite 主版本。

## 踩坑经验

详见 [references/REFERENCE-PITFALLS.md](references/REFERENCE-PITFALLS.md)。

关键摘要：

| # | 问题 | 解法 |
|---|------|------|
| 1 | 节点内按钮点击被 XYFlow 吞掉 | 容器级 click 委托 + `data-*` 属性 |
| 2 | `pointer-events: none` 内联样式覆盖不了 | CSS `!important` 无法覆盖内联样式 |
| 3 | `client:visible` 导致 height: 0 | 用 `client:only="react"` |
| 4 | 暗色主题节点不可见 | `colorMode="dark"` + 自定义 CSS |
| 5 | 拖拽光标抓手 | `panOnDrag={false}` |
| 6 | `@astrojs/react@6` + Astro 5 报 `Missing field 'moduleType'` | Astro 5 必须用 `@astrojs/react@4.x`；v6 专为 Astro 6 设计，拉入 Vite 8 与 Astro 5 内置的 Vite 6 冲突。见上方版本兼容矩阵 |
| 7 | 删除组件后 dev server 持续报 "No cached compile metadata" | ① `Ctrl+C` 停 server → ② `taskkill /F /IM node.exe`（确保端口释放）→ ③ 删 `.astro/` + `node_modules/.vite` → ④ 冷启动。浏览器 `Ctrl+Shift+R` 强刷。注意：此症状也可能由 #6 的版本冲突连锁引发，先用 `npm ls vite` 排除版本问题 |
| 8 | `@dagrejs/dagre` + compound nodes 报 `Cannot set properties of undefined (setting 'rank')` | dagre compound mode 有 bug，不能在 `setEdge` 中引用 group 节点 ID。解法：**两阶段布局** — ① 只对叶子节点调用 dagre（`{ compound: false }`），② 从叶子位置反推 group 包围盒（`minX/maxX/minY/maxY + padding`）赋给 group 节点的 `position` + `style.width/height` |
| 9 | React Flow compound nodes（`parentId` + `extent`）导致子节点重叠、group 框错位 | 不用 compound nodes。改为**独立背景节点方案**：group 节点不设 `parentId`，作为独立节点 `zIndex: 0`，子节点 `zIndex: 1`。布局引擎根据 `_parent`（存在 `data` 中）计算 group 包围盒并赋 `position + style.width/height`。group 节点用半透明虚线框渲染 |
| 10 | 自定义节点没有 Handle，所有边静默丢弃（`Couldn't create edge for source handle id: "null"`） | 每个自定义节点**必须**显式声明 `<Handle>` 组件（即使隐藏）。source 节点加 `type="source"`，target 节点加 `type="target"`，用 `style={{ opacity: 0 }}` 隐藏视觉但保留 DOM 连接点。**诊断技巧**：边看不到时，第一件事检查 `.react-flow__edges` 的宽高——为 0 就是 Handle 问题 |
| 11 | `html-to-image` 截图 ReactFlow 画布内容不完整 | ① 临时解锁容器 `width/height/overflow: visible`（container + flowEl + viewportEl 三步），② 通过 `getViewportForBounds` 计算精确 transform，③ 强制重置 FlipCard 状态避免 `backface-visibility` 干扰，④ `pixelRatio: 2` 高清输出，⑤ `finally` 中恢复原始样式 |
| 12 | ReactFlow 画布拦截页面纵向滚动 | `zoomOnScroll={false}`（禁止滚轮缩放）+ `preventScrolling={false}`（允许事件穿透到页面滚动）。仅靠 `zoomOnScroll={false}` 不够——默认 `preventScrolling=true` 仍会 `preventDefault()` 滚轮事件 |

## 画布控制配置速查

嵌入式场景（ReactFlow 作为页面一部分而非全屏）的推荐配置：

| 配置 | 默认值 | 嵌入式推荐 | 说明 |
|------|--------|-----------|------|
| `zoomOnScroll` | `true` | `false` | 禁止滚轮缩放，避免与页面滚动冲突 |
| `preventScrolling` | `true` | `false` | 允许 wheel 事件穿透到页面纵向滚动 |
| `zoomOnPinch` | `true` | `true` | 触控板双指缩放仍可用 |
| `panOnDrag` | `true` | `true` | 允许鼠标拖拽平移画布 |
| `nodesDraggable` | `true` | 按需 | 节点是否可拖拽重排 |
| `nodesConnectable` | `true` | `false` | 禁止用户手动连线 |
| `elementsSelectable` | `true` | `false` | 禁止点击选中 |

## 推荐输出格式

执行完毕后输出极简回执：**状态**（✅ 成功 / ⚠️ 部分成功 / ❌ 失败）+ **关键结果**（1-2 行，如操作对象、产出位置、下一步）。无需强制套用大表格。


## 约束

- 自定义节点内的交互元素必须用容器级事件委托，不能直接在节点内绑定 onClick
- 需要确定尺寸的容器必须用 `client:only="react"` 而非 `client:visible`
- 暗色主题下必须自定义节点背景色，XYFlow 默认只改画布背景

参考文档：references/REFERENCE-USAGE-DETAIL.md

参考文档：
- references/REFERENCE-README.md
