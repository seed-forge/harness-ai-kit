# Install

## Local development

```bash
pip install -e .
```

## Verify

```bash
difyctl --help
difyctl doctor
difyctl provider --help
difyctl studio browser-doctor
```

## Runtime configuration

Minimum recommended setup:

- set `DIFY_BASE_URL`
- set `DIFY_STUDIO_USERNAME`
- set `DIFY_STUDIO_PASSWORD`
- initialize `workspace_dir` with `difyctl config init --base-url ... --workspace-dir ...`

On Windows PowerShell, persistent user-scoped examples:

```powershell
setx DIFY_BASE_URL "https://dify.example.com"
setx DIFY_STUDIO_USERNAME "you@example.com"
setx DIFY_STUDIO_PASSWORD "your-password"
```

Open a new terminal after `setx`.

If `workspace_dir` points at a project with a nearby `.env`, `difyctl` can also auto-discover:

- `DIFY_BASE_URL`
- `DIFY_API_KEY`
- `DIFY_APP_API_KEY`

## Browser automation notes

- `studio import-dsl-run` prefers system Edge or Chrome before falling back to Playwright Chromium.
- Provide Studio credentials through `DIFY_STUDIO_USERNAME` and `DIFY_STUDIO_PASSWORD`.
- Successful DSL import returns the created app workflow URL.
- `studio create-empty-run` currently supports `workflow` and `chatflow`.
- `studio export-dsl-run` exports from the `/apps` card menu and is best used against apps that already have an exportable saved DSL.
- `studio duplicate-run` duplicates from the `/apps` card menu and returns the new app workflow URL plus `app_id`.
- `studio edit-info-run` updates app name, description, and max active requests from the `/apps` card menu, then syncs the local tracked metadata.

## Planned harness-ai-kit consumption

Once published to the team registry:

```bash
harness-ai-kit install cli difyctl
harness-ai-kit install skill infra-dify-ops --runtime codex --scope project
```
