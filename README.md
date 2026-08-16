# harness-ai-kit

[![PyPI](https://img.shields.io/pypi/v/harness-ai-kit.svg?color=blue)](https://pypi.org/project/harness-ai-kit/)
[![Python](https://img.shields.io/pypi/pyversions/harness-ai-kit.svg)](https://pypi.org/project/harness-ai-kit/)
[![License](https://img.shields.io/badge/license-Apache--2.0-green.svg)](LICENSE)
[![CI](https://github.com/seed-forge/harness-ai-kit/actions/workflows/ci.yml/badge.svg)](https://github.com/seed-forge/harness-ai-kit/actions/workflows/ci.yml)

**Package manager for AI agent assets** — install, lock and govern skills / CLIs / MCPs / loops across Codex, Claude Code, Cursor and Kiro. Includes an enterprise-grade AI-ops skill library.

[Quickstart](docs/quickstart.md) · [Skill Catalog](CATALOG.md) · [Usage Scenarios](docs/usage-scenarios.md) · [Docs](docs/) · [Roadmap](ROADMAP.md) · [Changelog](CHANGELOG.md) · [中文文档](README.zh-CN.md)

## Why

As AI agents proliferate, teams accumulate reusable prompts, skills, CLIs and MCP servers — but there's no `npm` for these assets. `harness-ai-kit` fills that gap: one CLI to install, resolve, lock, validate and govern AI agent assets across multiple runtimes.

### Build Less, Compose More

harness-ai-kit is a **composition layer, not another vertical toolkit**. It does **not** compete with well-known single-purpose community AI kits — it *composes* them. Where a focused community skill, CLI, or MCP server already does a job well, harness-ai-kit's role is to install, pin, and orchestrate it alongside everything else, never to reinvent it. Build less; reuse and compose more.

### Why not just copy SKILL.md files?

| | Copy-paste | harness-ai-kit |
|---|-----------|--------|
| Install a skill | `git clone` → find the right dir → copy files | `harness-ai-kit add skill <url>` |
| Pin versions | Manual tracking | `harness-ai-kit.lock` with SHA-256 |
| Team consistency | "Works on my machine" | `harness-ai-kit.yml` + `harness-ai-kit sync` = identical state |
| Multiple AI runtimes | Repeat for each tool | `--runtime codex/claude-code/cursor/kiro` |
| Dependency conflicts | Silent breakage | SAT solver detects conflicts upfront |
| Offline / air-gapped | Re-download everything | `harness-ai-kit sync --offline` from cache |

### No lock-in — you don't have to use harness-ai-kit

Every skill in the [catalog](CATALOG.md) is a plain folder of Markdown + JSON. If you don't want another CLI, you don't need one:

- **Let your agent fetch it** — paste the skill's GitHub URL to Codex / Claude Code / Cursor and ask it to install the skill into your runtime's skills directory.
- **`npx` / one-off scripts** — pull a single `SKILL.md` straight from the repo, no install step.
- **Copy the folder yourself** — drop it into `.agents/skills/` (Codex) or `.claude/skills/` (Claude Code) by hand.

harness-ai-kit is **not** a gatekeeper for the content. What it adds on top is the **asset manifest**: a curated, versioned, checksummed inventory (`harness-ai-kit.yml` + `harness-ai-kit.lock`) of *what* your project uses. If that inventory is useful to you, the CLI is the fastest way to manage it. If not, the skills work fine without it.

### Team collaboration — commit the manifest, not the assets

The manifest is where harness-ai-kit pays off most. The intended team flow:

```
Member A (sets up)
  harness-ai-kit add skill devlab-spec-driven-dev
  harness-ai-kit add skill diag-mysql-deadlock
  git add harness-ai-kit.yml harness-ai-kit.lock        # commit ONLY the manifest
  git commit -m "chore: pin team AI skills"

Member B (joins / updates)
  harness-ai-kit sync                            # done — exact same assets, SHA-256 verified
```

Two concrete benefits:

1. **Nothing sensitive leaves the repo.** Member A commits only two small YAML/JSON files. The raw skill folders — which may carry local paths, personal runtime config, or credentials from a member's own machine — are never committed. Member B re-materializes them locally from the manifest.
2. **Updates are cheap and non-destructive.** When the team bumps a skill version, members just `harness-ai-kit sync` (or `harness-ai-kit update`) to pull the latest. Because the lockfile records exactly what's managed by harness-ai-kit, a member's own hand-added / custom skills are left untouched — sync reconciles the manifest, it doesn't wipe your local additions.

In short: the manifest is the team's shared source of truth for "which AI assets we run", and `sync` is how everyone stays identical without sharing anything sensitive.

## Quick Start

```bash
pip install harness-ai-kit
harness-ai-kit init
cd your-project
harness-ai-kit add skill https://github.com/anthropics/skills/tree/main/skills/skill-creator
harness-ai-kit sync
```

> **Short alias:** every command is also available as `ai-kit` (e.g. `ai-kit sync`). Use whichever you prefer — both invoke the same CLI.

Verify it worked:

```bash
harness-ai-kit doctor              # health check — should be all green
ls .agents/skills/          # skill-creator should be here
```

The skill is now available to your AI agent. See [examples/](examples/README.md) for real-world usage patterns (team sync, multi-runtime, offline mode).

## Command Cheatsheet

| Command | What it does |
|---------|-------------|
| `harness-ai-kit init` | First-time machine setup |
| `harness-ai-kit add skill <id-or-url>` | Add a skill to your project |
| `harness-ai-kit sync` | Install declared assets to runtime |
| `harness-ai-kit list` | Browse available skills |
| `harness-ai-kit show <id>` | Show skill metadata |
| `harness-ai-kit lock` | Pin exact versions to harness-ai-kit.lock |
| `harness-ai-kit doctor` | Health check your environment |
| `harness-ai-kit remove skill <id>` | Remove a skill |
| `harness-ai-kit outdated` | Check for updates |
| `harness-ai-kit cache clean` | Clear local cache |

Full reference: [docs/cli-reference.md](docs/cli-reference.md)

## Features

- **Unified asset schema** — skills, CLIs, MCPs, plugins, hooks, subagents and loops share one typed dependency model with pinned versions
- **Dependency resolution** — `resolvelib`-based solver with lockfile (`harness-ai-kit.lock`) and checksum verification
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

## Built-in Skill Library

47 production-tested skills + 5 companion CLIs included. Install any with `harness-ai-kit add skill <id>` (or `pip install sf-<cli>`). Full categorized index: **[CATALOG.md](CATALOG.md)**.

> New here? Read [Usage Scenarios](docs/usage-scenarios.md) first — it explains how skills get pulled into real work via an SDD framework (e.g. Trellis), and how loops bind to a runtime.

<details>
<summary><strong>Database Expert Bases</strong> (9 skills — schema design, indexing, query tuning, replication)</summary>

| Skill | Domain |
|-------|--------|
| `public-mysql-expert-base` | MySQL/InnoDB — schema, indexes, locks, tuning |
| `public-postgres-expert-base` | PostgreSQL — B-Tree/GIN/GiST, JSONB, partitioning |
| `public-redis-expert-base` | Redis — data structures, connection pool, TTL |
| `public-mongodb-expert-base` | MongoDB — aggregation, indexes, replica sets |
| `public-kafka-expert-base` | Kafka — topics, consumer groups, exactly-once |
| `public-rabbitmq-expert-base` | RabbitMQ — exchanges, durability, dead letter |
| `public-oracle-expert-base` | Oracle — JDBC, LOB, character set |
| `public-nl2sql-expert-base` | NL2SQL — natural language to SQL |
| `public-git-workflow-expert-base` | Git — commit, branch, PR conventions |

</details>

<details>
<summary><strong>Diagnostic Playbooks</strong> (7 skills — enterprise troubleshooting chains)</summary>

| Skill | Scenario |
|-------|----------|
| `diag-mysql-deadlock` | InnoDB deadlock capture + lock chain analysis |
| `diag-mysql-slow-query` | Slow query log + EXPLAIN + index analysis |
| `diag-mysql-replication` | Master-slave delay root cause |
| `diag-container-oom` | dmesg OOM killer → cgroup → Docker memory |
| `diag-k8s-pod-crashloop` | CrashLoopBackOff full-chain diagnosis |
| `diag-k8s-node-pressure` | CPU/Memory/Disk/PID pressure |
| `diag-network-port-unreach` | DNS → TCP → iptables → service → route |

</details>

<details>
<summary><strong>AI Engineering Methodology</strong> (5 skills — spec-driven dev, agent architecture, eval, tech debt)</summary>

| Skill | Purpose |
|-------|---------|
| `devlab-spec-driven-dev` | Spec-driven AI collaboration (requirements → design → tasks) |
| `devlab-ai-agent-engineering` | AI agent app architecture methodology |
| `devlab-eval-driven-agent` | Eval-driven agent quality system |
| `devlab-ai-kit-miner` | Post-session retrospective → asset extraction |
| `devlab-tech-debt-ops` | Tech debt lifecycle (audit → refactor → verify) |

</details>

<details>
<summary><strong>Patent & Document Authoring</strong> (6 skills)</summary>

| Skill | Purpose |
|-------|---------|
| `patent-specification-writer` | Patent specification drafting |
| `patent-review` | Patent quality review with dimensions checklist |
| `patent-disclosure-workflow` | Patent disclosure end-to-end workflow |
| `work-sc-patent-specification-writer` | Patent spec (work-sc namespace) |
| `work-sc-software-copyright-writer` | Software copyright application materials |
| `document-reference-sop-builder` | Turn an exemplar document into a reusable SOP |

</details>

<details>
<summary><strong>General & Infra</strong> (7 skills)</summary>

| Skill | Purpose |
|-------|---------|
| `base-cn-registry-mirror-strategy` | China mirror acceleration (Docker/Debian/Python/Maven) |
| `base-goal-execution` | Goal-driven execution with checkpoints |
| `markitdown` | Document-to-Markdown conversion |
| `work-convert` / `work-export` | Document conversion/export |
| `post-task-skill-miner` | Post-task retrospective → skill extraction |
| `infra-system-env-ops` | Monit watchdog / service self-healing |

</details>

Full catalog with install commands: **[CATALOG.md](CATALOG.md)** · usage patterns: [docs/usage-scenarios.md](docs/usage-scenarios.md)

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    harness-ai-kit CLI                        │
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

See [ROADMAP.md](ROADMAP.md) for the full plan with milestone criteria.

| Phase | Content | Status |
|-------|---------|--------|
| **v0.1** (current) | CLI + schema + validate + GitHub direct install + curated skill library | ✅ Released |
| **v0.2** (planned) | Loop automation framework + hooks mechanism + skill authoring toolkit | 🔜 Planned |
| **v0.3** (future) | Expanded infra/devlab skill library + MCP assets + RBAC governance | 📋 Backlog |
| **Phase B** (long-term) | Public registry backend + browser UI + admin/publisher system | 🔬 Research |

## Project Layout

```
harness-ai-kit/
├── harness_ai_kit/      # CLI source code
│   ├── commands/        # Command handlers (install, resolve, lock, ...)
│   ├── domain/          # Domain models (manifest, lockfile, resolver, ...)
│   ├── infrastructure/   # Infrastructure (git ops, registry client, ...)
│   └── data/             # Default config seed
├── skills/              # Curated enterprise skill library
├── examples/            # Real-world usage examples
├── docs/                # Documentation
│   ├── quickstart.md    # Step-by-step getting started
│   ├── cli-reference.md # Complete CLI command reference
│   ├── concepts.md      # Core concepts explained
│   ├── skill-authoring.md # Write your own skills
│   ├── asset-map.md     # Skill library catalog
│   └── troubleshooting.md # Common issues and fixes
├── .github/             # CI, issue templates, community files
├── pyproject.toml       # Package metadata
└── LICENSE              # Apache-2.0
```

## Community & Support

- **Questions**: [GitHub Discussions](https://github.com/seed-forge/harness-ai-kit/discussions) or [SUPPORT.md](SUPPORT.md)
- **Bugs & features**: [Issue tracker](https://github.com/seed-forge/harness-ai-kit/issues)
- **Security**: See [SECURITY.md](SECURITY.md)
- **Changes**: See [CHANGELOG.md](CHANGELOG.md)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). We use the Developer Certificate of Origin (DCO) — all commits must be signed off.

## License

[Apache-2.0](LICENSE) © 2026 SeedForge
