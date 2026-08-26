# Portable Pipeline Review Example

Review a CI pipeline in this order:

1. Confirm the repository's build artifact and whether deployment is in scope.
2. Ensure credentials are injected through the CI platform's secret mechanism.
3. Pin build inputs and keep container image coordinates explicit.
4. Run the pipeline, inspect logs, and record only non-sensitive artifact
   coordinates and outcome.
5. Add a rollback or disable path before enabling automatic deployment.
