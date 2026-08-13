# sf-evalctl

Evaluation CLI for AI / data applications, companion to [harness-ai-kit](https://github.com/seed-forge/harness-ai-kit). Pairs with the `devlab-eval-driven-agent` skill.

`evalctl` runs the eval loop: execute eval sets, diff against a baseline to catch regressions, ingest real-world samples, collect feedback, and generate reports.

> **Status: trial** — the command surface is stable but some subcommands are still being fleshed out.

## Install

```bash
pip install sf-evalctl          # installs the `evalctl` command
pip install "sf-evalctl[sql]"   # + SQL-eval extras (sqlparse)
evalctl --help
```

Or via harness-ai-kit as a managed CLI asset:

```bash
harness-ai-kit add cli evalctl
```

## Commands

| Command | Purpose |
|---------|---------|
| `evalctl run` | Run an eval set against a target |
| `evalctl diff` | Diff results against a baseline to detect regressions |
| `evalctl ingest` | Ingest real-world samples into an eval set |
| `evalctl feedback` | Collect / record human feedback |
| `evalctl report` | Generate an evaluation report |

## License

Apache-2.0
