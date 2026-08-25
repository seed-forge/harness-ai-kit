---
name: devlab-cicd-onboard
description: Provider-neutral CI/CD onboarding workflow for repository analysis, pipeline design, configuration boundaries, and release verification.
---

# DevLab CI/CD Onboard

## Purpose

Use this Skill to introduce or evolve CI/CD in an application repository. It
turns repository facts into a provider-neutral plan, then produces reviewed
workflow and configuration changes for GitHub Actions, Jenkins, Woodpecker, or
another established CI platform.

It is an engineering workflow, not a platform-administration runbook. It does
not create accounts, change global CI settings, install plugins, or access
credentials.

## Inputs

- Repository path or source archive.
- Requested outcome: CI only, deployment pipeline, an environment change, or a
  migration between CI providers.
- Optional target environments and the CI provider already used by the team.

## Outputs

- A short repository and delivery-path assessment.
- A reviewed pipeline design and project-local configuration template.
- Workflow files or a patch when the repository has enough confirmed context.
- A structured escalation when a CI platform, secret, runner, or deployment
  prerequisite needs an operator.

## Workflow

1. Inspect the repository before selecting a provider: language, package
   manager, tests, build output, containerization, deployment target, and any
   existing CI files.
2. Select the smallest provider-compatible path. Preserve an existing working
   provider unless the request explicitly asks for migration. For a new public
   repository, GitHub Actions is the default recommendation.
3. Separate configuration by ownership:
   - versioned repository configuration contains only non-secret, portable
     values and placeholders;
   - CI secret stores hold tokens, SSH keys, registry credentials, and private
     endpoints;
   - platform-wide runners, plugins, credentials, and permissions remain
     operator-owned.
4. Produce a pipeline with explicit stages: dependency install, deterministic
   tests, build, artifact publication, optional deployment, and verification.
   A deployment must not happen until its target, credential reference, and
   rollback path are confirmed.
5. Offer quality gates as explicit, opt-in steps. Keep pull-request checks
   fast; prove each enabled gate with one intentional failure and one success.
6. Validate the generated YAML and scripts locally where possible. Then verify
   the provider run, artifact availability, and the deployed service contract
   separately.
7. Return an escalation instead of guessing when a required secret, runner
   capability, DNS rule, network path, approval, or deployment target is
   unknown.

## Configuration Boundary

The Skill has no required global credentials. Store provider API settings in
the provider's secret manager when an automation actually needs them. Keep
project-specific, non-secret deployment settings in a reviewed file such as
`.platform/jenkins.yml` or an equivalent provider-native configuration file.

### Runtime dependencies

The bundled Jenkins-style validator runs in the target repository's Python
virtual environment and requires `PyYAML`. The documented `--schema` path also
requires `jsonschema`:

```bash
python -m pip install "PyYAML>=6.0" "jsonschema>=4.18"
```

The selected CI provider remains an external prerequisite. Its runner image,
plugins, permissions, secret store, network access, and deployment tools are
owned and configured by the repository or platform operator; they are not
installed with this Skill.

Use the bundled `scripts/validate-jenkins-yml.py` only for the documented
Jenkins-style project configuration. It validates structure; it does not prove
that a remote host, credential, or CI service is reachable.

## References

- [Route table](REFERENCE-ROUTE-TABLE.md): provider and deployment selection.
- [Escalation boundary](REFERENCE-ESCALATION-BOUNDARY.md): operator hand-off.
- [Portable CI/CD patterns](references/REFERENCE-README.md):
  provider-neutral templates and acceptance rules.
- [Portable CI/CD patterns detail](references/REFERENCE-PORTABLE-CICD-PATTERNS.md)
- [Configuration schema](references/jenkins-yml-schema.json): optional
  Jenkins-style project configuration validation.

## Constraints

- Never place credentials, private URLs, hostnames, or customer values in a
  tracked workflow, script, fixture, or example.
- Do not enable deployments, destructive cleanup, or production changes by
  default.
- Do not treat a green configuration check as deployment acceptance. Verify
  the actual artifact and service contract.
- Use a platform's native secret and approval mechanisms; do not invent a
  second credential store in the repository.
- Keep generated pipeline commands aligned with the repository's documented
  local install and build commands.

## Human Decisions

| Decision | When it is required | Default |
| --- | --- | --- |
| Deployment target and approval path | Before a deploy-capable workflow is enabled | Ask and block deployment until confirmed |
| Quality-gate thresholds | Before a new gate can block delivery | Start with a reviewed, fast check |
| Provider migration | When an existing CI system is replaced | Preserve the existing provider unless explicitly requested |
