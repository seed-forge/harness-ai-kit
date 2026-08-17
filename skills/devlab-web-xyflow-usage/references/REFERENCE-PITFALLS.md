# XYFlow 踩坑经验参考

## Pitfall 1: 节点内按钮点击被 XYFlow 吞掉

### 现象

在自定义节点内放置 `<button>`，点击按钮时 XYFlow 拦截了 `pointerdown` 事件，按钮的 `onClick` 不触发。

### 原因

XYFlow 在底层用 `pointerdown` 监听拖拽事件，在事件冒泡到节点之前就被拦截了。

### 尝试过但无效的方案

| 方案 | 结果 |
|------|------|
| `e.stopPropagation()` 在 `onClick` 中 | ❌ 不够，XYFlow 在更底层拦截 |
| `e.stopPropagation()` 在 `onMouseDown` 中 | ❌ 不够 |
| `e.stopPropagation()` 在 `onPointerDown` 中 | ⚠️ 有时有效，不可靠 |
| CSS class `nodrag nopan` | ⚠️ 节点级别有效，子元素不一定有效 |

### 最终方案

**容器级 click 委托 + `data-*` 属性标记**：

```tsx
// 自定义节点：用 <span data-role="xxx"> 替代 <button>
function StageNode({ data }: NodeProps) {
  return (
    <div className="stage-node">
      {data.roleTasks.map((rt, i) => (
        <span key={i} className="stage-node__tag" data-role={rt.role}>
          {rt.role}
        </span>
      ))}
    </div>
  );
}

// 父组件：在容器 div 上监听 click，通过 closest() 查找目标
function LifecycleFlow() {
  const handleContainerClick = useCallback((e: React.MouseEvent) => {
    const tag = (e.target as HTMLElement).closest?.(".stage-node__tag");
    if (!tag) return;
    const role = (tag as HTMLElement).dataset.role;
    // ... 处理逻辑
  }, []);

  return (
    <div ref={containerRef} onClick={handleContainerClick}>
      <ReactFlow nodes={nodes} ... />
    </div>
  );
}
```

### 关键点

- 节点内不用 `<button>`，用 `<span data-xxx="yyy">` + CSS `cursor: pointer`
- 父组件用 `onClick` 委托，通过 `closest(".xxx")` 定位目标元素
- 同时设置 `panOnDrag={false}` 禁止画布平移（否则整个画布会跟着拖）

---

## Pitfall 2: `pointer-events: none` 内联样式覆盖不了

### 现象

XYFlow 动态在每个节点 wrapper 上设置 `style="pointer-events: none"`，导致节点内部所有交互元素无法响应鼠标事件。

### 原因

XYFlow 内部在某些配置下会给节点 wrapper 添加 `pointer-events: none`，内联样式优先级高于 CSS。

### 解法

CSS 强制覆盖：

```css
.react-flow__node { pointer-events: auto !important; }
```

同时给需要交互的子元素也加：

```css
.stage-node__tag {
  pointer-events: auto !important;
  cursor: pointer;
}
```

---

## Pitfall 3: `client:visible` 导致 ReactFlow 容器 height: 0

### 现象

Astro 中用 `client:visible` 包装 ReactFlow 组件，ReactFlow 控制台报错：

```
The parent container needs a width and a height to render the graph
```

### 原因

`client:visible` 会先渲染 HTML 骨架（无 React），此时容器 div 尺寸为 0。ReactFlow 的 `height: 100%` 解析为 0。

### 解法

改用 `client:only="react"`：

```astro
<FlowComponent client:only="react" />
```

或者在容器 div 上设置固定尺寸：

```tsx
<div style={{ width: "100%", height: "600px" }}>
  <ReactFlow ... />
</div>
```

### 选型规则

| 场景 | 用 `client:visible` | 用 `client:only="react"` |
|------|---------------------|--------------------------|
| 组件需要确定的容器尺寸 | ❌ | ✅ |
| 首屏不需要展示 | ✅ | ❌ |
| 依赖浏览器 API | ❌ | ✅ |

---

## Pitfall 4: 暗色主题下节点不可见

### 现象

设置 `colorMode="dark"` 后，画布背景变暗，但节点仍然是白色背景/黑色文字，或者完全透明不可见。

### 原因

`colorMode="dark"` 只改变画布背景和默认样式，不改变自定义节点的 DOM 内容。自定义节点需要自己处理暗色主题。

### 解法

```tsx
<ReactFlow colorMode="dark" ... />

// CSS 中使用项目的设计系统变量
.stage-node {
  background: var(--color-surface);
  border: 2px solid var(--color-border);
  color: var(--color-text);
}
```

---

## Pitfall 5: 拖拽光标抓手

### 现象

鼠标悬停在画布上时显示抓手光标（grab cursor），影响交互体验。

### 原因

XYFlow 默认启用 `panOnDrag`，画布可拖拽平移。

### 解法

```tsx
<ReactFlow
  panOnDrag={false}
  nodesDraggable={false}
  nodesConnectable={false}
  elementsSelectable={false}
  preventScrolling={false}
/>
```

如果需要部分节点可拖拽，用 CSS class 控制：

```css
.react-flow__node { cursor: default; }
.react-flow__node.draggable { cursor: grab; }
```

---

## Pitfall 6: fitView 后节点位置偏移

### 现象

`fitView` 后节点位置与预期不符，或者缩放级别不对。

### 原因

`fitView` 在节点尚未完全渲染到 DOM 时调用，计算的尺寸不准确。

### 解法

延迟调用：

```tsx
useEffect(() => {
  const timer = setTimeout(() => fitView({ padding: 0.3 }), 100);
  return () => clearTimeout(timer);
}, [fitView]);
```

或者用 `onInit` 回调：

```tsx
<ReactFlow onInit={() => fitView({ padding: 0.3 })} ... />
```

---

## Pitfall 7: `@dagrejs/dagre` compound mode 报 `Cannot set properties of undefined (setting 'rank')`

### 现象

使用 `@dagrejs/dagre` 的 `{ compound: true }` 模式布局包含 group 节点的图时，运行时报错：

```
Cannot set properties of undefined (setting 'rank')
```

堆栈指向 `network-simplex.ts` → `util.ts`。

### 原因

dagre compound mode 下，`setEdge` 如果传入了 group 节点 ID 作为 source 或 target，dagre 内部的 `rank` 赋值会访问不存在的节点元数据。这是 dagre 的已知 bug——compound mode 的 edge 引用处理不完整。

### 尝试过但无效的方案

| 方案 | 结果 |
|------|------|
| group 节点 width/height 设为 0 | ❌ 报错（dagre 仍尝试计算 rank） |
| 先 `setNode` 再 `setEdge` 最后 `setParent` | ❌ 顺序无关 |
| 只对叶子节点 `setEdge` | ❌ 如果 edge 的 source/target 是 group 节点仍然报错 |

### 最终方案：两阶段布局

**Phase 1** — 只对叶子节点布局（无 compound mode）：

```typescript
const g = new Dagre.graphlib.Graph().setDefaultEdgeLabel(() => ({}));
g.setGraph({ rankdir: "TB", ranksep: 180, nodesep: 100 });

// 只加叶子节点
leafNodes.forEach(node => g.setNode(node.id, { width: 160, height: 50 }));

// 只加叶子节点之间的边（跳过涉及 group 的边）
edges.forEach(edge => {
  if (g.hasNode(edge.source) && g.hasNode(edge.target)) {
    g.setEdge(edge.source, edge.target);
  }
});

Dagre.layout(g);
```

**Phase 2** — 从叶子位置反推 group 包围盒：

```typescript
groupNodes.forEach(group => {
  const children = nodes.filter(n => n._parent === group.id);
  const childBounds = children.map(c => positioned.get(c.id)).filter(Boolean);

  const pad = 40;
  const minX = Math.min(...childBounds.map(c => c.x)) - pad;
  const maxX = Math.max(...childBounds.map(c => c.x + c.w)) + pad;
  const minY = Math.min(...childBounds.map(c => c.y)) - pad - 20; // 额外顶部空间给标签
  const maxY = Math.max(...childBounds.map(c => c.y + c.h)) + pad;

  positioned.set(group.id, { x: minX, y: minY, w: maxX - minX, h: maxY - minY });
});
```

### 关键点

- **永远不要**在 dagre compound mode 下 `setEdge` 引用 group 节点 ID
- 两阶段法（先叶子 → 再反推 group）完全绕过 compound mode
- group 节点的 `position` 是左上角坐标（相对于父级），`style.width/height` 是包围盒尺寸

---

## Pitfall 8: React Flow compound nodes (`parentId` + `extent`) 导致子节点重叠

### 现象

使用 React Flow 的 compound node 特性（`parentId` + `extent: 'parent'`）配合 dagre 布局时，子节点互相重叠、group 框错位。

### 原因

React Flow 的 compound node 对 position 的解释与 dagre 输出不兼容：
- dagre 输出的是**绝对坐标**
- React Flow compound node 要求子节点 position 是**相对于父节点的坐标**
- 两者的坐标系不一致，导致子节点叠加在同一个位置

### 最终方案：独立背景节点

**完全不用** `parentId` / `extent`。改为：

1. group 节点不设 `parentId`，作为独立节点，`zIndex: 0`
2. 子节点 `zIndex: 1`（显示在 group 上方）
3. 在节点 `data` 中存储 `_parent` 字段，供布局引擎识别父子关系
4. 布局引擎根据 `_parent` 计算 group 包围盒

```typescript
// 节点映射
nodes.push({
  id: n.id,
  type: n.isGroup ? "group" : "service",
  position: { x: 0, y: 0 },
  data: { ...data, _parent: n.parent || null },
  zIndex: n.isGroup ? 0 : 1,
  // 注意：不设 parentId，不设 extent
});

// group 节点样式（独立背景）
{
  selector: "node[type='group']",
  style: {
    "background-color": "rgba(19,24,40,0.5)",
    "border": "2px dashed #5A6478",
    "border-radius": "12px",
    // width/height 由布局引擎动态计算
  }
}
```

### 关键点

- React Flow compound nodes 的 position 坐标系是**相对于父节点**的，dagre 给的是绝对坐标，两者不兼容
- 独立背景节点 + `zIndex` 是最可靠的 group 方案
- `_parent` 存在 `data` 中而非 `parentId`，避免 React Flow 的 compound node 机制介入

### 补充：完整实现模式（preset 坐标表 + group 包围盒反推）

当节点数量 < 30 时，preset 坐标表比 dagre 更可控。完整实现分三步：

**Step 1 — 节点映射（不设 parentId/extent）**：

```typescript
// topo-flow-types.ts
for (const n of view.nodes) {
  nodes.push({
    id: n.id,
    type: n.isGroup ? "group" : "service",
    position: { x: 0, y: 0 },  // 由布局引擎计算
    data: { ...data, _parent: n.parent || null },
    zIndex: n.isGroup ? 0 : 1,  // group 在底层
  });
}
```

**Step 2 — preset 坐标表（按 node ID 匹配）**：

```typescript
// topo-flow-layout.ts
function getPresetPositions(nodes) {
  const positions = new Map();
  const nodeIds = new Set(nodes.map(n => n.id));

  // 根据 node ID 特征判断当前是哪个视图
  if (nodeIds.has("layer-app")) {
    // architecture view
    positions.set("agent-hub", { x: 0, y: -160 });
    positions.set("app-brand", { x: -180, y: 0 });
    positions.set("app-chat", { x: 0, y: 0 });
    positions.set("app-search", { x: 180, y: 0 });
    positions.set("mw-dify", { x: -200, y: 200 });
    // ... 每个叶子节点一个坐标
  }

  if (nodeIds.has("biz-dev")) {
    // business view — 2×2 grid
    positions.set("agent-hub", { x: 0, y: -140 });
    positions.set("b-gitea", { x: -340, y: 80 });
    // ...
  }
  return positions;
}
```

**Step 3 — group 包围盒从子节点反推**：

```typescript
// 先应用叶子节点坐标
leafNodes.forEach(node => {
  const pos = presetPositions.get(node.id);
  if (pos) positioned.set(node.id, { x: pos.x, y: pos.y, w: nodeWidth, h: nodeHeight });
});

// 再计算 group 包围盒（从 data._parent 识别父子关系）
groupNodes.forEach(group => {
  const children = nodes.filter(n => (n.data as any)._parent === group.id);
  const childBounds = children.map(c => positioned.get(c.id)).filter(Boolean);

  const padX = 30, padY = 40;
  const minX = Math.min(...childBounds.map(c => c.x)) - padX;
  const maxX = Math.max(...childBounds.map(c => c.x + c.w)) + padX;
  const minY = Math.min(...childBounds.map(c => c.y)) - padY;   // 额外顶部空间给标签
  const maxY = Math.max(...childBounds.map(c => c.y + c.h)) + padX;

  positioned.set(group.id, { x: minX, y: minY, w: maxX - minX, h: maxY - minY });
});

// 应用到节点
return nodes.map(node => {
  const pos = positioned.get(node.id);
  if (!pos) return node;
  if (groupIds.has(node.id)) {
    return { ...node, position: { x: pos.x, y: pos.y },
      style: { ...node.style, width: pos.w, height: pos.h } };
  }
  return { ...node, position: { x: pos.x, y: pos.y } };
});
```

**为什么选 preset 而非 dagre**：
- dagre 两阶段布局（先叶子 → 再反推 group）理论上可行，但当边引用 group 节点时仍会 crash（Pitfall 7）
- preset 坐标表对 < 30 节点的架构图完全够用，且位置 100% 可控
- 维护成本：新增/删除节点时需要手动更新坐标表（约 5 分钟），但避免了 dagre 的不可预测性

---

## Pitfall 9: 自定义节点没有 Handle，所有边静默丢弃

### 现象

为自定义节点创建了边数据，但 `.react-flow__edges` 宽高为 0，内部无任何 `<g>` 元素。控制台报：

```
[React Flow]: Couldn't create edge for source handle id: "null", edge id: xxx→yyy
```

所有边都报这个错误，重复刷新也无法恢复。

### 原因

@xyflow/react v12 中，自定义节点**必须显式声明 `<Handle>` 组件**。即使边数据的 `source`/`target` id 正确，如果没有 Handle，xyflow 找不到连接点，直接静默丢弃整条边。

### 尝试过但无效的方案

| 方案 | 结果 |
|------|------|
| 重新注册 `edgeTypes` | ❌ 边类型没问题，是节点缺少 Handle |
| 检查 edge 的 `source`/`target` id | ❌ id 正确，但没有 Handle 可连接 |
| 给 edge 加 `style` / `markerEnd` | ❌ 边根本没渲染，样式无从生效 |
| 自定义边组件 `FlowingEdge` | ❌ 自定义边也依赖 Handle 才能渲染 |

### 最终方案

**每个自定义节点必须声明 Handle**（即使视觉上隐藏）：

```tsx
import { Handle, Position } from "@xyflow/react";

function MyNode({ data }) {
  return (
    <div className="my-node">
      {/* 作为连线目标：声明 target Handle */}
      <Handle type="target" position={Position.Top} id="top" style={{ opacity: 0 }} />
      {/* 自定义内容 */}
      <div>{data.label}</div>
      {/* 作为连线源：声明 source Handle */}
      <Handle type="source" position={Position.Bottom} id="bottom" style={{ opacity: 0 }} />
    </div>
  );
}
```

### 关键点

- **v12 的 Handle 是强制要求**，不是可选的——没有 Handle = 没有边
- Handle 的 `position` 决定连线从哪个方向画出，`id` 供 edge 数据中的 `sourceHandle`/`targetHandle` 引用
- 用 `style={{ opacity: 0, width: 1, height: 1 }}` 可以隐藏 Handle 的视觉表现但保留 DOM 连接点
- 同一节点可以有多个 Handle（如 target 在顶部、source 在底部），用不同 `id` 区分
- **诊断技巧**：如果边看不到，第一件事检查 `.react-flow__edges` 的宽高和内容——为 0 就是 Handle 问题

---

## Pitfall 10: html-to-image 截图 ReactFlow 画布内容不完整

### 现象

使用 `html-to-image`（`toPng`/`toSvg`）对 ReactFlow 容器截图，导出的图片只有可视区域内的内容，超出区域的节点被裁剪或缺失。

### 原因

ReactFlow 的 `.react-flow` 容器默认 `overflow: hidden`，`.react-flow__viewport` 只渲染视口内的节点。`html-to-image` 截图时忠实反映当前 DOM 的可见状态，不会展开隐藏内容。

### 尝试过但无效的方案

| 方案 | 结果 |
|------|------|
| 直接 `toPng(flowEl)` | ❌ 只截到可视区域 |
| 设置 `style.transform` 移动 viewport | ⚠️ 部分节点可见，但容器尺寸仍受限 |

### 最终方案

截图前临时解锁容器尺寸，截图后恢复：

```typescript
// 1. 获取所有节点边界
const bounds = getNodesBounds(nodes);
const padding = 60;
const width = Math.round(bounds.width + padding * 2);
const height = Math.round(bounds.height + padding * 2);
const { x, y, zoom } = getViewportForBounds(bounds, width, height, 0.5, 2, 0.2);

// 2. 保存原始样式
const origContainer = container.style.cssText;
const origFlow = flowEl.style.cssText;
const origVp = viewportEl.style.transform;

// 3. 临时解锁
container.style.width = `${width}px`;
container.style.height = `${height}px`;
container.style.overflow = "visible";
flowEl.style.width = `${width}px`;
flowEl.style.height = `${height}px`;
flowEl.style.overflow = "visible";
viewportEl.style.transform = `translate(${x}px, ${y}px) scale(${zoom})`;

// 4. 截图
const dataUrl = await toPng(flowEl, { backgroundColor: "#0B0F19", pixelRatio: 2 });

// 5. finally 恢复
container.style.cssText = origContainer;
flowEl.style.cssText = origFlow;
viewportEl.style.transform = origVp;
```

### 关键点

- **三步解锁**：`container` + `flowEl` + `viewportEl` 都要改，缺一不可
- `getViewportForBounds` 计算精确的平移+缩放，确保所有节点完整呈现
- `pixelRatio: 2` 输出高清图
- 如果节点有 FlipCard 翻转效果，截图前需强制 `transform: none` 并隐藏背面（`display: none`），避免 `backface-visibility` 干扰 html-to-image
- **必须在 `finally` 中恢复**原始样式，否则页面布局会被破坏

---

## Pitfall 11: ReactFlow 画布拦截页面纵向滚动

### 现象

ReactFlow 画布嵌入页面后，鼠标在画布区域内滚动时，页面不会纵向滚动，只有画布缩放或完全无响应。

### 原因

ReactFlow 默认 `preventScrolling={true}`，在画布的容器上监听 `wheel` 事件并调用 `event.preventDefault()`，阻止了浏览器的默认滚动行为。即使设置 `zoomOnScroll={false}`，`preventScrolling` 仍然生效。

### 最终方案

两个属性配合使用：

```tsx
<ReactFlow
  zoomOnScroll={false}        // 禁止滚轮缩放画布
  preventScrolling={false}     // 允许事件穿透到页面滚动
  zoomOnPinch={true}           // 触控板双指缩放仍可用
/>
```

### 关键点

- **`zoomOnScroll={false}` 不等于允许页面滚动**——`preventScrolling` 是独立的控制项
- `preventScrolling` 默认 `true`，会无条件 `preventDefault()` wheel 事件
- 设为 `false` 后，滚轮在画布区域只触发页面滚动，不缩放画布
- 如果需要画布内滚轮缩放 + 页面滚动共存，需自定义 wheel 事件处理（按区域判断）
