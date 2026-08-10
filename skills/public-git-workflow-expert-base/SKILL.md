---
name: public-git-workflow-expert-base
description: Git 工作流知识基座。extends netresearch/git-workflow-skill 上游通用 Git 知识，叠加团队 commit 规范、分支策略、Gitea 工作流、镜像同步经验。供 devlab-git-workflow-expert 等下游技能通过 extends 继承。
---

# Git Workflow Knowledge Base

Foundational guidance for Git version control workflows, branching strategies, commit conventions, and collaborative development.

> **Source**: Extends [netresearch/git-workflow-skill](https://github.com/netresearch/git-workflow-skill) v1.18.8 (CC-BY-SA-4.0). Team-specific rules overlay on top.

## 架构分层

```
┌─────────────────────────────────────────────┐
│  下游技能（extends 本基座）                    │
│  devlab-git-workflow-expert 等               │
├─────────────────────────────────────────────┤
│  团队规范叠加层（本文件 §团队规范章节）          │
│  commit 规范 / 分支策略 / Gitea / 镜像同步     │
├─────────────────────────────────────────────┤
│  上游通用知识（netresearch/git-workflow-skill） │
│  branching / commits / PR / CI / hooks       │
└─────────────────────────────────────────────┘
```

## Workflow

1. Determine the workflow model (Git Flow / GitHub Flow / Trunk-based).
2. Create branch following naming conventions (Section: Branch Naming).
3. Make atomic commits with Conventional Commits (Section: Commit Conventions).
4. Push and open PR with proper description (Section: PR Workflow).
5. Ensure CI green + all review threads resolved before merge.
6. Merge with appropriate strategy — **feature PR 默认 squash**（见 §PR Workflow）。
7. Release 打 tag：`v{major}.{minor}.{patch}`（见 §Release & Tag）。

## Critical Rules (Non-Negotiable)

1. **No direct push to main** — always open a PR.
2. **No merge before all threads resolved** — see references/pull-request-workflow.md.
3. **Feature PR 默认 squash merge** — 开发分支历史压缩为一个干净 commit；release/hotfix 保留完整历史。
4. **No "tested/verified" without pasted command output** — else say so explicitly.
5. **Force-push only with `--force-with-lease`** — never plain `--force`.
6. **Commit before rebase** — add → commit → fetch → rebase → push. Dirty tree aborts rebase.
7. **No editorializing** — state what changed, not how good it is.
8. **Gitea-first** — `git clone` 和 `git remote` 优先使用 Gitea 内网地址，避免直连 GitHub。
9. **内网镜像优先** — `git clone` 时优先 Gitea 内网镜像 URL，减少公网流量和延迟。

## Commit Conventions

### 上游 Conventional Commits

```
<type>[scope]: <description>

[optional body]

[optional footer(s)]
```

Types: `feat` (MINOR), `fix` (PATCH), `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`

Breaking change: Add `!` after type or `BREAKING CHANGE:` in footer.

### 团队叠加规范

在通用 Conventional Commits 基础上，团队额外约定：

1. **scope 使用组件/模块 ID**：如 `feat(cli):`, `fix(homelab-compose-app-deploy):`, `docs(ai-kit-forge):`
2. **description 使用中文或英文均可**，但同一 PR 内保持一致
3. **多变更拆原子 commit**：一个 commit 做一件事，便于 bisect 和 revert
4. **commit body 说明 why**：type+scope 说明 what，body 说明 why（非显而易见时）
5. **CHANGELOG 由 commit 自动生成**：`feat`/`fix`/`BREAKING CHANGE` 会出现在 CHANGELOG 中

References:
- [team-commit-conventions](references/REFERENCE-TEAM-COMMIT-CONVENTIONS.md)

## Branch Naming

```
feature/TICKET-123-description
fix/TICKET-456-bug-name
release/1.2.0
hotfix/1.2.1-security-patch
docs/update-skill-guide
refactor/simplify-auth-flow
```

### 团队分支策略选择

| 项目类型 | 推荐策略 | 理由 |
|----------|----------|------|
| 个人工具/脚本仓库 | Trunk-based（直接 main） | 轻量，无需 PR 流程 |
| CLI / Skill / 正式项目 | GitHub Flow（feature → main） | PR review + CI gate |
| 多人协作 / 生产服务 | Git Flow（develop + release + hotfix） | 完整发布管理 |

### 团队特殊约定

- **02-工程工作空间**：大部分子项目使用 Trunk-based 或 GitHub Flow
- **fleet-platform / 控制仓**：必须 PR + review，禁止直推 main
- **ai-kit skills 仓库**：PR + CI gate，merge 后自动 publish

References:
- [team-branch-strategy](references/REFERENCE-TEAM-BRANCH-STRATEGY.md)

## PR Workflow

### 上游规则（netresearch/git-workflow-skill）

1. Default-branch check before PR operations
2. Atomic commits, no squash unless asked
3. Merge strategies: merge / squash / rebase
4. Review thread resolution mandatory
5. Merge gate: CI green + threads resolved + rebased + signed

### 团队叠加

- **PR 标题遵循 commit convention**：`feat(cli): add shared-resources command`
- **PR body 包含变更摘要和影响范围**
- **Gitea PR**：使用 `tea pr create` 或 REST API，参考 giteactl 技能
- **自审 checklist**：merge 前自行检查 — 无遗留 TODO、测试通过、文档更新

### 合并策略（来自踩坑纠正）

| 场景 | 策略 | 理由 |
|------|------|------|
| Feature PR → main | **squash merge**（默认） | 历史干净，一个 feature 一个 commit |
| Release branch → main | merge commit | 保留 release 完整历史 |
| Hotfix → main | merge commit | 保留修复上下文 |
| 小修小补（typo/docs） | rebase (fast-forward) | 线性历史 |

> **注意**：上游 netresearch/git-workflow-skill 默认 no squash。本团队覆盖为 **feature PR 默认 squash**，release/hotfix 保留 merge commit。

References:
- [team-pr-workflow](references/REFERENCE-TEAM-PR-WORKFLOW.md)

## Release & Tag

### Tag 命名规范（来自踩坑纠正）

```
v{major}.{minor}.{patch}
```

| 示例 | 含义 |
|------|------|
| `v1.0.0` | 首个正式版 |
| `v1.2.3` | patch 修复 |
| `v2.0.0-rc.1` | 预发布候选 |
| `v0.1.0` | draft/trial 阶段 |

**规则**：
- Tag 必须带 `v` 前缀
- 严格遵循 SemVer（语义化版本）
- 打 tag 前确保 CI green、CHANGELOG 已更新
- `git tag -a v1.2.3 -m "release: v1.2.3"` 使用 annotated tag（不用 lightweight）
- 推送 tag：`git push origin v1.2.3`

### Tag 触发 CI Release

- Woodpecker：`.woodpecker.yml` 配置 `when: { event: tag }` 触发 release pipeline
- Jenkins：Jenkinsfile 配置 tag filter 触发 release build

## 多仓协同（来自高频踩坑）

团队日常在多个 Git 仓库间切换（Gitea 镜像、server-apps、控制仓、应用仓），86% 会话涉及多仓操作。

### 目录结构规范

```
~/repos/
├── gitea/           # Gitea 内网仓库
│   ├── server-apps/
│   ├── fleet-platform/
│   └── my-app/
└── github/          # GitHub 开源/镜像
    └── open-source-project/
```

### 多仓操作最佳实践

1. **按 remote 分目录**：`gitea/` vs `github/`，避免混淆
2. **使用 git worktree**：同一仓库多分支并行开发（详见 REFERENCE-ADVANCED-GIT.md）
3. **批量状态检查**：`for d in */; do echo "=== $d ==="; git -C "$d" status -s; done`
4. **统一 remote 命名**：origin = 主 remote（Gitea），upstream = 上游（GitHub）

References:
- [multi-repo](references/REFERENCE-MULTI-REPO.md)

## CI/CD Integration

### 上游规则

- Watching CI from CLI: `gh pr checks`, `gh run watch`
- Git mirror repository sync: `git push --mirror` gotchas

### 团队叠加

- **Woodpecker CI**：Homelab 项目主要 CI，使用 `.woodpecker.yml`
- **Jenkins**：Java 项目 + shared library，使用 Jenkinsfile
- **Git mirror sync**：Gitea ↔ GitHub 双向镜像，注意 `--mirror` 会覆盖所有 refs

References:
- [team-ci-cd](references/REFERENCE-TEAM-CI-CD.md)

## Git Hooks

### 上游支持

Detect hooks first:
```bash
ls lefthook.yml .lefthook.yml captainhook.json .pre-commit-config.yaml .husky/pre-commit 2>/dev/null || echo "No hooks"
```

Install: `lefthook install` | `composer install` | `npm install` | `pre-commit install`

### 团队叠加

- 优先使用 **lefthook**（跨语言、配置简洁）
- Python 项目可配合 **pre-commit** + ruff/black/isort
- 提交前必须通过 hook 检查：commit message 格式 + 基础 lint

## Advanced Operations

Reference:
- [advanced-git](references/REFERENCE-ADVANCED-GIT.md) — rebase, cherry-pick, bisect, stash, worktrees, reflog, recovery

## Gitea 工作流

团队内部 Git 平台为 Gitea，与 GitHub 的差异：

| 操作 | GitHub | Gitea |
|------|--------|-------|
| CLI | `gh` | `tea` / `giteactl` |
| PR 创建 | `gh pr create` | `tea pr create` 或 REST API |
| Mirror | `git push --mirror` | Gitea 内置镜像同步 |
| Webhook | GitHub Actions | Woodpecker CI |
| Token | Personal Access Token | API Token（Settings → Applications） |

References:
- [team-gitea-workflow](references/REFERENCE-TEAM-GITEA-WORKFLOW.md)

## Guardrails

- Never force-push to main/master without explicit user approval.
- Never use plain `--force` — always `--force-with-lease`.
- Never push secrets, tokens, or credentials in commits.
- Never skip CI checks before merge — ensure all gates green.
- Never use merge commit for feature PRs — use squash merge.
- Never use `dev/xxx` or unprefixed branch names — always `feature/xxx`, `fix/xxx`, etc.
- Never `git clone` from GitHub when a Gitea internal mirror exists.
- Prefer `git pull --rebase` over `git pull` to avoid merge commits on feature branches.
- Use `git add -p` for interactive staging when changes span multiple concerns.

参考文档：
- references/REFERENCE-README.md
