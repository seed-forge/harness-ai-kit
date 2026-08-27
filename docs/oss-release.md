# OSS Release Process

`docs/oss-public-release.yaml` is the only publish allowlist. It replaces
directory discovery: a new `cli/*` directory is never released until it has a
reviewed matrix entry.

## Normal Flow

1. Generate a public snapshot from the private source into the separate
   staging checkout, remove private operational details, and review the diff.
2. Align `pyproject.toml`, `cli.json`, and package `__version__` where the
   package uses them. For the core CLI, also align `README.md`,
   `README.zh-CN.md`, `INSTALL.md`, and `docs/quickstart.md` with the exact
   pinned public version. The release gate also requires the core English and
   Chinese README sections that define positioning, REMIX, lock-in boundary,
   workflow, architecture, and documentation, plus a minimum body size for
   each README; a short placeholder or heading-only outline cannot replace the
   public product documentation. Add a source test command plus a wheel
   `smoke_command` that invokes the installed public console entry point.
3. Commit the reviewed public staging baseline, then generate a checked
   staging manifest from that immutable commit. The manifest records each
   selected package's name, version, and source-tree SHA-256. Private-only
   versions may be intentionally skipped.
4. Set `publish: true` only for the reviewed packages. It is deliberately
   `false` by default. Assign `release_wave` values so dependencies publish in
   an earlier wave.
5. Run the release gate locally, then use the manual workflow from the reviewed
   commit: TestPyPI first, then PyPI. The TestPyPI run builds the checked
   distribution artifact. The production dispatch must provide that successful
   `testpypi_run_id`; it downloads the immutable artifact from that run and
   verifies its hashes against TestPyPI before publishing the exact same files
   to PyPI through OIDC. A pushed `v*` tag never publishes by itself; running
   the production workflow from a tag additionally creates the GitHub Release.
   The production run still performs the full gate for its tagged source,
   verifies existing PyPI hashes, publishes only missing identical versions,
   and reads hashes back before creating a GitHub Release.

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

The release gate runs source tests first, then creates a brand-new system-temp
virtual environment for every source test and generated wheel. Source tests
install the staging core and the selected CLI as editable packages, resolving
their declared dependencies only from public PyPI. Wheel smoke tests remove
`PYTHONPATH` and private pip index settings, install only from public PyPI plus
explicitly built dependency wheels, verify the installed distribution version,
and run the matrix `smoke_command`. A globally installed older CLI or cached
dependency cannot satisfy either check.
