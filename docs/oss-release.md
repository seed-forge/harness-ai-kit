# OSS Release Process

`docs/oss-public-release.yaml` is the only publish allowlist. It replaces
directory discovery: a new `cli/*` directory is never released until it has a
reviewed matrix entry.

## Normal Flow

1. Generate a public snapshot from the private source into the separate
   staging checkout, remove private operational details, and review the diff.
2. Align `pyproject.toml`, `cli.json`, and package `__version__` where the
   package uses them. Add and run a package test command.
3. Commit the reviewed public staging baseline, then generate a checked
   staging manifest from that immutable commit. The manifest records each
   selected package's name, version, and source-tree SHA-256. Private-only
   versions may be intentionally skipped.
4. Set `publish: true` only for the reviewed packages. It is deliberately
   `false` by default. Assign `release_wave` values so dependencies publish in
   an earlier wave.
5. Run the release gate locally, then use the manual workflow from the reviewed
   commit: TestPyPI first, then PyPI. A pushed `v*` tag never publishes by
   itself; running the production workflow from a tag additionally creates the
   GitHub Release. The workflow builds packages, performs the
   full gate, verifies existing PyPI hashes, publishes only missing identical
   versions through OIDC, and reads hashes back before creating a GitHub
   Release.

Private-only versions may be skipped. A public package version may not be
reused: an existing version is accepted only when every remote wheel and sdist
SHA-256 equals the newly built files. A hash difference is a hard failure.

## Trusted Publishing Setup

No PyPI token is stored in this repository. Before the first release of each
package, configure a PyPI Trusted Publisher for each target index:

| Setting | Production PyPI | TestPyPI |
|---|---|---|
| Owner | `seed-forge` | `seed-forge` |
| Repository | `harness-ai-kit` | `harness-ai-kit` |
| Workflow | `release.yml` | `release.yml` |
| Environment | `pypi` | `testpypi` |

Create matching protected GitHub environments. The `pypi` environment should
require a human approval; `testpypi` may be less restrictive. The first real,
approved release establishes package ownership. Do not publish a placeholder
package to reserve a name. The production workflow refuses to publish a
package version which has not first been read from TestPyPI.

## Local Commands

```bash
python -m pip install -e . build twine pytest
python tools/public_release_gate.py --mode ci --report build/release-gate.json
python tools/public_release_gate.py --mode ci --source-revision <staging-commit> --write-staging-manifest docs/oss-staging-manifest.json --package-id harness-ai-kit --package-id sf-difyctl --package-id sf-evalctl --package-id sf-loopctl --package-id sf-mineructl --package-id sf-nexusctl --package-id sf-ragflowctl --update-matrix-snapshot
python tools/public_release_gate.py --mode release --report build/release-gate.json
```

The final command intentionally fails until `publish: true`, a source commit,
and a matching staging manifest are present. That failure is the pre-release
control, not a reason to bypass it.
