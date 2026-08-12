# Skill Authoring Guide

## Directory Structure

```
my-skill/
├── SKILL.md          # Main skill document (required)
├── skill.json        # Metadata manifest (required)
├── USAGE.md          # Usage guide with copy-pasteable prompts (required)
├── CHANGELOG.md      # Version history (required)
├── EXAMPLE.md        # Multi-step examples (optional)
└── references/       # Reference documents (optional)
```

## skill.json Schema

```json
{
  "id": "my-skill",
  "name": "my-skill",
  "owner": "community",
  "version": "0.1.0",
  "status": "trial",
  "entry": "SKILL.md",
  "package_type": "skill",
  "summary": "One-line description.",
  "compatible_clients": ["codex", "claude-code"],
  "dependencies": [
    {
      "type": "cli",
      "id": "harness-ai-kit",
      "version": "==0.1.0",
      "scope": "required"
    }
  ]
}
```

Key rules:
- `id` must be lowercase, hyphenated, no spaces
- `version` must be pinned (`==x.y.z`) in dependencies
- `optional` dependencies must declare a `feature` name
- `USAGE.md` must include a `## 可直接复制的中文 Prompt` section

## Creating a New Skill

```bash
# Using harness-ai-kit's built-in template (if available)
harness-ai-kit add skill --new my-skill
```

Or manually:

1. Create `skills/my-skill/` directory
2. Write `SKILL.md` — the main instruction document
3. Write `skill.json` — metadata
4. Write `USAGE.md` — with at least one copy-pasteable prompt
5. Write `CHANGELOG.md` — `## 0.1.0 — initial release`
6. Test: `harness-ai-kit validate` should pass

## Validation

The CI pipeline validates:
- `skill.json` is valid JSON with required fields
- No internal hostnames or credentials (sensitive-scan)
- `USAGE.md` has the Chinese prompt section
