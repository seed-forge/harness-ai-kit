# work-markitdown 使用说明

## 团队成员

当需要把办公文档转成 Markdown 时：

1. 确认源文件存在（docx/pdf/pptx/xlsx 等）
2. 触发技能：描述需求（如"把这个 Word 转成 md"）或 `/work-markitdown`
3. 检查输出文件非空且内容完整
4. 如需后续导出，交给 `work-export` 或对应的 `work-sc-*` 技能

## Agent / AI IDE

当用户需要解析或读取文档内容时：

1. 加载 `work-markitdown` Skill
2. 优先使用 `.agents/tools/markitdown.cmd` 包装命令
3. 输出到 `*.markitdown.md`，不覆盖已有文件
4. 批量转换时使用 PowerShell 循环
5. 转换后校验：文件非空、无乱码、表格完整

## 可直接复制的中文 Prompt

```text
请使用 work-markitdown 技能，按照其 SKILL.md 描述的标准流程执行任务；
先做 dry-run/检查，向我展示结果与风险，经确认后再正式执行。
```
