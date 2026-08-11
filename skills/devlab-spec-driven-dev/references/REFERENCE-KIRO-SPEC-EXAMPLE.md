# Reference: Kiro spec 落地范例（一个具体实现）

> 本文是 `devlab-spec-driven-dev` 的**一个 example**，展示该方法论在 Kiro IDE 上的具体落地。方法论本身与工具无关；其他支持 spec 的 IDE/Agent 可类比。

## 目录结构

Kiro 把提案放在项目内 `.kiro/specs/<feature-name>/`：

```
.kiro/specs/<feature-name>/
├── requirements.md   # 需求 + 验收标准（可编号，逐条可验证）
├── design.md         # 技术设计（模块/数据流/正确性属性/影响面）
├── tasks.md          # 任务清单（可勾选，含依赖顺序）
└── README.md         # （可选）概览
```

## 典型协作流程

1. 用户描述需求 → AI 生成 `requirements.md`，用户审查确认（G1）。
2. AI 生成 `design.md`（含破坏性变更影响面、是否复用成熟库）→ 确认（G2）。
3. AI 生成 `tasks.md` 拆解 → 确认任务粒度/顺序（G3）。
4. 用户说 **"Run all tasks"** → AI 按 tasks.md 顺序执行，可委派子代理（如 `spec-task-execution` / `requirements-first-workflow`）逐任务实现；每完成一个任务同步勾选 `tasks.md` 状态。
5. 续跑：新会话中"continue with remaining tasks"，以 `tasks.md` 状态为准接续。

## 观察到的高频实践（来自真实会话）

- **提案审查先行**："审查一下【X】提案，给出改进建议" —— 实现前先评审提案质量。
- **提案联动更新**：某提案的技术方案变化时，同步更新相关提案的 `tasks.md`/`requirements.md`，避免事实源分裂。
- **状态跟踪**：大 spec 配 `STATUS.md` / `UPDATE_SUMMARY.md` 跟踪完成度；发现"任务状态未更新"要主动校正。
- **ADR**：关键架构决策记为 ADR（如 ADR-006/ADR-015）。

## 提案质量约束（本团队实践）

用户在多个 spec 中反复重申的固定约束：
1. 提案与代码注释全中文；
2. 允许破坏性变更，只需同步调用侧；
3. 工程化思维，不为解决而解决；
4. 减少不必要的属性测试，加快提案落地。

## 迁移到其他工具

- 无 `.kiro/` 目录的工具：把三件套放到约定目录（如 `docs/specs/` 或 `.workflow/`）即可，流程不变。
- 无 "Run all tasks" 原语的工具：以"逐任务执行 + 勾选 tasks.md"手动驱动。
