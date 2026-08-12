# Examples

Real-world usage patterns for harness-ai-kit.

## 1. Solo Developer — Codex + MySQL Diagnostics

You use Codex and want MySQL troubleshooting skills in your project.

```bash
pip install harness-ai-kit
harness-ai-kit init
cd my-backend-project

# Add the MySQL deadlock diagnostic skill
harness-ai-kit add skill diag-mysql-deadlock

# Verify
harness-ai-kit doctor
ls .agents/skills/diag-mysql-deadlock/SKILL.md
```

Now ask your AI agent: *"My MySQL is throwing deadlock errors, help me diagnose"*

---

## 2. Team — Shared Skills via harness-ai-kit.yml + harness-ai-kit.lock

Your team uses Claude Code. Everyone needs the same skills, pinned to exact versions.

**Team lead** (one-time setup):

```bash
harness-ai-kit init-project
harness-ai-kit add skill public-mysql-expert-base --runtime claude-code
harness-ai-kit add skill diag-mysql-slow-query --runtime claude-code
harness-ai-kit add skill diag-k8s-pod-crashloop --runtime claude-code
harness-ai-kit lock
git add harness-ai-kit.yml harness-ai-kit.lock
git commit -m "chore: pin team AI skills"
```

**Team members** (after cloning):

```bash
pip install harness-ai-kit
harness-ai-kit sync
# Done — same skills, same versions, same SHAs
```

---

## 3. GitHub Direct Install — Any Public Skill

Install a skill from any GitHub repo without cloning.

```bash
# Anthropic's skill-creator
harness-ai-kit add skill https://github.com/anthropics/skills/tree/main/skills/skill-creator

# Custom skill from your own repo
harness-ai-kit add skill myorg/ai-skills --subpath skills/code-reviewer --ref v1.0
```

---

## 4. Multi-Runtime — Same Skills for Codex + Claude Code

You switch between Codex and Claude Code and want the same skills in both.

```bash
# Install for Codex (project scope)
harness-ai-kit add skill base-goal-execution --runtime codex

# Also install for Claude Code (project scope)
harness-ai-kit add skill base-goal-execution --runtime claude-code

harness-ai-kit sync
```

Skills are installed to both `.agents/skills/` and `.claude/skills/`.

---

## 5. Offline / Air-Gapped

Your CI or air-gapped environment has no internet access.

```bash
# On a machine with internet — warm the cache
harness-ai-kit sync
# Copy ~/.harness-ai-kit/cache/ to the offline machine

# On the offline machine
harness-ai-kit sync --offline
```

---

## 6. Kiro — Steering + Skill Hybrid

Kiro uses steering files, not skill directories. harness-ai-kit handles the mapping.

```bash
harness-ai-kit add skill diag-k8s-node-pressure --runtime kiro
harness-ai-kit sync

# Skill is now at .kiro/steering/ + harness-harness-ai-kit-skills/
```

---

## Sample harness-ai-kit.yml

```yaml
schema_version: "2"
runtime: codex
scope: project
assets:
  skills:
    - id: diag-mysql-deadlock
      version: "==0.1.0"
    - id: public-mysql-expert-base
      version: "==0.1.0"
    - id: skill-creator
      sources: [git-repo]
      source_ref: https://github.com/anthropics/skills
      ref: main
      subpath: skills/skill-creator
```
