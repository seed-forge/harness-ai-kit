# ai-kit

[![PyPI](https://img.shields.io/pypi/v/harness-ai-kit.svg?color=blue)](https://pypi.org/project/harness-ai-kit/)
[![Python](https://img.shields.io/pypi/pyversions/harness-ai-kit.svg)](https://pypi.org/project/harness-ai-kit/)
[![License](https://img.shields.io/badge/license-Apache--2.0-green.svg)](LICENSE)
[![CI](https://github.com/seed-forge/harness-ai-kit/actions/workflows/ci.yml/badge.svg)](https://github.com/seed-forge/harness-ai-kit/actions/workflows/ci.yml)

**Package manager for AI agent assets** — install, lock and govern skills / CLIs / MCPs / loops across Codex, Claude Code, Cursor and Kiro. Includes an enterprise-grade AI-ops skill library.

## Why

As AI agents proliferate, teams accumulate reusable prompts, skills, CLIs and MCP servers — but there's no `npm` for these assets. `ai-kit` fills that gap: one CLI to install, resolve, lock, validate and govern AI agent assets across multiple runtimes.

## Quick Start

```bash
pip install harness-ai-kit
ai-kit init
ai-kit add skill https://github.com/anthropics/skills/tree/main/skills/skill-creator
ai-kit sync
```

That's it — the skill is now installed into your project's `.agents/skills/` directory, ready for your AI agent to use.

## Features

- **Unified asset schema** — skills, CLIs, MCPs, plugins, hooks, subagents and loops share one typed dependency model with pinned versions
- **Dependency resolution** — `resolvelib`-based solver with lockfile (`ai-kit.lock`) and checksum verification
- **Multi-runtime support** — install to Codex, Claude Code, Cursor, Kiro (project or global scope)
- **GitHub direct install** — install skills from any GitHub repo, no private registry required
- **Staging + rollback** — atomic installs with automatic rollback on failure
- **Offline mode** — cache-driven install without network access
- **Enterprise skill library** — curated ops skills (MySQL deadlock diagnosis, K8s CrashLoopBackOff, container OOM, etc.) included

## Installation

```bash
pip install harness-ai-kit
```

Requires Python >= 3.10 and `git`.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    ai-kit CLI                        │
│  init · add · install · sync · lock · resolve ·     │
│  graph · why · validate · doctor · upgrade · cache  │
├─────────────────────────────────────────────────────┤
│              Package Manager Core                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │ Resolver │  │ Lockfile │  │ Runtime Adapters  │   │
│  │ (resolve)│  │ (lock)   │  │ codex·claude·kiro│   │
│  └────┬─────┘  └────┬─────┘  └────────┬─────────┘   │
│       │              │                  │             │
│  ┌────▼──────────────▼──────────────────▼─────────┐  │
│  │          Source Abstraction Layer               │  │
│  │  GitHub repos · PyPI · raw registries · cache   │  │
│  └─────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────┤
│              Enterprise Skill Library                │
│  public-*-expert-base · diag-* · infra-* · loops     │
└─────────────────────────────────────────────────────┘
```

## Roadmap

| Phase | Content | Status |
|-------|---------|--------|
| **v0.1** (current) | CLI + schema + validate + GitHub direct install + curated skill library | ✅ Released |
| **v0.2** (planned) | Loop automation framework + hooks mechanism + skill authoring toolkit | 🔜 Planned |
| **v0.3** (future) | Expanded infra/devlab skill library + MCP assets + RBAC governance | 📋 Backlog |
| **Phase B** (long-term) | Public registry backend + browser UI + admin/publisher system | 🔬 Research |

## Project Layout

```
harness-ai-kit/
├── ai_kit/              # CLI source code
│   ├── commands/        # Command handlers (install, resolve, lock, ...)
│   ├── domain/          # Domain models (manifest, lockfile, resolver, ...)
│   ├── infrastructure/   # Infrastructure (git ops, registry client, ...)
│   └── data/             # Default config seed
├── skills/              # Curated enterprise skill library
├── docs/                # Documentation
├── .github/             # CI, issue templates, community files
├── pyproject.toml       # Package metadata
└── LICENSE              # Apache-2.0
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). We use the Developer Certificate of Origin (DCO) — all commits must be signed off.

## License

[Apache-2.0](LICENSE) © 2026 SeedForge
