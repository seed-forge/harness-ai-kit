---
name: work-sc-patent-specification-writer
description: "专利说明书撰写：起草发明/实用新型/外观专利说明书主体章节，含背景技术、技术方案、术语一致性。depends on docx（社区上游）。用户提到'专利说明书''背景技术''技术方案撰写'时使用。"
argument-hint: "<technical scheme / invention disclosure / patent topic>"
---

# Patent Specification Writer

Draft the main explanatory sections of a Chinese patent specification from technical disclosures or rough invention notes.

## Use This Skill For

- 专利说明书撰写
- 技术交底书整理为说明书内容
- 背景技术描述
- 技术方案、关键点、技术效果梳理
- 发明、实用新型、外观相关说明材料整理

Do not use this skill for formal claims drafting, legal opinions, infringement analysis, or filing strategy advice.

## Scope Boundary

This skill focuses on:

- 背景技术描述
- 技术方案撰写
- 关键创新点提炼
- 技术效果说明
- 术语一致性与文档整理

It does not draft 权利要求书 as a primary deliverable.

## Workflow

### 1. Intake the Technical Disclosure

First confirm or infer:

1. 专利类型
2. 核心创新点
3. 所属技术领域
4. 要解决的技术问题
5. 相对现有技术的优势
6. 技术效果

If the user information is incomplete, ask only for the most decision-critical missing items.

Prioritize questions about:

- 技术背景
- 现有问题
- 解决方案
- 创新点
- 预期效果

### 2. Extract Search Terms and Prior-Art Angles

Derive 2-5 high-value technical keywords from the disclosure.

If web search or research tools are available, use them to check:

- related prior art
- similar domestic and international solutions
- current technical development in the field

Summarize:

- mainstream technical routes
- representative products or methods
- maturity stage of the field
- major limitations in existing approaches

If external search is not available in the current environment, say clearly that the analysis is based on user-provided material only.

### 3. Draft Background Technology

Write:

#### （1）本发明所属技术领域

- Use 1-2 precise sentences
- Prefer the pattern:
  `本发明属于[大领域]，尤其涉及[具体细分领域]`

#### （2）该行业的技术发展现状

- Explain development background
- Introduce current mainstream routes
- Mention representative existing technologies when supported
- Explain application scenarios and practical demand

#### （3）现有技术中存在的缺陷

- Analyze concrete limitations in current approaches
- Discuss from technical effect, scope, cost, implementation complexity, or reliability
- Make the real-world consequences explicit
- Prepare the logic for introducing the invention

Keep this section objective and evidence-aware.

### 4. Draft the Technical Solution

Write:

#### （1）本发明采用的技术方案

- Open with:
  `本发明提供一种[技术方案名称]，旨在解决[技术问题]`
- Prefer step-based or module-based explanation
- Clarify:
  - structure or composition
  - function of components or steps
  - data flow or process flow
  - key principle or algorithm when needed
- Use strong logical connectors such as:
  `首先` `然后` `接着` `最后`

The description should be detailed enough that a skilled person could understand how to implement it.

#### （2）本发明的关键点

- Extract 3-5 core innovation points
- Label each as `【关键点X】`
- For each one, explain:
  - technical feature
  - difference from prior art
  - concrete problem solved

#### （3）本发明的技术效果

- Open with:
  `本发明相较于现有技术，具有以下技术效果：`
- Use itemized statements
- For each effect, explain:
  - effect description
  - technical reason behind it
  - supporting data or examples if available

Each effect should map back to a defect raised in the background section.

### 5. Integrate and Polish the Document

Before delivery:

- align terminology throughout
- check section logic
- remove marketing tone
- ensure the invention is described technically, not as vague business value
- add notes on missing evidence or still-needed material where necessary

## Default Output Structure

```markdown
一、背景技术描述

（1）本发明所属技术领域
[内容]

（2）该行业的技术发展现状
[内容]

（3）现有技术中存在的缺陷
[内容]

二、本发明的技术方案

（1）本发明采用的技术方案
[内容]

（2）本发明的关键点
[内容]

（3）本发明的技术效果
[内容]
```

Also include, when useful:

- 修改建议
- 待补充材料
- 术语统一建议

## Writing Rules

- Use Chinese unless the user asks otherwise
- Stay technical, precise, and non-promotional
- Do not fabricate data, patents, or prior-art references
- Distinguish clearly between verified material, user-provided assertions, and editorial synthesis
- When uncertainty remains, mark it conservatively instead of pretending it is settled


## 推荐输出格式

执行完毕后按以下结构输出：

**状态**：✅ 成功 / ⚠️ 部分成功 / ❌ 失败

| <章节/字数/合规检查> | <值/状态> | 说明 |
|------|------|------|

**下一步**：<可执行动作>
## Final Quality Check

Before delivering, verify:

- the technical field is stated precisely
- the background explains real industry context rather than empty generalities
- prior-art defects are concrete and usable
- the technical solution is logically structured and implementable
- the innovation points are specific rather than slogan-like
- the technical effects correspond to the identified defects
- the document does not drift into claim drafting
