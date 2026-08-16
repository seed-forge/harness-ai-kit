# infra-harbor-ops Usage

Use this skill for Harbor platform operations.

## 常用入口

平台地址与凭据通过配置注入（`~/.harness-ai-kit/config.yaml` 的 `assets.harborctl` 段），不在本技能硬编码。

```powershell
harborctl --help
# 平台健康巡检：先区分平台故障 vs CI/部署消费故障，
# 再逐项检查 project / robot / proxy cache / registry auth / registry token runtime / 反代配置。
```

## 可直接复制的中文 Prompt

```text
请使用 infra-harbor-ops 排查 Harbor：先区分平台故障还是 CI/部署消费故障，再检查 project、robot、proxy cache、registry token runtime 和反代配置。OCI 预热交给 infra-artifact-readiness-ops。
```
