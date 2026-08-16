# Nexus 仓库命名规范

基于现有 65 个仓库的实际命名提取的规范。新建仓库时必须遵循。

## 通用命名模式

| 类型 | 模式 | 示例 |
|------|------|------|
| proxy | `{format}-proxy-{上游源}` | `pypi-proxy-repository-aliyun`, `docker-proxy-dockerhub` |
| hosted | `{format}-hosted-{用途}` | `pypi-hosted-repository`, `raw-hosted-cli` |
| group | `{format}-group` 或 `{format}-all-{用途}` | `pypi-group-repository-all`, `raw-all-skill` |

## 各格式具体规范

### PyPI
- proxy: `pypi-proxy-repository-{源}` — 如 `pypi-proxy-repository-tsinghua`
- hosted: `pypi-hosted-{用途}` — 如 `pypi-hosted-pytorch`
- group: `pypi-group-repository-all`

### npm
- proxy: `private-npm-proxy-{源}` — 如 `private-npm-proxy-taobao`
- hosted: `private-npm-hosted`
- group: `private-npm-group`

### Maven2
- proxy: `nexus-private-proxy-{源}` 或 `private-maven-proxy-{源}` — 如 `nexus-private-proxy-aliyun-repository`
- hosted: `private-maven-hosted-{用途}` 或 `maven-{releases|snapshots}` — 如 `private-maven-hosted-dev-platform`
- group: `maven-public` 或 `nexus-private-public`

### NuGet
- proxy: `nuget.org-proxy`
- hosted: `nuget-hosted`
- group: `nuget-group`

### Docker
- proxy: `docker-proxy-{源}` — 如 `docker-proxy-dockerhub`
- hosted: `docker-hosted-{用途}` — 如 `docker-hosted-private`
- group: `docker-public`

### Raw
- proxy: `private-raw-proxy-{名}` — 如 `private-raw-proxy---node-sass`
- hosted: `raw-hosted-{用途}` — 如 `raw-hosted-soft`, `raw-hosted-cli`
- group: `raw-all-{用途}` — 如 `raw-all-soft`, `raw-all-skill`

### APT (Nexus OSS 限制)
- proxy: `apt-{发行版}-{dist}` — 如 `apt-ubuntu-jammy`, `apt-ubuntu-jammy-security`
- hosted: 支持（命名同上）
- group: **Nexus OSS 不支持**（仅 Pro 版）

### Conda
- proxy: `conda-proxy-repository-{源}` — 如 `conda-proxy-repository-tsinghua`
- hosted/group: Nexus OSS 不支持

## Blob Store 选择策略

### 标准规则

| 场景 | Blob Store 命名 | 说明 |
|------|-----------------|------|
| 新 format 首仓 | `{format}-hosted-store` | 每种 format 独立 blob store，禁止共用 |
| 按用途隔离 | `{format}-hosted-store-{用途}` | 同 format 多 hosted 且需物理隔离时使用 |
| proxy 仓库 | `{format}-proxy-store` | proxy 缓存独立存储 |
| group 仓库 | `{format}-group-store` 或 `{format}-all-store` | group 聚合存储 |

### 创建 hosted 仓库时决策流程

1. 查 `nexusctl --json repo list` 确认该 format 是否已有专用 blob store
2. 若已有 → 直接复用（如 `pypi-hosted-store`）
3. 若需按用途隔离（如 CLI 包 vs 业务包）→ 新建 `{format}-hosted-store-{用途}`
4. `write_policy` 统一为 `allow`（hosted 允许写入）
5. **禁止**新仓库使用 `default` blob store

### 遗留特例（待无感治理）

| 仓库 | 现状 | 目标 | 治理方式 |
|------|------|------|----------|
| nuget-hosted | 使用 `default` | `nuget-hosted-store` | 新建专用 store + 仓库迁移 |
| private-npm-hosted | 使用 `npm-repository-storage`（旧名） | `npm-hosted-store` | 新建 store + 仓库迁移 |
| raw-hosted-cli | 共享 `raw-hosted-store-soft` | `raw-hosted-store-cli` | 新建独立 store + 迁移 |

治理时机：在 Nexus 维护窗口期执行，需先停写 → 创建新 store → 移动数据 → 更新仓库配置 → 验证。

## 命名检查清单

创建新仓库前确认：
1. 前缀是否为 format 名（pypi/npm/maven/docker/raw/nuget/apt/conda）
2. 中间是否标识类型（proxy/hosted/group 或 all）
3. 后缀是否说明源或用途（避免含义不明的名称）
4. 是否与已有仓库名称冲突（用 `nexusctl repo list` 检查）
