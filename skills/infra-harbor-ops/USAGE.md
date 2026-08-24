# infra-harbor-ops Usage

Use this skill for Harbor platform operations.

## 常用入口

```powershell
.\组织内部集群\run-ansible-action.ps1 -Action inspect_registry_auth -Target <host>
.\组织内部集群\run-ansible-action.ps1 -Action inspect_registry_token_runtime -Target <host>
```

## 可直接复制的中文 Prompt

```text
请使用 infra-harbor-ops 排查 <host> Harbor：先区分平台故障还是 CI/部署消费故障，再检查 project、robot、proxy cache、registry token runtime 和反代配置。OCI 预热交给 infra-artifact-readiness-ops。
```
