---
name: work-export
description: "办公文档通用 Outflow 编排：从内容（Markdown/数据/大纲）出发，调度社区上游技能生成目标格式文档（docx/pdf/xlsx/pptx）。depends on docx, pdf, xlsx, pptx 社区上游技能。用户提到'导出为 Word''生成 PDF''做成 Excel''做成 PPT''导出文档'时使用。"
---

# work-export

## 用途

作为 work 命名空间的**通用 Outflow 基座**，提供从内容（Markdown / 结构化数据 / 大纲）到目标格式文档的统一导出管线。

本技能不实现格式生成逻辑，而是编排社区上游技能（docx/pdf/xlsx/pptx），提供：
- 统一的格式选择决策树
- 标准化的输出校验流程
- 与 `work-markitdown`（Inflow）形成闭环

## 依赖

- **depends**: `docx`（md→docx）、`pdf`（md→pdf）、`xlsx`（data→xlsx）、`pptx`（outline→pptx）
- **协作**: `work-markitdown`（Inflow 侧）、`work-convert`（格式互转）
- **被依赖**: `work-sc-*` 场景技能

## 适用场景

- 从 Markdown 内容导出为 Word 文档（报告、手册、合同等）
- 从 Markdown 内容导出为 PDF
- 从结构化数据导出为 Excel 表格
- 从大纲/结构导出为 PowerPoint 演示文稿
- 为 `work-sc-*` 场景技能提供底层导出能力

## 不适用场景

- 需要精确格式控制的专业排版 → 直接调用社区上游 `docx` / `pdf` 技能
- 文件格式互转（docx→pdf）→ 用 `work-convert`
- 解析/读取文档内容 → 用 `work-markitdown`

## 格式选择决策树

```
用户需要导出什么格式？
├─ Word (.docx)
│   → 调用 docx 社区上游技能
│   → docx-js 生成 / pandoc 转换
├─ PDF (.pdf)
│   → 调用 pdf 社区上游技能
│   → reportlab 生成 / soffice 转换
├─ Excel (.xlsx)
│   → 调用 xlsx 社区上游技能
│   → openpyxl 生成
├─ PowerPoint (.pptx)
│   → 调用 pptx 社区上游技能
│   → pptxgenjs 生成
└─ 多种格式
    → 按依赖顺序：源文档 → 派生导出
    → 例：先生成 docx，再从 docx 转 pdf
```

## 工作流

### Markdown → Word

1. 确认 Markdown 源文件内容已确认
2. 调用 `docx` 技能生成 `.docx`
3. 校验：在 Office/WPS 中打开确认格式正确

### Markdown → PDF

1. 确认 Markdown 源文件内容已确认
2. 选择管线：
   - 直接生成：`reportlab` / `md-to-pdf`
   - 经 docx 中转：先生成 docx → `soffice --convert-to pdf`
3. 校验：渲染页面确认排版

### 数据 → Excel

1. 确认数据源（CSV / JSON / 数据库查询结果）
2. 调用 `xlsx` 技能生成 `.xlsx`
3. 校验：打开确认公式无错误、格式正确

### 大纲 → PowerPoint

1. 确认大纲结构（标题/要点层级）
2. 调用 `pptx` 技能生成 `.pptx`
3. 校验：缩略图预览确认布局

## 统一输出校验

每种格式导出后 MUST 执行：

| 格式 | 校验项 |
|------|--------|
| docx | Office/WPS 打开无报错，标题/段落格式正确 |
| pdf | 页数正确，无截断/空白页，中文无乱码 |
| xlsx | 公式无 #REF!/#VALUE! 错误，表头对齐 |
| pptx | 缩略图预览，文字不溢出，图片显示正常 |

## 与 work 生态的协作

```
内容 (Markdown/数据/大纲)
    │
    ▼
work-export (本技能：内容→目标格式)
    │
    ├─→ docx (社区上游：Word 生成)
    ├─→ pdf  (社区上游：PDF 生成)
    ├─→ xlsx (社区上游：Excel 生成)
    └─→ pptx (社区上游：PPT 生成)
```

## 推荐输出格式

执行完毕后按以下结构输出：

**状态**：✅ 成功 / ⚠️ 部分成功 / ❌ 失败

| <输入→输出文件/格式/路径> | <值/状态> | 说明 |
|------|------|------|

**下一步**：<可执行动作>

## 约束

- 不实现格式生成逻辑，完全依赖社区上游技能
- 多格式导出时按依赖顺序执行（源文档 → 派生导出）
- 每次导出后 MUST 输出校验结果和文件路径
- 中文文档默认使用思源黑体或微软雅黑
