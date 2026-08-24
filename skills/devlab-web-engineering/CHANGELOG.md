# Changelog

## 0.2.0 - 2026-08-22
- 增加 Web Vitals、前端错误、日志、告警、RUM/Trace 的接入基线和安全边界。

## 0.1.3 - 2026-08-21

- 增加 `base-diagram-ops` 可选消费触点，提供 Web、集成和安全架构视图的工程事实。

## [0.1.2] - 2026-08-21

### Added
- `profiles/vue/scripts/run-acceptance.sh.template`：可复用的外部人工验收启动器，统一处理
  前后端进程生命周期、IPv4/IPv6 端口检查、HTTP 就绪探测和 FQDN/overlay/回环地址输出。
- 明确项目必须在后端命令中显式加载 `.env`，例如 `uv run --env-file`；共享模板不绑定具体
  应用、端口、代理、域名或凭据。

### Fixed
- 修正 QA 集成目标为已横向化的 `devlab-qa-ops`。
- 增加运行时配置声明，生成的 Vue 开发脚本默认回环监听、启用严格端口，并支持显式配置 host/port。
- 移除 registry reference 中的内部域名，改由 `devlab-infra-usage` 或运行时配置注入。

## [0.1.1] - 2026-08-21

### Added
- 外部人工验收运行约束：仅在明确需要时绑定 `0.0.0.0`；前端端口与 API proxy target
  必须可配置，Vite 使用严格端口模式，分别验证回环与目标网络入口。
- 明确将具体端口分配、FQDN 和防火墙规则委派给目标部署环境的运维规范，避免在工程技能中硬编码。

## [0.1.0] - 2026-08-14

### Added
- Web / 前端工程化能力层（Capability Layer），与 `devlab-srv-engineering` 同构：
  六域 + Phase 0-3 工作流 + profiles 路由 + Out of Scope 路由表
- 路由键 = 语言 × 框架 双维（TS 主线 / JS 兼容 / 语言维度扩展位）
- profiles/vue.md（实战级：六域完整工作流 + Vite 主线/Webpack 兼容 + 微前端场景层）
- profiles/react.md（模板级）+ angular/next/nuxt 走 references 引用层
- workflows/×3（bootstrap 吸收 5 阶段 / build / packaging）
- principles/×4（构建可复现性 / 依赖治理 / 项目结构 / 环境一致性）
- references/（跨框架 4 份迁移 + 索引 + 社区引用清单）
- profiles/vue/scripts/*.template（common/dev/build/test/lint/doctor/orchestrator/.env）

### Changed
- 吸收 `devlab-web-bootstrap`（v1.0.1）：5 阶段工作流 / 8 决策点 D0-D7 / 5 踩坑案例 /
  6 份 references / 5 内置代码片段全量迁入，原资产 retire
