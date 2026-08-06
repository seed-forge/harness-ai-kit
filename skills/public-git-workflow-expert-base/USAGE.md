# public-git-workflow-expert-base 使用说明

## 一句话

Git 工作流知识基座，被下游技能通过 extends 继承。一般不直接使用。

## 触发场景

| 你说的话 | AI 自动执行 |
|----------|-------------|
| 被 extends 继承 | devlab-git-workflow-expert 自动合并本技能的 commit/branch/PR 等章节 |
| 直接使用 | 安装后获取 Git 工作流通用知识 + 团队规范参考 |

## 可直接复制的中文 Prompt

```
我在创建一个新的 feature 分支，帮我按团队规范设置分支名和 commit 格式。
```

```
这个 PR 准备 merge，帮我检查是否符合团队 Git workflow 规范。
```

## 覆盖主题

### 上游通用（netresearch/git-workflow-skill）
- Branching Strategies（Git Flow / GitHub Flow / Trunk-based）
- Conventional Commits（feat/fix/docs/refactor...）
- PR Workflow（merge gate / review threads / merge strategies）
- CI/CD Integration（gh pr checks / mirror sync）
- Git Hooks（lefthook / pre-commit / husky）
- Advanced Operations（rebase / cherry-pick / bisect / worktrees）

### 团队叠加层
- Commit scope 规范（使用组件/模块 ID）
- 分支策略选择矩阵（按项目类型）
- Gitea 工作流（tea / giteactl CLI）
- Woodpecker + Jenkins CI 集成
- Git mirror sync（Gitea ↔ GitHub）

## 与下游技能的分工

- **你（知识基座）**：提供 Git 工作流通用知识 + 团队规范叠加
- **下游（devlab-git-workflow-expert）**：面向开发者的具体指导、交互式操作
- **运维（infra-*-ops）**：CI/CD 流水线部署、Git 镜像同步操作

## 来源

extends [netresearch/git-workflow-skill](https://github.com/netresearch/git-workflow-skill) v1.18.8（CC-BY-SA-4.0）
