# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-08-10

Initial public release of harness-ai-kit — the package manager for AI agent assets.

### Added

- **CLI core**: `harness-ai-kit` command with init, add, sync, lock, resolve, graph, list, doctor, verify, remove, search subcommands
- **Unified asset model**: six asset kinds (skill / cli / mcp / plugin / hook / subagent) sharing a single typed dependency graph
- **Dependency solver**: SAT-based resolution via resolvelib with feature flags and scope overrides
- **Lockfile**: `ai-kit.lock` with SHA-256 content integrity verification
- **Multi-runtime sync**: Codex, Claude Code, Cursor, Kiro — project-level or global install
- **GitHub direct install**: install skills from any GitHub repo without a private registry
- **Atomic install**: staging-based install with automatic rollback on failure
- **Offline mode**: cache-backed offline install for air-gapped environments
- **23 curated skills**:
  - 9 expert bases: MySQL, PostgreSQL, Redis, MongoDB, Kafka, RabbitMQ, Oracle, NL2SQL, Git workflow
  - 7 diagnostic playbooks: MySQL deadlock / slow query / replication, container OOM, K8s CrashLoop / node pressure, network port unreachability
  - 6 utilities: registry mirror strategy, goal execution, markitdown, work convert, work export, post-task skill miner
  - 1 flagship: infra system environment ops
- **CI pipeline**: lint, import check, CLI smoke test, skill validation, sensitive-scan, secret-scan (Python 3.10 / 3.11 / 3.12 matrix)
- **Community scaffolding**: CONTRIBUTING, CODE_OF_CONDUCT, issue templates, PR template
- **Bilingual docs**: English README + Chinese README, quickstart, concepts, skill authoring guide, asset map

### Security

- No internal network references, credentials, or proprietary endpoints in shipped code
- CI sensitive-scan blocks internal domain/IP patterns on every push
