# Team CI/CD Reference

## CI 平台分布

| 平台 | 适用项目 | 配置文件 | 触发方式 |
|------|----------|----------|----------|
| Woodpecker CI | Homelab 应用、fleet-platform | `.woodpecker.yml` | Gitea webhook |
| Jenkins | Java 项目、shared library | `Jenkinsfile` | Gitea/GitHub webhook |
| GitHub Actions | GitHub 开源项目 | `.github/workflows/*.yml` | GitHub event |

## Woodpecker CI

### 典型 pipeline 结构

```yaml
pipeline:
  build:
    image: golang:1.22
    commands:
      - make build

  test:
    image: golang:1.22
    commands:
      - make test

  publish:
    image: plugins/docker
    settings:
      registry: harbor.base.example.com
      repo: ${CI_REPO}
    when:
      branch: [main]
```

### 与 Gitea 的集成

- Woodpecker 通过 Gitea webhook 触发
- 构建状态回写到 Gitea commit status
- Pipeline 日志可从 Woodpecker UI 或 Gitea commit 页面查看

## Jenkins

### Shared Library 模式

团队 Jenkins 使用 shared library，Jenkinsfile 引用共享函数：

```groovy
@Library('homelab-jenkins-shared-library') _

standardPipeline(
  appName: 'my-app',
  buildTool: 'maven',
  deployTarget: '<host-02>'
)
```

### 关键插件

- Git plugin — 源码拉取
- Pipeline — Jenkinsfile 支持
- Credentials Binding — 凭据管理
- SSH Agent — 远程部署

## Git Mirror Sync

### Gitea ↔ GitHub 双向镜像

使用 Gitea 内置镜像同步功能：

1. Gitea 仓库 Settings → Mirror Settings
2. 配置 GitHub remote URL + credentials
3. 同步方向：push（Gitea → GitHub）或 pull（GitHub → Gitea）

### 注意事项

- `git push --mirror` 会**覆盖目标仓库所有 refs**，慎用
- 镜像同步不包含 issues、PR、wiki 等非 Git 数据
- 同步失败时检查网络连通性和 token 有效性
- 建议配置同步间隔而非实时同步，减少 API 压力

## Pipeline 触发规范（来自踩坑纠正）

### Git Push → Pipeline 映射

| Git 事件 | 触发 Pipeline | 配置方式 |
|----------|--------------|----------|
| Push to `main` | CI build + test | `when: { branch: [main] }` |
| Push to `feature/*` | CI build + test（不发布） | `when: { branch: [feature/*] }` |
| Push tag `v*` | **Release pipeline**（构建 + 发布） | `when: { event: tag }` |
| PR opened | PR checks（lint + test） | Webhook 自动触发 |

### Tag 命名与 Release Pipeline

```bash
# 正确：触发 release pipeline
git tag -a v1.2.3 -m "release: v1.2.3"
git push origin v1.2.3

# 错误：不会触发 release pipeline
 git tag -a 1.2.3          # 缺少 v 前缀
 git tag -a release-1.2.3  # 错误前缀，CI 规则不匹配
 git tag v1.2.3            # lightweight tag，缺少注释
```

### 常见触发失败排查

| 症状 | 根因 | 修复 |
|------|------|------|
| Push 后 pipeline 未触发 | 分支匹配规则错误 | 检查 `when.branch` 配置 |
| Tag push 未触发 release | tag 命名不符合 `v*` 规则 | 使用 `v{major}.{minor}.{patch}` |
| PR checks 未运行 | Webhook 未配置或 token 过期 | 检查 Gitea → Woodpecker webhook |
| Jenkins 未触发 | Jenkinsfile 缺少或 SCM 配置错误 | 检查 Jenkins job SCM 轮询/webhook |
