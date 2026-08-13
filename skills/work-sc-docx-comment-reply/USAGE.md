# work-sc-docx-comment-reply - Usage

## Overview

从 Word .docx 文件中提取批注（comments）上下文，为每条批注生成回复，并以 threaded replies 形式写回文档。

## Prerequisites

- 社区技能 `docx` 已安装（通过 `source_url` 自动安装或手动从 IDE marketplace 安装）
- Python 3.10+ 可用

## 适用场景

- 专利/论文/合同/内部评审等需要逐条回复批注的文档
- 批量处理多人审阅的文档批注

## 使用方式

向 AI 提供以下信息：
1. 目标 .docx 文件路径
2. 回复策略（逐条回复 / 选择性回复 / 按审阅人过滤）
3. 回复风格（正式 / 简洁 / 技术讨论）

## Known Pitfalls

- 批注可能引用已删除的文本，需要容错处理
- 写回操作会修改原文件，建议先备份

## 可直接复制的中文 Prompt

```text
请使用 work-sc-docx-comment-reply 技能，按照其 SKILL.md 描述的标准流程执行任务；
先做 dry-run/检查，向我展示结果与风险，经确认后再正式执行。
```
