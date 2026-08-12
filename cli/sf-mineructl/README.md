# sf-mineructl

Ops CLI for a [MinerU](https://github.com/opendatalab/MinerU) document-parsing service, companion to [harness-ai-kit](https://github.com/seed-forge/harness-ai-kit).

`mineructl` drives a MinerU HTTP service: health checks, submitting documents, polling status, and fetching results. It reads its endpoint/credentials from your own config — no endpoints are hardcoded.

## Install

```bash
pip install sf-mineructl       # installs the `mineructl` command
mineructl --help
```

Or via harness-ai-kit as a managed CLI asset:

```bash
harness-ai-kit add cli mineructl
```

## Configure

`mineructl` resolves config through harness-ai-kit's asset-config loader. Point it at your own MinerU service:

- Global: `~/.harness-ai-kit/config.yaml` under the `mineructl` asset key, or
- Per-invocation: `--base-url <your-mineru-url>` and `--profile <name>`.

No default base URL ships with the package — you supply your own.

## Commands

| Command | Purpose |
|---------|---------|
| `mineructl doctor` | Check config + service reachability |
| `mineructl probe` / `version` | Probe the service / show its version |
| `mineructl submit <file>` | Submit a document for parsing |
| `mineructl status <task>` | Poll a task's status |
| `mineructl result <task>` | Fetch a finished task's result |
| `mineructl tasks` | List recent tasks |

## License

Apache-2.0
