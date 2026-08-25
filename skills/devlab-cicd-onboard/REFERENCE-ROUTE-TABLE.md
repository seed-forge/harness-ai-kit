# CI/CD Route Table

Choose the route from repository facts, not from an assumed platform.

| Repository shape | Preferred first step | Delivery route | Evidence before enabling deployment |
| --- | --- | --- | --- |
| Python package or service | Install locked dependencies, run tests, build a wheel/container as applicable | GitHub Actions or established provider | Artifact can be installed in a clean environment |
| Node.js frontend | Use the repository's locked package-manager command, lint/test/build | Static artifact or container deployment | Built output and preview smoke check |
| Java Maven or Gradle service | Reproduce the documented build and tests | Artifact repository or container deployment | Artifact metadata and health-check contract |
| Go service | Run module tests and produce a reproducible binary or container | Binary or container deployment | Target platform and checksum/health check |
| Containerized service | Build once, scan if available, publish a tagged image | Compose, Kubernetes, or managed runtime | Image digest, rollout status, and service probe |
| Multiple deployable modules | Split build/test ownership by module | Separate or matrix jobs with explicit dependencies | Each selected module has its own artifact and verification |

## Provider Selection

1. Reuse the provider already configured in the repository when it is healthy.
2. For a new public repository, prefer GitHub Actions because workflow,
   environment approval, and Trusted Publishing can remain in the same public
   repository.
3. Use Jenkins, Woodpecker, or another provider when the team already owns its
   runners, credential store, and maintenance path.
4. A migration requires a parallel validation run and an explicit rollback
   plan. Do not replace a working production workflow solely for consistency.

## Project Configuration Template

Keep non-secret deployment intent in a project-reviewed file. This example
contains placeholders only; actual endpoints and credentials stay in the CI
provider configuration.

```yaml
modules:
  pathMapping:
    service-name: module/path

environments:
  staging:
    deployHost: "${DEPLOY_HOST}"
    deployUser: "${DEPLOY_USER}"
    deployDir: "${DEPLOY_DIR}"
    credentialsId: "deploy-credential-reference"

steps:
  buildMaven:
    skipTests: false
  deployViaSsh:
    transport: rsync
```

## Quality Gates

- Keep pull-request gates deterministic and bounded in duration.
- Store thresholds with the project tests, not duplicated in a workflow file.
- Start a new quality gate in reporting mode.
- Before making it blocking, capture one intentional failure and one passing
  run, then record the acceptance criterion in the repository.
