# markitdown Usage

## When To Use
- Use this skill when you need to 调用已安装的 MarkItDown，把 docx、pdf、pptx、xlsx、图片、html、csv 等资料稳定转换为 markdown.
- Use it when the task matches the asset's documented workflow and should stay within the skill boundary.

## Inputs
- Task goal, source material, and workspace context.
- Any upstream files or examples that the workflow needs to inspect or transform.

## Output
- The result defined by the main document and its workflow.

## 可直接复制的中文 Prompt
### 场景 1：直接调用技能
```text
请使用 `markitdown` 这个技能处理我的任务。
输入材料：<在这里补充文件、链接、原始文本或项目背景>。
目标：<在这里补充你要完成的结果>。
要求：先判断这个技能是否适合；如果缺少关键输入，先列出缺口；执行时遵循 `SKILL.md` 的规则。
输出：最终结果、关键检查点、还需要我补充的内容。
```

## Fast Path
- Open `SKILL.md` first.
- Read `EXAMPLE.md` only when the workflow is multi-step, parameter-heavy, or easy to misuse.
