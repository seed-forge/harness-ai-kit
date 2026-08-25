# Changelog

## 0.10.5 - 2026-08-25

- Public release metadata now uses the `public` namespace and `seedforge` owner; the portable CI/CD references are complete for an OSS installation.

## 0.10.4 - 2026-08-25

- Resolve the public Skill from `public-registry`; do not require the private
  team registry in a public installation.

## 0.10.3 - 2026-08-25

- First public staging version of the CI/CD onboarding workflow.
- Replaced organization-specific CI topology, repository access, shared-library,
  and operator dependencies with provider-neutral, configurable guidance.
- Removed embedded platform endpoint and credential assumptions. CI credentials
  now belong exclusively in the chosen provider's secret store.

## 0.10.2 - 2026-08-20

- Private-source portability preparation. The public version is derived from a
  reviewed subset and does not include private topology or operational data.
