# Portable CI/CD Patterns

## Ownership Model

| Concern | Owner | Where it belongs |
| --- | --- | --- |
| Build, tests, artifact names, and non-secret defaults | Application repository | Version-controlled files |
| Tokens, private endpoints, SSH keys, signing material | CI provider or secret manager | Encrypted secrets or protected environments |
| Runner images, plugins, global credentials, and organization policy | CI platform operator | Provider administration |
| Deployment target and rollback approval | Application owner and operator | Reviewed delivery record |

Never move a value from the latter three rows into a repository merely to make
a sample pipeline execute.

## Minimal Pipeline Shape

```text
checkout -> dependency install -> test -> build -> artifact verification
        -> optional publish -> optional deploy -> service verification
```

Every optional stage needs a declared input and an observable result:

| Stage | Required input | Observable result |
| --- | --- | --- |
| Test | Reproducible dependency install | Test report and exit code |
| Build | Version and source revision | Immutable artifact or image digest |
| Publish | Provider-managed credential | Artifact registry readback |
| Deploy | Confirmed target and approval | Rollout result or deployment record |
| Verify | Defined health or functional contract | Target-specific probe result |

## GitHub Actions Baseline

For a new public repository, start with a build-only workflow. Add protected
environments only after the package or service has a confirmed release target.

```yaml
name: CI

on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-python@v7
        with:
          python-version: "3.12"
      - run: python -m pip install --upgrade pip
      - run: python -m pip install -e .
      - run: python -m pytest -q
```

Adjust the install and test commands to match the repository. Do not copy this
example into a Node.js, Java, or Go project unchanged.

## Deployment Guardrails

- Build once and promote the same artifact; do not rebuild on the production
  deployment job.
- Use provider-managed environments for approval and protected secrets.
- Require a bounded timeout, a clear failure signal, and a rollback or stop
  condition for each deployment action.
- Verify the externally consumed service contract after deployment. A runner's
  process exit code alone is insufficient.
- Keep destructive cleanup disabled unless the target and retention policy are
  explicitly confirmed.

## Jenkins-Style Configuration

The bundled schema and validation script support a project-local configuration
file. They validate names and required fields only. The actual credential ID,
host, and environment variables must be supplied by the CI platform at run
time.

```bash
python scripts/validate-jenkins-yml.py .platform/jenkins.yml \
  --schema references/jenkins-yml-schema.json
```

Use `bash scripts/sync-service-list.sh .platform/jenkins.yml` to generate a
reviewable service-list snippet for a repository that has multiple modules.
