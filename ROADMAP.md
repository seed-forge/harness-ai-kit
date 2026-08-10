# Roadmap

harness-ai-kit 的分阶段演进路线。每个阶段都有明确的交付物和验收标准。

> Star / Watch 本仓库以跟踪进展。有建议请开 [Discussion](https://github.com/seed-forge/harness-ai-kit/discussions)。

---

## v0.1 — Foundation (Current)

**Status**: Released

| Item | Detail |
|------|--------|
| CLI core | init / add / sync / lock / resolve / graph / list / doctor / verify / remove / search |
| Asset model | 6 kinds: skill, cli, mcp, plugin, hook, subagent |
| Dependency solver | SAT-based via resolvelib, feature flags, scope overrides |
| Lockfile | ai-kit.lock with SHA-256 integrity |
| Multi-runtime | Codex, Claude Code, Cursor, Kiro |
| Install | GitHub direct install, atomic staging + rollback, offline mode |
| Curated skills | 23 skills (expert bases, diagnostic playbooks, utilities) |
| CI | Python 3.10–3.12 matrix, sensitive-scan, secret-scan |

---

## v0.2 — Automation & Authoring

**Status**: Planned

| Item | Detail |
|------|--------|
| Loop framework | Declarative loop assets for recurring AI workflows |
| Hooks | Pre/post-install and pre/post-sync lifecycle hooks |
| Skill authoring toolkit | Scaffold, validate, and test new skills locally |
| ai-kit upgrade | Self-update with rollback |
| Rich search | Full-text search across skill name, description, tags |
| Config profiles | Named configuration profiles for multi-project workflows |

**Target**: Q4 2026

---

## v0.3 — Ecosystem Expansion

**Status**: Backlog

| Item | Detail |
|------|--------|
| Extended skill library | infra-* and devlab-* skill packs (50+ skills) |
| MCP assets | First-class MCP server install/manage via CLI |
| RBAC governance | Role-based access for asset publishing (consumer / contributor / maintainer) |
| Plugin system | User-defined CLI plugins via entry points |
| Import/export | Bundle skills into portable .aikit archives |

**Target**: H1 2027

---

## Phase B — Platform (Research)

**Status**: Exploring

| Item | Detail |
|------|--------|
| Public registry | Central registry with web UI for skill discovery |
| Browser UI | Visual skill browser and one-click install |
| Admin console | Org-level asset governance, usage analytics |
| Federation | Cross-org skill sharing with trust policies |

**Target**: TBD — gated on community adoption metrics from v0.1–v0.3

---

## Milestone Criteria

We ship each phase when:

1. All CI checks pass on Python 3.10–3.12
2. New features have documentation in `docs/`
3. Breaking changes are called out in CHANGELOG with migration notes
4. At least one real-world usage validation before tagging

## How to Influence the Roadmap

- **Feature requests**: Open an [issue](https://github.com/seed-forge/harness-ai-kit/issues/new?template=feature_request.md)
- **Skill proposals**: Use the [skill proposal template](https://github.com/seed-forge/harness-ai-kit/issues/new?template=skill_proposal.md)
- **Discussions**: Join [GitHub Discussions](https://github.com/seed-forge/harness-ai-kit/discussions) for open-ended design conversations
