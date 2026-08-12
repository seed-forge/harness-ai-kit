---
name: post-task-skill-miner
description: Review a completed multi-turn task, conversation transcript, final artifacts, and repeated execution patterns to decide whether the work should be distilled into a reusable skill, Loop asset, SOP, or knowledge card. Includes 6-signal Loop scoring model and extraction rubric (merged from session-to-loop). Use when Codex, Claude Code, or similar AI IDE agents finish a long task and need a structured retrospective.
argument-hint: "<conversation summary / task transcript / final artifact set>"
---

# post-task-skill-miner

## 用途

用于在一次较长、较复杂、已经完成的 AI 协作任务结束后，复盘这次工作里是否存在值得沉淀的 Skill。

这个 Skill 适用于以下场景：

- Codex、Claude Code 完成了一次多轮长对话任务，想判断是否值得提炼成复用能力
- 团队发现某类任务经常重复出现，但还不确定应不应该正式做成 Skill
- 需要区分“只值得做知识卡片”与“值得进入执行层 Skill”之间的边界
- 需要输出一个后续可交给 `skill-creator`、`harness-ai-kit` 或项目级 Skill 目录继续落地的候选规范

## 输入

- 已完成任务的对话记录、摘要或关键回合
- 本次 session 中与该任务相关的连续历史
  - 默认不是只看最后一轮消息
  - 而是结合本次 session 内相关多轮对话
  - 如果本次 session 中间已经有过阶段总结、总结稿或 compact，则默认以那次总结为基线，再承接之后到当前的新增内容
- 最终产物，例如文档、代码改动、命令记录、交付说明
- 执行过程中重复出现的步骤、判断、工具链或约束
- 可选的现有 Skill 清单，用于判断是否重复造轮子
- 可选的沉淀目标范围：
  - 只收藏
  - 项目级 Skill
  - 团队共享 Skill

## 输出

- 是否建议沉淀的明确结论
- 候选 Skill 或 SOP 的名称、定位和边界
- 建议沉淀层级：
  - 只建知识卡片
  - 建项目级 Skill
  - 建团队共享 Skill
- 不建议沉淀时的原因说明
- 建议沉淀时的最小规格草案：
  - 用途
  - 输入
  - 输出
  - 工作流
  - 约束
  - 依赖关系
- Loop 资产提炼（当候选满足 6 信号评分 ≥ 5 时）：
  - `loop.json` — Loop 元数据（schema_version, maker, checker, stop_conditions, convergence_metric）
  - `LOOP.md` — Maker 入口 prompt（执行步骤、上下文、约束）
  - `CHECK.md` — Checker 验证 prompt（rubric 维度、通过阈值、失败条件）
  - `USAGE.md` — 触发条件、使用方法、适用场景说明

## session 历史使用规则

当用这个 Skill 做任务后复盘时，默认把复盘对象理解为“本次 session 的连续协作过程”，而不是只看最后一次问答。

具体规则如下：

1. 默认回看本次 session 中与该任务直接相关的全部关键对话、阶段结论和交付说明
2. 如果本次 session 中已经做过一次明确的阶段总结、总结稿、复盘结论或 memory compact：
   - 默认把那次总结视为已沉淀基线
   - 本轮复盘重点放在“那次总结之后到当前最新消息”之间新增的事实、反复步骤、判断口径和例外
3. 如果早期探索和后期已验证结论冲突：
   - 以后期已验证结果为准
   - 但要指出哪些早期假设、路径或命名已经失效
4. 如果同一任务在本次 session 里经历了多次试错、返工或重构：
   - 不只记录最后成功方案
   - 还要提炼那些重复出现的判断顺序、失败模式、边界条件和触发语境
5. 只有当用户明确要求“只复盘当前这一轮”时，才退回单轮视角

## 工作流

1. 先确认复盘对象已经基本完成，不把尚未收敛的中途探索误判为可复用 Skill。
2. 先从本次 session 历史中确认复盘边界：
   - 这次任务从哪一段对话开始进入稳定主题
   - 中间是否做过一次阶段总结或 compact
   - 当前需要新增复盘的，是全量经验，还是“上次总结之后”的增量经验
3. 收集这次任务中的关键证据：
   - 最终交付物是什么
   - 为了交付反复执行了哪些步骤
   - 哪些判断依赖稳定规则，而不是一次性灵感
   - 是否出现了明确的输入、输出与验收方式
4. 将经验拆成三类：
   - 一次性问题求解
   - 可复用 SOP
   - 可执行 Skill 候选
5. 对每个候选点做复用性判断：
   - 未来是否大概率重复出现
   - 是否存在相对稳定的触发语境
   - 输入输出是否足够清楚
   - 工作流是否能被讲清，而不是只能靠上下文感觉
6. 与现有 Skill 做对照：
   - 是新增 Skill
   - 是已有 Skill 的补充章节
   - 是两个 Skill 之间的桥接方法
   - 还是仅应作为知识卡片收藏
7. 产出最终建议时，至少给出以下之一：
   - `不建议沉淀`
   - `建议先做知识卡片`
   - `建议做项目级 Skill`
   - `建议做团队共享 Skill`
8. 若建议沉淀为 Skill，再给出最小实现草案，供后续直接进入 `skill-creator` 或 `harness-ai-kit` 的创建流程。
9. 若候选满足 Loop 提炼条件（见下方「Loop 提炼能力」章节），同时输出 Loop 草案到 `loops/{loop_id}/draft/` 目录。

## Loop 提炼能力

> 本节合并自原 `session-to-loop` 技能，提供从重复 session 中提炼 Loop 资产的完整能力。

### 适用信号

当以下信号明显成立时，候选应进入 Loop 提炼流程（而非仅作为 Skill）：

1. 同一操作序列在 session 中出现 ≥ 3 次
2. 存在稳定的「触发 → 执行 → 验证 → 迭代」闭环
3. 收敛条件可量化（测试通过率、错误计数、迭代上限）
4. Maker / Checker 职责可分离（执行者 ≠ 验证者）

### 6 信号评分模型

对每个候选做量化评分，决定 Loop 提炼优先级：

| 信号 | 分值 | 判定条件 |
|------|------|----------|
| S1 重复模式 | +2 | 同一操作序列在 session 中出现 ≥ 2 次 |
| S2 明确输入输出 | +1 | 可从 session 中识别出清晰的输入/输出格式 |
| S3 验收可验证 | +1 | 成功或失败能被客观验证（测试通过率、lint 结果等） |
| S4 存在触发事件 | +1 | 存在明确的触发条件（CI failure、定时任务、用户命令） |
| S5 不依赖临场判断 | +1 | 关键决策点可被规则化 |
| S6 未来复现 | +1 | 该模式在未来很可能再次出现 |

**阈值**：≥ 5 强候选（自动生成草案）；3-4 弱候选（提示用户确认）；≤ 2 不建议（保留为知识卡片）。

完整评分细则见 [references/REFERENCE-VALUE-SCORING.md](references/REFERENCE-VALUE-SCORING.md)。

### Skill → Loop 字段映射

从 session 经验到 Loop 资产字段的提取分三级：

- **自动层**：模式匹配直接填充（loop.id、loop.name、maker.entry、checker.entry）
- **半自动层**：语义分类推断候选值，需人工确认（loop.summary、maker.description、stop_conditions）
- **需人工层**：无法可靠自动推导（rubric.dimensions、convergence_metric）

完整映射矩阵见 [references/REFERENCE-EXTRACTION-RUBRIC.md](references/REFERENCE-EXTRACTION-RUBRIC.md)。

### 多 Skill 组合策略

当一个 Loop 由多个 Skill 组合而成时，按以下三种模式处理：

- **串联**（Pipeline）：A→B→C 依次执行，前一个输出是后一个输入
- **并联**（Parallel）：A/B/C 独立执行后汇总
- **选择**（Conditional）：根据输入特征选择不同分支

组合模式判定信号见 EXTRACTION-RUBRIC.md 末节。

### Loop 草案输出

提炼完成后输出到 `loops/{loop_id}/draft/` 目录：

1. `loop.json` — Loop 元数据
2. `LOOP.md` — Maker 入口（参考 [templates/loop.md.template](templates/loop.md.template)）
3. `CHECK.md` — Checker 验证（参考 [templates/check.md.template](templates/check.md.template)）
4. `USAGE.md` — 使用说明（参考 [templates/usage.md.template](templates/usage.md.template)）

草案生成后，推荐执行 `loopctl validate` 校验结构合法性，再用 `loopctl promote` 提升到正式目录。

### 业务线判断补充

如果本次候选不只是“一个新 Skill”，而可能是一整条新的业务线，应额外判断：

1. 这类任务是否已经形成稳定主题，例如：
   - 一组固定对象
   - 一组固定目标
   - 一组固定资料入口
2. 这类主题是否已经明显超出单个原子 Skill 的范围
3. 未来是否很可能围绕同一主题继续派生多个场景型或原子型 Skill
4. 如果现在不开这条业务线，后续经验是否会持续散落在多个不相干 Skill 中

若以上信号明显成立，输出建议中应允许新增一类结论：

- `建议新开业务线 Skill`

此时还应补充两项内容：

- 该业务线下现有 Skill 应如何归类或挂接
- 该业务线第一条场景型 Skill 最适合从哪个稳定场景开始

## 判断标准

优先满足以下信号时，再建议进入执行层：

1. 同类任务已经重复出现，或明确会重复出现
2. 步骤顺序、判断口径、依赖关系相对稳定
3. 输入与输出可以向其他人或其他 AI 说明清楚
4. 成功与失败能被验证，而不是只能主观感觉
5. 它比单纯写一段临时提示词更值得长期维护

若主要符合以下特征，则不要急着做成 Skill：

- 只解决一次性的特例问题
- 关键成功因素高度依赖临场判断
- 范围过宽，像“以后所有任务都这样做”
- 只是某个更大 Skill 中的一小条补充说明
- 和现有 Skill 高度重叠，只是名称不同

## 沉淀层级选择

### 只做知识卡片

适用于：

- 经验有启发，但流程还不稳定
- 价值主要在判断思路，而不是固定执行流程
- 暂时没有必要进入 `.agents/skills/` 或团队分发仓库

### 做项目级 Skill

适用于：

- 明显受当前仓库、当前工作流、当前目录结构约束
- 在这个项目里会反复使用
- 复用价值已经成立，但还不适合直接推广到团队

### 做团队共享 Skill

适用于：

- Codex、Claude Code 等 AI IDE 都可能复用
- 不依赖个人目录、个人账号或私有上下文
- 输入输出、边界和工作流已经稳定
- 团队成员能在别的项目中直接理解并使用

## 推荐输出格式

建议按以下结构输出结论：

```markdown
# 复盘结论

## 一、任务概况
## 二、候选沉淀点
## 三、是否建议做成 Skill
## 四、建议沉淀层级
## 五、候选 Skill 最小规格
## 六、与现有 Skill 的关系
## 七、暂不沉淀的部分
```

## 约束

- 不要为了“看起来体系化”而强行把每次任务都包装成 Skill。
- 不要把尚未验证的一次性技巧伪装成通用工作流。
- 优先收敛边界，再命名 Skill，不要先起一个很大的名字再倒推内容。
- 如果现有 Skill 只需补一段规则，优先建议更新旧 Skill，而不是新建重复 Skill。
- 如果证据不足，应明确说“暂不建议沉淀”，而不是含糊给出伪结论。
- 若用户要求共享出去，输出内容必须避免私有路径、私有账号、个人习惯和敏感信息。
- 不要只根据最后一轮消息做复盘；默认结合本次 session 的连续历史。
- 如果本次 session 已有阶段总结，不要机械地从头重写整段历史，优先补“总结之后的新经验”。

## 专题引用

- **[references/REFERENCE-VALUE-SCORING.md](references/REFERENCE-VALUE-SCORING.md)**：6 信号评分模型详解（合并自 session-to-loop）。
- **[references/REFERENCE-EXTRACTION-RUBRIC.md](references/REFERENCE-EXTRACTION-RUBRIC.md)**：Skill→Loop 字段映射矩阵与 Rubric 提取策略（合并自 session-to-loop）。
- **[templates/](templates/)**：Loop.md、CHECK.md、USAGE.md 的模板骨架（合并自 session-to-loop）。

## 推荐触发方式

适合在任务已经基本完成后，用下面这类说法触发：

```text
用 $post-task-skill-miner 复盘这次任务，判断有没有值得沉淀成 skill 或 SOP 的内容。
```

```text
这轮长对话做完了。用 $post-task-skill-miner 看看是该更新旧 skill、做知识卡片，还是新建 skill。
```

```text
请用 $post-task-skill-miner 分析这次经验是否已经值得新开一条业务线 skill。
```

```text
请用 $post-task-skill-miner 基于本次 session 的连续历史来复盘；如果中间已经总结过，就从那次总结之后到现在继续判断。
```

```text
这次 session 同一个模式跑了很多次。用 $post-task-skill-miner 看看有没有值得提炼成 Loop 的。
```

如果任务还没完成、证据还不够、方案还在发散阶段，不要过早触发本 Skill。

## 示例

示例 1：多轮任务后发现重复进行了“读取长对话、识别重复步骤、判断是否应沉淀 Skill”的动作。

合格输出应能明确说明：

- 这不是一次性问答，而是稳定复盘流程
- 它适合做成分析型 Skill，而不是执行型脚本
- 它的输入、输出、判断标准和沉淀层级都可以明确描述

示例 2：一次任务里只是临时修了一个特殊环境问题。

合格输出应能明确说明：

- 该经验可以写进知识卡片或故障记录
- 但暂时不值得单独做成 Skill

## Human Decisions

> 结构化同源见 `decisions.yaml`；以下为人类可读汇总。

| # | 决策点 | 触发条件 | 选项 | 默认行为 |
|---|--------|---------|------|---------|
| HD-1 | 提炼资产是否推进创建 | 复盘识别出可沉淀的 skill/Loop/SOP/知识卡片草案后 | 用户确认后推进创建 / 仅记录建议不落地 | 必问 |

参考文档：
- references/REFERENCE-README.md
