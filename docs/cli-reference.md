# CLI Reference

Complete reference for all `harness-ai-kit` commands. Run `harness-ai-kit <command> --help` for inline help.

## Setup & Configuration

### `harness-ai-kit init`

Initialize this machine with default settings.

```bash
harness-ai-kit init                    # first-time setup
harness-ai-kit init --skip-sync        # skip repo sync if checkout exists
```

Creates `~/.harness-ai-kit/config.yaml` and clones the skill repository.

### `harness-ai-kit doctor`

Health check for your harness-ai-kit environment.

```bash
harness-ai-kit doctor                  # full check
harness-ai-kit doctor runtimes         # check runtime adapters only
harness-ai-kit doctor skills           # check installed skills
harness-ai-kit doctor --json           # machine-readable output
```

### `harness-ai-kit config`

Inspect or update CLI configuration.

```bash
harness-ai-kit config show             # current config
harness-ai-kit config set key value    # update a value
```

Config path: `~/.harness-ai-kit/config.yaml`

---

## Project Setup

### `harness-ai-kit init-project`

Create `ai-kit.yml` (project manifest) in the current directory.

```bash
harness-ai-kit init-project
```

This declares your project's intent — which runtime, scope, and assets to use.

### `harness-ai-kit manifest`

Inspect or migrate the project manifest.

```bash
harness-ai-kit manifest show           # show current ai-kit.yml
harness-ai-kit manifest migrate        # upgrade schema version
```

---

## Installing Skills

### `harness-ai-kit add`

Add a skill to your project and sync.

```bash
# From GitHub (most common)
harness-ai-kit add skill https://github.com/OWNER/REPO/tree/main/path/to/skill

# Shorthand with --subpath
harness-ai-kit add skill OWNER/REPO --subpath path/to/skill

# From the curated library
harness-ai-kit add skill diag-mysql-deadlock

# Specify runtime and scope
harness-ai-kit add skill my-skill --runtime claude-code --scope global

# Add without installing (just update ai-kit.yml)
harness-ai-kit add skill my-skill --no-install
```

### `harness-ai-kit sync`

Reconcile your project to match `ai-kit.yml`.

```bash
harness-ai-kit sync                    # install declared assets
harness-ai-kit sync --offline          # use cache only
```

### `harness-ai-kit remove`

Remove a skill from the project.

```bash
harness-ai-kit remove skill my-skill   # remove from manifest + uninstall
```

### `harness-ai-kit uninstall`

Remove an installed skill without touching `ai-kit.yml`.

```bash
harness-ai-kit uninstall my-skill
```

---

## Discovery & Inspection

### `harness-ai-kit list`

List available skills.

```bash
harness-ai-kit list                    # all skills
harness-ai-kit list skills             # skills only
harness-ai-kit list --json             # JSON output
```

### `harness-ai-kit show`

Show metadata for one skill.

```bash
harness-ai-kit show diag-mysql-deadlock
```

### `harness-ai-kit cat`

Print the main document (SKILL.md) for a skill.

```bash
harness-ai-kit cat diag-mysql-deadlock
```

### `harness-ai-kit search`

Search skills by keyword.

```bash
harness-ai-kit search mysql
```

---

## Dependency Management

### `harness-ai-kit lock`

Resolve dependencies and write `ai-kit.lock`.

```bash
harness-ai-kit lock                    # resolve + write lockfile
harness-ai-kit lock --offline          # resolve from cache only
```

### `harness-ai-kit resolve`

Preview dependency resolution without installing.

```bash
harness-ai-kit resolve skill my-skill
```

### `harness-ai-kit graph`

Show the dependency tree for a skill.

```bash
harness-ai-kit graph skill my-skill
```

### `harness-ai-kit why`

Explain why a dependency appears in the graph.

```bash
harness-ai-kit why my-dependency
```

---

## Maintenance

### `harness-ai-kit outdated`

Show which installed assets have newer versions.

```bash
harness-ai-kit outdated
```

### `harness-ai-kit diff`

Compare manifest, lock, and runtime state.

```bash
harness-ai-kit diff
```

### `harness-ai-kit upgrade`

Upgrade installed assets.

```bash
harness-ai-kit upgrade                 # upgrade all
harness-ai-kit upgrade skills          # skills only
```

### `harness-ai-kit prune`

Remove orphaned installs not declared in `ai-kit.yml`.

```bash
harness-ai-kit prune
```

### `harness-ai-kit cache`

Manage the local package cache.

```bash
harness-ai-kit cache list              # show cached artifacts
harness-ai-kit cache clean             # clear cache
```

---

## Global Options

| Flag | Description |
|------|-------------|
| `--version` / `-V` | Show CLI version |
| `--config-path PATH` | Override config file location |
| `--runtime RUNTIME` | Target runtime: `codex`, `claude-code`, `cursor`, `kiro`, `qoder` |
| `--scope SCOPE` | Install scope: `project`, `global` |
| `--offline` | Use local cache only |
| `--json` | Machine-readable JSON output |
