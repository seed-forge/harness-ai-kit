---
name: work-markitdown
description: "办公文档通用 Inflow 编排：把 DOCX、PDF、PPTX、XLSX、图片、HTML、CSV 等 15+ 格式稳定转换为 Markdown。extends 上游 markitdown 技能，补充本地环境适配和批量转换工作流。用户提到'转成 md''文档转 markdown''解析文档''读取文档内容'时使用。"
---

# work-markitdown

## 用途

作为 work 命名空间的**通用 Inflow 基座**，提供 15+ 种文件格式到 Markdown 的统一转换入口。

本技能 `extends` 上游 `markitdown` 社区技能，不重新实现转换逻辑，而是：
- 补充本地环境已验证的稳定调用方式
- 定义与 work-* 编排层其他技能的协作约定
- 提供批量转换和质量校验工作流

## 依赖

- **extends**: `markitdown`（社区上游，负责实际格式转换）
- **被依赖**: `work-export`、`work-convert`、`work-dispatcher`、`work-sc-*` 场景技能

## 适用场景

- 把 `docx`、`pdf`、`pptx`、`xlsx` 转成 markdown
- 批量把资料文件夹转换成更适合 LLM 处理的文本格式
- 在 Obsidian 知识库项目里落地文档转写结果
- 为下游 `work-export`（导出）或 `work-sc-*`（场景）提供 Inflow 输入

## 不适用场景

- 需要保留格式精确排版的导出 → 用 `work-export`
- 文件格式互转（docx→pdf）→ 用 `work-convert`
- 对 Word/PDF 做精细编辑 → 直接调用社区上游 `docx` / `pdf` 技能

## 本地环境适配

### 稳定调用方式

优先使用本地包装命令：

```powershell
.\.agents\tools\markitdown.cmd input.docx -o output.md
```

回退方式：

```powershell
python -m markitdown input.docx -o output.md
```

### 已验证依赖

不建议 `pip install "markitdown[all]"`（实测可能回退主包版本）。推荐：

```powershell
python -m pip install --upgrade markitdown>=0.1.5
python -m pip install openpyxl pandas pydub python-pptx pdfminer-six pdfplumber mammoth xlrd
```

如需 Azure / OpenAI 增强能力，各自配置凭证。

## 支持格式

| 格式 | 说明 | 质量 |
|------|------|------|
| PDF | 文本提取 | 良好（扫描件需 OCR） |
| DOCX | Word 文档 | 良好（表格/格式保留） |
| PPTX | PowerPoint | 良好（含备注） |
| XLSX | Excel | 良好（表格数据） |
| Images | JPEG/PNG/GIF/WebP | EXIF + OCR |
| Audio | WAV/MP3 | 元数据 + 转写 |
| HTML | 网页 | 清洁转换 |
| CSV/JSON/XML | 结构化数据 | 表格/结构化 |
| ZIP | 归档 | 迭代内容 |
| EPUB | 电子书 | 全文提取 |

## 工作流

### 单文件转换

1. 确认源文件存在
2. 执行转换，输出到新文件名（如 `*.markitdown.md`），避免覆盖已有 `.md`
3. 抽查文件头部，确认非空
4. 如需 Obsidian 使用，做 markdown 清洗

### 批量转换

```powershell
Get-ChildItem -Path "资料目录" -Include *.docx,*.pdf,*.pptx,*.xlsx -Recurse | ForEach-Object {
    $outName = $_.FullName -replace '\.[^.]+$', '.markitdown.md'
    python -m markitdown $_.FullName -o $outName
    Write-Host "Converted: $($_.Name) -> $outName"
}
```

### 质量校验

转换后检查：
- 文件非空且行数 > 5
- 无明显乱码或截断
- 表格数据完整（如有）

## 与 work 生态的协作

```
源文件 (docx/pdf/pptx/xlsx/...)
    │
    ▼
work-markitdown (本技能：文件→MD)
    │
    ├─→ work-export (MD→目标格式导出)
    ├─→ work-sc-patent-docx-exporter (MD→专利文档)
    └─→ 直接交付 (知识库/Obsidian)
```

## 推荐输出格式

执行完毕后按以下结构输出：

**状态**：✅ 成功 / ⚠️ 部分成功 / ❌ 失败

| <输入→输出文件/格式/路径> | <值/状态> | 说明 |
|------|------|------|

**下一步**：<可执行动作>

## 约束

- 不覆盖已有同名 `.md` 文件，默认输出 `*.markitdown.md`
- 扫描件 PDF 的 OCR 质量取决于原文件清晰度
- Azure Document Intelligence 和 OpenAI 增强需要各自 API Key
- 本技能不实现格式转换逻辑，完全依赖上游 `markitdown`
