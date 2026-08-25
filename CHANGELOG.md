# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.18.2] - 2026-08-25

### Fixed

- Map distribution names such as `PyYAML` to their import modules in
  environment diagnostics, so public Skill dependency checks report the real
  runtime state.

## [0.18.1] - 2026-08-25

### Changed

- Synced the reviewed public core from the private source line through the OSS
  build projection. The public package now carries the current portable
  configuration, registry, plugin, validation, and manifest behavior without
  private publish, role, governance, or loop-run commands.

### Added

- Added the provider-neutral `devlab-cicd-onboard` Skill to public staging.

## [0.2.2] - 2026-08-24

### Fixed

- Make `validate` use the public `CATALOG.md` contract in public checkouts,
  without requiring internal-only catalog metadata or unpublished governance
  assets.

## [0.2.1] - 2026-08-24

### Changed

- Added a matrix-gated TestPyPI/PyPI release path with package-specific builds,
  tests, immutable artifact verification, and post-publish hash readback.

## [0.2.0] - 2026-08-12

Naming unification release: the project is now consistently **`harness-ai-kit`**, plus 11 additional curated skills.

### Changed

- **BREAKING — the canonical name is now `harness-ai-kit` throughout.** The Python package (`harness_ai_kit`), primary command (`harness-ai-kit`), project manifest (`harness-ai-kit.yml`), lockfile (`harness-ai-kit.lock`), config directory (`~/.harness-ai-kit/`), runtime skill bundle root (`harness-ai-kit-skills`), and product env var (`HARNESS_AI_KIT_PRODUCT`) were all unified from the earlier `ai-kit` naming.
  - The short command **`ai-kit` is retained as an alias** and keeps working (`ai-kit sync` == `harness-ai-kit sync`).
  - **Migration for early adopters:** rename `ai-kit.yml` → `harness-ai-kit.yml` and `ai-kit.lock` → `harness-ai-kit.lock` in your project; move `~/.ai-kit/` → `~/.harness-ai-kit/`; then re-run `harness-ai-kit sync`. Skill inject markers (`<!-- ai-kit:inject ... -->`) become `<!-- harness-ai-kit:inject ... -->` and are refreshed automatically on the next sync.

### Added

- **11 additional curated skills** (34 total): AI engineering methodology (spec-driven dev, agent engineering, eval-driven agent, ai-kit miner, tech-debt ops), patent & document authoring (6), and testing/quality (web deep acceptance, web E2E, tech-fit eval)
- **Skill catalog** (`CATALOG.md`) and **usage scenarios** (`docs/usage-scenarios.md`) covering the skill+SDD and loop+runtime models

## [0.1.0] - 2026-08-10

Initial public release of harness-ai-kit — the package manager for AI agent assets.

### Added

- **CLI core**: `harness-ai-kit` command with init, add, sync, lock, resolve, graph, list, doctor, verify, remove, search subcommands
- **Unified asset model**: six asset kinds (skill / cli / mcp / plugin / hook / subagent) sharing a single typed dependency graph
- **Dependency solver**: SAT-based resolution via resolvelib with feature flags and scope overrides
- **Lockfile**: `harness-ai-kit.lock` with SHA-256 content integrity verification
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
