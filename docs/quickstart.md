# Quick Start

Get from zero to a working AI skill in under 2 minutes.

## Prerequisites

- Python >= 3.10 (`python --version` to check)
- Git (`git --version` to check)
- One of: Codex, Claude Code, Cursor, or Kiro

## Step 1: Install

```bash
pip install harness-ai-kit
```

Verify:

```bash
harness-ai-kit --version
# Expected: harness-ai-kit 0.1.0
```

## Step 2: Initialize

```bash
harness-ai-kit init
```

This creates `~/.ai-kit/config.yaml` and clones the skill repository.

Verify:

```bash
harness-ai-kit doctor
# Expected: all checks pass (git, config, checkout, runtime)
```

## Step 3: Add a Skill

```bash
cd your-project
harness-ai-kit add skill https://github.com/anthropics/skills/tree/main/skills/skill-creator
```

This downloads the skill and records it in `harness-ai-kit.yml`.

## Step 4: Sync

```bash
harness-ai-kit sync
```

This installs the skill into your AI runtime's skill directory.

Verify:

```bash
ls .agents/skills/skill-creator/    # Codex
# or
ls .claude/skills/skill-creator/    # Claude Code
```

## Step 5: Use It

Open your AI coding tool and ask it to use the skill. For example:

> "Help me create a new skill using the skill-creator skill"

The AI agent reads the SKILL.md from the installed directory and follows its instructions.

---

## What's Next?

- **Browse curated skills**: `harness-ai-kit list` — 23 production-tested skills included
- **See all commands**: [CLI Reference](cli-reference.md)
- **Real-world examples**: [examples/](../examples/README.md) — team sync, multi-runtime, offline mode
- **Trouble?**: [Troubleshooting guide](troubleshooting.md)
- **Write your own skill**: [Skill Authoring Guide](skill-authoring.md)

## Multi-Runtime Quick Reference

```bash
# Codex (default) — installs to .agents/skills/
harness-ai-kit add skill <id> --runtime codex

# Claude Code — installs to .claude/skills/
harness-ai-kit add skill <id> --runtime claude-code

# Cursor — installs to .cursor/rules/
harness-ai-kit add skill <id> --runtime cursor

# Kiro — installs to .kiro/steering/ + harness-ai-kit-skills/
harness-ai-kit add skill <id> --runtime kiro
```

## Team Workflow

```bash
# Team lead: pin skills for the project
harness-ai-kit init-project
harness-ai-kit add skill diag-mysql-deadlock
harness-ai-kit lock
git add harness-ai-kit.yml harness-ai-kit.lock && git commit -m "pin team skills"

# Team members: get identical state
harness-ai-kit sync
```
