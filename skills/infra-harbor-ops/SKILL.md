---
name: infra-harbor-ops
description: Harbor 平台运维技能。凡是用户提到 Harbor project、robot、proxy cache、registry token、OCI registry、Harbor 反代或 Harbor runtime health 时触发。
---

# infra-harbor-ops

用于 Harbor 平台级 day-2 运维。Harbor 负责 OCI 镜像、proxy cache、robot/project 权限和 registry token runtime。

## 边界

- 本 skill 负责：project/robot/proxy cache、Harbor 反代和 token runtime 排障、平台健康巡检。
- `infra-artifact-readiness-ops` 负责 CI/部署消费侧的 OCI 预热和 readiness gate。
- `infra-nexus-ops` 负责语言包仓库，不把 Docker 代理缓存放进 Nexus。

## 操作顺序

1. 先判断是平台问题还是消费链问题。
2. 平台问题查 Harbor config、proxy、token runtime、project/robot。
3. 消费链问题转 `infra-artifact-readiness-ops` 做 warm/readiness。
4. 涉及 Woodpecker/Kaniko 时联动 `infra-woodpecker-pipeline-ops`。


## 推荐输出格式

执行完毕后输出极简回执：**状态**（✅ 成功 / ⚠️ 部分成功 / ❌ 失败）+ **关键结果**（1-2 行，如操作对象、产出位置、下一步）。无需强制套用大表格。
## 配置上下文

本技能依赖以下配置，AI 在运行时按如下优先级解析：

1. 用户对话中明确提供的值（最高优先级）
2. `~/.harness-ai-kit/config.yaml` 中 `assets.infra-harbor-ops` 或 `global` 段
3. `config.defaults.yaml` 中的默认值

如用户未提供且无默认值的 required 字段，**必须主动询问用户**。
禁止从 AGENTS.md 或脚本中读取硬编码配置值。

参考文档：
- references/REFERENCE-HARBORCTL-CLI.md
