# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.18.17] - 2026-08-27

### Fixed

- Make public source resolution prefer the public registry, falling back only
  to a user-configured registry. The OSS build no longer accepts private
  `internal-registry` or `workspace-repo` source selectors.
- Add a post-projection source-policy regression so future private defaults
  cannot silently change the public package contract.
- Ignore local staging `.tmp` state in the public release scan so prior test
  environments cannot create false-positive secret or network findings.

## [0.18.16] - 2026-08-27

### Fixed

- Make the OSS command surface self-contained after maintainer-only commands
  are removed from the public build. Public CLI startup no longer imports
  private authoring, publishing, governance, release, or loop-run modules.
- Add a build-projection startup regression so every public core candidate can
  import and execute `harness-ai-kit --version` before publication.

## [0.18.15] - 2026-08-27

### Fixed

- Resolve project-manifest runtime targets from the declared project directory,
  preventing nested projects from installing into a user-level `.agents/skills`
  directory.
- Restore the full product documentation front door and add a quickstart that
  uses the current `~/.harness-ai-kit/config.yaml` configuration location.
- Treat the public changelog, roadmap, README files, and quickstart as
  reviewed build inputs so a public release cannot silently replace them with
  generated placeholder text or a stale version record.

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

Naming unification release: the project is now consistently **`harness-ai-kit`**,
plus 11 additional curated skills.

### Changed

- **BREAKING: the canonical name is now `harness-ai-kit` throughout.** The
  Python package (`harness_ai_kit`), primary command (`harness-ai-kit`),
  project manifest (`harness-ai-kit.yml`), lockfile (`harness-ai-kit.lock`),
  config directory (`~/.harness-ai-kit/`), runtime skill bundle root
  (`harness-ai-kit-skills`), and product environment variable
  (`HARNESS_AI_KIT_PRODUCT`) were unified from the earlier `ai-kit` naming.
  - The short command `ai-kit` remains an alias.
  - Early adopters can rename `ai-kit.yml` to `harness-ai-kit.yml` and
    `ai-kit.lock` to `harness-ai-kit.lock`, move `~/.ai-kit/` to
    `~/.harness-ai-kit/`, then run `harness-ai-kit sync`.

### Added

- 11 additional curated skills and a public asset catalog.

## [0.1.0] - 2026-08-10

Initial public release of harness-ai-kit, the package manager for AI agent
assets.

### Added

- CLI core for initialization, installation, synchronization, locking,
  resolution, inspection, and validation.
- A typed asset model with reproducible lockfiles and staged installation.
- Multi-runtime support for Codex, Claude Code, Cursor, and Kiro.
- GitHub direct installation, offline cache support, and public CI checks.

### Security

- No internal network references, credentials, or proprietary endpoints in
  shipped code.
