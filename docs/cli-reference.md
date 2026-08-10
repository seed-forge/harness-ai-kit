# CLI Reference

Complete reference for all `ai-kit` commands. Run `ai-kit <command> --help` for inline help.

## Setup & Configuration

### `ai-kit init`

Initialize this machine with default settings.

```bash
ai-kit init                    # first-time setup
ai-kit init --skip-sync        # skip repo sync if checkout exists
```

Creates `~/.ai-kit/config.yaml` and clones the skill repository.

### `ai-kit doctor`

Health check for your ai-kit environment.

```bash
ai-kit doctor                  # full check
ai-kit doctor runtimes         # check runtime adapters only
ai-kit doctor skills           # check installed skills
ai-kit doctor --json           # machine-readable output
```

### `ai-kit config`

Inspect or update CLI configuration.

```bash
ai-kit config show             # current config
ai-kit config set key value    # update a value
```

Config path: `~/.ai-kit/config.yaml`

---

## Project Setup

### `ai-kit init-project`

Create `ai-kit.yml` (project manifest) in the current directory.

```bash
ai-kit init-project
```

This declares your project's intent — which runtime, scope, and assets to use.

### `ai-kit manifest`

Inspect or migrate the project manifest.

```bash
ai-kit manifest show           # show current ai-kit.yml
ai-kit manifest migrate        # upgrade schema version
```

---

## Installing Skills

### `ai-kit add`

Add a skill to your project and sync.

```bash
# From GitHub (most common)
ai-kit add skill https://github.com/OWNER/REPO/tree/main/path/to/skill

# Shorthand with --subpath
ai-kit add skill OWNER/REPO --subpath path/to/skill

# From the curated library
ai-kit add skill diag-mysql-deadlock

# Specify runtime and scope
ai-kit add skill my-skill --runtime claude-code --scope global

# Add without installing (just update ai-kit.yml)
ai-kit add skill my-skill --no-install
```

### `ai-kit sync`

Reconcile your project to match `ai-kit.yml`.

```bash
ai-kit sync                    # install declared assets
ai-kit sync --offline          # use cache only
```

### `ai-kit remove`

Remove a skill from the project.

```bash
ai-kit remove skill my-skill   # remove from manifest + uninstall
```

### `ai-kit uninstall`

Remove an installed skill without touching `ai-kit.yml`.

```bash
ai-kit uninstall my-skill
```

---

## Discovery & Inspection

### `ai-kit list`

List available skills.

```bash
ai-kit list                    # all skills
ai-kit list skills             # skills only
ai-kit list --json             # JSON output
```

### `ai-kit show`

Show metadata for one skill.

```bash
ai-kit show diag-mysql-deadlock
```

### `ai-kit cat`

Print the main document (SKILL.md) for a skill.

```bash
ai-kit cat diag-mysql-deadlock
```

### `ai-kit search`

Search skills by keyword.

```bash
ai-kit search mysql
```

---

## Dependency Management

### `ai-kit lock`

Resolve dependencies and write `ai-kit.lock`.

```bash
ai-kit lock                    # resolve + write lockfile
ai-kit lock --offline          # resolve from cache only
```

### `ai-kit resolve`

Preview dependency resolution without installing.

```bash
ai-kit resolve skill my-skill
```

### `ai-kit graph`

Show the dependency tree for a skill.

```bash
ai-kit graph skill my-skill
```

### `ai-kit why`

Explain why a dependency appears in the graph.

```bash
ai-kit why my-dependency
```

---

## Maintenance

### `ai-kit outdated`

Show which installed assets have newer versions.

```bash
ai-kit outdated
```

### `ai-kit diff`

Compare manifest, lock, and runtime state.

```bash
ai-kit diff
```

### `ai-kit upgrade`

Upgrade installed assets.

```bash
ai-kit upgrade                 # upgrade all
ai-kit upgrade skills          # skills only
```

### `ai-kit prune`

Remove orphaned installs not declared in `ai-kit.yml`.

```bash
ai-kit prune
```

### `ai-kit cache`

Manage the local package cache.

```bash
ai-kit cache list              # show cached artifacts
ai-kit cache clean             # clear cache
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
