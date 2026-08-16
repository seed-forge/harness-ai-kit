# Changelog

## [0.15.0] - 2026-08-12

### Added
- **新 `plugin` 命令组：tool 插件（builtin tool provider）授权配置管理**，覆盖 MCP SSE 等插件的服务器/凭据配置场景：
  - `plugin list [--type builtin]`：列出已装 tool provider 与授权状态。
  - `plugin tools --provider <p>`：列出 provider 暴露的工具（MCP SSE 为已发现的 MCP server 工具）。
  - `plugin auth-info --provider <p>`：查看凭据条目（secret 值递归打码，含 servers_config 嵌套 JSON 内的 key）。
  - `plugin auth-set --provider <p> --credentials/--credentials-file [--name] [--type api-key] [--credential-id] [--dry-run]`：新增或更新凭据（contributor；--dry-run 输出打码载荷不实际调用）。
  - `plugin auth-remove --provider <p> --credential-id <id> [--dry-run]`：删除凭据（maintainer）。
  - Console API 路由对照 Dify CE 1.16.1 `tool_providers.py` 核实（tool-providers / builtin add/update/delete/credentials/tools/info）。
- 7 个新测试（148 total）。

### Fixed
- `difyctl/__init__.py` 版本号漂移修正（0.13.1 → 与 pyproject 对齐）。

## [0.14.0] - 2026-08-06

### Added
- **`build_llm_node` now defaults to retry + error handling**: every LLM node scaffolded by `difyctl workflow-create scaffold` includes `retry_config` (`{retry_enabled: true, max_retries: 3, retry_interval: 1000}`) and `error_strategy` (`{type: default_value, default_value: ""}`). Transient model failures (429/5xx/timeout) auto-retry 3 times; if all retries fail, the node outputs a fallback value so downstream nodes continue instead of crashing the workflow.
  - Pass `retry_config=None` to disable auto-retry (debug only).
  - Pass `error_strategy=None` to disable fallback (workflow will abort on error).
  - newapi proxy-level retry + channel fallback remains the first safety net; Dify-side retry is the second layer for model-response-level errors.

### Changed
- `dsl validate`: LLM nodes missing `retry_config` or `error_strategy` now emit a warning prompting manual addition.

## [0.13.1] - 2026-08-03

### Docs
- README `config init` 示例修正：`--workspace-dir` 指向实际的 dify 资源目录 `./fleet-platform/resources/dify`。

## [0.13.0] - 2026-08-01

### Added
- **`workflow-create scaffold` now supports `tool` step type** (`build_tool_node`) — scaffold builtin-tool nodes (SearXNG/Firecrawl/Tavily web search etc.) into a workflow DSL. Runtime inputs → `tool_parameters` (wrapped `{type,value}`); static knobs → `tool_configurations` (raw).
- **Cross-node reference remapping**: spec steps can reference each other (and `start`) by stable spec-id in `{{#id.field#}}` mixed strings and `value_selector`/`variable_selector` heads; the scaffold rewrites them to generated node-ids. Enables multi-node data flow (e.g. two-stage `tool → template → tool → llm`).
- +2 tests (140 total). Verified end-to-end: scaffolding the shipped `deep-research-websearch` spec → import → run green (73s, cited source).

## [0.12.2] - 2026-08-01

### Changed
- Default HTTP `timeout_seconds` **20 → 120** (config.defaults.yaml + code fallbacks). Long chains (SearXNG search → Firecrawl scrape → LLM) take 50-65s and were timing out on 20s; 120s is a safer default. Per-run override still available via `app run --timeout`.

## [0.12.1] - 2026-08-01

### Added
- `app run --timeout <seconds>`: override the per-run HTTP timeout (0 = config default). Needed for long chains (e.g. SearXNG search → Firecrawl full-page scrape → LLM), which can take 50-65s and previously timed out on the 20s default. Verified: two-stage deep-research workflow green via `app run --timeout 150` (56s). +1 test (138 total).

## [0.12.0] - 2026-08-01

### Added (Phase 3: polish + closes the deferred add-doc gap)

- **`dataset add-doc`**: add a text document to a knowledge base via the `/v1` dataset API, auto-resolving a dataset service key from Console (or `--dataset-key`). Closes the 0.10.0-deferred RAG ingestion gap. `--text` or `--file`.
- **`app annotations`**: list an app's annotations (Q&A cache) via Console API.
- **Global `--quiet` / `--verbose`**: `--quiet` suppresses human error/warning lines on stderr (stdout JSON never affected); `--verbose` emits request tracing.
- **`app run --stream` live output**: SSE answer chunks now print to stderr as they arrive (`post_sse(on_chunk=...)`), while stdout still returns the aggregated JSON.
- **`dataset list --name`**: case-insensitive name substring filter.
- **Pagination determinism**: `_list_all_apps`/`_list_all_datasets` sort collected results by `created_at` then `id`.

### Testing
- **Integration test**: `ConsoleApiClient` exercised over real HTTP against a localhost mock server (JSON parse + non-JSON 404 safety).
- 137 total tests.

### Verified (real instance)
- `dataset add-doc` full cycle: create → add-doc (doc_id + batch) → documents=1 → delete, all green.
- `app annotations` → 200; `dataset list --name 营销` → 12 filtered; streaming on_chunk unit-verified.

## [0.11.0] - 2026-07-30

### Added (Phase 2: author & operator closed loop)

- **`dsl lint --dsl <file> [--strict]`**: local static analysis — hardcoded-secret scan (security, → error), dangling `{{#node.field#}}` variable references, empty model refs on LLM-type nodes. No network.
- **`dsl retarget --dsl <file> --provider --model [--mode] [--output]`**: rewrite the model provider+name across all LLM/agent nodes + `model_config` (bulk model rebind; formerly a throwaway script).
- **`dsl apply --dir <dir> [--publish] [--dry-run]`**: declarative GitOps sync — for each DSL, create if the name is new, update-in-place if exactly one live match, skip if ambiguous. Idempotent.
- **`app delete --yes`**: destructive delete now requires explicit `--yes` (previously deleted immediately); stdout stays pure JSON when blocked.
- **Transient-error retry**: `ConsoleApiClient` retries safely — GET on any transient (5xx/network), any method on 429/503 (load-shedding); never retries writes on ambiguous 5xx (avoids double create/update).

### Deferred
- `dataset add-doc` (document ingestion): the Console `documents` endpoint requires a complex `data_source.info_list` schema (upload-file flow) or a separate text shape — proper modeling deferred to a focused follow-up rather than a rushed guess. List/show/documents/create/delete remain available (0.10.0).

### Verified (real instance)
- lint on article-write DSL → clean (7 nodes); retarget → 3 models rebound to ollama; `apply --dry-run` → correctly plans `would-update 5d86526f`; `app delete` without `--yes` → blocked.
- 9 new tests; 132 total.

## [0.10.0] - 2026-07-30

### Added (Phase 1: knowledge bases + backup + output hygiene)

- **`dataset` command group** (knowledge bases via Console API): `list` (paginated all pages), `show`, `documents`, `create` (`--indexing-technique high_quality|economy`), `delete` (guarded by `--yes`). Closes the RAG knowledge-base management gap.
- **`dsl export --all --output-dir <dir>`**: full backup — exports EVERY live app's DSL to `<app-id>.dify.yml` (disaster recovery). Verified 218/218 on the live instance.
- **Output hygiene**: all human error/warning text now routed to **stderr** via `eprint`; **stdout stays pure JSON** so scripts can consume it cleanly (previously 75 error paths polluted stdout).
- **Robustness**: `console_api._safe_json` — `_parse_response`/`_parse_error` no longer crash on non-JSON (e.g. HTML 404) bodies.

### Verified (real instance)
- `dataset list` → 21 KBs; create→delete cycle → 204; `delete` without `--yes` blocked with pure-JSON stdout.
- `dsl export --all` → 218/218 apps backed up, 0 failed.
- 5 new tests; 124 total.

## [0.9.0] - 2026-07-30

### Added (lifecycle completeness: progressive + long-term use)

**Progressive use (iterate on an existing app):**
- **`dsl import --app-id <id>` = update-in-place**: imports INTO an existing app (Dify `imports` + `app_id`), replacing its draft with **no duplicate**. Fixes the blocker where 0.8.1's dedup guard left no update path (e.g. `article-write`).
- **`dsl import --update-if-exists`**: if exactly one live app shares the DSL's name, update it; if none, create; if several, error with the candidate ids.
- **`dsl diff --app-id <id> --dsl <file>`**: unified diff of a local DSL vs the live app's exported DSL (normalized, sorted-key) — preview an update before pushing.
- Dedup block message now names the exits: `--app-id <id>` / `--update-if-exists` / `--allow-duplicate`.

**Long-term use (fleet governance):**
- **`registry sync [--dry-run] [--status]`**: backfill the ledger from live apps — upsert every untracked live app (resource_id derived, collisions suffixed).
- **`registry prune-duplicates [--keep newest|oldest] [--apply]`**: plan (default dry-run) or apply cleanup of duplicate-name apps, keeping one per name; `--apply` deletes surplus + marks ledger deprecated.
- **Pagination**: audit/sync/prune/dedup now page through ALL apps (`_list_all_apps`) instead of the first 100 — verified against a 218-app instance.

### Verified (real instance)
- Update-in-place GREEN: export→`import --app-id` on `article-write` returned completed with the SAME app_id, no duplicate.
- `dsl diff` identical/changed both correct; `registry sync --dry-run` (16 tracked, 85+ untracked); `prune-duplicates` dry-run plans surplus deletions; audit paginated to 218 live apps.
- 6 new tests; 119 total.

## [0.8.1] - 2026-07-30

### Added (import dedup guard)

- **`dsl import` pre-flight dedup**: before creating a new app, checks live apps for a matching `app.name`; **blocks** the import (exit 1, no app created) if a duplicate exists, listing the existing app_id(s). Bypass with `--allow-duplicate`. Fails open (proceeds with a warning) if the live listing is unreachable. Fixes the root cause of duplicate workflows (previously every import created a new app unconditionally).
- **`registry audit` now reports `duplicate_names`**: groups live apps sharing a display name (e.g. surfaced `novel-pre` ×8, `Video Editorial Brain v2` ×2, `Sales Intake` ×2 on the live instance).
- `registry_ops.find_live_apps_by_name` helper.

### Verified (real instance)
- `app upload` re-verified GREEN (status 201, real file_id) after the server-side storage fix.
- Dedup guard live: re-importing an existing name ("Ledger Loop Smoke") is now blocked with the existing app_id; `registry audit` lists the 3 duplicate-name groups.
- 4 new tests (duplicate detection + find_by_name + import block + --allow-duplicate bypass); 113 total.

## [0.8.0] - 2026-07-30

### Added (full /v1 runtime coverage)

- **12 new `app` runtime subcommands** (all app-* service-token, mode-agnostic):
  `run-status` (`GET /v1/workflows/run/{id}`) · `stop` (`POST /v1/workflows/tasks/{id}/stop`) · `upload` (`POST /v1/files/upload`) · `logs` (`GET /v1/workflows/logs`) · `conversations` · `messages` · `conversation-rename` · `conversation-delete` · `feedback` (`POST /v1/messages/{id}/feedbacks`) · `suggested` · `audio-to-text` · `text-to-audio`.
- **`app run --stream`**: force streaming (`post_sse` aggregation) for chat/completion; agent-chat already auto-streams.
- api_client: `request_v1` (generic GET/POST/DELETE JSON), `post_multipart` (RFC7578 file upload), `post_binary` (save audio) — no third-party deps.
- Discoverability: `workflow-create` help now points to `app run` for runtime execution.

### Verified (real instance)
- Green: `logs` (total=2), `conversations` (2), `messages` (1), `feedback` (`{result:success}`); `run-status`/`suggested` route correctly (404 bogus / 400 app-disabled).
- `upload` returns server 500 on this instance — reproduced identically with the `requests` library, confirming a Dify-side storage issue, not a CLI defect (multipart is byte-correct).
- 5 new tests (12-command routing + multipart + binary + --stream + encoder); 110 total.

## [0.7.1] - 2026-07-30

### Fixed (agent-chat streaming — required for "agent" app coverage)

- **agent-chat apps only support streaming** (Dify rejects blocking with `Agent Chat App does not support blocking mode`). `app run` / import-smoke now route agent-chat through **`post_sse`** (new): sends `response_mode: streaming`, reads the SSE `data:` events, and aggregates `agent_message`/`message` answer chunks into `{answer, conversation_id, message_id, events}`. Other types (workflow/chat/advanced-chat/completion) keep blocking.
- `_cmd_app_run` now delegates to the shared `_run_app_core` (single routing source) so `app run` and `dsl import --smoke` behave identically across all app types.

### Verified (real instance)
- **workflow**: no-LLM echo → `succeeded`, outputs `{echo: ...}` (green, model-independent).
- **advanced-chat/chat**: real model answer via `/v1/chat-messages` (green).
- **agent-chat**: streaming路由/SSE 解析已通 (reaches model layer; green blocked only by app-side model 402/config, external).
- **registry audit**: correctly classified live(100)/ledger(5)/zombie(1)/unregistered.
- 2 new tests (post_sse aggregation + agent streaming routing); 105 total.

## [0.7.0] - 2026-07-30

### Added (app service-key + run + fleet ops)

- **`app keys list/create/delete`**：经 Console API `/console/api/apps/{id}/api-keys` 管理 service token。`create` 完整 `app-*` token 仅一次性打印 + 写入 `config.yaml assets.difyctl.app_keys`（app_id→token 映射，本地明文非 Git），ledger 只存 masked 元数据 `service_key:{key_id,prefix,created_at}`。
- **`app run`（全类型 mode-aware）**：按 app mode 路由 `/v1/workflows/run`(workflow) · `/v1/chat-messages`(chat/agent-chat/chatflow) · `/v1/completion-messages`(completion)；mode 解析 `--mode>ledger>默认 workflow`；key 解析 `--app-key>app_keys[app_id]>app_api_key`；支持 `--inputs(@file|json)/--query/--user/--conversation-id`。
- **`app delete`/`app rename`**：Console API 删除（+ ledger status→deprecated + 清 config key）/ 改名（GET→merge→PUT 保留 icon 字段 + 同步 ledger title/app_name）。
- **`app publish`**：发布 app 草稿 workflow（`/console/api/apps/{id}/workflows/publish`）——workflow/chatflow 应用在 `/v1` 调用前必须发布；`dsl import --smoke` 会自动先发布再冒烟。
- **`registry audit`**：live apps（apps_list）vs ledger 比对，报告僵尸条目 / 未登记 app / 名称漂移。
- **`dsl import --create-key/--smoke`（opt-in）**：导入成功后可自动建 key（存 config + ledger masked）+ 冒烟调用；结果 masked 折入返回 JSON。
- config：`app_keys`(map, sensitive) schema + `write_unified_app_key`/`forget_unified_app_key`/`resolve_app_key`；api_client 增 `post_json`（/v1 Bearer POST）。

### Security
- 完整 service token 只进本地 config.yaml + `app keys create` 一次性 stdout；ledger/其余输出一律掩码。回归单测断言 import 输出不含完整 token。

### Notes
- 新增 21 个单测（P1 端点/P2 config/P3 keys/P4 run 全类型/P5 import 闭环/P6 audit+lifecycle），共 103 全绿。

## [0.6.0] - 2026-07-30

### Added (ledger unification + naming governance)

- **O1 单一台账真源**：`registry`/`resource` 命令改为读写 `ledger.yaml`（v2 schema），写回**合并保留顶层元数据**（version/ledger_type/runtime_system/maintainer）；`resources.yml` 降为只读回退（首次写入自动迁移到 ledger.yaml + 告警）。`registry init` 幂等（不再覆盖已有台账）。
- **upsert 合并语义修复**：既有条目 upsert 由「整体替换」改为「合并」，不再丢失未传入的字段（如 dsl_version/status）。
- **C3 resource_id 校验**：`validate_resource_id()`（`^[a-z][a-z0-9]*(-[a-z0-9]+)*$`，3–50），在 `resource init`/`registry upsert` 硬校验；错误信息自包含正则 + 指向 fleet-platform 命名规范。
- **O2 dsl_path 标准化**：统一为文件形式 `resources/<id>/dsl/current.yml`（`canonical_dsl_path`）。
- **U5 import→台账闭环**：`dsl import` 成功后默认自动 `ensure_resource` + 归档 DSL（current + snapshot）+ upsert ledger；新增 `--resource-id`（缺省从 DSL app.name 派生并校验）与 `--no-register`；返回 JSON 增 `registered`/`register_error`。

### Notes
- 命名规范权威真源：`fleet-platform/resources/dify/README.md`「资源命名规范」；SKILL 与 CLI 仅引用/内置正则。
- 新增 10 个单测（C3/O1/O2/U5），共 88 个全绿。

## [0.5.7] - 2026-07-29

### Docs

- README "Browser automation": rewrote to reflect config-first credentials, headless-by-default, `console_key` auto-save/auto-refresh lifecycle, and added a **Linux / headless server setup** section (`playwright install chromium` + `install-deps`, `--no-sandbox` note).
- USAGE.md: fixed stale title (`dify-resource-ops` → `difyctl`), config-first inputs, and added a **Linux / headless fast path** with copy-paste setup + opt-out flags (`--headed`, `--no-save-console-key`, `--no-auto-refresh`).

## [0.5.6] - 2026-07-29

### Changed (headless / Linux robustness)

- **Login is headless by default** (already was): `provider login` and the console_key auto-refresh both launch Chromium headless — no window pops up, no interference with the user's desktop. Use `--headed` on `provider login` only for debugging.
- **Linux/container hardening**: on Linux the browser now launches with `--no-sandbox` and `--disable-dev-shm-usage` (bundled Chromium otherwise fails as root / in containers), and Playwright's bundled `chromium` is tried first (Edge/Chrome channels are rarely installed on servers). Windows/macOS behavior unchanged (system channels first, no extra args).
- 3 new tests: Linux prefers chromium + no-sandbox, Windows keeps channel-first with no extra args, `_launch_browser` forwards headless + args (78 tests total).

## [0.5.5] - 2026-07-29

### Added (console_key lifecycle)

- **`provider login` now auto-writes the captured cookie to `assets.difyctl.console_key`** in `~/.harness-ai-kit/config.yaml` (merge-preserving all other keys/assets). Subsequent commands work with no `--console-key` flag and no env vars. Opt out with `--no-save-console-key`.
- **Auto-refresh on expiry**: before any Console API call, an expired stored cookie is detected (JWT `exp` claim) and a silent re-login (via `studio_username`/`studio_password` from config.yaml) recaptures + rewrites `console_key`. Opt out globally with `--no-auto-refresh`; explicit `--console-key` is never auto-refreshed.
- config.py: `write_unified_config_value()` (merge-preserving writeback), `cookie_expired()` (JWT exp parse, safe-false on non-JWT/malformed), `unified_config_path()`.
- 3 new regression tests: expired→refresh+writeback, fresh→no re-login, `--no-auto-refresh`→skip (75 tests total).

### Fixed

- cli.py: added missing `import sys` (an expired-cookie warning path referenced `sys.stderr`).

## [0.5.4] - 2026-07-29

### Fixed (config governance)

- **`console_key` now read from `assets.difyctl`** in `~/.harness-ai-kit/config.yaml` (source of truth), not only `--console-key` flag or profile. Priority: CLI arg > active profile > config.yaml > `DIFY_CONSOLE_KEY` env. Fixes harness-ai-kit config-governance non-compliance.
- **`provider login` seeds `studio_username`/`studio_password` from config.yaml** into the expected env vars, so login works without exporting env vars. Verified live against http://<service-url>:11181 (config-only, no env).
- **`workflow-create scaffold` reads `dsl_version` from config.yaml** with correct priority (--dsl-version > config > auto-detect > default 0.6.0); fixed a copy-paste bug that assigned dsl_version to base_url and a non-firing `isinstance(cfg, dict)` guard on AppConfig.
- config.defaults.yaml: added `console_key` (sensitive) schema entry; removed duplicate `legacy_asset_ids`.
- 2 new regression tests: console_key read from config.yaml + CLI-arg override precedence (72 tests total).

## [0.5.3] - 2026-07-29

### Fixed

- **`dsl detect-version` crash**: handler used `json.dumps` but `json` was never imported at module level → `NameError`. Switched to `print_json`. Added regression test. Verified live against http://<service-url>:11181: export-based detection reads authoritative DSL version `0.6.0` from a real app.

### Verified (end-to-end, real instance)

- Full chain proven live: DeFi 需求 → `workflow-create intake` spec → `scaffold` DSL → `dsl validate` (ok) → `dsl import --via auto` → **Console API import completed** (app created, `imported_dsl_version: 0.6.0`).

## [0.5.2] - 2026-07-29

### Fixed

- **Version drift fix**: `__init__.__version__` was left at 0.5.0 in the 0.5.1 wheel (pyproject/cli.json were 0.5.1) → `difyctl --version` mis-reported. Now all four locations (pyproject/cli.json/__init__/catalog) synced to 0.5.2.

### Changed

- **`workspace_dir` default → `fleet-platform/resources/dify`**: Dify resource ledger merged from root `dify-resources/` into `fleet-platform` (it is a resource ledger; runtime lives in Dify). Maintenance spec: `fleet-platform/resources/dify/README.md`.

## [0.5.1] - 2026-07-29

### Added (auto DSL version detection)

- **`dsl detect-version` command**: Runtime probing of real Dify instance via `/console/api/version` or app export to read true DSL version (authoritative over hard-coded defaults)
- **`workflow-create scaffold --dsl-version auto`**: Auto-detect + save to config → future scaffolds inherit detected version
- **config.yaml `dsl_version` field** for team-wide default; workflow_create.py accepts `dsl_version="auto"` param
- Version validation relaxes unknown-but-valid semver versions to warnings instead of errors (so detected versions pass)
- New test suite: 7 additional tests for version detection paths (export-based authoritative / product-version heuristics)
- Migration plan documented (`docs/dify-resources-to-fleetplatform-migration-plan.md`)

### Changed

- `build_app_dsl.py` removes hard-coded `SUPPORTED_VERSIONS` list; validates semver format only
- Default scaffold DSL version remains 0.6.0 for backward compatibility until first auto-detect run

## [0.5.0] - 2026-07-29

### Changed (BREAKING-soft)

- CLI renamed from `difyresctl` → `difyctl`: package name, entry commands, config section (`assets.difyctl`) all switched; keeps `difyresctl` deprecated shim (prints deprecation warning then forwards), `assets.difyresctl` config section reads auto-fallback during migration period
- `workflow-create scaffold` output upgraded to **import-ready DSL** (`app`/`kind: app`/`version: "0.6.0"`/`workflow.features`/完整 graph node wrapper + position + edges), can directly import via API or Studio, no longer a skeleton for manual reference only

### Added

- **`dsl import --dsl <file> [--via auto|api|browser]`**: Dual-track DSL import. API path uses `POST /console/api/apps/imports` (yaml-content mode, pending auto-confirm); 5xx/network errors auto-fallback to Playwright; 4xx config errors directly report without fallback
- **`dsl export --app-id <id> [--output <file>]`**: Export DSL via Console API `GET /console/api/apps/{id}/export`
- **`dsl validate <file> [--target-version]`**: In-house validator covers version/kind/mode, graph endpoints & reachability, cycle detection, edge references, LLM required fields (model/prompt_template/context), code outputs declaration + `error` reserved name, variable-ref syntax, if-else branch handles (dimensions reference yzmw123/dify-workflow-dsl-skill, implementation self-developed)
- **spec v2** (`version: 2`): step supports `llm/code/http-request/if-else/template-transform` node types, step-level model override + outputs declaration; v1 spec continues to be supported
- Node templates + layout algorithm adapted from MIT-licensed yoloyolo8/dify-workflow-writer & LingyiChen-AI/workflow-skill


## [0.4.2] - 2026-07-29

### Fixed / Governance

- **配置真源统一到 `~/.harness-ai-kit/config.yaml`**：`_resolve_runtime_config` 改为经 `get_config()`（unified asset config loader）以 config.yaml `assets.difyresctl` 为真源解析 base_url/app_api_key/workspace_dir/timeout，legacy `~/.difyresctl/config.json` 仅作 profiles fallback。修复此前所有命令只读独立 dotfile、违反 config-governance「禁止 ~/<dotdir>/ 独立配置目录」的问题。
- **填充 config.defaults.yaml schema**（此前为空 `config: []`）：声明 base_url/studio_username/studio_password/app_api_key/workspace_dir/timeout_seconds，含 sensitivity 标注；studio 登录凭据改由 config.yaml 提供（取代 DIFY_STUDIO_USERNAME/PASSWORD 环境变量）。
- 修 `__init__.__version__` 版本漂移（0.4.0 → 与 pyproject/cli.json 对齐 0.4.2）。

## [0.4.1] - 2026-07-28

### Fixed

- **`ConsoleApiClient.post()` dropped the request path** (`self._request("POST", body)`), which broke `provider_add_model`, `provider_validate_model`, and any POST-based provider operation. Now forwards `(method, path, body)` correctly.

### Added

- **`provider models --provider <p>`**: query the configured model ledger for a provider (the "台账" view) so the current model inventory is always visible.
- **`provider add-model`**: add a single custom model with credentials to a customizable-model provider (e.g. `openai_api_compatible`), with `--dry-run` payload preview that needs no console session.

## [0.4.0] - 2026-07-26

### Added

- Dify 资源治理场景 RBAC：按语义分层——remove=maintainer；登记/创建/导入类=contributor；读开放

