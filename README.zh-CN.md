# ai-kit

[![PyPI](https://img.shields.io/pypi/v/harness-ai-kit.svg?color=blue)](https://pypi.org/project/harness-ai-kit/)
[![Python](https://img.shields.io/pypi/pyversions/harness-ai-kit.svg)](https://pypi.org/project/harness-ai-kit/)
[![License](https://img.shields.io/badge/license-Apache--2.0-green.svg)](LICENSE)
[![CI](https://github.com/seed-forge/harness-ai-kit/actions/workflows/ci.yml/badge.svg)](https://github.com/seed-forge/harness-ai-kit/actions/workflows/ci.yml)

**AI 资产包管理器** — 像 npm 管理依赖一样管理 AI 时代的 Skill / CLI / MCP / Loop 资产，支持 Codex、Claude Code、Cursor、Kiro 多运行时。内置企业级 AI 运维技能库。

## 快速开始

```bash
pip install harness-ai-kit
ai-kit init
ai-kit add skill https://github.com/anthropics/skills/tree/main/skills/skill-creator
ai-kit sync
```

技能会安装到项目的 `.agents/skills/` 目录，AI 助手立即可用。

## 核心特性

- **统一资产模型**：六类资产（skill / cli / mcp / plugin / hook / subagent）共享一套类型化依赖模型
- **依赖求解**：基于 resolvelib 的 SAT 求解器，锁文件（ai-kit.lock）+ SHA-256 校验
- **多运行时适配**：Codex / Claude Code / Cursor / Kiro，项目级或全局级安装
- **GitHub 直装**：从任意 GitHub 仓库安装技能，无需私有 registry
- **原子安装回滚**：staging 安装 + 失败自动回滚
- **离线模式**：基于缓存的离线安装
- **企业级技能库**：MySQL 死锁诊断、K8s CrashLoop 排查、容器 OOM 分析等

## 安装

```bash
pip install harness-ai-kit
```

需要 Python >= 3.10 和 `git`。

## 路线图

| 阶段 | 内容 | 状态 |
|------|------|------|
| **v0.1**（当前） | CLI + schema + GitHub 直装 + 23 个精选技能 | ✅ 已发布 |
| **v0.2** | Loop 自动化框架 + hooks + 技能编写工具包 | 🔜 计划中 |
| **v0.3** | 扩展 infra/devlab 技能库 + MCP 资产 + RBAC 治理 | 📋 待办 |
| **Phase B** | 公共 registry + browser UI + admin 系统 | 🔬 研究 |

## 许可证

[Apache-2.0](LICENSE) © 2026 SeedForge
