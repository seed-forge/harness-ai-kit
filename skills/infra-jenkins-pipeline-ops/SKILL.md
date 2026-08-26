---
name: infra-jenkins-pipeline-ops
description: Operate Jenkins jobs, credentials, plugins and shared libraries through a portable, configuration-driven workflow.
---

# Jenkins Pipeline Operations

## Purpose

Use this Skill to inspect or operate a Jenkins instance, review a Jenkinsfile,
or diagnose a Jenkins Pipeline. It works with self-hosted and managed Jenkins
deployments and does not assume a particular network, container host, registry
or source-control server.

## Required Configuration

Configure the companion CLI in `~/.harness-ai-kit/config.yaml`:

```yaml
assets:
  jenkinsctl:
    jenkins_url: https://jenkins.example.com/
    jenkins_user: automation-user
    jenkins_api_token: <store-outside-source-control>
```

The checked-in `config.defaults.yaml` defines the complete schema. Command-line
values override the global configuration. Environment variables are CI-only
fallbacks; do not put tokens in a repository or an agent instruction file.

## Workflow

1. Confirm the target Jenkins URL, intended action and whether it changes
   shared platform state.
2. Run `jenkinsctl doctor` and use read-only job/configuration commands first.
3. Export the current job configuration before an update, disable or delete.
4. Keep credentials in the Jenkins credential store and reference their IDs;
   never put credential material in a Jenkinsfile.
5. After a write, read the relevant job/configuration back and report the
   effective result.

## Guardrails

- Prefer the REST API or `jenkins-cli.jar`; use SSH CLI only when explicitly
  configured by the operator.
- Treat job deletion, credential changes, plugin changes and global tool or
  shared-library configuration as high-impact operations.
- `jenkinsctl` applies role checks from `~/.harness-ai-kit/config.yaml`.
  Read-only commands are available to consumers; daily delivery actions need
  contributor access; shared platform and credential changes need maintainer
  access.
- Use generic service URLs and documentation IP ranges in examples. Do not
  copy hostnames, private addresses, tokens, credentials or deployment
  topology into public material.
