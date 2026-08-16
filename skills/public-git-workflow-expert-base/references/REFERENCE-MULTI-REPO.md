# Multi-Repo Coordination Reference

> 来源：853 会话挖掘，86% 会话涉及多仓操作（GIT-P01）。

## 团队多仓现状

团队日常在以下仓库类型间频繁切换：

| 仓库类型 | 示例 | Remote |
|----------|------|--------|
| 工作空间 | 02-工程工作空间 | Gitea |
| 控制仓 | fleet-platform | Gitea |
| 应用仓 | 各 Team 应用 | Gitea |
| 技能仓 | harness-ai-kit skills | Gitea |
| 开源/镜像 | GitHub 开源项目 | GitHub |
| 基础设施 | server-apps | Gitea |

## 目录结构规范

```
~/repos/
├── gitea/              # Gitea 内网仓库（主 remote）
│   ├── workspaces/
│   │   └── 02-工程工作空间/
│   ├── control/
│   │   └── fleet-platform/
│   ├── apps/
│   │   ├── ragflow/
│   │   └── dify/
│   └── skills/
│       └── harness-ai-kit/
└── github/             # GitHub 开源/镜像（upstream）
    └── open-source-project/
```

### 目录命名约定

- 按 **remote 来源** 分顶层目录：`gitea/` vs `github/`
- 按 **业务域** 分子目录：`workspaces/`、`control/`、`apps/`、`skills/`
- 仓库目录名 = 仓库实际名称，不做缩写

## Remote 命名规范

| 场景 | Remote 名称 | URL 来源 |
|------|-------------|----------|
| Gitea 内网（主） | `origin` | Gitea SSH URL |
| GitHub 上游 | `upstream` | GitHub HTTPS/SSH URL |
| 个人 fork | `fork` | 个人 Gitea/GitHub fork |

```bash
# 典型 multi-remote 配置
git remote -v
# origin    git@gitea.internal:org/my-repo.git (fetch)
# origin    git@gitea.internal:org/my-repo.git (push)
# upstream  https://github.com/upstream/repo.git (fetch)
# upstream  https://github.com/upstream/repo.git (push)
```

## 批量操作脚本

### 批量状态检查

```bash
# 检查所有子仓库的状态
for d in */; do
  if [ -d "$d/.git" ]; then
    echo "=== $d ==="
    git -C "$d" status -s
    echo ""
  fi
done
```

### 批量 fetch

```bash
# 所有子仓库拉取最新
for d in */; do
  if [ -d "$d/.git" ]; then
    echo "=== Fetching $d ==="
    git -C "$d" fetch --all --prune
  fi
done
```

### 批量分支清理

```bash
# 清理所有子仓库的已合并分支
for d in */; do
  if [ -d "$d/.git" ]; then
    echo "=== Cleaning $d ==="
    git -C "$d" branch --merged main | grep -v 'main\|master' | xargs -r git -C "$d" branch -d
  fi
done
```

## Git Worktree 使用场景

当需要在**同一仓库**的多个分支上并行工作时，优先使用 worktree 而非多次 clone：

```bash
# 创建 worktree（新目录 + 新分支）
git worktree add ../my-feature feature/my-feature

# 创建 worktree（checkout 已有分支）
git worktree add ../hotfix-branch hotfix/urgent-fix

# 查看所有 worktrees
git worktree list

# 完成后清理
git worktree remove ../my-feature
git worktree prune  # 清理已删除目录的残留
```

### Worktree vs 多次 Clone

| 维度 | Worktree | 多次 Clone |
|------|----------|-----------|
| 磁盘占用 | 低（共享 .git） | 高（每个 clone 一份 .git） |
| 分支冲突 | 不可能（同一仓库） | 可能（两个 clone 同分支） |
| 状态同步 | 自动（同一仓库） | 手动（分别 fetch） |
| 适用场景 | 同仓库多分支 | 不同配置/环境的隔离 |

## 内网镜像优先规则

`git clone` 时优先使用 Gitea 内网镜像，避免直连 GitHub：

```bash
# ✅ 正确：使用 Gitea 内网镜像
git clone git@gitea.internal:mirror/some-open-source-repo.git

# ❌ 错误：直连 GitHub（除非 Gitea 无此镜像）
git clone https://github.com/some-org/some-repo.git
```

**例外**：Gitea 上确实没有该仓库的镜像时，可以直连 GitHub，并考虑是否需要创建镜像。
