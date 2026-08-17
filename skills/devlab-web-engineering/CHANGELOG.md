# Changelog

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
