# harness-ai-kit

Package manager for AI agent assets (skills / CLIs / MCPs / plugins / loops).

Install skills from any GitHub repository into Codex, Claude Code, Cursor, Kiro
or **DeepSeek Harness (dsh)** with dependency resolution, lockfiles, checksums and
rollback.

## First-class dsh runtime

- `harness-ai-kit install skill <id> --runtime dsh --scope project`
  installs into `.agents/skills` (dsh rank 200 native scan, zero config).
- `harness-ai-kit install skill <id> --runtime dsh --scope global`
  installs into `~/.agents/skills` (dsh rank 500 native scan).
- `harness-ai-kit doctor dsh` checks the dsh baseline (`@deepseek-ai/dsh@0.1.0-rc.6`,
  pnpm >=10, `DSH_HOME`, profile dirs).
- `harness-ai-kit install plugin harness-ai-kit-plugin --profile web` installs the
  bundled dsh plugin (session tools + virtual skill provider; zero workspace
  bloat).

See [docs/dsh-integration.md](./docs/dsh-integration.md) for the full integration
model.

## Deterministic test boundary

Asset authoring and test policy is bundled in
`docs/asset-authoring-contract.md`. Unit and combination tests are offline and
use temporary fixtures/mocked transports. Real registry, Nexus, TLS, credential
and role-bound publishing checks belong to an explicit integration run:

```powershell
$env:HARNESS_AI_KIT_INTEGRATION = "1"
python -m pytest -q --run-integration -m integration
```

The default test command must remain reproducible without external services:

```powershell
python -m pytest -q
```

- Repository: https://github.com/seed-forge/harness-ai-kit
- License: Apache-2.0

```bash
pip install --upgrade harness-ai-kit==0.18.2
harness-ai-kit init
harness-ai-kit add skill https://github.com/OWNER/REPO/tree/main/path/to/skill
harness-ai-kit sync
```
