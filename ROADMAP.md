# harness-ai-kit Roadmap

## Product Direction

`harness-ai-kit` is a portable package manager and composition layer for AI
agent assets. Its core job is to make a project's selected Skills, CLIs, MCPs,
plugins, hooks, subagents, and loops explicit, reproducible, and installable
across supported AI coding runtimes.

The product follows a composition-first rule: reuse a focused public asset when
it already solves the problem; add orchestration, metadata, and reproducibility
only where they create durable value.

## Current Public Foundation

The public core provides the following stable direction:

| Area | Current contract |
|---|---|
| Project declaration | `harness-ai-kit.yml` describes the requested assets and features |
| Reproducible state | `harness-ai-kit.lock` records resolved sources, versions, and checksums |
| Installation | Staged materialization verifies selected assets before replacing runtime targets |
| Sources | Public Git repositories and configured public registries can provide assets |
| Runtime support | Codex, Claude Code, Cursor, Kiro, and dsh adapters are part of the product boundary |
| Public catalog | Assets enter the public catalog only through an explicit allowlist and redaction gate |
| Configuration | Endpoints and credentials belong in user configuration, never public asset defaults |

The current published catalog is intentionally selective. A private asset is
not implied to be public, and an internal iteration does not imply a public
release. See [the catalog](CATALOG.md) for the source of truth.

## Near-Term: Authoring And Automation

The next product layer improves how portable assets are created and operated:

- clearer authoring templates and offline validation contracts;
- richer dependency, environment, and provenance declarations;
- Loop and Hook authoring patterns with explicit runtime and safety boundaries;
- better discovery and upgrade guidance for public assets;
- public examples that demonstrate complete, reproducible workflows.

These capabilities are released only when their public behavior, documentation,
and tests are ready. They are not promised merely because private experiments
exist.

## Later: Ecosystem Expansion

As the public core and asset ecosystem mature, the roadmap includes:

- broader engineering and operations asset families;
- improved MCP and plugin installation paths;
- publish and contributor workflows that preserve provenance and review;
- richer visibility into dependency, lockfile, and runtime state.

Expansion remains guided by portability. An asset that depends on a private
network topology, credentials, or an unportable platform fact remains outside
the public catalog until it can be safely generalized.

## Platform Milestones

Registry services, a browser experience, and organization-level administration
are separate platform milestones. They must not become hidden prerequisites for
the core CLI:

| Milestone | Intent | Boundary |
|---|---|---|
| Public registry | Discover reviewed public assets | Optional source for the core resolver |
| Browser | Explore assets and their contracts | Convenience layer, not a required runtime |
| Publisher and admin flows | Review, provenance, and organization governance | Explicitly permissioned and separately deployed |
| Federation | Cross-organization sharing with trust policies | Requires a clear security model before delivery |

## Release Principles

1. Public documentation describes shipped behavior, a marked roadmap item, or
   an explicit non-goal. It must not describe private-only capability as public.
2. Public releases use an allowlisted staging tree, redaction scans, package
   checks, and fresh-install evidence.
3. TestPyPI and PyPI are distinct release states; a successful build or GitHub
   commit is not proof of publication.
4. Public documentation is versioned source material. Build scripts may render
   it but must not silently replace it with an abbreviated product description.

## Participation

Use GitHub Issues for defects and focused feature requests. Use Discussions for
design questions and asset proposals. Star or Watch the repository to follow
released public batches; community interest never unlocks an unreviewed asset.
