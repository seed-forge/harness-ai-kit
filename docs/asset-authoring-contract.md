# Asset Authoring Contract

This document is the source-of-truth contract used by the templates, scaffold
commands, `validate`, and `doctor assets`.

## Metadata

- Every installable asset includes its declared entry document, `USAGE.md`, and `CHANGELOG.md`.
- `environment.system` is a list of structured executable requirements. Each item has `name`, `command`, optional `platforms`, `optional`, and `install_commands`; do not use bare strings.
- `environment.python_strategy` is one of `none`, `project-venv`, or `global-python`.
- Config schemas point to a file whose first marker is `$schema: harness-ai-kit-config/v1`.
- `sources` describes package resolution only. `provenance` separately records an adapted asset's lineage. A `public-remix` or `internal-remix` records each upstream URL, fixed revision, license, retrieval date, and local adaptation; references without an adopted derivative stay in review evidence, not runtime instructions.
- `structure_profile` is opt-in: `direct` keeps the procedure in `SKILL.md`; `folder-light` admits independently useful documents; `routed` has multiple independently selected paths. Every declared profile has one or more globally unique `responsibility_keys` so overlapping Skills have an explicit canonical owner.
- `load_plan` is optional only for `direct`; `folder-light` / `routed` declare `always_read` and route-specific references. Every Markdown document under `references/`, `profiles/`, `rules/`, or `workflows/` must be reachable from that plan and named from `SKILL.md`. The validator rejects unsafe paths, dead documents, duplicate route ids, and duplicate responsibility owners.

## Namespace And Install Mode

- Publishable bundle assets (`skill`, `loop`, `plugin`, `subagent`) explicitly use `namespace: team` or `namespace: public`.
- Manual assets (`hook`, `mcp`) and CLI distributions do not declare `namespace`.
- CLI dependencies are typed asset references only and never carry a namespace; Python packages belong in `pyproject.toml` or the declared environment fields.

## Dependency And Test Boundaries

- Local dependency version ranges are checked offline by `validate`.
- Registry-only and Git `source_url` dependencies are checked by the resolver/doctor integration path; offline validation does not guess remote state.
- Unit and combination tests use temporary fixtures, `offline: true`, a maintainer role where write commands are under test, and mocked HTTP transports. Registry, Nexus, TLS, and role-bound publishing tests are explicit integration tests.
- Skill routing suites use `evals/skills/<id>/suite.yaml`. New suites classify cases as `positive`, `negative`, `forbidden`, `neighbor`, or `progressive-load`; the last case type explicitly declares the support documents injected for that task. Reports record the selected documents and hashes alongside `used`, `appropriate`, `holdout`, and `challenge` results. This is Harness injection evidence, not a claim that a model made a particular hidden tool call.

## Test Commands

The repository `conftest.py` registers `unit`, `combination`, and `integration`
markers. Tests under an `integration/` directory or named `test_integration_*`
are treated as integration tests automatically. The default suite is therefore
offline and deterministic:

```powershell
python -m pytest -q
python -m pytest -q -m "unit or combination"
```

Real registry/Nexus/TLS/credential checks require both explicit opt-in and an
explicit integration opt-in:

```powershell
$env:HARNESS_AI_KIT_INTEGRATION = "1"
python -m pytest -q --run-integration -m integration
```

The integration contract test reads `skill_registry_index_url`, `role`, and
registry credentials from `~/.harness-ai-kit/config.yaml`. CI may provide an
explicit config path with `HARNESS_AI_KIT_INTEGRATION_CONFIG`; it must never
print credential values. For an internal HTTP-only endpoint, set
`HARNESS_AI_KIT_INTEGRATION_ALLOW_HTTP=1`; for a private CA, set
`HARNESS_AI_KIT_INTEGRATION_CA_BUNDLE=<path-to-ca.pem>`. Use
`HARNESS_AI_KIT_INTEGRATION_ACTION=publish` only when the configured role is at
least `contributor` and publish credentials are present. A missing endpoint,
role, credential, or TLS trust chain is a **blocked integration**, not a
combination-test warning or a reason to weaken an assertion. The configured
`offline` value must be `false`; the CLI has no online bypass flag.

If the external preconditions are absent, run the default suite and report the
integration boundary as blocked; do not weaken an integration assertion or
convert a failed remote check into a warning. This prevents historical full
combination runs from failing because of registry availability, role policy,
or network certificate state while preserving a reproducible real-system gate.

The generated assets inherit these defaults from `skills/_template`,
`plugins/_template`, `mcps/_template`, and the `harness-ai-kit create` commands.
