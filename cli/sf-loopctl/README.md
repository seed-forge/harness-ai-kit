# sf-loopctl

Loop asset lifecycle CLI for [harness-ai-kit](https://github.com/seed-forge/harness-ai-kit) loop assets.

`loopctl` manages the full lifecycle of Loop assets: `list`, `validate`, `run`, `status`, `extract`, `promote`. It reuses the public `harness_ai_kit.domain` loop layer, so it works anywhere harness-ai-kit is installed.

## Install

```bash
pip install sf-loopctl        # installs the `loopctl` command (pulls in harness-ai-kit)
loopctl --help
```

Or via harness-ai-kit as a managed CLI asset:

```bash
harness-ai-kit add cli loopctl
```

## Commands

| Command | Purpose |
|---------|---------|
| `loopctl list` | List loop assets in the current repo/project |
| `loopctl validate <id>` | Validate a loop manifest and its contract predicates |
| `loopctl run <id>` | Advance a loop run and persist state |
| `loopctl status <id>` | Show a loop run's current state |
| `loopctl extract` | Extract a loop asset draft from session artifacts |
| `loopctl promote` | Promote an extracted draft toward publication |

## License

Apache-2.0
