---
name: devlab-web-echarts-usage
description: ECharts 在 Astro/前端项目中的完整集成指南，包含 tree-shaking、IntersectionObserver 按需加载、自定义系列集成、拓扑图实现、雷达图配置、Astro Islands 数据传递、调试经验。
---

# devlab-web-echarts-usage

## 用途

ECharts 在 Astro/前端项目中的完整集成指南，包含 tree-shaking、IntersectionObserver 按需加载、自定义系列集成、拓扑图实现、雷达图配置、调试经验。

**适用场景**：
- 在 Astro/React/Vue 项目中引入 ECharts 图表
- 需要 tree-shaking 以避免全量 300KB 加载
- 需要 IntersectionObserver 按需加载（视口进入才加载）
- 实现 force-directed 拓扑图、雷达图、散点图等
- 处理 ECharts 在 Astro Islands 模式下的数据传递

## 核心概念

### Tree-Shaking 导入

ECharts 必须使用 tree-shaking 导入，否则会加载全量 ~300KB：

```typescript
// ✅ 正确：只导入需要的子模块
import * as echarts from "echarts/core";
import { RadarChart, ScatterChart, EffectScatterChart } from "echarts/charts";
import { TooltipComponent, LegendComponent, GridComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

echarts.use([RadarChart, ScatterChart, EffectScatterChart, TooltipComponent, LegendComponent, GridComponent, CanvasRenderer]);

// ❌ 错误：全量导入
import * as echarts from "echarts";
```

### Astro Islands 数据传递

Astro 组件通过 `data-*` 属性传递数据到客户端脚本：

```astro
<div class="chart" data-scores={JSON.stringify(scores)}></div>

<script>
const container = document.querySelector('.chart');
const scores = JSON.parse(container.dataset.scores);
// 使用 scores 初始化 ECharts...
</script>
```

### IntersectionObserver 按需加载

图表不在首屏时，延迟加载以减少首屏 JS payload：

```typescript
export function observeChart(container, onReady) {
  const observer = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (entry.isIntersecting) {
        observer.unobserve(container);
        const chart = echarts.init(container);
        if (chart) onReady(chart);
      }
    }
  }, { rootMargin: "200px" });
  observer.observe(container);
}
```

## 实现流程

1. 确定目标图表类型（雷达图/拓扑图/折线图等）
2. 配置 tree-shaking imports（echarts/charts + echarts/components）
3. 设置 IntersectionObserver 按需加载
4. 实现图表渲染 + 响应式 resize
5. 处理 Astro Islands 集成（客户端脚本 + 数据传递）
6. 处理 prefers-reduced-motion 降级

## 推荐输出格式

执行完毕后输出极简回执：**状态**（✅ 成功 / ⚠️ 部分成功 / ❌ 失败）+ **关键结果**（1-2 行，如操作对象、产出位置、下一步）。无需强制套用大表格。


## 约束

- **MUST** 使用 ECharts tree-shaking（非全量 300KB）
- **MUST** IntersectionObserver 按需加载
- **MUST** 处理 prefers-reduced-motion 降级（显示静态数据或简化图表）
- **MUST NOT** 在 SSR 阶段执行 ECharts 初始化（仅 client-side）

## 参考

- [ECharts 官方文档](https://echarts.apache.org/)
- [ECharts Tree Shaking](https://echarts.apache.org/handbook/en/basics/import/)
- [踩坑经验](references/REFERENCE-PITFALLS.md)

参考文档：
- references/REFERENCE-README.md
