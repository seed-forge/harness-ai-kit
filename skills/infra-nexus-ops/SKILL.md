---
name: infra-nexus-ops
description: Nexus 平台运维技能。凡是用户提到 Nexus 仓库、raw/PyPI/npm/Maven group、hosted/proxy、仓库巡检、Nexus inventory、创建仓库、blobstore、cleanup policy、nexusctl 时触发。
---

# infra-nexus-ops

用于 Nexus 平台级 day-2 运维。覆盖仓库 CRUD、blob store 管理、cleanup policy 查询、健康探测、inventory 导出与漂移检测。

## 边界

- 本 skill 负责：Nexus repo CRUD（proxy/hosted/group）、blob store 管理、cleanup policy 查询、巡检、inventory 导出到 fleet-platform、漂移检测。
- 不负责：CI 大依赖 manifest 预热、Harbor OCI warm、readiness gate，归 `infra-artifact-readiness-ops`。
- 不负责：Harbor project/robot/proxy cache，归 `infra-harbor-ops`。

## 配置上下文

配置优先级：CLI 参数 > 环境变量 > Profile 文件 > 默认值。

| 配置项 | 环境变量 | Profile 字段 | 默认值 | 敏感度 |
|--------|---------|-------------|--------|--------|
| base_url | NEXUS_BASE_URL | base_url | http://nexus.{base_domain}:19010 | public |
| user | NEXUS_USER | user | - | sensitive |
| password | NEXUS_PASSWORD | password | - | sensitive |

Profile 文件：`~/.nexusctl/profiles.yaml`，详见 `config.defaults.yaml`。

## 操作顺序

### 只读巡检

1. `nexusctl doctor` — 健康检查
2. `nexusctl repo list --json` — 导出仓库事实
3. `nexusctl probe --repository <name>` — 探测仓库
4. `nexusctl inventory summary` — 概览统计
5. 若涉及 CI 依赖，交给 `infra-artifact-readiness-ops`

### 仓库变更

1. `nexusctl doctor` 确认平台健康
2. `--dry-run` 预览请求体
3. 去掉 `--dry-run` 执行
4. `nexusctl repo get --format <fmt> --type <type> --name <name>` 验证

### 创建仓库

```bash
# 预设（推荐）
nexusctl repo create-from-preset pypi-org-proxy --dry-run
nexusctl repo create-from-preset pypi-org-proxy

# 手动 proxy
nexusctl repo create-proxy --format pypi --name pypi-proxy-repository-custom --remote-url https://pypi.org/

# hosted（blob store 自动推导为 {format}-hosted-store）
nexusctl repo create-hosted --format pypi --name pypi-hosted-custom --write-policy allow

# group
nexusctl repo create-group --format pypi --name pypi-group-custom --members "pypi-proxy-repository-custom,pypi-hosted-custom"

# APT proxy
nexusctl repo create-proxy --format apt --name apt-ubuntu-jammy --remote-url http://mirrors.aliyun.com/ubuntu/ --distribution jammy
```

### 更新仓库

```bash
# 修改 group 成员
nexusctl repo update-group --format pypi --name pypi-all --add-members new-repo
nexusctl repo update-group --format pypi --name pypi-all --remove-members old-repo

# 修改 proxy 上游
nexusctl repo update-proxy --format pypi --name pypi-proxy-repository-aliyun --remote-url https://new-url/

# 修改 hosted 写策略
nexusctl repo update-hosted --format pypi --name pypi-hosted-repository --write-policy deny
```

### 删除仓库

```bash
nexusctl repo delete --name <repo-name> --yes
```

## Blob Store 管理

```bash
nexusctl blobstore list
nexusctl blobstore create-file --name pypi-new-store --dry-run
nexusctl blobstore delete --name old-store --yes
```

## Cleanup Policy 查询

```bash
nexusctl cleanup-policy list
nexusctl cleanup-policy get --name base-policy-docker
```

## Inventory 导出与漂移检测

```bash
# 概览
nexusctl inventory summary

# 导出到 fleet-platform
nexusctl inventory export --output fleet-platform --output-path <fleet-platform>/infra/artifact-registry.yaml

# 快速导出（跳过详情补充）
nexusctl inventory export --output yaml --skip-detail

# 漂移检测
nexusctl inventory diff --against <fleet-platform>/infra/artifact-registry.yaml
```

## 仓库命名规范

创建仓库前必须参考 `references/REFERENCE-NAMING-CONVENTIONS.md`。

## 预设列表

`nexusctl repo list-presets` 查看内置预设。


## 推荐输出格式

执行完毕后输出极简回执：**状态**（✅ 成功 / ⚠️ 部分成功 / ❌ 失败）+ **关键结果**（1-2 行，如操作对象、产出位置、下一步）。无需强制套用大表格。
## 认证

`doctor` 不需要认证，其他命令需要 admin 权限。

## RBAC 角色门禁

- **RBAC 角色门禁（nexusctl ≥ 0.5.0）**：写操作受 `~/.harness-ai-kit/config.yaml` 的 `role` 字段约束
  - consumer：repo list/get、inventory、cleanup-policy、probe/doctor 等只读命令
  - contributor：repo create-*（扩容性新仓库登记，含 --dry-run）、user create-readonly（只读账号发放）
  - maintainer：repo update-*/delete、blobstore create/delete、user create/delete（影响所有消费方解析与 IAM）
  - 权限不足时 CLI 报 `requires role ...`，按提示引导用户升级 role，不得绕过

参考文档：
- references/REFERENCE-NEXUSCTL-CLI.md
- references/REFERENCE-README.md


## 用途

<!-- TODO: 描述本技能解决的重复性工作和触发场景 -->

## 工作流

<!-- TODO: 列出执行步骤 -->

1. ...
2. ...
3. ...

## 约束与边界

<!-- TODO: 说明前提假设和能力边界 -->

- ...
- **环境适配**：主机名 <host>/<host> 为逻辑名示例；IP/域名使用占位符（`{hs_host}`/`{base_domain}`/`{root_domain}` 等），解析自 `~/.harness-ai-kit/config.yaml` 顶层字段，规范见 docs/config-governance.md。


## 参考文档

- [REFERENCE-NAMING-CONVENTIONS.md](references/REFERENCE-NAMING-CONVENTIONS.md)
- [REFERENCE-NEXUSCTL-CLI.md](references/REFERENCE-NEXUSCTL-CLI.md)
- [REFERENCE-RAW-ASSET-RETIREMENT.md](references/REFERENCE-RAW-ASSET-RETIREMENT.md)
- [REFERENCE-README.md](references/REFERENCE-README.md)
