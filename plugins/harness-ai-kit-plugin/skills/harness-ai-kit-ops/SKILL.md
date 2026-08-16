---
name: harness-ai-kit-ops
description: 'harness-ai-kit 资产操作手册（dsh 随包精简版）：list/search/info/install/doctor 团队 Skill/CLI/Plugin/Loop 资产，及 doctor dsh 环境检查。当用户在 dsh 会话中询问团队资产、安装技能、检查 dsh 环境时使用。'
---

# harness-ai-kit 操作手册（dsh 随包版）

本技能随 `harness-ai-kit-plugin` bundle 注册。完整版见团队仓库
`skills/harness-ai-kit-ops/`（可 `install skill harness-ai-kit-ops --scope global` 获取）。

## 核心命令

- `harness-ai-kit list assets --json`：列全部资产（或 `list clis` / `list skills`）
- `harness-ai-kit show <kind> <id> --json`：看单个资产元数据
- `harness-ai-kit install skill <id> --runtime dsh --scope project`：装技能到 `.agents/skills`
  （dsh rank 200 原生扫描，无需额外配置）
- `harness-ai-kit install plugin <id> --profile <p>`：装 dsh 插件（委托 `dsh plugin add`）
- `harness-ai-kit doctor dsh`：dsh/pnpm 版本、DSH_HOME、profile 检查（基线 dsh 0.1.0-rc.6、pnpm >=10）

## dsh 会话内使用

直接调用 `harness-ai-kit` 工具：

- `harness-ai-kit(action: list, assetType: skill)`：列 registry 技能目录
- `harness-ai-kit(action: search, query: "kafka")`：关键词搜索
- `harness-ai-kit(action: info, assetType: cli, assetId: <id>)`：看 CLI 详情
- `harness-ai-kit(action: install, assetType: skill, assetId: <id>, runtime: dsh)`：安装技能

## 约束

- 安装类操作会落入 dsh 权限审批流（workspace-write），这是特性而非缺陷。
- CLI 不在 PATH 时工具自动回退直读 registry index（只读动作可用）。
- 技能正文按需加载：本手册只占一行元数据，调用时才读取。
