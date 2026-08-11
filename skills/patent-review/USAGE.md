# patent-review 使用说明

## 快速开始

```text
/patent-review "C:\path\to\disclosure.md"
```

## 常用模式

### Dry-run 审查（默认）
```text
/patent-review "C:\path\to\disclosure.md"
```
仅输出问题清单，不修改任何文件。

### 自动修复模式
```text
/patent-review --fix "C:\path\to\disclosure.md"
```
中等和轻微问题自动修复，阻塞问题逐项人工确认。

### 关联多文档审查
```text
/patent-review "C:\path\to\disclosure-a.md" "C:\path\to\disclosure-b.md"
```
额外启用跨文档接口一致性检查。

### 指定审查维度
```text
/patent-review --dimensions dataflow,terminology "C:\path\to\disclosure.md"
```
仅审查指定维度。

### 限制最大轮次
```text
/patent-review --rounds 5 "C:\path\to\disclosure.md"
```
最多5轮审查。

## 输出解读

- **阻塞问题**：必须修复才能提交
- **中等问题**：建议修复后提交
- **轻微问题**：已知优化项，不阻塞提交
- **结论**："建议导出Word" 或 "不建议导出" + 原因

## 可直接复制的中文 Prompt

```text
请使用 patent-review 技能，按照其 SKILL.md 描述的标准流程执行任务；
先做 dry-run/检查，向我展示结果与风险，经确认后再正式执行。
```
