# Escalation Boundary

This Skill may prepare repository changes and explain prerequisites. It must
escalate platform-owned work rather than attempting it with guessed settings.

## Escalate When

- A runner image, plugin, permission, or network route is missing.
- A repository requires a secret, signing key, registry credential, or provider
  environment approval that has not been confirmed.
- The deployment target, rollback procedure, or responsible operator is
  unknown.
- A requested action changes shared CI infrastructure, organization policy, or
  production access.

## Escalation Format

```yaml
escalation:
  type: infra-blocked | needs-review | security-sensitive
  summary: "What cannot be completed from repository scope"
  impact: "Which CI/CD stage remains blocked"
  required_owner: "CI platform administrator | application operator | security reviewer"
  suggested_action: "Concrete, reversible next action"
  urgency: low | medium | high | critical
```

## Completion Boundary

A successful YAML parse or workflow configuration review is not a deployment
acceptance result. A completed rollout requires the provider run, published
artifact, target environment, and service contract to be verified separately.
