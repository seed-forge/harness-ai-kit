# Skill 资产创建规范

## 何时选择 Skill

- 流程可文档化，步骤稳定
- 特定库/框架的使用指南（`*-usage` 后缀）
- 输入输出明确，可被其他团队成员理解

## Skill 目录结构

```
skills/{id}/
├── SKILL.md          # 核心文件：用途、输入、输出、工作流、约束
├── skill.json        # 元数据：namespace, id, version, tags, dependencies
├── USAGE.md          # 精炼说明 + "可直接复制的中文 Prompt"
├── CHANGELOG.md      # 版本历史
└── references/       # 可选：拆分过大的内容
    └── REFERENCE-*.md
```

## skill.json 必填字段

| 字段 | 说明 | 示例 |
|------|------|------|
| `namespace` | 资产命名空间 | `"team"` |
| `id` | 唯一标识 | `"devlab-web-test-e2e"` |
| `name` | 人类可读名称 | `"React 研发 SOP"` |
| `version` | 语义化版本 | `"0.1.0"` |
| `status` | `draft` / `trial` / `stable` | `"trial"` |
| `tags` | 关键词标签 | `["devlab", "react", "frontend"]` |
| `summary` | 一句话说明 | — |
| `dependencies` | 依赖列表（DependencySpec 对象） | 见下方 |
| `compatible_clients` | 兼容的 IDE 客户端 | `["codex", "claude-code", "cursor"]` |

## dependencies 格式

```json
"dependencies": [
  {"type": "skill", "namespace": "team", "id": "base-session-ai-kit-miner", "version": ">=0.3.0", "scope": "required"}
]
```

- `scope` 为 `required` 时自动安装；`optional` 需 `--feature` 触发
- `version` 必须为合法 specifier（`>=0.2.0`、`==1.0.0` 等）

## SKILL.md 标准结构

```markdown
---
name: {id}
description: {一句话说明}. Triggers on "{触发词}".
---

# {id}

## 用途
## 输入
## 输出
## 工作流
## 约束
## 专题引用
```

## `*-usage` 后缀规则

当沉淀内容是**特定库/框架的使用指南**时，使用 `*-usage` 后缀：

- 包含库的基本信息（名称、GitHub 地址、官方文档、版本）
- 包含核心概念和 API 模式
- 包含踩坑经验（`references/REFERENCE-PITFALLS.md`）
- 包含与目标框架的集成指南
- 不包含业务特定的实现代码

**示例**：`devlab-web-xyflow-usage` 包含 @xyflow/react 的库信息、核心概念、踩坑经验、框架集成指南。

## 团队共享 vs 项目级

| 条件 | 位置 |
|------|------|
| 输入输出稳定 + 不依赖私有上下文 | 团队共享 `harness-ai-kit/skills/` |
| 输入输出不稳定 或 依赖私有上下文 | 项目级 `.claude/skills/` |
