# Phase 1: Project Exploration

**目标**: 深入理解项目的定位、技术栈、需求和约束，产出项目上下文包。

## Objective

- 扫描项目结构，识别技术栈
- 提取项目的业务定位和核心需求
- 识别项目的设计语言和约束条件
- 产出标准化的 project-context.md

## Execution Steps

### Step 1: 读取项目关键文件

```bash
# 读取项目根目录的关键配置文件
ls {project_path}/
cat {project_path}/package.json
cat {project_path}/README.md
cat {project_path}/CLAUDE.md  # if exists
```

### Step 2: 扫描项目结构

```bash
# 识别项目目录结构
find {project_path} -maxdepth 2 -type f -name "*.json" -o -name "*.yaml" -o -name "*.yml" -o -name "*.toml" | head -20
```

### Step 3: 识别技术栈

从 package.json 中提取：
- 框架（React/Vue/Astro/Next.js 等）
- 构建工具（Vite/Webpack/Rollup 等）
- 测试框架（Jest/Vitest/Playwright 等）
- 核心依赖（UI 库、动画库、可视化库等）

### Step 4: 提取设计语言

```bash
# 查找主题/样式相关文件
find {project_path} -type f \( -name "*.css" -o -name "*.scss" -o -name "*.less" \) | head -10
grep -r "theme\|color\|palette" {project_path}/src --include="*.css" --include="*.ts" --include="*.js" | head -20
```

### Step 5: 识别业务需求

从 README、CLAUDE.md、文档中提取：
- 核心功能列表
- 目标用户
- 性能要求
- 兼容性要求

### Step 6: 生成 project-context.md

按照 `specs/analysis-template.md` 中的结构，生成项目上下文包。

## Output

- **File**: `project-context.md`
- **Location**: `.workflow/.tech-fit/{timestamp}/`
- **Format**: Markdown

## Next Phase

Proceed to [Phase 2: Library Research](02-library-research.md) with the generated project-context.md.
