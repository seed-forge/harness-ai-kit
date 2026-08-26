# woodpeckerctl

`woodpeckerctl` is a small Python wrapper around the Woodpecker CI API. It
provides repository, build, secret, queue, agent, audit, and configuration
commands while keeping the command name stable.

## Install

```bash
pip install sf-woodpeckerctl
```

The distribution name is `sf-woodpeckerctl`; the installed command remains
`woodpeckerctl`.

## Configure

Put the service URL and token in the shared Harness AI Kit configuration:

```yaml
assets:
  woodpeckerctl:
    woodpecker_url: https://woodpecker.example.invalid
    woodpecker_token: <your-api-token>
```

The schema is shipped as `woodpeckerctl/config.defaults.yaml`. Command-line
`--server` and `--token` values are supported for one-off overrides; no service
endpoint is compiled into the package.

## Quick start

```bash
woodpeckerctl doctor
woodpeckerctl repo list
woodpeckerctl build list --repo owner/project
woodpeckerctl config show
```

Use the Woodpecker API and repository permissions appropriate for your own
installation. This project is not affiliated with the Woodpecker maintainers.
