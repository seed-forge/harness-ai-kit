# ECharts 踩坑经验

## 踩坑 1: CustomChart 导入缺失

**症状**：ECharts 报错 "Series custom is used but not imported"

**根因**：使用了 `type: "custom"` 系列但没有导入 CustomChart 模块。

**修复**：
```typescript
import { CustomChart } from "echarts/charts";
echarts.use([CustomChart]);
```

**教训**：每种 ECharts 系列类型都需要单独导入并注册。使用前检查 `echarts/charts` 的可用导出。

---

## 踩坑 2: Vite 缓存导致 Outdated Optimize Dep

**症状**：`net::ERR_ABORTED 504 (Outdated Optimize Dep)`，ECharts 模块无法加载。

**根因**：Vite 的预构建缓存（node_modules/.vite）与新安装的 ECharts 版本不一致。

**修复**：
```bash
rm -rf node_modules/.vite
npm run dev  # 或 npm run build
```

**症状链**：
```
ECharts 版本升级 → Vite 缓存未更新 → Outdated Optimize Dep 504 → 图表空白
```

**教训**：安装新 ECharts 子模块后，如果出现模块加载错误，第一反应是清除 Vite 缓存。

---

## 踩坑 3: EffectScatter 需要额外导入

**症状**：`type: "effectScatter"` 系列渲染为空，无节点显示。

**根因**：EffectScatterChart 没有被导入和注册。

**修复**：
```typescript
import { EffectScatterChart } from "echarts/charts";
echarts.use([EffectScatterChart]);
```

**教训**：EffectScatter 是特殊系列，不在默认的 ScatterChart 中。

---

## 踩坑 4: Lines 系列需要 LineChart

**症状**：`type: "lines"` 系列不显示连线。

**根因**：LineChart 没有被导入。

**修复**：
```typescript
import { LinesChart } from "echarts/charts";
echarts.use([LinesChart]);
```

---

## 踩坑 5: 图表 resize 未处理

**症状**：窗口大小变化后图表不自适应。

**修复**：
```typescript
const ro = new ResizeObserver(() => chart.resize());
ro.observe(container);
(container as any).__chartResizeObserver = ro;
```

**清理**：
```typescript
export function disposeChart(chart, container) {
  if (chart && !chart.isDisposed()) chart.dispose();
  if (container?.__chartResizeObserver) {
    container.__chartResizeObserver.disconnect();
  }
}
```

---

## 踩坑 6: Astro Islands 中 ECharts script 类型

**症状**：Astro 的 `<script>` 标签在构建时被处理为模块，导致全局变量不可用。

**修复**：使用 `<script>` 而非 `<script type="module">`，或通过 import 直接使用。

---

## 踩坑 7: prefers-reduced-motion 下图表静止

**症状**：用户开启系统"减少动画"后，图表完全不显示。

**修复**：在 CSS 中添加降级样式，在 JS 中检测并跳过动画初始化。

```css
@media (prefers-reduced-motion: reduce) {
  .chart { opacity: 1 !important; }
}
```

```typescript
const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
if (!prefersReducedMotion) {
  // 初始化动画图表
} else {
  // 显示静态版本
}
```
