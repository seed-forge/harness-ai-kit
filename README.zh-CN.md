# harness-ai-kit

[![PyPI](https://img.shields.io/pypi/v/harness-ai-kit.svg?color=blue)](https://pypi.org/project/harness-ai-kit/)
[![Python](https://img.shields.io/pypi/pyversions/harness-ai-kit.svg)](https://pypi.org/project/harness-ai-kit/)
[![License](https://img.shields.io/badge/license-Apache--2.0-green.svg)](LICENSE)
[![CI](https://github.com/seed-forge/harness-ai-kit/actions/workflows/ci.yml/badge.svg)](https://github.com/seed-forge/harness-ai-kit/actions/workflows/ci.yml)

**面向 AI Agent 资产的包管理器与组合层。**

`harness-ai-kit` 用于安装、解析、锁定、校验和同步 Skill、CLI、MCP、插件、Hook、Subagent 与 Loop，覆盖 Codex、Claude Code、Cursor、Kiro 和 DeepSeek Harness（dsh）等运行时。

[快速开始](docs/quickstart.md) · [资产目录](CATALOG.md) · [使用场景](docs/usage-scenarios.md) · [核心概念](docs/concepts.md) · [路线图](ROADMAP.md) · [变更记录](CHANGELOG.md) · [English](README.md)

## 为什么需要它

团队很容易积累大量提示词、Skill、CLI 和 MCP，但真正困难的是让它们可复现：项目装了什么、版本是否兼容、资产落在哪个运行时、队友如何得到同一套可工作的环境。

`harness-ai-kit` 将项目声明作为事实源：

```text
harness-ai-kit.yml  ->  解析依赖  ->  harness-ai-kit.lock  ->  安装到运行时
       项目意图           执行计划          完整性快照             Codex / Claude / Cursor / Kiro / dsh
```

锁文件保存解析后的来源和校验和；安装先在 staging 目录完成，再替换目标运行时目录。它既适合个人，也让团队可以在多个项目和运行时中维护同一套 AI 工程环境。

## REMIX 方法论

本项目是组合层，不是另一个垂直 AI 工具集。社区或团队已有的 Skill、CLI、MCP 能解决问题时，应优先组合、锁定和复用，而不是从头重写。

- **R**euse：复用社区或团队已验证的资产。
- **E**xtend：以明确的小范围扩展适配相近资产。
- **M**ix：把 Skill、CLI、MCP 与运行时资产组合成工作流。
- **I**ntegrate：通过类型化 manifest 与 lockfile 统一管理。
- e**X**ecute：在受支持的 AI 编程运行时中执行同一份声明。

## 不锁定内容

安装后的 Skill 仍是普通 Markdown 和元数据目录。你可以阅读、复制，或直接从 Git 仓库安装，并不必须使用本工具。`harness-ai-kit` 增加的是可复现资产清单、依赖求解、校验和与运行时同步，不是内容门槛。

## 快速开始

前置条件：Python 3.10+ 与 Git。

```bash
python -m pip install --upgrade harness-ai-kit
harness-ai-kit init

mkdir my-agent-project
cd my-agent-project
harness-ai-kit init-project
harness-ai-kit add skill https://github.com/OWNER/REPO/tree/main/path/to/skill
harness-ai-kit sync
harness-ai-kit doctor
```

`init` 会创建或更新 `~/.harness-ai-kit/config.yaml`；`init-project` 创建项目 manifest；`sync` 解析依赖、写入 lockfile，并将资产安装到所选运行时。具体运行时的安装说明见[快速开始](docs/quickstart.md)。

## 团队协作

提交项目声明和 lockfile，而不是提交复制出来的运行时目录：

```text
维护者                             团队成员
------                             --------
添加并审查资产                     拉取项目
确认 lockfile                      harness-ai-kit sync
提交 manifest + lockfile           得到同一套解析后的资产
```

这样可以避免把本机运行时和个性化内容带入版本库，同时保留可审计的团队基线。`sync` 只协调受管理资产，不会盲目清空无关的本地文件。

## 核心能力

| 能力 | 结果 |
|---|---|
| 统一资产模型 | Skill、CLI、MCP、插件、Hook、Subagent、Loop 使用同一套依赖契约 |
| 依赖解析与锁定 | 固化版本、来源、特性开关与 SHA-256 校验和 |
| 多运行时适配 | 在受支持的 AI 编程运行时中按项目或全局范围安装 |
| Git 源安装 | 直接从公开 Git 仓库安装经过审查的 Skill |
| 安全落盘 | staging、校验、替换与可回滚的安装流程 |
| 配置边界 | 用户的端点与凭据保存在 `~/.harness-ai-kit/config.yaml`，不写入资产 |
| 公共资产目录 | 可复用工程、诊断和 AI 开发资产见[目录](CATALOG.md) |

## 架构

```text
                     harness-ai-kit CLI
 init | add | install | sync | lock | doctor | validate | upgrade
                              |
                   manifest 与依赖解析器
                              |
                     harness-ai-kit.lock
                              |
                 来源适配器、缓存与校验和验证
                              |
              AI 编程运行时适配器与资产 bundle
```

公开产品行为与私有运行上下文严格分离。公开包必须在用户自己的配置和公开依赖下工作；私有端点、凭据与部署拓扑不进入公开仓。

## 使用路径

- **采用公共 Skill**：从 Git 仓库安装并同步到项目运行时。
- **共享工程基线**：提交 manifest 与 lockfile，让团队解析到相同资产。
- **编写资产**：遵循元数据契约，本地验证，通过明确审核发布。
- **使用 dsh**：通过 dsh runtime adapter 安装 Skill 或 bundled plugin，详见 [dsh 集成](docs/dsh-integration.md)。

[使用场景](docs/usage-scenarios.md) 说明 Skill、Loop 与 spec-driven 工作流各自适用的边界。

## 路线图

当前公开产品专注于可携带的资产管理、可复现安装和经过审查的公共目录。后续优先扩展资产编写与自动化；registry、浏览器和组织管理属于独立的平台里程碑，不是核心 CLI 的隐式依赖。

完整范围、里程碑与非目标见 [ROADMAP.md](ROADMAP.md)。

## 文档入口

- [快速开始](docs/quickstart.md)
- [核心概念](docs/concepts.md)
- [CLI 参考](docs/cli-reference.md)
- [资产目录](CATALOG.md)
- [资产编写契约](docs/asset-authoring-contract.md)
- [常见问题](docs/troubleshooting.md)
- [OSS 发布流程](docs/oss-release.md)

## 贡献与安全

贡献约定见 [CONTRIBUTING.md](CONTRIBUTING.md)，安全披露见 [SECURITY.md](SECURITY.md)。问题和功能建议请使用 GitHub Issues；开放设计讨论可使用 GitHub Discussions。

## 许可证

[Apache-2.0](LICENSE) © 2026 SeedForge。
