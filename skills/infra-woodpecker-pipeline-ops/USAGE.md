# Woodpecker Pipeline Operations Usage

Install the companion CLI and validate configuration before use:

```bash
python -m pip install sf-woodpeckerctl
woodpeckerctl doctor
woodpeckerctl repo info --repo <owner/repository>
woodpeckerctl build list --repo <owner/repository> --limit 5
```

Start from repository and build inspection. For a failing build, collect the
build number and log first; do not expose or rotate secrets as a diagnostic
shortcut.

## 可直接复制的中文 Prompt

```text
请使用 infra-woodpecker-pipeline-ops 审查或操作 Woodpecker CI。
目标：<填入仓库检查、构建诊断或流水线变更>。
配置只从 ~/.harness-ai-kit/config.yaml 的 assets.woodpeckerctl 读取；先读取仓库
和构建状态，涉及 secrets、激活或发布时说明影响和所需权限。
输出：检查结果、日志结论、回读验证和后续动作。
```
