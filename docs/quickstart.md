# Quickstart

This guide creates a reproducible project-local AI asset setup. It does not
require a private registry, a maintainer checkout, or a machine-specific
configuration.

## Prerequisites

- Python 3.10 or later
- Git
- A supported AI coding runtime, such as Codex, Claude Code, Cursor, Kiro, or
  dsh

## Install

```bash
python -m pip install --upgrade harness-ai-kit
harness-ai-kit --version
```

## Initialize Your Local Configuration

```bash
harness-ai-kit init
```

This creates or updates `~/.harness-ai-kit/config.yaml`. It is the shared
location for user-specific endpoints and credentials; do not write those
values into a project manifest, lockfile, or Skill.

For a registry-backed public catalog, configure the public registry endpoint
in that file. You can also use a public Git source directly, as shown below.

## Create A Project And Add A Public Skill

```bash
mkdir my-agent-project
cd my-agent-project
harness-ai-kit init-project --runtime codex
harness-ai-kit add skill https://github.com/anthropics/skills/tree/main/skills/skill-creator
```

`init-project` writes `harness-ai-kit.yml`, which declares what the project
wants. `add` resolves the source, writes `harness-ai-kit.lock`, and installs
the selected Skill into the configured runtime directory.

## Verify The Result

```bash
harness-ai-kit sync
harness-ai-kit doctor
```

For the default Codex project runtime, the installed Skill is under
`.agents/skills/`. The manifest and lockfile are the files to commit; the
runtime directory is a materialized working copy.

## Next Steps

- See the [CLI reference](cli-reference.md) for command options.
- See [usage scenarios](usage-scenarios.md) for choosing Skills and Loops.
- See [concepts](concepts.md) for manifests, locks, sources, and runtime
  materialization.
- Use [troubleshooting](troubleshooting.md) when a source, dependency, or
  runtime check fails.
