---
name: patent-disclosure-workflow
description: End-to-end project workflow for Chinese patent technical disclosure drafting, polishing, pre-review, and conditional Word export. Use for patent writing, structure alignment, anti-AI-tone polishing, client pre-review preparation, and export coordination.
argument-hint: "<patent topic / markdown draft / disclosure materials>"
---

# Patent Disclosure Workflow

面向项目内专利技术交底材料的完整工作流技能。它覆盖专利编写、结构化整理、专业化润色、预审版收口，以及在用户明确要求时触发的 `docx` 导出。

## 适用场景

- 需要从技术材料、项目说明、产品规划或草稿整理成专利技术交底书
- 需要根据客户意见补强“如何做到、凭什么做到、是否可实施”
- 需要消除明显 AI 味道，让文本更像专业技术交底材料
- 需要把交底书整理成更适合客户审阅或交代理的版本
- 需要在内容确认后导出 `Word`

## 范围边界

本 Skill 主要覆盖：

- 技术交底材料 intake
- 背景技术、技术问题、详细技术方案、创新点和技术效果撰写
- 章节级编写要求对齐
- 技术底层机制补强
- AI 味道清理和术语统一
- 预审版整理
- 按需调用导出 SOP

本 Skill 不直接承担：

- 正式权利要求书起草
- 法律授权判断
- 侵权分析
- 申请策略法律意见

## 总工作流

### SOP 1：收集与识别

先确认或推断：

1. 专利主题
2. 技术领域
3. 现有问题
4. 核心技术方案
5. 相比现有技术的差异点
6. 是否已有草稿、客户意见、参考模板

若存在 `docx` 参考材料，优先用 `$markitdown` 转成 `md` 再分析。

### SOP 2：章节级写作与补强

默认采用五段式技术交底书结构：

1. `一、背景技术`
2. `二、技术问题`
3. `三、详细技术方案`
4. `四、本技术方案的有益效果/创新点`
5. `五、其它`

详细的章节编写要求见：

- `references/REFERENCE-PATENT-SECTION-WRITING-REQUIREMENTS.md``r`n- 若输入来自 `docx` 参考件，优先启用 `markitdown` 转写后再进入工作流

在进入正文编写、结构补强、创新点提炼和技术效果整理阶段时，默认调用或复用：

- `patent-specification-writer`

调用原则：

1. 由 `patent-disclosure-workflow` 负责判断当前是否进入编写阶段
2. 一旦进入编写阶段，正文主体内容优先沿用 `patent-specification-writer` 的通用专利写作能力
3. 项目级差异化规则，如去 AI 味、客户预审口径、版本表达限制、章节对齐要求，由本 Skill 叠加控制

### SOP 3：技术深度校验

对每份交底材料至少检查以下问题：

- 讲的是“功能”还是“实现机制”
- 每一核心功能是否都有相应技术实现方案
- 关键术语是否可落到数据结构、规则、模块、流程或判定逻辑
- 是否说明触发条件、输入、处理、输出、异常分支
- 是否足以让本领域普通技术人员据此实施

如果答案偏弱，优先补：

- 模块输入/处理/输出关系
- 状态数据结构
- 规则模板或策略模板
- 候选结果排序、阈值、二次确认或回退逻辑
- 失败分支与人工接管分支

### SOP 4：去 AI 味润色

本项目内专利文本润色时，默认执行以下规则：

- 少用“首先、然后、接着、最后”一串流水连接词
- 少用“第一、第二、第三”口吻，优先改成“一是、二是、三是”或直接技术枚举
- 少写空泛价值表述，优先写处理逻辑和技术条件
- 少写营销化语言，保持技术交底语气
- 保持术语统一，不在同一文档里来回切换同义说法

### SOP 5：预审版整理

若当前阶段是客户预审或内部评审：

- 正文保持技术交底体例
- 可以在 `五、其它` 中保留预审说明、保护方向建议、后续权利要求抽取重点
- 不在标题区直接写“预审版”，版本词只放文件名

### SOP 6：导出 SOP

只有在用户明确要求导出 `Word` 时，才进入导出步骤。

导出动作不在本 Skill 内重复实现，而是调用项目级子技能：

- `work-sc-patent-docx-exporter`

调用前提：

1. `md` 内容已确认
2. 章节结构已对齐
3. 术语已统一
4. 预审说明已放到合适位置

调用原则：

1. `patent-disclosure-workflow` 不直接重写导出逻辑
2. 导出阶段默认调用 `work-sc-patent-docx-exporter`
3. 首页信息栏、固定副标题、一级标题黑体、版本词仅放文件名等规则，统一由 `patent-docx-exporter` 执行

## 默认判断规则

- 用户只说“调整专利”“重写”“润色”“压实”，默认停留在 `md`
- 用户只说“模板不对”，优先检查章节结构与章节说明，不急着导出
- 用户明确说“转 Word”“输出 docx”，才触发导出 SOP

## 与现有项目技能的关系

- `patent-specification-writer`
  - 偏说明书/交底书写作主体
  - 是本 Skill 在编写阶段默认复用的通用专利写作子技能
- `work-sc-patent-docx-exporter`
  - 偏最终 `docx` 导出
  - 是本 Skill 在导出阶段默认调用的导出子技能
- `patent-disclosure-workflow`
  - 作为更上层工作流技能，负责把写作、补强、润色、预审和导出串起来


## 推荐输出格式

执行完毕后按以下结构输出：

**状态**：✅ 成功 / ⚠️ 部分成功 / ❌ 失败

| <章节/字数/合规检查> | <值/状态> | 说明 |
|------|------|------|

**下一步**：<可执行动作>
## 参考材料

- `references/REFERENCE-PATENT-SECTION-WRITING-REQUIREMENTS.md`
- 若输入来自 `docx` 参考件，优先启用 `markitdown` 转写后再进入工作流

## Human Decisions

> 结构化同源见 `decisions.yaml`；以下为人类可读汇总。

| # | 决策点 | 触发条件 | 选项 | 默认行为 |
|---|--------|---------|------|---------|
| HD-1 | 导出 Word 文档 | 交底材料撰写完成、需要导出 Word 之前 | 用户确认内容后导出 / 退回修改 | 必问 |

参考文档：
- references/REFERENCE-README.md
