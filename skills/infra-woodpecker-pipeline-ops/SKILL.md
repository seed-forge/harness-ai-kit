---
name: infra-woodpecker-pipeline-ops
description: Design, inspect and operate portable Woodpecker CI pipelines with explicit repository and deployment boundaries.
---

# Woodpecker Pipeline Operations

## Purpose

Use this Skill to inspect Woodpecker repositories and builds, design a
portable CI pipeline, or diagnose build failures. It does not assume a
specific Git host, container registry, image repository, internal platform or
deployment topology.

## Required Configuration

Configure the companion CLI in `~/.harness-ai-kit/config.yaml`:

```yaml
assets:
  woodpeckerctl:
    woodpecker_url: https://ci.example.com/
    woodpecker_token: <store-outside-source-control>
```

The checked-in `config.defaults.yaml` is the configuration contract. Use
command-line values for a one-off action and environment variables only as CI
fallbacks. Do not create a separate `~/.woodpeckerctl` source of truth.

## Workflow

1. Identify repository purpose before changing a pipeline: build-only images,
   libraries and deployed applications have different delivery boundaries.
2. Use `woodpeckerctl doctor`, repository inspection and build logs before
   modifying configuration.
3. Keep platform credentials in Woodpecker secrets and use secret references
   in pipeline definitions; never write registry credentials or tokens into a
   repository.
4. Keep build integration separate from deployment configuration. Enable a
   deployment only when its target, approval path and rollback are explicit.
5. Trigger or observe a build, inspect logs and report the resulting artifact
   coordinates without exposing secret values.

## Guardrails

- Treat repository activation, secret management and trusted-build changes as
  operator-controlled actions.
- Build and log queries are read-only. Writes must respect the configured
  role and the target platform's access controls.
- Use public placeholders in examples. Private registry addresses, hostnames,
  user names, repository names and release evidence never enter the public
  projection.
