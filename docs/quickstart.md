# Quick Start

## 1. Install

```bash
pip install harness-ai-kit
```

## 2. Initialize

```bash
ai-kit init
```

This creates `~/.ai-kit/config.yaml` with default settings (PyPI index, GitHub source support).

## 3. Add a Skill from GitHub

```bash
cd my-project
ai-kit add skill https://github.com/anthropics/skills/tree/main/skills/skill-creator
ai-kit sync
```

The skill is now installed at `.agents/skills/skill-creator/` (Codex project scope by default).

## 4. Use Other Runtimes

```bash
# Claude Code (project scope)
ai-kit add skill anthropics/skills --subpath skills/skill-creator --runtime claude-code --scope project

# Cursor
ai-kit add skill anthropics/skills --subpath skills/skill-creator --runtime cursor --scope project

# Kiro
ai-kit add skill anthropics/skills --subpath skills/skill-creator --runtime kiro --scope project
```

## 5. Explore Built-in Skills

The repository includes a curated enterprise skill library:

```bash
ai-kit list          # list all available skills
ai-kit show diag-mysql-deadlock  # show a specific skill's metadata
ai-kit cat diag-mysql-deadlock   # print the skill's SKILL.md
```

## 6. Lock and Reproduce

```bash
ai-kit lock          # resolve all dependencies and write ai-kit.lock
ai-kit sync          # install from lockfile (reproducible)
```

Share `ai-kit.yml` and `ai-kit.lock` with your team — anyone running `ai-kit sync` gets the exact same versions.
