# Jenkins Pipeline Operations Usage

Install the companion CLI and verify configuration before attempting an action:

```bash
python -m pip install sf-jenkinsctl
jenkinsctl doctor
jenkinsctl job list
```

For a Pipeline change, read the current job configuration, review the
Jenkinsfile, apply the smallest intended update, and read back the job and the
latest build result. Use project scope when installing this Skill.

## 可直接复制的中文 Prompt

```text
请使用 infra-jenkins-pipeline-ops 审查或操作 Jenkins。
目标：<填入只读检查、构建触发或配置变更>。
Jenkins 地址和认证信息只从 ~/.harness-ai-kit/config.yaml 读取；先执行只读检查，
涉及 Job、凭据、插件或全局配置变更时先说明影响、备份和所需角色。
输出：执行结果、回读验证和未完成风险。
```
