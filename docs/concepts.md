# Core Concepts

## Asset Types

ai-kit manages six asset types, all sharing a unified dependency model:

| Type | Description | Install Target |
|------|-------------|----------------|
| `skill` | AI agent skill (SKILL.md + metadata) | `.agents/skills/` (codex) / `.claude/skills/` (claude-code) |
| `cli` | Python CLI package (pip-installable) | system or venv |
| `mcp` | MCP server/tool | `ai-kit-assets/mcps/` |
| `plugin` | Runtime plugin | `ai-kit-assets/plugins/` |
| `hook` | Git or runtime hook | `ai-kit-assets/hooks/` |
| `subagent` | Subagent definition | `ai-kit-assets/subagents/` |

## Dependency Model

- Each asset declares typed dependencies with pinned versions (`==x.y.z`)
- Optional dependencies must declare a `feature` name
- The resolver uses `resolvelib` for SAT-based dependency resolution
- Resolution result is captured in `ai-kit.lock` (the install contract)

## Lockfile

`ai-kit.lock` is a JSON snapshot containing:
- Root assets (what you asked to install)
- Resolved versions (exact, pinned)
- Source chosen for each node (GitHub repo, PyPI, registry)
- Checksums (SHA-256) for integrity verification
- Runtime target and selected features

## Runtime Adapters

| Runtime | Project Scope | Global Scope |
|---------|--------------|--------------|
| Codex | `.agents/skills/` | `~/.codex/skills/` |
| Claude Code | `.claude/skills/` | `~/.claude/skills/` |
| Kiro | `.kiro/steering/` + `ai-kit-skills/` | `~/.kiro/steering/` |
| Cursor | `.cursor/rules/` | (not supported) |

## Project Manifest

`ai-kit.yml` is the project intent file — it declares what assets your project wants:

```yaml
schema_version: "2"
runtime: codex
scope: project
assets:
  skills:
    - id: skill-creator
      sources: [git-repo]
      source_ref: https://github.com/anthropics/skills/tree/main/skills/skill-creator
      ref: main
      subpath: skills/skill-creator
```

## GitHub Direct Install

The primary v0.1 installation path — no private registry required:

```bash
ai-kit add skill https://github.com/OWNER/REPO/tree/main/path/to/skill
```

Supported source forms:
- `github.com/OWNER/REPO`
- `https://github.com/OWNER/REPO/tree/BRANCH/path`
- `OWNER/REPO` (with `--subpath`)
- `git@github.com:OWNER/REPO.git`
