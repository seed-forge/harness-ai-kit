# difyctl Usage

## When To Use
- Use this CLI when you need the installed `difyctl` command.
- It is Dify usage-layer resource operations, covering app inspection, local DSL capture, workflow creation, dual-track DSL import/export, and Studio browser automation for create/import/export/duplicate/edit flows.
- Use it when the task is a command-line lifecycle action, install, or packaging step.

## Inputs
- CLI arguments and credentials from `~/.harness-ai-kit/config.yaml` (`assets.difyctl`), with env vars as CI fallback.
- Repo root, config path, runtime, scope, or registry settings when needed.

## Output
- Command output, installed status, or generated artifacts.

## 可直接复制的中文 Prompt
### 场景 1：让 AI 帮你调用 CLI
```text
请使用 `difyctl` 这个 CLI 处理当前任务。
先确认命令参数、工作目录、环境变量和作用范围。
如果依赖没装好，先列出缺口和安装方式。
输出：可直接执行的命令、预期结果、失败时排查点。
```

## Fast Path
- Install the CLI first, then read `README.md` and `INSTALL.md` before release work.
- Open `README.md` when you need the command entrypoint details.

## Linux / headless (no X server) fast path
One-time browser setup, then fully config-driven login (headless by default, no window):

```bash
pip install difyctl playwright
playwright install chromium          # bundled Chromium (preferred on Linux)
playwright install-deps chromium     # system libs on Debian/Ubuntu (needs sudo)

# Put creds once in ~/.harness-ai-kit/config.yaml under assets.difyctl:
#   studio_username / studio_password
difyctl provider login               # headless login → console_key auto-saved to config.yaml
difyctl dsl detect-version           # reads console_key from config; auto-refreshes if expired
```

- On Linux the browser launches with `--no-sandbox` / `--disable-dev-shm-usage` and prefers bundled Chromium — works as root / in containers.
- Opt-outs: `--headed` (show window, debug), `--no-save-console-key` (don't persist cookie), `--no-auto-refresh` (don't re-login on expiry).
