# infra-nexus-ops Usage

Use this skill for Nexus platform operations (巡检 + CRUD + blobstore + inventory).

## 只读巡检

```powershell
nexusctl doctor
nexusctl repo list --json
nexusctl probe --repository pypi-group-repository-all
nexusctl inventory summary
nexusctl blobstore list
nexusctl cleanup-policy list
```

## 仓库 CRUD

```powershell
# 创建（预设）
nexusctl repo create-from-preset pypi-org-proxy --dry-run
nexusctl repo create-from-preset pypi-org-proxy

# 创建（手动）
nexusctl repo create-proxy --format pypi --name pypi-proxy-repository-custom --remote-url https://pypi.org/
nexusctl repo create-hosted --format npm --name npm-hosted-custom --write-policy allow
nexusctl repo create-group --format maven --name maven-group-custom --members "maven-central,maven-releases"
nexusctl repo create-proxy --format apt --name apt-ubuntu-jammy --remote-url http://mirrors.aliyun.com/ubuntu/ --distribution jammy

# 查看
nexusctl repo get --format pypi --type proxy --name pypi-proxy-repository-aliyun --json

# 更新
nexusctl repo update-group --format pypi --name pypi-group-repository-all --add-members new-repo
nexusctl repo update-proxy --format pypi --name pypi-proxy-repository-aliyun --remote-url https://new-url/
nexusctl repo update-hosted --format pypi --name pypi-hosted-repository --write-policy deny

# 删除
nexusctl repo delete --name old-repo --yes
```

## Blob Store 管理

```powershell
nexusctl blobstore list --json
nexusctl blobstore create-file --name pypi-new-store --dry-run
nexusctl blobstore delete --name old-store --yes
```

## Inventory 导出与漂移检测

```powershell
nexusctl inventory summary
nexusctl inventory export --output fleet-platform --output-path <fleet-platform>/infra/artifact-registry.yaml
nexusctl inventory export --output yaml --skip-detail
nexusctl inventory diff --against <fleet-platform>/infra/artifact-registry.yaml
```

## 调试模式

```powershell
nexusctl --verbose doctor
nexusctl repo list --verbose --json
```

## 可直接复制的中文 Prompt

```text
请使用 infra-nexus-ops 巡检 Nexus：先运行 nexusctl doctor，再导出 repo list，核对各 format group 入口，最后运行 inventory summary。构建预热交给 infra-artifact-readiness-ops。
```

```text
请使用 infra-nexus-ops 在 Nexus 上创建一个 PyPI proxy 仓库代理 pypi.org，先用 --dry-run 预览，确认后执行，最后导出 inventory 到 fleet-platform 并运行 diff 检测漂移。
```
