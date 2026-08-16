# sf-difyctl

Usage-layer operations CLI for a [Dify](https://dify.ai) instance, companion to [harness-ai-kit](https://github.com/seed-forge/harness-ai-kit). Pairs with the `infra-dify-ops` skill.

`difyctl` drives the Dify usage layer: dual-track DSL import (Console API first, Playwright fallback), per-instance DSL version detection, import-ready DSL authoring & validation, provider configuration, and a resource ledger.

> **Status: trial.**

## Install

```bash
pip install sf-difyctl          # installs the `difyctl` command
difyctl --help
```

Or via harness-ai-kit as a managed CLI asset:

```bash
harness-ai-kit add cli difyctl
```

## Configuration

Point it at your own Dify instance via the harness-ai-kit config — **no host or credential is baked in**:

```yaml
# ~/.harness-ai-kit/config.yaml
assets:
  difyctl:
    base_url: "https://your-dify-host"
    # console key / app keys go here too (never committed)
```

Precedence: CLI flags > `assets.difyctl` in `~/.harness-ai-kit/config.yaml` > env vars > `config.defaults.yaml` (empty by default).

## Commands (usage layer)

| Area | What it does |
|------|--------------|
| `doctor` / `probe` | Instance health & connectivity check |
| `dsl import` | Dual-track import (Console API → Playwright fallback) with auto version detect |
| `dsl authoring` / `lint` / `validate` | Import-ready DSL authoring & validation |
| `provider *` | Model provider configuration |
| `resource *` | Resource ledger (capture / ensure / scan / summarize) |
| `app key *` | Service API key management |

`tests/` and `scripts/` in this directory are **development-only** (they expect a reachable Dify instance) and are **not** shipped in the pip package.

## License

Apache-2.0
