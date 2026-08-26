# woodpeckerctl 用法

详见 SKILL.md。

## 可直接复制的中文 Prompt

```text
请使用 woodpeckerctl 技能，按照其 SKILL.md 描述的标准流程执行任务；
先做 dry-run/检查，向我展示结果与风险，经确认后再正式执行。
```

## 0.3.0 新增命令示例

### 仓库激活 / 停用 / 配置

```bash
# 激活（已知 gitea 仓库 id）
woodpeckerctl repo activate --gitea-id 42

# 激活（便捷版：给 owner/name，自动经 giteactl 配置解析 gitea id）
woodpeckerctl repo activate --repo deploy-apps/myapp

# 停用（wp_repo_id 可先通过 repo list --json 查询）
woodpeckerctl repo deactivate --id 7

# 修改仓库配置（可组合多个字段）
woodpeckerctl repo update --id 7 --enabled true --trusted true
woodpeckerctl repo update --id 7 --timeout 180 --branch main
```

### 仓库 secret 管理

```bash
# 列出 secrets（不显示值）
woodpeckerctl secret list --repo deploy-apps/myapp

# 添加 secret（默认 events=push,tag,manual）
woodpeckerctl secret add --repo deploy-apps/myapp --key REGISTRY_TOKEN --value 'xxx'

# 从文件读取值（推荐，避免 shell 历史泄露）
woodpeckerctl secret add --repo deploy-apps/myapp --key KUBECONFIG --value-file ./kubeconfig.yaml --events push,tag

# 删除 secret
woodpeckerctl secret remove --repo deploy-apps/myapp --key REGISTRY_TOKEN
```

### 队列与 Agent 状态

```bash
# 队列状态（pending / waiting_on_deps / running 计数与明细）
woodpeckerctl queue status
woodpeckerctl queue status --json

# Agent 列表（在线判定：last_contact 距今 < 5 分钟）
woodpeckerctl agent list
```
