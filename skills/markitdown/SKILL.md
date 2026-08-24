---
name: markitdown
description: 使用当前环境已安装的 MarkItDown，把 DOCX、PDF、PPTX、XLSX、图片、HTML、CSV 等文件稳定转换为 Markdown。用户提到“转成 md”“markitdown”“文档转 markdown”“把 docx/pdf/pptx/xlsx 变成 markdown”时使用。
---

# MarkItDown

这是当前项目的本地化 `markitdown` 技能入口。

它基于上游全局 Skill，但这里补上了本环境下已经验证过的稳定用法，避免每次重复处理安装和命令路径问题。

## Use This Skill For

- 把 `docx`、`pdf`、`pptx`、`xlsx` 转成 markdown
- 批量把资料转换成更适合 LLM 处理的文本格式
- 在 Obsidian 项目里落地文档转写结果

## Environment Notes

- 当前环境已验证 `python -m markitdown` 可用
- 建议优先调用本地包装命令：
  - `.\.agents\tools\markitdown.cmd`
- 如果直接输入 `markitdown` 失败，通常是因为 Python 的 `Scripts` 目录不在 `PATH`

## Stable Invocation

```powershell
.\.agents\tools\markitdown.cmd input.docx -o output.md
```

或：

```powershell
python -m markitdown input.docx -o output.md
```

## Verified Dependency Strategy

本环境里不建议直接依赖：

```bash
pip install "markitdown[all]"
```

因为实测可能把主包错误回退到旧版本。

更稳的方式是：

```powershell
python -m pip install --upgrade markitdown==0.1.5
python -m pip install azure-ai-documentintelligence azure-identity openpyxl pandas pydub python-pptx speechrecognition youtube-transcript-api openai pathvalidate puremagic mammoth olefile xlrd pdfminer-six pdfplumber
```

## Workflow

1. 确认源文件存在，并避免覆盖现有 `.md`
2. 优先输出到新文件名，例如 `*.markitdown.md`
3. 转换后抽查文件头部，确认不是空文件
4. 如需给 Obsidian 使用，再做一轮 markdown 清洗


## 推荐输出格式

执行完毕后按以下结构输出：

**状态**：✅ 成功 / ⚠️ 部分成功 / ❌ 失败

| <输入→输出文件/格式/路径> | <值/状态> | 说明 |
|------|------|------|

**下一步**：<可执行动作>
## Practical Notes

- DOCX 已在当前环境验证通过
- PDF、PPTX、XLSX、音频、YouTube 转写依赖已补齐
- Azure Document Intelligence 和 OpenAI 增强能力仍需各自凭证
