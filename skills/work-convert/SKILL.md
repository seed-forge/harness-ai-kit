---
name: work-convert
description: "办公文档格式互转编排：文件 → 文件的格式转换（docx→pdf, pptx→pdf, xlsx→pdf 等）。depends on 社区上游 docx/pdf/xlsx/pptx 和 LibreOffice soffice。用户提到'转成 PDF''格式转换''docx 转 pdf''文档格式互转'时使用。"
---

# work-convert

## 用途

作为 work 命名空间的**格式互转编排层**，提供文件到文件的格式转换能力。

与 `work-export`（内容→格式）的区别：
- `work-export`：从内容出发，生成目标格式
- `work-convert`：从已有文件出发，转换为另一种格式

## 依赖

- **depends**: `docx`、`pdf`、`xlsx`、`pptx`（社区上游）、`work-markitdown`（中转）
- **被依赖**: `work-dispatcher`、`work-sc-*` 场景技能

## 适用场景

- Word 文档转 PDF（docx → pdf）
- PPT 转 PDF（pptx → pdf）
- Excel 转 PDF（xlsx → pdf）
- 任意 Office 文档转 Markdown（经 work-markitdown）
- Markdown 转 HTML（配合模板）

## 不适用场景

- 从原始内容生成文档 → 用 `work-export`
- 解析/读取文档内容 → 用 `work-markitdown`

## 转换管线选择

```
源文件格式 → 目标格式
├─ docx → pdf
│   ├─ 首选：soffice --headless --convert-to pdf
│   └─ 备选：调用 docx + pdf 技能链
├─ pptx → pdf
│   └─ soffice --headless --convert-to pdf
├─ xlsx → pdf
│   └─ soffice --headless --convert-to pdf
├─ * → md
│   └─ 调用 work-markitdown
├─ md → html
│   └─ 配合 CSS 模板生成 standalone HTML
├─ md → docx
│   └─ 调用 docx 技能（pandoc / docx-js）
└─ md → pdf
    ├─ 经 docx 中转：md → docx → pdf
    └─ 直接：reportlab / weasyprint
```

## LibreOffice soffice 管线

最常用的格式互转方式：

```powershell
# Word → PDF
soffice --headless --convert-to pdf input.docx --outdir output/

# PPT → PDF
soffice --headless --convert-to pdf input.pptx --outdir output/

# Excel → PDF
soffice --headless --convert-to pdf input.xlsx --outdir output/

# 批量转换
Get-ChildItem -Path "源目录" -Include *.docx,*.pptx,*.xlsx | ForEach-Object {
    soffice --headless --convert-to pdf $_.FullName --outdir "输出目录/"
}
```

**注意事项**：
- Windows 上 soffice 路径：`"C:\Program Files\LibreOffice\program\soffice.exe"`
- 中文文件名需确保终端编码支持
- 转换后检查输出文件非空

## 质量校验

| 转换方向 | 校验项 |
|---------|--------|
| → pdf | 页数合理、无空白页、中文无乱码 |
| → md | 内容完整、表格保留、无截断 |
| → html | 浏览器渲染正常、样式一致 |
| → docx | Office/WPS 打开无报错 |

## 推荐输出格式

执行完毕后按以下结构输出：

**状态**：✅ 成功 / ⚠️ 部分成功 / ❌ 失败

| <输入→输出文件/格式/路径> | <值/状态> | 说明 |
|------|------|------|

**下一步**：<可执行动作>

## 约束

- 不实现格式转换逻辑，依赖 soffice 和社区上游技能
- soffice 不可用时回退到社区上游技能链式转换
- 每次转换后 MUST 校验输出文件
- 批量转换时输出进度信息
