# DevLab Web Engineering — 使用说明

## Overview

Web / 前端工程化能力层（Capability Layer）。六域覆盖：Project Bootstrap / Build /
Dependency / Packaging / Runtime-Environment / Engineering Convention。
路由键 = 语言 × 框架 双维，按框架路由到 Profile 执行工程化落地。

吸收自 `devlab-web-bootstrap`（v1.0.1，已 retire）：5 阶段工作流 / 8 决策点 /
5 踩坑案例 / references 全量迁入。

## Prerequisites

- Node.js ≥ 18（项目版本由 .nvmrc / engines 决定）
- Bash 4.0+（生成脚本）；shellcheck 可选
- 可选：`devlab-infra-usage`（registry/API 地址查询）、`devlab-web-context`（画像输入）

## 触发场景

- 初始化前端项目工程（脚手架 + 生命周期脚本 + 工程规范）
- 构建/打包/容器化排障
- 微前端（qiankun/micro-app）工程配置
- CRA → Vite 迁移

## 快速使用

```text
用户: "帮我初始化这个 Vue3 + Vite 项目的工程化，生成 dev/build/test 脚本"
执行: Phase 0 扫描 + 决策卡片（D0-D7）→ 路由 profiles/vue.md → 生成 scripts/ → 验证
```

## 可直接复制的中文 Prompt

```
请使用 devlab-web-engineering 技能：
1. 扫描当前前端项目（识别语言×框架、构建工具、包管理器、已有脚本）
2. 展示 Phase 0 决策卡片（D0-D7），每项带推荐值，等我确认后再动手
3. 按对应 Profile 生成/补全工程化配置与 scripts/ 生命周期脚本
4. 执行验证（bash -n / shellcheck / dry-run）并输出验证报告
```

## Known Pitfalls

- 微前端子应用 `$route.params` 页面刷新即空，必须链式导航进入
- 子应用挂载期错误被吞：用例 reset 勿放在导航后
- 私有 registry 不可达时自动降级官方源（setup_registry）
- 端口冲突先确认进程归属再清理（自己的旧进程直接杀，他人进程需确认）
- 对外人工验收才绑定 `0.0.0.0`；端口与 API 代理地址必须可配置，Vite 必须启用严格端口模式

详细陷阱见 `profiles/vue/REFERENCE-PITFALLS.md`。

## External manual acceptance

Vue full-stack projects can copy `profiles/vue/scripts/run-acceptance.sh.template` into
their own `scripts/` directory. Configure the command arrays and project-specific health
URLs in the copy; keep the shared launcher responsible for process cleanup, IPv4/IPv6
port checks, readiness probes, and printing FQDN / overlay / loopback addresses.

For Python services, let the backend command load the project env file explicitly, for
example `uv run --env-file "$ENV_FILE" uvicorn my_app.main:app`. The template does not
hard-code an application name, port, FQDN, overlay IP, proxy target, or credential.
