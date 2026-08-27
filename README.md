# harness-ai-kit

[![PyPI](https://img.shields.io/pypi/v/harness-ai-kit.svg?color=blue)](https://pypi.org/project/harness-ai-kit/)
[![Python](https://img.shields.io/pypi/pyversions/harness-ai-kit.svg)](https://pypi.org/project/harness-ai-kit/)
[![License](https://img.shields.io/badge/license-Apache--2.0-green.svg)](LICENSE)
[![CI](https://github.com/seed-forge/harness-ai-kit/actions/workflows/ci.yml/badge.svg)](https://github.com/seed-forge/harness-ai-kit/actions/workflows/ci.yml)

**A package manager and composition layer for AI agent assets.**

`harness-ai-kit` installs, resolves, locks, validates, and synchronizes Skills,
CLIs, MCPs, plugins, hooks, subagents, and loops across Codex, Claude Code,
Cursor, Kiro, and DeepSeek Harness (dsh).

[Quickstart](docs/quickstart.md) · [Asset Catalog](CATALOG.md) · [Usage Scenarios](docs/usage-scenarios.md) · [Concepts](docs/concepts.md) · [Roadmap](ROADMAP.md) · [Changelog](CHANGELOG.md) · [中文文档](README.zh-CN.md)

## Why

AI teams collect useful prompts, Skills, CLIs, and MCP servers quickly. The
hard part is making that collection reproducible: knowing what is installed,
which versions work together, where it is materialized, and how a teammate can
get the same working state without copying runtime directories.

`harness-ai-kit` makes the project manifest the source of truth:

```text
harness-ai-kit.yml  ->  resolve  ->  harness-ai-kit.lock  ->  runtime materialization
       intent             plan          integrity snapshot       Codex / Claude / Cursor / Kiro / dsh
```

The lock records resolved sources and checksums. Installation uses a staging
directory and only replaces the runtime target after the selected assets are
ready. The result is useful for one developer, and essential when a team needs
the same AI engineering environment across projects and runtimes.

## The REMIX Method

This project is a composition layer, not another vertical AI toolkit. When a
focused community Skill, CLI, or MCP already solves a problem, the preferred
path is to compose it, pin it, and make it reproducible instead of rebuilding
it.

- **R**euse proven assets from the community or your own repositories.
- **E**xtend an asset when a small, explicit adaptation is enough.
- **M**ix Skills, CLIs, MCPs, and runtime assets into one workflow.
- **I**ntegrate the selected assets through a typed manifest and lockfile.
- e**X**ecute the same declared environment across supported runtimes.

## No Lock-In

An installed Skill is still a normal directory of Markdown and metadata. You
can read it, copy it, or install it directly from its Git repository without
using this tool. `harness-ai-kit` is not a gatekeeper for content; it adds the
reproducible inventory, dependency resolution, checksums, and runtime sync
around that content.

## Quick Start

Requirements: Python 3.10+ and Git.

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

`init` creates or updates the shared configuration at
`~/.harness-ai-kit/config.yaml`. `init-project` creates the project manifest;
`sync` resolves it, writes the lockfile, and materializes the selected assets
for the configured runtime. See the [quickstart](docs/quickstart.md) for
runtime-specific installation details.

## Team Workflow

Commit the declaration and lockfile, not copied runtime directories:

```text
Maintainer                         Teammate
----------                         --------
add selected assets                clone or pull the project
review the lockfile                harness-ai-kit sync
commit manifest + lockfile         receive the same resolved asset set
```

This keeps local customizations out of version control while allowing a shared,
auditable AI asset baseline. `sync` reconciles managed assets; it is not a
blind wipe of unrelated local files.

## What It Provides

| Capability | Outcome |
|---|---|
| Typed asset model | One dependency contract for Skills, CLIs, MCPs, plugins, hooks, subagents, and loops |
| Resolution and lockfiles | A reproducible selection of versions, sources, features, and SHA-256 checksums |
| Multiple runtime adapters | Project or global installation for supported AI coding runtimes |
| Git-based sources | Install a reviewed Skill directly from a public Git repository |
| Safe materialization | Staging, verification, replacement, and rollback-aware installation flow |
| Configuration boundary | User-specific endpoints and credentials live in `~/.harness-ai-kit/config.yaml`, not in assets |
| Curated public assets | Reusable engineering, diagnostic, and AI-development assets listed in the [catalog](CATALOG.md) |

## Architecture

```text
                     harness-ai-kit CLI
 init | add | install | sync | lock | doctor | validate | upgrade
                              |
                 manifest + dependency resolver
                              |
                     harness-ai-kit.lock
                              |
         source adapters + cache + checksum verification
                              |
      runtime adapters and asset bundles for AI coding environments
```

The public project deliberately separates portable product behavior from
private operating context. Public packages must work with a user's own
configuration and public dependencies; private endpoints, credentials, and
deployment topology do not belong in the published tree.

## Usage Paths

- **Adopt a public Skill:** install from a Git repository, then sync it into a
  project runtime.
- **Share an engineering baseline:** commit the manifest and lockfile so the
  team resolves the same assets.
- **Author an internal or public asset:** use the metadata contract, validate
  it locally, and publish only through an explicit reviewed release path.
- **Run dsh:** install Skills or the bundled plugin through the dsh runtime
  adapter. See [dsh integration](docs/dsh-integration.md).

The [usage scenarios](docs/usage-scenarios.md) explain when to use a Skill,
when a loop is appropriate, and how a spec-driven workflow can route both.

## Roadmap

The current public product focuses on portable asset management, reproducible
installation, and a reviewed public catalog. Future work expands authoring and
automation first; registry, browser, and organization administration remain
separate platform milestones rather than hidden dependencies of the core CLI.

See [ROADMAP.md](ROADMAP.md) for scope, milestones, and non-goals.

## Documentation

- [Quickstart](docs/quickstart.md)
- [Core concepts](docs/concepts.md)
- [CLI reference](docs/cli-reference.md)
- [Asset catalog](CATALOG.md)
- [Asset authoring contract](docs/asset-authoring-contract.md)
- [Troubleshooting](docs/troubleshooting.md)
- [OSS release process](docs/oss-release.md)

## Contributing And Security

Use [CONTRIBUTING.md](CONTRIBUTING.md) for contribution expectations and
[SECURITY.md](SECURITY.md) for responsible disclosure. Issues and feature
requests belong in the GitHub issue tracker; open-ended design discussion can
use GitHub Discussions.

## License

[Apache-2.0](LICENSE) © 2026 SeedForge.
