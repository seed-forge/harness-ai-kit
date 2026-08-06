# Team Gitea Workflow Reference

## 平台概述

团队内部 Git 平台为 Gitea，主要实例：

| 实例 | 用途 | CLI 工具 |
|------|------|----------|
| Gitea（内网） | 内部仓库、CI 触发 | `tea` / `giteactl` |
| GitHub（公网） | 开源项目、镜像同步 | `gh` |

## tea CLI 常用操作

```bash
# 登录
tea login add --url https://gitea.internal --token <token>

# 查看仓库
tea repos list

# 创建 PR
tea pr create --head feature/my-feature --base main --title "feat: ..."

# 查看 PR
tea pr list --state open

# 查看 CI 状态
tea pr view <number>
```

## giteactl（团队自研）

giteactl 是 tea 的补充 wrapper，主要补治理缺口：

```bash
# 镜像管理（tea 不支持）
giteactl mirror create --source gitea --target github --repo my-repo
giteactl mirror sync --repo my-repo
giteactl mirror status --repo my-repo

# 批量审计（tea 不支持）
giteactl org audit --org my-org

# 仓库生命周期
giteactl repo archive --repo my-repo
giteactl repo transfer --repo my-repo --new-owner other-org
```

## Gitea vs GitHub 差异速查

| 操作 | GitHub (`gh`) | Gitea (`tea`) |
|------|---------------|---------------|
| 创建 PR | `gh pr create` | `tea pr create` |
| 查看 checks | `gh pr checks` | `tea pr view` |
| Merge PR | `gh pr merge` | `tea pr merge` |
| 创建 issue | `gh issue create` | `tea issues create` |
| Fork | `gh repo fork` | `tea repo fork` |
| Release | `gh release create` | `tea release create` |

## Token 管理

- Gitea API Token：Settings → Applications → Generate New Token
- 所需权限：`repo`（完整仓库访问）、`user`（用户信息）
- Token 存储在 `~/.team-ai-kit/config.yaml` 的 `assets.giteactl` 段
- 禁止硬编码在脚本或文档中
