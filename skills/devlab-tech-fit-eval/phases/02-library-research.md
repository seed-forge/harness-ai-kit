# Phase 2: Library Research

**目标**: 深入理解技术库的能力、限制和生态，产出技术库分析报告。

## Objective

- 研究库的官方文档和 API 参考
- 分析库的核心能力、性能特征、平台支持
- 研究库的生态（框架集成、社区活跃度）
- 识别库的限制和已知问题
- 产出标准化的 library-analysis.md

## Execution Steps

### Step 1: 研究库的官方信息

```bash
# WebSearch: 库的官方文档
WebSearch("{library_name} official documentation API reference")
```

### Step 2: 分析核心能力

从官方文档中提取：
- 核心 API 和功能列表
- 支持的渲染方式（SVG/Canvas/DOM）
- 配置参数和选项
- 性能特征

### Step 3: 研究生态和集成

```bash
# WebSearch: 框架集成
WebSearch("{library_name} React Vue Angular integration")
```

分析：
- 框架集成方式
- 社区活跃度（GitHub star、贡献者、issue 响应时间）
- 版本发布频率
- 替代方案

### Step 4: 识别限制和问题

```bash
# WebSearch: 已知问题
WebSearch("{library_name} known issues limitations")
```

### Step 5: 生成 library-analysis.md

按照 `specs/analysis-template.md` 中的结构，生成技术库分析报告。

## Output

- **File**: `library-analysis.md`
- **Location**: `.workflow/.tech-fit/{timestamp}/`
- **Format**: Markdown

## Next Phase

Proceed to [Phase 3: Fit Point Identification](03-fit-points.md) with the generated library-analysis.md.
