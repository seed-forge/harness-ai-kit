---
name: devlab-spec-driven-dev
description: 通用 spec 驱动的 AI 协作开发方法论。把需求转成 requirements/design/tasks 三件套提案作为事实源，经审查→细化→分任务执行→回归验证，全程 human-on-the-loop。适用于任何支持 spec 工作流的 AI IDE/Agent（Kiro spec 仅为一个 example）。Triggers on "spec 驱动", "写个提案", "requirements design tasks", "Run all tasks", "分任务执行", "spec-driven development".
---

# devlab-spec-driven-dev

## 用途

将"AI 协作开发"从"边聊边改代码"升级为**spec 驱动**：先把需求沉淀为结构化提案（requirements / design / tasks），经人类审查确认后，再由 AI 分任务顺序执行并回归。适用于**任何**支持 spec 工作流的 AI IDE / Agent —— Kiro 的 `.kiro/specs/` 只是其中一个具体实现（见 `references/REFERENCE-KIRO-SPEC-EXAMPLE.md`）。

**核心价值**：把"意图"显式化、可审查、可追溯、可分任务并行/续跑，避免大改动中途失焦、返工、上下文丢失。

## 适用场景

- 中大型功能/重构：需求有多个子任务、需要拆解与阶段验收。
- 多轮协作 / 跨会话续跑：需要一份稳定的"事实源"承接进度。
- 需要人类在关键决策点把关（架构、破坏性变更）的 AI 协作开发。

## 不适用场景

- 一次性小改动（改个文案、修个明显 typo）——直接改即可，不必起 spec。
- 纯探索性调研（用 ask/研究类流程）。

## 输入

- 需求描述（自然语言）。
- 目标代码库现状。
- 约束与偏好（语言、是否允许破坏性变更、测试力度等）。

## 输出

- `specs/<name>/` 提案三件套：`requirements.md`（需求+验收标准）、`design.md`（技术设计）、`tasks.md`（可勾选任务清单）。
- 可选：`README.md` 概览、ADR 架构决策记录、`STATUS.md`/`UPDATE_SUMMARY.md` 进度跟踪。
- 分任务执行后的实现 + 回归结果。

## 工作流

```
Phase 1: 需求 → requirements.md
  → 澄清目标、边界、验收标准（每条需求可验证）
  → ⛔ Gate G1（human）：需求是否完整/无歧义

Phase 2: 设计 → design.md
  → 技术方案、模块划分、数据流、正确性属性、破坏性变更影响面
  → 调研是否有成熟库/方案可复用
  → ⛔ Gate G2（human）：设计与取舍确认

Phase 3: 任务拆解 → tasks.md
  → 拆为可独立勾选、可验证的任务（含依赖顺序）
  → ⛔ Gate G3（human）：任务粒度与顺序确认

Phase 4: 执行（Run all tasks）
  → 按 tasks.md 顺序执行；可委派子代理逐任务实现
  → 每完成一个任务勾选状态、同步 tasks.md
  → 变更调用侧同步（破坏性变更）

Phase 5: 回归与收尾
  → 跑测试/评测；更新 STATUS；必要时回写 design（实现偏差）
```

### 提案质量约束（默认规范，可按团队覆盖）

1. **语言一致**：提案与代码注释使用团队约定语言（本团队默认中文）。
2. **破坏性变更策略**：允许破坏性变更，但**必须同步变更所有调用侧**，不保留无意义的向后兼容代码。
3. **工程化思维**：方案要面向可维护性与复用，而非"为解决问题而解决"。
4. **测试力度适配**：保留必要的属性/单元测试，**减少不必要的测试以加快提案落地**；关键正确性属性必须覆盖。
5. **提案-实现一致**：实现偏离设计时，回写 design/tasks，保持事实源一致。

### human-on-the-loop 决策门禁

| Gate | 时机 | 人类确认 |
|------|------|---------|
| G1 | requirements 完成 | 需求完整性/验收标准 |
| G2 | design 完成 | 架构取舍、破坏性变更影响面 |
| G3 | tasks 完成 | 任务拆解粒度与顺序 |

> 关键决策**给选项 + 推荐**，由人类拍板（"方向1(推荐)/方向2…你怎么决策？"），而非 AI 直接定夺。

## 与其他 devlab-* / 平台 Skill 的关系

| Skill | 关系 | 说明 |
|-------|------|------|
| `devlab-ai-agent-engineering` | **上游** | 提供架构方法论，本技能把架构落地为 spec 并执行 |
| `devlab-eval-driven-agent` | **下游** | Phase 5 回归用评测体系验证 |
| `devlab-tech-debt-ops` | **并行** | 重构类 spec 引用其重构编排方法 |
| 各 AI IDE 原生 spec 能力 | **载体** | Kiro spec / 其他工具的 spec 均为本方法论的具体实现 |

## reference

- `references/REFERENCE-KIRO-SPEC-EXAMPLE.md` — 以 Kiro `.kiro/specs/` 为例的一个具体落地范例（目录结构、Run all tasks、子代理编排）。

## 约束

- spec 是**事实源**：进度、决策、变更都要回写 spec，不散落在对话里。
- 不硬编码具体 IDE 的路径/命令为唯一方式——Kiro 仅为 example，方法论与工具解耦。
- 每条需求必须可验证；每个任务必须可独立勾选。
- 破坏性变更必须同步调用侧并在 design 记录影响面。

## 推荐触发方式

```text
按 spec 驱动方式做这个需求：先出 requirements/design/tasks 提案，我确认后再 Run all tasks
```

```text
用 devlab-spec-driven-dev 把这个重构拆成提案三件套，关键决策给我选项
```
