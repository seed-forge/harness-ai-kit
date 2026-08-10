# Team Commit Conventions Reference

## 提交格式

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

## Scope 规范

scope 使用**组件/模块 ID**，保持与代码库中的标识一致：

| scope 示例 | 含义 |
|------------|------|
| `cli` | ai-kit CLI 工具链 |
| `homelab-compose-app-deploy` | Homelab Compose 部署技能 |
| `ai-kit-forge` | Forge 资产创造器 |
| `infra-datasource-ops` | 数据源运维技能 |
| `public-git-workflow-expert-base` | 本知识基座 |

## 实际示例

```
feat(cli): ai-kit v0.7.4 — 新增 shared-resources 命令

添加 shared-resources 子命令，支持查询和同步跨空间共享资源清单。
```

```
fix(homelab-compose-app-deploy): 修复 <your-panel>-network 外部网络检测逻辑

之前的检测方式依赖 docker network inspect，当网络不存在时会报错。
改用 docker network ls --filter name= 方式，返回空结果时自动创建。
```

```
docs(ai-kit-forge): 补充 Loop 资产内容规范章节

添加 loop.json 必填字段表、LOOP.md/CHECK.md/USAGE.md 标准结构说明。
```

```
refactor!: 重构 config-governance 配置优先级链

BREAKING CHANGE: 配置优先级从 L1→L2→L3 改为 L3→L2→L1，
与 AGENTS.md 中声明的优先级保持一致。
```

## 反模式

- `update code` — 无 type、无 scope、无信息量
- `feat: 新增功能` — 没有 scope，description 太泛
- `fix bug` — 没有 scope，没说修了什么 bug
- `WIP` — 不应出现在正式分支历史中
