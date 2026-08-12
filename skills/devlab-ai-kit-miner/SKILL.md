---
name: devlab-ai-kit-miner
description: Review completed dev sessions to decide whether work should be distilled into devlab-* assets (skills, CLI tools, MCP servers, loops, subagents, or knowledge cards). Based on post-task-skill-miner, specialized for dev workflows (不局限于前后端，覆盖全栈研发场景). Triggers on "devlab-ai-kit-miner", "devlab skill miner", "研发复盘", "技能提炼", "沉淀决策".
---

# devlab-ai-kit-miner

## 用途

在一次较长的研发协作会话结束后，复盘本次工作中是否存在值得沉淀的资产。

基于 post-task-skill-miner 的复盘能力，增加了：
- 研发场景特有的**多资产类型决策**（Skill / CLI / MCP / Loop / Subagent）
- `devlab-*` 命名规范
- 团队仓库 vs 项目级的沉淀位置决策
- 与 `harness-ai-kit` 工具链的集成指引

## 输入

- 已完成研发任务的对话记录、摘要或关键回合
- 本次 session 中与该任务相关的连续历史
- 最终产物（代码、文档、配置、命令记录）
- 执行过程中重复出现的步骤、判断、工具链或约束
- 可选：现有 Skill 清单（`harness-ai-kit/skills/` + `.claude/skills/`）

## 输出

- 是否建议沉淀的明确结论
- 建议的资产类型：Skill / CLI / MCP / Loop / Subagent / 知识卡片
- 建议的沉淀位置：项目级 / 团队共享
- 候选资产的最小规格草案
- 与现有 `devlab-*` 资产的关系（新增 / 补充 / 桥接 / 重复）

## 工作流

1. 确认复盘对象已完成，不把中途探索误判为可复用资产。
2. 从本次 session 历史中确认复盘边界（起始点、阶段总结、增量经验）。
3. 收集关键证据：最终交付物、反复执行的步骤、依赖稳定规则的判断、明确的输入/输出/验收方式。
4. 将经验拆分：一次性问题求解 / 可复用 SOP / 可执行资产候选。
5. 对每个候选做复用性判断（是否重复、触发语境、输入输出清晰度）。
6. 与现有 `devlab-*` 资产对照（新增 / 补充 / 桥接 / 重复 / 不沉淀）。
7. 判断资产类型 → 查阅对应 reference 获取详细规范。
8. 判断沉淀位置（项目级 vs 团队共享）。
9. 输出结论和最小规格草案。

## 资产类型决策矩阵

| 信号 | 资产类型 | 详细规范 |
|------|---------|---------|
| 流程可文档化，步骤稳定 | **Skill** | [REFERENCE-ASSET-SKILL.md](references/REFERENCE-ASSET-SKILL.md) |
| 需要命令行工具封装 | **CLI** | [REFERENCE-ASSET-CLI.md](references/REFERENCE-ASSET-CLI.md) |
| 需要外部服务集成 | **MCP** | [REFERENCE-ASSET-MCP-SUBAGENT.md](references/REFERENCE-ASSET-MCP-SUBAGENT.md) |
| 需要周期性闭环或循环排障 | **Loop** | [REFERENCE-ASSET-LOOP.md](references/REFERENCE-ASSET-LOOP.md) |
| 需要独立 Agent 角色 | **Subagent** | [REFERENCE-ASSET-MCP-SUBAGENT.md](references/REFERENCE-ASSET-MCP-SUBAGENT.md) |
| 判断思路 / 经验 / 启发 | **知识卡片** | 不创建资产，记录到 Obsidian 知识库 |
| 特定库/框架的使用指南 | **Skill（`*-usage`）** | [REFERENCE-ASSET-SKILL.md](references/REFERENCE-ASSET-SKILL.md) |

**复盘决策深度参考**：[REFERENCE-DISTILLATION-RULES.md](references/REFERENCE-DISTILLATION-RULES.md)（R1-R5 规则 + A1-A4 反模式）

## 沉淀位置决策

```
输入输出是否稳定？
  否 → 项目级 (.claude/skills/)
  是 → 是否依赖私有上下文？
    是 → 项目级
    否 → 团队共享 (harness-ai-kit/skills/)
```

## 命名规范

遵循 `docs/namespace-conventions.md` 中 devlab 二级命名体系：

| 前缀 | 领域 | 示例 |
|------|------|------|
| `devlab-srv-*` | 后端 / 服务（API、业务逻辑、中间件集成） | `devlab-srv-spring-boot-sop` |
| `devlab-web-*` | 网站 / Web 应用（页面、组件、前端框架） | `devlab-web-react-sop` |
| `devlab-tool-*` | 开发工具（脚手架、代码生成、工程化脚本） | `devlab-tool-codegen-sop` |
| `devlab-cicd-*` | CI/CD 编排（构建、部署、流水线配置） | `devlab-cicd-onboard` |
| `devlab-*`（省略二级） | 不归属特定技术栈 | `devlab-troubleshooting` |

**判定规则**：后端服务 → `srv`；网站/Web → `web`；开发工具 → `tool`；CI/CD → `cicd`；不归属 → 省略。

## 与 post-task-skill-miner 的关系

| 维度 | post-task-skill-miner | devlab-ai-kit-miner |
|------|----------------------|-------------------|
| 适用范围 | 通用任务复盘 | 研发场景专用（全栈） |
| 资产类型 | Skill / Loop / 知识卡片 | Skill / CLI / MCP / Loop / Subagent / 知识卡片 |
| Loop 提炼 | 内置 6 信号评分 + 字段映射 Rubric | 复用上游评分，增加研发 Loop 子类型判定 |
| 命名规范 | 无 | `devlab-srv/web/tool` 二级前缀 |
| 沉淀位置 | 不区分 | 项目级 vs 团队共享 |
| 工具链集成 | 无 | harness-ai-kit (skill.json, USAGE.md, CHANGELOG.md) |

**依赖链**：`devlab-ai-kit-miner` → `post-task-skill-miner`（通用判断 + Loop 提炼）。

## 与 ai-kit-forge 的接力

本技能负责**复盘提炼**阶段，输出资产草案。如需实际创建资产（骨架生成 → validate → publish），由 `ai-kit-forge` 接手。

```
devlab-ai-kit-miner 复盘输出草案
        │
        ▼ (用户确认后衔接)
ai-kit-forge 接收草案 → 生成骨架 → validate → publish
```

## 团队共享资产必要条件

1. `skill.json` / `cli.json` / `loop.json` 完整填写
2. `USAGE.md` 存在且包含"可直接复制的中文 Prompt"
3. `CHANGELOG.md` 记录版本历史
4. 不含私有路径、凭证、个人习惯
5. 输入输出可被其他团队成员理解

## 约束

- 不要为了体系化而强行沉淀。证据不足时明确说"暂不建议"。
- 先检查 `harness-ai-kit/skills/` 和 `.claude/skills/` 是否已有可复用资产。
- 沉淀到团队仓库必须有对应的 metadata 文件 + `USAGE.md` + `CHANGELOG.md`。
- 涉及私有路径、凭证、个人习惯的内容不得进入团队共享。
- 不要只根据最后一轮消息做复盘；默认结合 session 连续历史。

## 专题引用

- [REFERENCE-DISTILLATION-RULES.md](references/REFERENCE-DISTILLATION-RULES.md)：沉淀决策规则与反模式（R1-R5, A1-A4）
- [REFERENCE-ASSET-SKILL.md](references/REFERENCE-ASSET-SKILL.md)：Skill 资产创建规范
- [REFERENCE-ASSET-CLI.md](references/REFERENCE-ASSET-CLI.md)：CLI 资产创建规范
- [REFERENCE-ASSET-LOOP.md](references/REFERENCE-ASSET-LOOP.md)：Loop 资产创建规范（含子类型）
- [REFERENCE-ASSET-MCP-SUBAGENT.md](references/REFERENCE-ASSET-MCP-SUBAGENT.md)：MCP / Subagent 资产创建规范
- [REFERENCE-REAL-WORLD-EXAMPLE.md](references/REFERENCE-REAL-WORLD-EXAMPLE.md)：真实案例复盘

## 推荐触发方式

```text
用 devlab-ai-kit-miner 复盘这次研发会话，判断有没有值得沉淀的内容。
```

```text
这轮开发做完了。用 devlab-ai-kit-miner 看看是该更新旧资产、做知识卡片，还是新建 devlab-* 资产。
```

## 推荐输出格式

```markdown
# 复盘结论

## 一、任务概况
## 二、候选沉淀点
## 三、资产类型判断
## 四、沉淀位置建议
## 五、候选资产最小规格
## 六、与现有 devlab-* 资产的关系
## 七、暂不沉淀的部分
```

## 八、与审查流水线的关系

本技能产出的沉淀候选建议作为草稿进入 Draft → Review → Merge 流水线（`historyminerctl push`），
由 [`ai-kit-review-ops`](../ai-kit-review-ops/SKILL.md) 统一五维审查后融合，不直提交。

## Human Decisions

> 结构化同源见 `decisions.yaml`；以下为人类可读汇总。

| # | 决策点 | 触发条件 | 选项 | 默认行为 |
|---|--------|---------|------|---------|
| HD-1 | 提炼资产是否推进创建/发布 | 复盘识别出可沉淀的 devlab-* 资产草案后 | 用户确认后推进创建/发布 / 仅记录不落地 | 必问 |

参考文档：
- references/REFERENCE-README.md
