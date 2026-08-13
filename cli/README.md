# CLIs

Companion command-line tools for [harness-ai-kit](https://github.com/seed-forge/harness-ai-kit). Each subdirectory is an **independent, pip-installable package** published to PyPI under the `sf-` prefix (PyPI has no real namespaces, so `sf-` is our brand prefix — see the note below).

| Directory | PyPI package | Command | What it does |
|-----------|--------------|---------|--------------|
| `sf-loopctl/` | `sf-loopctl` | `loopctl` | Loop asset lifecycle (list / validate / run / status / extract / promote) |
| `sf-mineructl/` | `sf-mineructl` | `mineructl` | Ops CLI for a MinerU document-parsing service |
| `sf-evalctl/` | `sf-evalctl` | `evalctl` | Eval loop for AI/data apps (run / diff / ingest / feedback / report) |

## Install a CLI

```bash
pip install sf-loopctl          # -> `loopctl` command
pip install sf-mineructl        # -> `mineructl` command
pip install sf-evalctl          # -> `evalctl` command
```

Each CLI declares `harness-ai-kit` as a dependency and reuses its public `domain` / `infrastructure` layers.

## Publishing

All CLIs are published by [`.github/workflows/publish-clis.yml`](../.github/workflows/publish-clis.yml) via PyPI **Trusted Publishing** (OIDC, no stored tokens). The workflow **auto-discovers** every `cli/*/` directory that has a `pyproject.toml` — nothing in the workflow needs editing when you add a CLI.

Trigger a CLI release (decoupled from the core package):

```bash
git tag cli-v0.1.0
git push origin cli-v0.1.0
```

> **One-time per package:** because PyPI has no namespaces, each `sf-<name>` project needs its own Trusted Publisher on PyPI (Owner `seed-forge`, Repo `harness-ai-kit`, Workflow `publish-clis.yml`, Environment `pypi`).

## Add a new CLI

Use the scaffolder — it creates a ready-to-publish skeleton that the workflow picks up automatically:

```bash
python tools/new-cli.py <name>        # e.g. python tools/new-cli.py fooctl
```

This generates `cli/sf-<name>/` with `pyproject.toml`, `README.md`, `cli.json`, and a `<name>/cli.py` entry stub. Fill in the command logic, then tag `cli-v*` to publish.

## Namespace note

PyPI has no organization namespaces (unlike npm scopes). `sf-` is a plain name prefix used for SeedForge branding; it is not reserved or enforced by PyPI. The installed **command** name stays short (`loopctl`, not `sf-loopctl`).
