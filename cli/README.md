# CLIs

Companion command-line tools for [harness-ai-kit](https://github.com/seed-forge/harness-ai-kit). Each subdirectory is an **independent, pip-installable package** published to PyPI under the `sf-` prefix (PyPI has no real namespaces, so `sf-` is our brand prefix — see the note below).

| Directory | PyPI package | Command | What it does |
|-----------|--------------|---------|--------------|
| `sf-loopctl/` | `sf-loopctl` | `loopctl` | Loop asset lifecycle (list / validate / run / status / extract / promote) |
| `sf-mineructl/` | `sf-mineructl` | `mineructl` | Ops CLI for a MinerU document-parsing service |
| `sf-evalctl/` | `sf-evalctl` | `evalctl` | Eval loop for AI/data apps (run / diff / ingest / feedback / report) |
| `sf-nexusctl/` | `sf-nexusctl` | `nexusctl` | Nexus repository ops (repo CRUD / blobstore / cleanup-policy / inventory / user/role) |
| `sf-difyctl/` | `sf-difyctl` | `difyctl` | Dify usage-layer ops (DSL import / validate / version detect / provider config) |
| `sf-ragflowctl/` | `sf-ragflowctl` | `ragflowctl` | RAGFlow operations (doctor / dataset / document / ingest / retrieval) |

## Install a CLI

```bash
pip install sf-loopctl          # -> `loopctl` command
pip install sf-mineructl        # -> `mineructl` command
pip install sf-evalctl          # -> `evalctl` command
pip install sf-nexusctl         # -> `nexusctl` command
pip install sf-difyctl          # -> `difyctl` command
pip install sf-ragflowctl       # -> `ragflowctl` command
```

Each CLI declares `harness-ai-kit` as a dependency and reuses its public `domain` / `infrastructure` layers.

## Publishing

Publication is governed by the explicit [`docs/oss-public-release.yaml`](../docs/oss-public-release.yaml) matrix and [`.github/workflows/release.yml`](../.github/workflows/release.yml). Adding a `cli/*/` directory never makes it publishable by itself. A package needs a reviewed source path, aligned versions, a test command, a staging manifest entry and `publish: true` in the matrix.

After the matrix and staging manifest have passed review, trigger a repository release:

```bash
git tag v0.15.0
git push origin v0.15.0
```

> **One-time per package and channel:** because PyPI has no namespaces, each `sf-<name>` project needs its own Trusted Publisher. Use Owner `seed-forge`, Repository `harness-ai-kit`, Workflow `release.yml`, and the matching `pypi` or `testpypi` GitHub environment.

## Add a new CLI

Use the scaffolder, then add an explicit matrix entry and release tests:

```bash
python tools/new-cli.py <name>        # e.g. python tools/new-cli.py fooctl
```

This generates `cli/sf-<name>/` with `pyproject.toml`, `README.md`, `cli.json`, and a `<name>/cli.py` entry stub. Fill in the command logic, add tests, and update the reviewed release matrix before creating a release tag.

## Namespace note

PyPI has no organization namespaces (unlike npm scopes). `sf-` is a plain name prefix used for SeedForge branding; it is not reserved or enforced by PyPI. The installed **command** name stays short (`loopctl`, not `sf-loopctl`).
