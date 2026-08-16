---
name: patent-review
description: Multi-round cyclic rigorous review of Chinese patent technical disclosure documents. Supports multi-dimension review (data flow closure, terminology consistency, state transition, formula completeness, error code routing, text-diagram consistency), round-by-round convergence, and optional auto-fix (default off, severe issues require human confirmation).
argument-hint: "<patent disclosure .md files...> [--fix] [--rounds N] [--dimensions dataflow,terminology,statemachine,formula,errorcode,diagram]"
---

# patent-review

## 用途

面向中文专利技术交底书的 **多轮循环严格审查** 技能。在 `patent-disclosure-workflow`（编写层）和 `work-sc-patent-docx-exporter`（导出层）之间插入审查闭环，确保交底材料在导出前经过充分逻辑验证。

适用场景：
- 专利交底书 `.md` 初稿完成后，需要逐行审查逻辑闭合性
- 多份关联专利文档之间的跨文档接口一致性检查
- 需要量化审查质量：多轮循环直到连续N轮无阻塞问题
- 客户审阅或提交专利局前的最后一次质量把关

## 与现有专利技能的关系

```
patent-disclosure-workflow (编排层)
    ├── patent-specification-writer (写作)
    ├── patent-review (审查闭环) ← 本技能
    │     ├── 多轮循环审查
    │     ├── 多维度审查
    │     └── 可选修复（默认dry-run）
    └── work-sc-patent-docx-exporter (导出)
```

本技能不负责：写作、润色、格式调整、Word 导出、权利要求书起草。

## 输入

- 一份或多份专利技术交底书 `.md` 文件（绝对路径）
- 可选：`--fix` 标志（启用自动修复模式，默认关闭）
- 可选：`--rounds N`（最大审查轮次，默认无限制）
- 可选：`--dimensions`（指定审查维度子集，默认全维度）
- 可选：附图文件（PNG/drawio XML）用于图文一致性审查

## 输出

- 每轮审查的问题清单（按严重程度分级：阻塞/中等/轻微）
- 问题趋势报告（问题数量随轮次递减曲线）
- 修复状态追踪（哪些已修复、哪些需人工确认）
- 最终交付结论（是否建议导出Word/提交客户审阅）

## 核心工作流

### 阶段一：启动审查

1. 确认输入文件存在且为 `.md` 格式
2. 识别输入文件数量：
   - **单文件模式**：仅审查单份交底书的内部逻辑闭合性
   - **多文件模式**：额外启用跨文档接口一致性检查
3. 读取全部输入文件全文
4. 若含 `--dimensions`，从审查维度矩阵中选择指定维度；否则默认全部7个维度（见专题引用）

### 阶段二：多轮循环审查

```
FOR round = 1, 2, 3, ... UNTIL 连续N轮无阻塞问题：
  1. 从零逐行审查（不参考前一轮结果，确保独立判断）
  2. 按7个审查维度逐一检查
  3. 输出问题清单（阻塞/中等/轻微分级）
  4. 若发现阻塞问题：
     a. 默认模式（dry-run）：列出问题，等待用户指令
     b. --fix 模式：中等和轻微问题自动修复；阻塞问题列出示警，AskUserQuestion 逐项确认后修复
  5. 记录本轮问题数量和严重程度
  6. 若本轮无阻塞问题，clean_count++；否则 clean_count=0
  7. 若 clean_count >= REQUIRED_CLEAN_ROUNDS (默认3)，输出最终报告并结束
END FOR
```

**收敛判断**：连续3轮无阻塞问题即可交付。如果连续3轮后问题数仍在下降趋势中，继续审查直到收敛平稳。

### 阶段三：输出最终报告

- 全轮次问题数量趋势表
- 剩余已知优化项（非阻塞）清单
- 交付结论：是否建议导出Word/提交客户审阅
- 修复记录摘要

## 审查维度矩阵

| 编号 | 维度 | 检查内容 | 阻塞判定 |
|------|------|---------|---------|
| D1 | 数据流闭合 | 步骤间输入/输出是否一一对应；字段是否有明确的写入步骤和读取步骤；表格定义但正文未使用的"孤儿字段" | 数据来源断裂、无写入步骤的字段 |
| D2 | 术语一致性 | 状态名、枚举值、字段名、编号格式、版本号、错误代码是否前后一致 | 同一概念在不同位置使用不同名称 |
| D3 | 状态迁移 | 状态机是否覆盖所有迁移路径；失败分支是否有对应处理；超时/异常是否有兜底 | 未定义的迁移路径、死循环 |
| D4 | 公式完整性 | 每个公式的变量定义、取值范围、边界兜底是否完整；是否存在除零或语义歧义 | 公式变量无定义、除零风险 |
| D5 | 错误代码分流 | 每个错误代码是否有明确的分流路径；同一代码是否承载多种语义（过载） | 错误代码语义过载导致分流歧义 |
| D6 | 实施例一致性 | 实施例中的步骤顺序、状态值、术语是否与正文对应；时序描述是否矛盾 | 实施例与正文描述直接冲突 |
| D7 | 图文一致性 | 附图中的节点文本、连线方向、步骤编号是否与正文一致（需 `.drawio` 或 `.xml` 附图文件，由 `drawio-skill` 解析） | 附图与正文描述不一致 |

详细检查方法见 `references/REFERENCE-REFERENCE-REVIEW-DIMENSIONS.md`。

## 推荐输出格式

执行完毕后输出专利审查结论:

**审查轮次**: {current_round}/{max_rounds or 'indefinite'}
**收敛状态**: {convergence_status} (连续{clean_rounds}轮无阻塞问题)

**问题统计**:
- 本轮发现：{problems_this_round}
- 阻塞级别：{blocker_count}
- 中等级别：{warning_count}
- 轻微级别：{info_count}

**关键问题清单**:
{critical_issues_list}

**修复建议**: [需人工确认]/[自动修复]/[忽略]
**交付结论**: 建议导出 Word / 需继续审查 / 暂缓提交

## 约束

- **默认不修复**：`--fix` 关闭时，仅输出问题清单，不修改任何文件。
- **修复需确认**：即使用户传 `--fix`，阻塞级别的问题也必须逐项经 `AskUserQuestion` 确认后才执行修复。
- **不重复造轮子**：写作能力复用 `patent-specification-writer`，导出复用 `work-sc-patent-docx-exporter`；修复由本技能执行 `Edit` 工具直接操作。
- **每次循环独立**：每轮审查从零读取文件，不受前一轮的结论影响（防止"隧道视野"漏掉新问题）。
- **收敛判断严格**：至少连续3轮无阻塞问题才判定为可交付；仅收敛到"轻微问题"级别时记录为"已知优化项"。
- **图文审查为可选特性**：D7 维度需用户提供 `.drawio` 或 `.xml` 附图文件。启用时先调用 `drawio-skill` 解析图为节点/连线清单，再与正文交叉校验。无附图时自动跳过该维度。
- **跨文档接口检查**：多文件模式下额外检查文档间的字段承接关系表、版本号命名空间、错误代码命名空间是否闭合。

## 专题引用

- `references/REFERENCE-REFERENCE-REVIEW-DIMENSIONS.md` — 7个审查维度的详细检查方法和示例
- 主 `SKILL.md` 保留入口、工作流、约束和维度索引；具体检查清单、反例和修复模板放在专题文档中。

## 使用示例

**示例 1：单文件审查（dry-run）**
```
用户: 用 patent-review 审查这份交底书
Claude: (读取文件 → 全维度审查 → 输出问题清单 → 等待用户指令)
```

**示例 2：多文件关联审查 + 自动修复**
```
用户: 用 patent-review --fix 审查这两份关联专利
Claude: (读取两份文件 → 全维度 + 跨文档接口审查 → 中等/轻微自动修复
       → 阻塞问题逐项AskUserQuestion确认 → 修复 → 进入下一轮)
```

**示例 3：指定维度和轮次上限**
```
用户: 用 patent-review --dimensions dataflow,terminology --rounds 3 审查这份交底书
Claude: (仅审查数据流闭合和术语一致性，最多3轮)
```

**示例 4：含附图的图文一致性审查**
```
用户: 用 patent-review --dimensions diagram 审查交底书和附图
Claude: (解析附图 → 提取节点文本和连线 → 与正文S1-S7步骤描述交叉校验)
```

## 触发方式

```text
/patent-review <文件路径...> [--fix] [--rounds N] [--dimensions ...]
```

或在对话中描述需求，由编排层 `patent-disclosure-workflow` 在预审阶段自动调用本技能。

## Human Decisions

> 结构化同源见 `decisions.yaml`；以下为人类可读汇总。

| # | 决策点 | 触发条件 | 选项 | 默认行为 |
|---|--------|---------|------|---------|
| HD-1 | --fix 模式的自动修改确认 | 使用 --fix 模式、对中高危问题执行自动修复之前（经 AskUserQuestion） | 用户确认后执行修复 / 仅报告不修改 | 必问 |

参考文档：
- references/REFERENCE-README.md
