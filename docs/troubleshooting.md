# Troubleshooting

Common issues and how to fix them. Run `harness-ai-kit doctor` first — it catches most problems.

## Installation Issues

### `pip install harness-ai-kit` fails

**Python version too old**

```
ERROR: Package 'harness-ai-kit' requires a different Python: 3.9 not in '>=3.10'
```

Fix: Upgrade to Python 3.10 or later.

```bash
python --version    # must be >= 3.10
```

**Permission denied on Windows**

```
ERROR: Could not install packages due to an OSError: [WinError 5]
```

Fix: Use `--user` flag or run from a virtual environment.

```bash
pip install --user harness-ai-kit
# or
python -m venv .venv && .venv\Scripts\activate && pip install harness-ai-kit
```

---

## Setup Issues

### `harness-ai-kit doctor` reports "git not found"

harness-ai-kit requires `git` for cloning skill repositories.

Fix: Install git from https://git-scm.com/ and restart your terminal.

### `harness-ai-kit init` fails with network error

```
ERROR: Could not clone repository
```

Possible causes:

1. **No internet connection** — check your network
2. **Corporate proxy** — set `HTTPS_PROXY` environment variable
3. **GitHub not reachable** — try `curl -I https://github.com` to verify

Fix for proxy:

```bash
# PowerShell
$env:HTTPS_PROXY = "http://proxy.company.com:8080"
harness-ai-kit init

# Bash
export HTTPS_PROXY=http://proxy.company.com:8080
harness-ai-kit init
```

---

## Skill Installation Issues

### `harness-ai-kit add skill` fails with "skill not found"

The skill ID doesn't exist in the curated library.

Fix: Check available skills with `harness-ai-kit list`, or use a GitHub URL:

```bash
harness-ai-kit list                              # browse curated skills
harness-ai-kit add skill https://github.com/OWNER/REPO/tree/main/path/to/skill
```

### `harness-ai-kit sync` fails with "checksum mismatch"

The downloaded content doesn't match the lockfile's SHA-256.

Fix: Re-lock and re-sync.

```bash
harness-ai-kit lock --refresh    # re-resolve from source
harness-ai-kit sync
```

### Skills not appearing in your AI tool

Check that the runtime and scope are correct:

```bash
harness-ai-kit doctor runtimes    # verify runtime adapter is healthy
harness-ai-kit diff               # compare declared vs installed state
```

Common mistake: installed with `--scope global` but the AI tool reads project scope, or vice versa.

---

## Lock & Dependency Issues

### `harness-ai-kit lock` fails with "conflict"

Two assets require incompatible versions of the same dependency.

Fix: Check the conflict message, then either:
- Pin a compatible version explicitly in `ai-kit.yml`
- Remove the conflicting asset
- Report it as an issue if it seems like a bug

### `harness-ai-kit resolve` shows unexpected dependencies

Run `harness-ai-kit why <dependency>` to understand why it was pulled in.

---

## Runtime Issues

### Codex: skills installed but not recognized

Verify the install directory:

```bash
harness-ai-kit doctor runtimes    # should show codex target path
ls .agents/skills/        # should contain your skills
```

### Claude Code: skills not loading

Verify the install directory:

```bash
ls .claude/skills/        # project scope
ls ~/.claude/skills/      # global scope
```

---

## Cache Issues

### Stale cache causing problems

```bash
harness-ai-kit cache clean
harness-ai-kit sync
```

---

## Still Stuck?

1. Run `harness-ai-kit doctor --json` and save the output
2. Check [existing issues](https://github.com/seed-forge/harness-ai-kit/issues)
3. Open a [new issue](https://github.com/seed-forge/harness-ai-kit/issues/new?template=bug_report.md) with the doctor output attached
