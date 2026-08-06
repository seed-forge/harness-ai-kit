# work-convert 使用说明

## 团队成员

当需要转换文档格式时：

1. 确认源文件存在
2. 触发技能：描述需求（如"把这个 Word 转成 PDF"）或 `/work-convert`
3. 检查输出文件非空且内容正确

## Agent / AI IDE

当用户需要格式转换时：

1. 加载 `work-convert` Skill
2. 按转换管线选择表确定最佳路径
3. 优先使用 soffice（docx/pptx/xlsx → pdf）
4. 回退到社区上游技能链式转换
5. 转换后校验输出文件

## 可直接复制的中文 Prompt

```text
请使用 work-convert 技能，按照其 SKILL.md 描述的标准流程执行任务；
先做 dry-run/检查，向我展示结果与风险，经确认后再正式执行。
```
