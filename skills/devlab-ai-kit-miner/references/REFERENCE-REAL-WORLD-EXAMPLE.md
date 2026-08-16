# 真实案例：personal-brand-showcase 研发会话复盘

## 会话概况

- **项目**：personal-brand-showcase（个人品牌展示站）
- **技术栈**：Astro 5 + React 19 + @xyflow/react + GSAP + anime.js
- **会话时长**：约 4 小时
- **主要工作**：项目详情弹窗改造 → 生命周期地图（XYFlow 画布）→ 管理泳道 → 沉淀

## 复盘结论

### 建议沉淀的资产

| # | 资产 | 类型 | 沉淀位置 | 理由 |
|---|------|------|---------|------|
| 1 | `devlab-web-xyflow-usage` | Skill (`*-usage`) | 团队共享 | XYFlow 自定义节点的 6 条踩坑经验，高频复用 |
| 2 | `devlab-xyflow-troubleshoot-loop` | Loop | 团队共享 | 循环排障流程，HUMAN-ON-THE-LOOP 模式 |

### 不建议沉淀的部分

| 内容 | 原因 |
|------|------|
| 具体的 CSS 样式代码 | 项目特定，不可复用 |
| 数据结构（TaskDetail/RoleTask） | 业务特定 |
| GSAP 动画序列代码 | 场景特定，GSAP API 本身已足够通用 |
| 管理泳道坐标对齐逻辑 | 项目特定的布局计算 |

### 沉淀决策过程

1. **识别重复模式**：XYFlow 节点内按钮点击问题在会话中反复出现（尝试了 stopPropagation、onMouseDown、onPointerDown、nodrag/nopan CSS class，均不可靠），最终用容器级 click 委托解决
2. **判断复用性**：这是 XYFlow 自定义节点的通用问题，不依赖业务上下文
3. **选择资产类型**：
   - 踩坑经验 → Skill（`*-usage` 后缀，包含库信息+核心概念+踩坑经验）
   - 排障流程 → Loop（Maker 诊断 → Checker 验证 → 迭代）
4. **选择沉淀位置**：不依赖私有上下文 → 团队共享

### 命名决策

- `devlab-web-xyflow-usage` 而非 `frontend-xyflow`
- 理由：`-usage` 后缀表示"使用指南"，是通用知识；不加后缀表示"组件实现"，是项目特定代码
- 参考：`devlab-frontend-accordion`（组件实现）vs `devlab-web-xyflow-usage`（库使用指南）

### Skill + Loop 联动

- **Skill** 提供知识：XYFlow 节点内按钮点击的根因（XYFlow 在 pointerdown 层拦截拖拽事件）和解法（容器级 click 委托）
- **Loop** 提供流程：当用户遇到 XYFlow 问题时，Maker 参考 Skill 的踩坑经验定位根因，Checker 独立验证修复效果
- **HUMAN-ON-THE-LOOP**：Maker 和 Checker 自动执行，但交互验证（浏览器中点击测试）需要用户确认

## 经验教训

1. **`client:visible` vs `client:only`**：需要确定尺寸的 React 组件必须用 `client:only="react"`，这是 Astro + React Islands 的通用陷阱
2. **XYFlow 事件拦截**：不要在自定义节点内直接绑定 onClick，用容器级委托 + data 属性
3. **排障类经验用 Loop 沉淀**：不可能穷举所有踩坑以 Skill 记录，Loop 的循环诊断-验证模式更适合
