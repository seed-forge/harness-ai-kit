# work-export 使用说明

## 团队成员

当需要从内容导出办公文档时：

1. 确认源内容（Markdown / 数据 / 大纲）已就绪
2. 触发技能：描述需求（如"把这个 md 导出成 Word"）或 `/work-export`
3. 等待导出完成，检查输出文件
4. 在 Office/WPS 中打开确认格式正确

## Agent / AI IDE

当用户需要导出文档时：

1. 加载 `work-export` Skill
2. 按格式选择决策树确定目标格式
3. 调度对应的社区上游技能（docx/pdf/xlsx/pptx）
4. 执行统一输出校验
5. 输出文件路径和校验结果

## 可直接复制的中文 Prompt

```text
请使用 work-export 技能，按照其 SKILL.md 描述的标准流程执行任务；
先做 dry-run/检查，向我展示结果与风险，经确认后再正式执行。
```
