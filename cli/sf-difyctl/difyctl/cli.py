from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

from difyctl.api_client import get_json, post_json, post_sse, request_v1, post_multipart, post_binary
from difyctl.config import (
    AppConfig,
    cookie_expired,
    env_base_url,
    forget_unified_app_key,
    get_config,
    load_config,
    merge_config,
    normalize_base_url,
    resolve_app_key,
    resolve_config_path,
    resolve_active_profile,
    resolve_console_key,
    resolve_providers_dir,
    save_config,
    write_unified_app_key,
    write_unified_config_value,
)
from difyctl.console_api import ConsoleApiClient, ConsoleAuth, build_model_credential_payload, should_fallback
from difyctl.dsl_validate import validate_dsl
from difyctl.dsl_lint import lint_dsl, retarget_dsl
from difyctl.dsl_detect_version import detect_dsl_version
from difyctl.output import error_line, print_json, success_line, warning_line
from difyctl.provider_config import (
    build_add_payload,
    load_manifest_yaml,
    load_provider_yaml,
    resolve_env_vars,
    write_back_provider_id,
)
from difyctl.registry_ops import audit_against_live, batch_filter, canonical_dsl_path, find_live_apps_by_name, get_registry_resource, init_registry, list_registry_resources, registry_is_legacy_only, upsert_registry_resource
from difyctl.studio_browser import (
    StudioAutomationError,
    browser_doctor,
    capture_console_cookie,
    create_empty_app,
    edit_app_info_from_apps,
    duplicate_app_from_apps,
    export_dsl_from_apps,
    login_and_import_dsl,
)
from difyctl.resource_ops import capture_dsl, derive_resource_id, ensure_resource, scan_resources, summarize_dsl, validate_resource_id, workspace_root, resource_dir, read_resource
from difyctl.studio_ops import build_create_plan, build_duplicate_plan, build_export_plan
from difyctl.workflow_create import default_spec_payload, load_spec, scaffold_dsl_from_spec, validate_spec_payload, write_dsl, write_spec
from difyctl.dsl_authoring import DEFAULT_DSL_VERSION
from . import __version__


_QUIET = False


def eprint(msg, **kwargs) -> None:
    """Print human-facing errors/warnings to stderr so stdout stays pure JSON.

    Suppressed entirely under global --quiet (stdout JSON is never affected).
    """
    if _QUIET:
        return
    kwargs.setdefault("file", sys.stderr)
    print(msg, **kwargs)


APP_ENDPOINTS = {
    "info": "/v1/info",
    "parameters": "/v1/parameters",
    "meta": "/v1/meta",
}

ENV_API_KEY_NAMES = ("DIFY_API_KEY", "DIFY_APP_API_KEY")


def _safe_text(value: object) -> str:
    return str(value).strip() if value is not None else ""


def _read_simple_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        values[key] = value
    return values


def _workspace_candidate_env_files(workspace_dir: str) -> list[Path]:
    if not workspace_dir:
        return []
    root = Path(workspace_dir).expanduser().resolve()
    candidates = [
        root / ".env",
        root.parent / ".env",
        root.parent.parent / ".env",
    ]
    unique: list[Path] = []
    seen: set[str] = set()
    for item in candidates:
        key = str(item)
        if key not in seen:
            unique.append(item)
            seen.add(key)
    return unique


def _discover_project_secrets(workspace_dir: str) -> tuple[str, str, str, str]:
    for env_path in _workspace_candidate_env_files(workspace_dir):
        payload = _read_simple_env_file(env_path)
        if not payload:
            continue
        base_url = normalize_base_url(payload.get("DIFY_BASE_URL", ""))
        api_key = ""
        api_key_name = ""
        for env_name in ENV_API_KEY_NAMES:
            api_key = _safe_text(payload.get(env_name, ""))
            if api_key:
                api_key_name = env_name
                break
        if base_url or api_key:
            return base_url, api_key, str(env_path), api_key_name
    return "", "", "", ""


def _resolve_effective_remote_config(config: AppConfig) -> tuple[str, str, dict[str, str]]:
    source = {
        "base_url": "",
        "app_api_key": "",
        "project_env_path": "",
    }
    base_url = normalize_base_url(config.base_url)
    if base_url:
        source["base_url"] = "config-or-arg"
    else:
        env_url = env_base_url()
        if env_url:
            base_url = env_url
            source["base_url"] = "env:DIFY_BASE_URL"

    api_key = _safe_text(config.app_api_key)
    if api_key:
        source["app_api_key"] = "config-or-arg"
    else:
        for env_name in ENV_API_KEY_NAMES:
            env_value = _safe_text(os.environ.get(env_name, ""))
            if env_value:
                api_key = env_value
                source["app_api_key"] = f"env:{env_name}"
                break

    discovered_base_url, discovered_api_key, env_path, discovered_api_key_name = _discover_project_secrets(config.workspace_dir)
    if not base_url and discovered_base_url:
        base_url = discovered_base_url
        source["base_url"] = "project-env:DIFY_BASE_URL"
        source["project_env_path"] = env_path
    if not api_key and discovered_api_key:
        api_key = discovered_api_key
        source["app_api_key"] = f"project-env:{discovered_api_key_name or 'DIFY_API_KEY'}"
        source["project_env_path"] = env_path
    return base_url, api_key, source


def _read_current_dsl_summary(root: Path, resource_id: str) -> dict[str, object] | None:
    resource_root = resource_dir(root, resource_id)
    dsl_dir = resource_root / "dsl"
    candidates = sorted(dsl_dir.glob("current.*"))
    if not candidates:
        return None
    current_path = candidates[0]
    summary = summarize_dsl(current_path)
    summary["current_path"] = str(current_path)
    return summary


def _build_reconcile_payload(config: AppConfig, resource_id: str) -> dict[str, object]:
    root = _require_workspace(config)
    registry_entry = get_registry_resource(root, resource_id)
    if registry_entry is None:
        raise FileNotFoundError(f"Registry entry not found: {resource_id}")

    resource_root = resource_dir(root, resource_id)
    local_resource = read_resource(resource_root) if resource_root.exists() else None
    dsl_summary = _read_current_dsl_summary(root, resource_id)

    live_app: dict[str, object] | None = None
    live_error = ""
    effective_base_url, effective_app_api_key, remote_source = _resolve_effective_remote_config(config)
    if effective_base_url and effective_app_api_key:
        try:
            result = get_json(effective_base_url, effective_app_api_key, APP_ENDPOINTS["info"], config.timeout_seconds)
            if isinstance(result.payload, dict):
                live_app = result.payload
            else:
                live_error = f"Unexpected /v1/info payload type at status {result.status_code}"
        except Exception as exc:
            live_error = f"live app check failed: {exc}"
    else:
        live_error = "base_url or app_api_key is missing; skipped live app check"

    registry_app_id = _safe_text(registry_entry.get("app_id", ""))
    registry_app_name = _safe_text(registry_entry.get("app_name", ""))
    registry_title = _safe_text(registry_entry.get("title", ""))

    local_app_id = _safe_text(local_resource.app_id) if local_resource else ""
    local_app_name = _safe_text(local_resource.app_name) if local_resource else ""
    local_title = _safe_text(local_resource.title) if local_resource else ""

    live_name = _safe_text(live_app.get("name", "")) if live_app else ""
    live_description = _safe_text(live_app.get("description", "")) if live_app else ""
    live_mode = _safe_text(live_app.get("mode", "")) if live_app else ""

    current_dsl_name = _safe_text(dsl_summary.get("name", "")) if dsl_summary else ""
    current_dsl_description = _safe_text(dsl_summary.get("description", "")) if dsl_summary else ""
    current_dsl_mode = _safe_text(dsl_summary.get("mode", "")) if dsl_summary else ""

    observations: list[str] = []
    if live_app:
        if registry_app_name and live_name and registry_app_name != live_name:
            observations.append("registry app_name differs from live app name")
        if local_app_name and live_name and local_app_name != live_name:
            observations.append("resource app_name differs from live app name")
        if registry_title and live_name and registry_title != live_name:
            observations.append("registry title differs from live app name")
        if current_dsl_name and live_name and current_dsl_name != live_name:
            observations.append("current DSL name differs from live app name")
        if registry_entry.get("mode") and live_mode and _safe_text(registry_entry.get("mode")) != live_mode:
            observations.append("registry mode differs from live app mode")
        if current_dsl_mode and live_mode and current_dsl_mode != live_mode:
            observations.append("current DSL mode differs from live app mode")
    if registry_app_id and local_app_id and registry_app_id != local_app_id:
        observations.append("registry app_id differs from local resource app_id")
    if registry_app_id and not local_app_id:
        observations.append("local resource app_id is empty while registry app_id is set")
    if registry_app_name and local_app_name and registry_app_name != local_app_name:
        observations.append("registry app_name differs from local resource app_name")
    if registry_title and local_title and registry_title != local_title:
        observations.append("registry title differs from local resource title")

    return {
        "resource_id": resource_id,
        "status": "warning" if observations or live_error else "ok",
        "workspace_dir": str(root),
        "live_app_check": {
            "available": bool(live_app),
            "error": live_error,
            "base_url": effective_base_url,
            "base_url_source": remote_source["base_url"],
            "app_api_key_source": remote_source["app_api_key"],
            "project_env_path": remote_source["project_env_path"],
            "name": live_name,
            "description": live_description,
            "mode": live_mode,
        },
        "registry": registry_entry,
        "local_resource": (
            {
                "resource_id": local_resource.resource_id,
                "mode": local_resource.mode,
                "title": local_resource.title,
                "app_id": local_resource.app_id,
                "app_name": local_resource.app_name,
                "tags": list(local_resource.tags),
                "updated_at": local_resource.updated_at,
                "path": str(local_resource.path),
            }
            if local_resource
            else None
        ),
        "current_dsl": dsl_summary,
        "observations": observations,
    }


def _build_reconcile_diff_payload(payload: dict[str, object]) -> dict[str, object]:
    live_app_check = payload.get("live_app_check", {})
    live_error = ""
    if isinstance(live_app_check, dict):
        live_error = _safe_text(live_app_check.get("error", ""))
    return {
        "resource_id": payload.get("resource_id", ""),
        "status": payload.get("status", ""),
        "live_app_error": live_error,
        "observations": payload.get("observations", []),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="difyctl",
        description="Task-oriented CLI for Dify usage-layer resource operations.",
    )
    parser.add_argument("--config", help="Use this difyctl config file for the current command.")
    parser.add_argument("--json", action="store_true", help="Return machine-readable JSON when supported.")
    parser.add_argument("--base-url", help="Override the configured Dify base URL for this command.")
    parser.add_argument("--app-api-key", help="Override the configured Dify app API key for this command.")
    parser.add_argument("--workspace-dir", help="Override the configured local resource workspace for this command.")
    parser.add_argument("--timeout-seconds", type=int, help="Override the configured HTTP timeout for this command.")
    parser.add_argument("--profile", help="Use a named Dify profile for Console API operations.")
    parser.add_argument("--console-key", help="Override the console credential (Admin API key or session cookie).")
    parser.add_argument("--no-auto-refresh", action="store_true", help="Do not auto re-login when the stored console_key cookie is expired.")
    parser.add_argument("--no-browser-fallback", action="store_true", help="Disable automatic browser fallback for provider operations.")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress human-readable error/warning lines on stderr (stdout JSON unaffected).")
    parser.add_argument("--verbose", action="store_true", help="Emit request tracing to stderr for debugging.")

    parser.add_argument(
        "--version", "-V",
        action="version",
        version=f"difyctl {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command", required=True, metavar="command")

    config_parser = subparsers.add_parser("config", help="Inspect or initialize difyctl config.")
    config_subparsers = config_parser.add_subparsers(dest="config_command", required=True, metavar="config_command")
    config_subparsers.add_parser("show", help="Show the effective config.")
    config_init = config_subparsers.add_parser("init", help="Write a starter config file.")
    config_init.add_argument("--base-url", required=True, help="Dify base URL such as https://dify.example.com.")
    config_init.add_argument("--app-api-key", default="", help="Optional app API key used for app-scoped inspection.")
    config_init.add_argument("--workspace-dir", required=True, help="Local resource workspace directory.")
    config_init.add_argument("--timeout-seconds", type=int, default=20, help="Default HTTP timeout.")
    config_init.add_argument("--force", action="store_true", help="Overwrite an existing config file.")

    subparsers.add_parser("doctor", help="Check whether config and workspace are ready.")

    app_parser = subparsers.add_parser("app", help="Inspect the current Dify app through app-token endpoints.")
    app_subparsers = app_parser.add_subparsers(dest="app_command", required=True, metavar="app_command")
    app_subparsers.add_parser("info", help="Call /v1/info.")
    app_subparsers.add_parser("parameters", help="Call /v1/parameters.")
    app_subparsers.add_parser("meta", help="Call /v1/meta.")

    app_keys = app_subparsers.add_parser("keys", help="Manage app service API keys (Dify /v1 tokens) via Console API.")
    app_keys_sub = app_keys.add_subparsers(dest="keys_command", required=True, metavar="keys_command")
    _akl = app_keys_sub.add_parser("list", help="List an app's service API keys (masked).")
    _akl.add_argument("--app-id", required=True, help="Dify app id.")
    _akc = app_keys_sub.add_parser("create", help="Create a service API key; token printed once + saved to config.yaml app_keys.")
    _akc.add_argument("--app-id", required=True, help="Dify app id.")
    _akd = app_keys_sub.add_parser("delete", help="Revoke a service API key by id.")
    _akd.add_argument("--app-id", required=True, help="Dify app id.")
    _akd.add_argument("--key-id", required=True, help="Service key id to revoke.")

    app_run = app_subparsers.add_parser("run", help="Invoke an app (workflow/chat/agent/completion) via /v1.")
    app_run.add_argument("--app-id", default="", help="Dify app id (used to resolve stored key + mode).")
    app_run.add_argument("--app-key", default="", help="Override the app-* service token.")
    app_run.add_argument("--mode", default="", help="App mode (workflow/chat/agent-chat/advanced-chat/completion); auto-resolved from ledger/live if omitted.")
    app_run.add_argument("--inputs", default="", help="Inputs as JSON string or @file.json.")
    app_run.add_argument("--query", default="", help="User query (required for chat/completion apps).")
    app_run.add_argument("--user", default="difyctl", help="End-user identifier.")
    app_run.add_argument("--response-mode", default="blocking", help="blocking (default); streaming reserved.")
    app_run.add_argument("--conversation-id", default="", help="Conversation id for multi-turn chat (optional).")
    app_run.add_argument("--stream", action="store_true", help="Use streaming mode and aggregate the SSE answer (auto-on for agent-chat).")
    app_run.add_argument("--timeout", type=int, default=0, help="Override HTTP timeout (seconds) for this run; needed for long chains (e.g. search+scrape). 0 = use config default.")

    app_delete = app_subparsers.add_parser("delete", help="Delete (retire) an app via Console API + mark ledger deprecated.")
    app_delete.add_argument("--app-id", required=True, help="Dify app id.")
    app_delete.add_argument("--yes", action="store_true", help="Confirm the destructive delete (required).")
    app_rename = app_subparsers.add_parser("rename", help="Rename/redescribe an app via Console API + sync ledger.")
    app_rename.add_argument("--app-id", required=True, help="Dify app id.")
    app_rename.add_argument("--name", required=True, help="New app name.")
    app_rename.add_argument("--description", default=None, help="New description (optional).")

    app_publish = app_subparsers.add_parser("publish", help="Publish an app's draft workflow (required before /v1 run for workflow/chatflow apps).")
    app_publish.add_argument("--app-id", required=True, help="Dify app id.")

    # ── Runtime /v1 operations (all use the app-* service token) ──
    _ars = app_subparsers.add_parser("run-status", help="Get a workflow run's detail/status via /v1/workflows/run/{id}.")
    _ars.add_argument("--app-id", default="", help="Dify app id (for stored key resolution).")
    _ars.add_argument("--app-key", default="", help="Override app-* service token.")
    _ars.add_argument("--run-id", required=True, help="workflow_run_id returned by app run.")

    _astop = app_subparsers.add_parser("stop", help="Stop a streaming workflow task via /v1/workflows/tasks/{task_id}/stop.")
    _astop.add_argument("--app-id", default="", help="Dify app id.")
    _astop.add_argument("--app-key", default="", help="Override app-* service token.")
    _astop.add_argument("--task-id", required=True, help="task_id to stop.")
    _astop.add_argument("--user", default="difyctl", help="End-user identifier (must match the run's user).")

    _aup = app_subparsers.add_parser("upload", help="Upload a file for file/image workflow inputs via /v1/files/upload.")
    _aup.add_argument("--app-id", default="", help="Dify app id.")
    _aup.add_argument("--app-key", default="", help="Override app-* service token.")
    _aup.add_argument("--file", required=True, help="Local file path to upload.")
    _aup.add_argument("--user", default="difyctl", help="End-user identifier.")

    _alogs = app_subparsers.add_parser("logs", help="List workflow run logs via /v1/workflows/logs.")
    _alogs.add_argument("--app-id", default="", help="Dify app id.")
    _alogs.add_argument("--app-key", default="", help="Override app-* service token.")
    _alogs.add_argument("--page", default="1", help="Page number.")
    _alogs.add_argument("--limit", default="20", help="Page size.")
    _alogs.add_argument("--keyword", default="", help="Optional keyword filter.")

    _aconv = app_subparsers.add_parser("conversations", help="List a chat app's conversations via /v1/conversations.")
    _aconv.add_argument("--app-id", default="", help="Dify app id.")
    _aconv.add_argument("--app-key", default="", help="Override app-* service token.")
    _aconv.add_argument("--user", default="difyctl", help="End-user identifier.")
    _aconv.add_argument("--limit", default="20", help="Page size.")

    _amsg = app_subparsers.add_parser("messages", help="List messages in a conversation via /v1/messages.")
    _amsg.add_argument("--app-id", default="", help="Dify app id.")
    _amsg.add_argument("--app-key", default="", help="Override app-* service token.")
    _amsg.add_argument("--conversation-id", required=True, help="Conversation id.")
    _amsg.add_argument("--user", default="difyctl", help="End-user identifier.")
    _amsg.add_argument("--limit", default="20", help="Page size.")

    _acr = app_subparsers.add_parser("conversation-rename", help="Rename a conversation via /v1/conversations/{id}/name.")
    _acr.add_argument("--app-id", default="", help="Dify app id.")
    _acr.add_argument("--app-key", default="", help="Override app-* service token.")
    _acr.add_argument("--conversation-id", required=True, help="Conversation id.")
    _acr.add_argument("--name", default="", help="New name (omit with --auto-generate).")
    _acr.add_argument("--auto-generate", action="store_true", help="Let Dify auto-generate the name.")
    _acr.add_argument("--user", default="difyctl", help="End-user identifier.")

    _acd = app_subparsers.add_parser("conversation-delete", help="Delete a conversation via /v1/conversations/{id}.")
    _acd.add_argument("--app-id", default="", help="Dify app id.")
    _acd.add_argument("--app-key", default="", help="Override app-* service token.")
    _acd.add_argument("--conversation-id", required=True, help="Conversation id.")
    _acd.add_argument("--user", default="difyctl", help="End-user identifier.")

    _afb = app_subparsers.add_parser("feedback", help="Send message feedback (like/dislike) via /v1/messages/{id}/feedbacks.")
    _afb.add_argument("--app-id", default="", help="Dify app id.")
    _afb.add_argument("--app-key", default="", help="Override app-* service token.")
    _afb.add_argument("--message-id", required=True, help="Message id.")
    _afb.add_argument("--rating", default="like", choices=("like", "dislike", "null"), help="Feedback rating.")
    _afb.add_argument("--content", default="", help="Optional feedback content.")
    _afb.add_argument("--user", default="difyctl", help="End-user identifier.")

    _asug = app_subparsers.add_parser("suggested", help="Get suggested follow-up questions via /v1/messages/{id}/suggested.")
    _asug.add_argument("--app-id", default="", help="Dify app id.")
    _asug.add_argument("--app-key", default="", help="Override app-* service token.")
    _asug.add_argument("--message-id", required=True, help="Message id.")
    _asug.add_argument("--user", default="difyctl", help="End-user identifier.")

    _aann = app_subparsers.add_parser("annotations", help="List an app's annotations (Q&A cache) via Console API.")
    _aann.add_argument("--app-id", required=True, help="Dify app id.")
    _aann.add_argument("--limit", default="20", help="Page size.")

    _a2t = app_subparsers.add_parser("audio-to-text", help="Speech-to-text via /v1/audio-to-text (multipart).")
    _a2t.add_argument("--app-id", default="", help="Dify app id.")
    _a2t.add_argument("--app-key", default="", help="Override app-* service token.")
    _a2t.add_argument("--file", required=True, help="Local audio file path.")
    _a2t.add_argument("--user", default="difyctl", help="End-user identifier.")

    _t2a = app_subparsers.add_parser("text-to-audio", help="Text-to-speech via /v1/text-to-audio (saves audio file).")
    _t2a.add_argument("--app-id", default="", help="Dify app id.")
    _t2a.add_argument("--app-key", default="", help="Override app-* service token.")
    _t2a.add_argument("--text", default="", help="Text to synthesize (or use --message-id).")
    _t2a.add_argument("--message-id", default="", help="Message id to synthesize instead of --text.")
    _t2a.add_argument("--output", required=True, help="Output audio file path.")
    _t2a.add_argument("--user", default="difyctl", help="End-user identifier.")

    dsl_parser = subparsers.add_parser("dsl", help="Author, validate, import, export, and inspect Dify DSL files.")
    dsl_subparsers = dsl_parser.add_subparsers(dest="dsl_command", required=True, metavar="dsl_command")
    dsl_summarize = dsl_subparsers.add_parser("summarize", help="Summarize a local DSL file.")
    dsl_summarize.add_argument("path", help="Path to a YAML or JSON DSL file.")

    dsl_validate = dsl_subparsers.add_parser("validate", help="Validate a local DSL file for import readiness.")
    dsl_validate.add_argument("path", help="Path to a YAML DSL file.")
    dsl_validate.add_argument("--target-version", default="", help="Require an exact DSL version (e.g. 0.6.0).")
    dsl_validate.add_argument("--strict", action="store_true", help="Treat warnings as errors.")

    dsl_import = dsl_subparsers.add_parser("import", help="Import a DSL file into Dify (Console API first, Playwright fallback).")
    dsl_import.add_argument("--dsl", required=True, help="Local DSL file path to import.")
    dsl_import.add_argument("--via", default="auto", choices=("auto", "api", "browser"), help="Execution track: auto (API then browser fallback), api-only, or browser-only.")
    dsl_import.add_argument("--skip-validate", action="store_true", help="Skip local DSL validation before import.")
    dsl_import.add_argument("--username-env", default="DIFY_STUDIO_USERNAME", help="Environment variable that stores the Studio login username (browser track).")
    dsl_import.add_argument("--password-env", default="DIFY_STUDIO_PASSWORD", help="Environment variable that stores the Studio login password (browser track).")
    dsl_import.add_argument("--headed", action="store_true", help="Launch Chromium with a visible window (browser track).")
    dsl_import.add_argument("--resource-id", default=None, help="Ledger resource_id to register under (kebab-case). Defaults to a slug derived from the DSL app name.")
    dsl_import.add_argument("--no-register", action="store_true", help="Do not auto-archive the DSL or upsert the ledger after a successful import.")
    dsl_import.add_argument("--create-key", action="store_true", help="After a successful import, create a service API key + save it to config.yaml (opt-in).")
    dsl_import.add_argument("--allow-duplicate", action="store_true", help="Skip the pre-import dedup guard and import even if a live app with the same name already exists.")
    dsl_import.add_argument("--app-id", default="", help="Update-in-place: import INTO this existing app (replaces its draft, no duplicate). Skips the dedup guard.")
    dsl_import.add_argument("--update-if-exists", action="store_true", help="If exactly one live app shares the DSL's name, update it in place; if none, create; if several, error.")
    dsl_import.add_argument("--smoke", action="store_true", help="After import, create a key and run one smoke invocation (implies --create-key). Requires --smoke-inputs/--smoke-query.")
    dsl_import.add_argument("--smoke-inputs", default="", help="Inputs (JSON or @file) for --smoke run.")
    dsl_import.add_argument("--smoke-query", default="", help="Query for --smoke run against chat/completion apps.")

    dsl_export = dsl_subparsers.add_parser("export", help="Export an app's DSL via the Console API (or --all for a full backup).")
    dsl_export.add_argument("--app-id", default="", help="Dify app id to export (omit with --all).")
    dsl_export.add_argument("--output", default="", help="Write the exported YAML to this path instead of stdout.")
    dsl_export.add_argument("--all", action="store_true", help="Back up EVERY live app's DSL into --output-dir (disaster recovery).")
    dsl_export.add_argument("--output-dir", default="", help="Directory for --all backup (one <app-id>.dify.yml per app).")

    dsl_diff = dsl_subparsers.add_parser("diff", help="Diff a local DSL file against the live app's exported DSL (preview an update before pushing).")
    dsl_diff.add_argument("--app-id", required=True, help="Live Dify app id to compare against.")
    dsl_diff.add_argument("--dsl", required=True, help="Local DSL file to compare.")

    dsl_lint = dsl_subparsers.add_parser("lint", help="Static-analyze a DSL: hardcoded secrets, dangling var refs, empty model refs.")
    dsl_lint.add_argument("--dsl", required=True, help="Local DSL file to lint.")
    dsl_lint.add_argument("--strict", action="store_true", help="Exit non-zero on warnings too (default: only on errors).")

    dsl_retarget = dsl_subparsers.add_parser("retarget", help="Rewrite the model provider+name across a DSL's LLM/agent nodes.")
    dsl_retarget.add_argument("--dsl", required=True, help="Local DSL file to rewrite.")
    dsl_retarget.add_argument("--provider", required=True, help="Target model provider (e.g. langgenius/openai_api_compatible/openai_api_compatible).")
    dsl_retarget.add_argument("--model", required=True, help="Target model name.")
    dsl_retarget.add_argument("--mode", default="", help="Optional model mode (chat/completion).")
    dsl_retarget.add_argument("--output", default="", help="Write to this path instead of overwriting --dsl.")

    dsl_apply = dsl_subparsers.add_parser("apply", help="Declaratively sync a folder of DSL files to live apps (create new / update existing by name).")
    dsl_apply.add_argument("--dir", required=True, help="Directory of *.dify.yml / *.yaml DSL files.")
    dsl_apply.add_argument("--publish", action="store_true", help="Publish each app's draft after create/update (workflow/advanced-chat).")
    dsl_apply.add_argument("--dry-run", action="store_true", help="Show the create/update/skip plan without executing.")

    dsl_detect_version = dsl_subparsers.add_parser(
        "detect-version",
        help="Detect the canonical DSL version used by this Dify instance.",
    )
    dsl_detect_version.add_argument(
        "--app-id",
        default="",
        help="Optional app ID; if provided, uses exported app's version field (authoritative).",
    )
    dsl_detect_version.add_argument(
        "--fallback-mode",
        default="auto",
        choices=["auto"],
        help="Fallback detection mode (currently only auto).",
    )

    resource_parser = subparsers.add_parser("resource", help="Manage local Dify resource capture under a project workspace.")
    resource_subparsers = resource_parser.add_subparsers(dest="resource_command", required=True, metavar="resource_command")
    resource_init = resource_subparsers.add_parser("init", help="Create a managed resource folder.")
    resource_init.add_argument("resource_id", help="Stable resource identifier.")
    resource_init.add_argument("--mode", required=True, choices=("workflow", "chatflow", "agent", "chatbot", "completion", "other"), help="Primary Dify resource mode.")
    resource_init.add_argument("--title", default="", help="Human-readable title.")
    resource_init.add_argument("--app-id", default="", help="Optional Dify app identifier.")
    resource_init.add_argument("--app-name", default="", help="Optional Dify app name.")
    resource_init.add_argument("--tag", action="append", default=[], help="Repeatable resource tag.")
    resource_init.add_argument("--dsl", help="Optional DSL file to capture immediately.")

    resource_capture = resource_subparsers.add_parser("capture", help="Capture a DSL export into the managed resource folder.")
    resource_capture.add_argument("resource_id", help="Managed resource identifier.")
    resource_capture.add_argument("--dsl", required=True, help="Path to the exported Dify DSL file.")
    resource_capture.add_argument("--label", default="", help="Optional snapshot label.")
    resource_capture.add_argument("--no-promote", action="store_true", help="Do not replace dsl/current.* for this capture.")

    resource_subparsers.add_parser("list", help="List managed resources.")
    resource_show = resource_subparsers.add_parser("show", help="Show one managed resource.")
    resource_show.add_argument("resource_id", help="Managed resource identifier.")

    registry_parser = subparsers.add_parser("registry", help="Manage the project-level Dify resource registry.")
    registry_subparsers = registry_parser.add_subparsers(dest="registry_command", required=True, metavar="registry_command")
    registry_init = registry_subparsers.add_parser("init", help="Create resources.yml in the workspace root.")
    registry_init.add_argument("--force", action="store_true", help="Overwrite the existing registry file.")
    registry_subparsers.add_parser("list", help="List registry entries.")
    registry_subparsers.add_parser("audit", help="Compare live apps vs ledger: zombies / unregistered / drift / duplicate names.")
    registry_sync = registry_subparsers.add_parser("sync", help="Backfill the ledger from live apps: upsert untracked live apps as ledger entries.")
    registry_sync.add_argument("--status", default="untracked", help="status value for newly backfilled entries (default: untracked).")
    registry_sync.add_argument("--dry-run", action="store_true", help="Show what would be added without writing the ledger.")
    registry_prune = registry_subparsers.add_parser("prune-duplicates", help="Plan (default) or apply cleanup of duplicate-name live apps, keeping one per name.")
    registry_prune.add_argument("--keep", default="newest", choices=("newest", "oldest"), help="Which app to keep per duplicate group (by created_at).")
    registry_prune.add_argument("--apply", action="store_true", help="Actually delete the surplus apps (DESTRUCTIVE). Default is a dry-run plan.")
    registry_show = registry_subparsers.add_parser("show", help="Show one registry entry.")
    registry_show.add_argument("resource_id", help="Registry resource identifier.")
    registry_upsert = registry_subparsers.add_parser("upsert", help="Insert or update one registry entry.")
    registry_upsert.add_argument("resource_id", help="Registry resource identifier.")
    registry_upsert.add_argument("--mode", required=True, help="Resource mode such as workflow or chatflow.")
    registry_upsert.add_argument("--title", required=True, help="Human-readable title.")
    registry_upsert.add_argument("--tag", action="append", default=[], help="Repeatable tag.")
    registry_upsert.add_argument("--app-id", default="", help="Optional Dify app identifier.")
    registry_upsert.add_argument("--app-name", default="", help="Optional Dify app name.")
    registry_upsert.add_argument("--dsl-path", default="", help="Optional relative DSL path.")

    # Knowledge bases (datasets)
    dataset_parser = subparsers.add_parser("dataset", help="Manage Dify knowledge bases (datasets) via the Console API.")
    dataset_subparsers = dataset_parser.add_subparsers(dest="dataset_command", required=True, metavar="dataset_command")
    ds_list = dataset_subparsers.add_parser("list", help="List knowledge bases (paginated, all pages).")
    ds_list.add_argument("--limit", default="30", help="Page size.")
    ds_list.add_argument("--name", default="", help="Filter: only datasets whose name contains this substring (case-insensitive).")
    ds_show = dataset_subparsers.add_parser("show", help="Show one knowledge base's detail.")
    ds_show.add_argument("--dataset-id", required=True, help="Knowledge base id.")
    ds_docs = dataset_subparsers.add_parser("documents", help="List documents inside a knowledge base.")
    ds_docs.add_argument("--dataset-id", required=True, help="Knowledge base id.")
    ds_docs.add_argument("--limit", default="30", help="Page size.")
    ds_create = dataset_subparsers.add_parser("create", help="Create a knowledge base.")
    ds_create.add_argument("--name", required=True, help="Knowledge base name.")
    ds_create.add_argument("--indexing-technique", default="high_quality", choices=("high_quality", "economy"), help="Indexing technique (high_quality needs an embedding model).")
    ds_create.add_argument("--permission", default="only_me", help="Access permission (only_me / all_team_members).")
    ds_create.add_argument("--description", default="", help="Optional description.")
    ds_delete = dataset_subparsers.add_parser("delete", help="Delete a knowledge base (DESTRUCTIVE).")
    ds_delete.add_argument("--dataset-id", required=True, help="Knowledge base id.")
    ds_delete.add_argument("--yes", action="store_true", help="Confirm the destructive delete (required).")
    ds_add = dataset_subparsers.add_parser("add-doc", help="Add a text document to a knowledge base via the /v1 dataset API.")
    ds_add.add_argument("--dataset-id", required=True, help="Knowledge base id.")
    ds_add.add_argument("--name", required=True, help="Document name.")
    ds_add.add_argument("--text", default="", help="Document text (or use --file to read from a file).")
    ds_add.add_argument("--file", default="", help="Read document text from this local file.")
    ds_add.add_argument("--indexing-technique", default="economy", choices=("high_quality", "economy"), help="Indexing technique.")
    ds_add.add_argument("--dataset-key", default="", help="Dataset service key (dataset-*). Auto-resolved from Console if omitted.")

    batch_parser = subparsers.add_parser("batch", help="Filter the resource registry and output a batch plan.")
    batch_subparsers = batch_parser.add_subparsers(dest="batch_command", required=True, metavar="batch_command")
    batch_plan = batch_subparsers.add_parser("plan", help="Build a filtered plan from resources.yml.")
    batch_plan.add_argument("--mode", default="", help="Filter by mode.")
    batch_plan.add_argument("--tag", default="", help="Filter by tag.")
    batch_plan.add_argument("--selector", default="", help="Filter by resource_id or title substring.")

    reconcile_parser = subparsers.add_parser("reconcile", help="Compare live app facts with tracked local metadata.")
    reconcile_subparsers = reconcile_parser.add_subparsers(dest="reconcile_command", required=True, metavar="reconcile_command")
    reconcile_show = reconcile_subparsers.add_parser("show", help="Show one resource reconciliation summary.")
    reconcile_show.add_argument("resource_id", help="Tracked resource identifier.")
    reconcile_diff = reconcile_subparsers.add_parser("diff-only", help="Show only drift observations for one tracked resource.")
    reconcile_diff.add_argument("resource_id", help="Tracked resource identifier.")

    workflow_parser = subparsers.add_parser("workflow-create", help="Author workflow specs + scaffold Dify DSL drafts (runtime execution: `difyctl app run`).")
    workflow_subparsers = workflow_parser.add_subparsers(dest="workflow_command", required=True, metavar="workflow_command")
    workflow_intake = workflow_subparsers.add_parser("intake", help="Create a structured workflow spec from explicit business inputs.")
    workflow_intake.add_argument("--name", required=True, help="Workflow name.")
    workflow_intake.add_argument("--mode", required=True, choices=("workflow", "chatflow", "agent", "chatbot", "completion"), help="Target Dify mode.")
    workflow_intake.add_argument("--goal", required=True, help="Business goal of the workflow.")
    workflow_intake.add_argument("--input", action="append", default=[], help="Repeatable input variable name.")
    workflow_intake.add_argument("--output", action="append", default=[], help="Repeatable output variable name.")
    workflow_intake.add_argument("--step", action="append", default=[], help="Repeatable business step name.")
    workflow_intake.add_argument("--spec-out", required=True, help="Output path of the generated workflow spec YAML.")
    workflow_intake.add_argument("--force", action="store_true", help="Overwrite the target spec file if it exists.")

    workflow_validate = workflow_subparsers.add_parser("validate-spec", help="Validate a workflow spec YAML file.")
    workflow_validate.add_argument("--spec", required=True, help="Workflow spec file path.")

    workflow_scaffold = workflow_subparsers.add_parser("scaffold", help="Generate a starter Dify DSL draft from a workflow spec.")
    workflow_scaffold.add_argument("--spec", required=True, help="Workflow spec file path.")
    workflow_scaffold.add_argument("--output", required=True, help="Output path of the scaffolded DSL YAML.")
    workflow_scaffold.add_argument("--force", action="store_true", help="Overwrite the target DSL file if it exists.")
    workflow_scaffold.add_argument("--dsl-version", default="", help="DSL version (auto=detect from config/live instance; 0.6.0/0.7.0 otherwise).")

    workflow_draft = workflow_subparsers.add_parser("draft", help="Create a minimal workflow spec from a plain demand note.")
    workflow_draft.add_argument("--from-demand", required=True, help="Plaintext or markdown demand note path.")
    workflow_draft.add_argument("--name", required=True, help="Workflow name.")
    workflow_draft.add_argument("--mode", default="workflow", choices=("workflow", "chatflow", "agent", "chatbot", "completion"), help="Target Dify mode.")
    workflow_draft.add_argument("--spec-out", required=True, help="Output path of the generated draft spec.")
    workflow_draft.add_argument("--force", action="store_true", help="Overwrite the target spec file if it exists.")

    studio_parser = subparsers.add_parser("studio", help="Bridge local resource assets to Dify Studio operations.")
    studio_subparsers = studio_parser.add_subparsers(dest="studio_command", required=True, metavar="studio_command")
    studio_create = studio_subparsers.add_parser("create-plan", help="Generate a Studio create or import plan.")
    studio_create.add_argument("--name", required=True, help="App name.")
    studio_create.add_argument("--mode", required=True, choices=("workflow", "chatflow", "agent", "chatbot", "completion"), help="Target Dify mode.")
    studio_create.add_argument("--description", default="", help="Optional app description.")
    studio_create.add_argument("--dsl", default="", help="If provided, build an import-DSL plan instead of empty app creation.")

    studio_export = studio_subparsers.add_parser("export-plan", help="Generate a Studio export DSL plan for one tracked resource.")
    studio_export.add_argument("resource_id", help="Tracked resource identifier.")

    studio_duplicate = studio_subparsers.add_parser("duplicate-plan", help="Generate a Studio duplicate plan for one tracked resource.")
    studio_duplicate.add_argument("resource_id", help="Tracked resource identifier.")

    studio_browser_doctor = studio_subparsers.add_parser("browser-doctor", help="Check whether Playwright automation prerequisites are ready.")
    studio_browser_doctor.add_argument("--username-env", default="DIFY_STUDIO_USERNAME", help="Environment variable that stores the Studio login username.")
    studio_browser_doctor.add_argument("--password-env", default="DIFY_STUDIO_PASSWORD", help="Environment variable that stores the Studio login password.")

    studio_import_run = studio_subparsers.add_parser("import-dsl-run", help="Attempt a Playwright-based Studio login and DSL import run.")
    studio_import_run.add_argument("--dsl", required=True, help="Local DSL file path to upload.")
    studio_import_run.add_argument("--username-env", default="DIFY_STUDIO_USERNAME", help="Environment variable that stores the Studio login username.")
    studio_import_run.add_argument("--password-env", default="DIFY_STUDIO_PASSWORD", help="Environment variable that stores the Studio login password.")
    studio_import_run.add_argument("--headed", action="store_true", help="Launch Chromium with a visible window for interactive verification.")

    studio_create_run = studio_subparsers.add_parser("create-empty-run", help="Create a blank Dify app through the Studio modal.")
    studio_create_run.add_argument("--name", required=True, help="App name to create in Dify Studio.")
    studio_create_run.add_argument("--mode", required=True, choices=("workflow", "chatflow", "agent", "chatbot", "completion"), help="Target Dify mode.")
    studio_create_run.add_argument("--description", default="", help="Optional app description.")
    studio_create_run.add_argument("--resource-id", default="", help="If provided, initialize and register a local tracked resource after creation.")
    studio_create_run.add_argument("--tag", action="append", default=[], help="Repeatable resource tag for the optional local tracked resource.")
    studio_create_run.add_argument("--username-env", default="DIFY_STUDIO_USERNAME", help="Environment variable that stores the Studio login username.")
    studio_create_run.add_argument("--password-env", default="DIFY_STUDIO_PASSWORD", help="Environment variable that stores the Studio login password.")
    studio_create_run.add_argument("--headed", action="store_true", help="Launch Chromium with a visible window for interactive verification.")

    studio_export_run = studio_subparsers.add_parser("export-dsl-run", help="Export one tracked app DSL through the Studio app-card menu.")
    studio_export_run.add_argument("resource_id", help="Tracked resource identifier.")
    studio_export_run.add_argument("--output", default="", help="Optional export file path. Defaults to the tracked resource current DSL path.")
    studio_export_run.add_argument("--no-capture", action="store_true", help="Only save the exported file, do not capture it into the tracked resource directory.")
    studio_export_run.add_argument("--username-env", default="DIFY_STUDIO_USERNAME", help="Environment variable that stores the Studio login username.")
    studio_export_run.add_argument("--password-env", default="DIFY_STUDIO_PASSWORD", help="Environment variable that stores the Studio login password.")
    studio_export_run.add_argument("--headed", action="store_true", help="Launch Chromium with a visible window for interactive verification.")

    studio_duplicate_run = studio_subparsers.add_parser("duplicate-run", help="Duplicate one tracked app through the Studio app-card menu.")
    studio_duplicate_run.add_argument("resource_id", help="Tracked resource identifier.")
    studio_duplicate_run.add_argument("--name", default="", help="Optional name for the duplicated app. Defaults to '<source> Copy'.")
    studio_duplicate_run.add_argument("--new-resource-id", default="", help="If provided, initialize and register a local tracked resource for the duplicated app.")
    studio_duplicate_run.add_argument("--tag", action="append", default=[], help="Repeatable resource tag for the optional duplicated tracked resource.")
    studio_duplicate_run.add_argument("--username-env", default="DIFY_STUDIO_USERNAME", help="Environment variable that stores the Studio login username.")
    studio_duplicate_run.add_argument("--password-env", default="DIFY_STUDIO_PASSWORD", help="Environment variable that stores the Studio login password.")
    studio_duplicate_run.add_argument("--headed", action="store_true", help="Launch Chromium with a visible window for interactive verification.")

    studio_edit_run = studio_subparsers.add_parser("edit-info-run", help="Edit one tracked app info through the Studio app-card menu.")
    studio_edit_run.add_argument("resource_id", help="Tracked resource identifier.")
    studio_edit_run.add_argument("--name", default="", help="Optional new app name. Defaults to the current tracked app name.")
    studio_edit_run.add_argument("--description", default=None, help="Optional new app description. Omit to keep the current Studio value.")
    studio_edit_run.add_argument("--max-active-requests", type=int, default=None, help="Optional max active requests value. Use 0 for unlimited.")
    studio_edit_run.add_argument("--username-env", default="DIFY_STUDIO_USERNAME", help="Environment variable that stores the Studio login username.")
    studio_edit_run.add_argument("--password-env", default="DIFY_STUDIO_PASSWORD", help="Environment variable that stores the Studio login password.")
    studio_edit_run.add_argument("--headed", action="store_true", help="Launch Chromium with a visible window for interactive verification.")

    # ── provider ──
    provider_parser = subparsers.add_parser("provider", help="Manage Dify model providers through the Console API.")
    provider_subparsers = provider_parser.add_subparsers(dest="provider_command", required=True, metavar="provider_command")

    provider_add = provider_subparsers.add_parser("add", help="Add a model provider from a YAML definition.")
    provider_add.add_argument("--from", dest="from_yaml", required=True, help="Path to provider YAML file.")
    provider_add.add_argument("--type", default="", help="Override provider type.")
    provider_add.add_argument("--name", default="", help="Override provider display name.")
    provider_add.add_argument("--api-key", default="", help="Override API key.")
    provider_add.add_argument("--api-base", default="", help="Override API base URL.")
    provider_add.add_argument("--dry-run", action="store_true", help="Validate and print the payload without creating.")

    provider_subparsers.add_parser("list", help="List configured model providers.")

    provider_test = provider_subparsers.add_parser("test", help="Test provider connectivity.")
    provider_test.add_argument("--provider", required=True, help="Provider name (as registered in Dify).")
    provider_test.add_argument("--model", required=True, help="Model name to test.")

    provider_remove = provider_subparsers.add_parser("remove", help="Remove a model provider.")
    provider_remove.add_argument("--provider", required=True, help="Provider name to remove.")
    provider_remove.add_argument("--force", action="store_true", help="Skip confirmation prompt.")
    provider_remove.add_argument("--dry-run", action="store_true", help="Print what would be removed.")

    provider_update = provider_subparsers.add_parser("update", help="Update a model provider from a YAML definition.")
    provider_update.add_argument("--provider", required=True, help="Provider name to update.")
    provider_update.add_argument("--from", dest="from_yaml", required=True, help="Path to updated provider YAML file.")
    provider_update.add_argument("--dry-run", action="store_true", help="Validate and print the update payload without applying.")

    provider_batch_parser = provider_subparsers.add_parser("batch", help="Batch operations from a manifest YAML.")
    provider_batch_parser.add_argument("--manifest", required=True, help="Path to manifest YAML file.")
    provider_batch_parser.add_argument("--dry-run", action="store_true", help="Validate all entries without applying.")
    provider_batch_parser.add_argument("--apply", action="store_true", help="Apply all entries (create missing providers).")
    provider_batch_parser.add_argument("--diff", action="store_true", help="Show diff between manifest and live providers.")

    provider_login = provider_subparsers.add_parser("login", help="Log into Dify via browser and capture session cookie for Console API (Community Edition).")
    provider_login.add_argument("--username-env", default="DIFY_STUDIO_USERNAME", help="Environment variable for Dify login username.")
    provider_login.add_argument("--password-env", default="DIFY_STUDIO_PASSWORD", help="Environment variable for Dify login password.")
    provider_login.add_argument("--headed", action="store_true", help="Show browser window during login.")
    provider_login.add_argument("--no-save-console-key", action="store_true", help="Do not persist the captured cookie to config.yaml (one-off/ephemeral login).")

    # Model ledger query: list configured models for a provider (the "台账" view)
    provider_models = provider_subparsers.add_parser("models", help="List configured models for a provider (model ledger).")
    provider_models.add_argument("--provider", required=True, help="Full provider path, e.g. langgenius/openai_api_compatible/openai_api_compatible.")
    provider_models.add_argument("--model-type", default="llm", help="Model type filter (llm, text-embedding, rerank, ...). Default llm.")

    # Add a single custom model to a customizable-model provider (e.g. openai_api_compatible)
    provider_add_model = provider_subparsers.add_parser("add-model", help="Add a single custom model with credentials to a provider.")
    provider_add_model.add_argument("--provider", required=True, help="Full provider path, e.g. langgenius/openai_api_compatible/openai_api_compatible.")
    provider_add_model.add_argument("--model", required=True, help="Model name, e.g. mimo-v2.5-pro.")
    provider_add_model.add_argument("--api-key", dest="api_key", default="", help="Consumer API key for the model endpoint. Supports ${ENV_VAR}.")
    provider_add_model.add_argument("--endpoint-url", dest="endpoint_url", required=True, help="OpenAI-compatible endpoint base URL, e.g. http://<service-url>:13033/v1.")
    provider_add_model.add_argument("--model-type", default="llm", help="Model type (llm, text-embedding, rerank, ...). Default llm.")
    provider_add_model.add_argument("--context-size", dest="context_size", default="128000", help="Context window size. Default 128000.")
    provider_add_model.add_argument("--max-tokens", dest="max_tokens", default="128000", help="Max output tokens. Default 128000.")
    provider_add_model.add_argument("--dry-run", action="store_true", help="Print the payload without applying.")

    # ── plugin（tool 插件 / MCP server 授权配置管理）──
    plugin_parser = subparsers.add_parser("plugin", help="Manage tool plugins (builtin tool providers, e.g. MCP SSE) via Console API.")
    plugin_subparsers = plugin_parser.add_subparsers(dest="plugin_command", required=True, metavar="plugin_command")

    plugin_list = plugin_subparsers.add_parser("list", help="List installed tool providers with authorization status.")
    plugin_list.add_argument("--type", default="builtin", choices=("builtin", "api", "workflow", "mcp", "model"), help="Provider type filter. Default builtin.")

    plugin_tools = plugin_subparsers.add_parser("tools", help="List tools a provider exposes (for MCP SSE: discovered MCP server tools).")
    plugin_tools.add_argument("--provider", required=True, help="Full provider path, e.g. junjiem/mcp_sse/mcp_sse.")

    plugin_auth_info = plugin_subparsers.add_parser("auth-info", help="Show a provider's credential entries (secret values masked).")
    plugin_auth_info.add_argument("--provider", required=True, help="Full provider path, e.g. junjiem/mcp_sse/mcp_sse.")

    plugin_auth_set = plugin_subparsers.add_parser("auth-set", help="Create or update a provider credential entry (credentials as JSON). contributor role.")
    plugin_auth_set.add_argument("--provider", required=True, help="Full provider path, e.g. junjiem/mcp_sse/mcp_sse.")
    plugin_auth_set.add_argument("--credentials", default="", help="Credentials JSON object string, e.g. '{\"servers_config\": \"{...}\"}'.")
    plugin_auth_set.add_argument("--credentials-file", default="", help="Path to credentials JSON file (wins over --credentials).")
    plugin_auth_set.add_argument("--name", default="", help="Credential display name (<=30 chars; add mode only).")
    plugin_auth_set.add_argument("--type", default="api-key", help="Credential type. Default api-key.")
    plugin_auth_set.add_argument("--credential-id", default="", help="Update this existing credential id instead of adding a new entry.")
    plugin_auth_set.add_argument("--dry-run", action="store_true", help="Print the (masked) payload without calling the API.")

    plugin_auth_remove = plugin_subparsers.add_parser("auth-remove", help="Delete a provider credential entry by id. maintainer role.")
    plugin_auth_remove.add_argument("--provider", required=True, help="Full provider path.")
    plugin_auth_remove.add_argument("--credential-id", required=True, help="Credential id to delete.")
    plugin_auth_remove.add_argument("--dry-run", action="store_true", help="Print the request without calling the API.")

    return parser


def _resolve_runtime_config(args: argparse.Namespace) -> tuple[Path, AppConfig]:
    config_path = resolve_config_path(args.config)
    legacy = load_config(config_path)
    # Config governance: ~/.harness-ai-kit/config.yaml (assets.difyctl) is the
    # single source of truth; the legacy ~/.difyctl/config.json only supplies
    # profiles as a fallback. get_config() layers defaults < .env.tak < env <
    # config.yaml and includes legacy paths as fallback.
    try:
        unified = get_config()
    except Exception:
        unified = {}
    if isinstance(unified, dict) and (unified.get("base_url") or unified.get("workspace_dir")):
        saved = AppConfig(
            base_url=str(unified.get("base_url", legacy.base_url) or ""),
            app_api_key=str(unified.get("app_api_key", legacy.app_api_key) or ""),
            workspace_dir=str(unified.get("workspace_dir", legacy.workspace_dir) or ""),
            timeout_seconds=int(unified.get("timeout_seconds", legacy.timeout_seconds) or 120),
            profiles=legacy.profiles,
            active_profile=legacy.active_profile,
        )
    else:
        saved = legacy
    merged = merge_config(
        saved,
        base_url=args.base_url,
        app_api_key=args.app_api_key,
        workspace_dir=args.workspace_dir,
        timeout_seconds=args.timeout_seconds,
        profile=getattr(args, "profile", None),
    )
    return config_path, merged


def _require_workspace(config: AppConfig) -> Path:
    return workspace_root(config.workspace_dir)


def _require_remote(config: AppConfig) -> None:
    effective_base_url, effective_app_api_key, _ = _resolve_effective_remote_config(config)
    if not effective_base_url or not effective_app_api_key:
        raise RuntimeError("base_url and app_api_key are required for remote app inspection")


def _doctor_payload(config_path: Path, config: AppConfig) -> dict[str, object]:
    workspace = Path(config.workspace_dir).expanduser().resolve() if config.workspace_dir else None
    effective_base_url, effective_app_api_key, remote_source = _resolve_effective_remote_config(config)
    return {
        "config_path": str(config_path),
        "config_exists": config_path.exists(),
        "base_url_configured": bool(config.base_url),
        "app_api_key_configured": bool(config.app_api_key),
        "effective_base_url": effective_base_url,
        "effective_base_url_source": remote_source["base_url"],
        "effective_app_api_key_configured": bool(effective_app_api_key),
        "effective_app_api_key_source": remote_source["app_api_key"],
        "project_env_path": remote_source["project_env_path"],
        "workspace_dir": str(workspace) if workspace else "",
        "workspace_exists": bool(workspace and workspace.exists()),
        "ready_for_remote_inspect": bool(effective_base_url and effective_app_api_key),
        "ready_for_resource_capture": bool(workspace),
    }


def _resolve_console_credential(args, config) -> tuple[str, str]:
    """Return (base_url, console_key) for Console API operations.

    Priority (per harness-ai-kit config governance): CLI args > active profile >
    assets.difyctl in ~/.harness-ai-kit/config.yaml > env var DIFY_CONSOLE_KEY.
    """
    effective_base_url = config.base_url
    effective_console_key = ""
    profile_config = resolve_active_profile(config)
    if profile_config:
        if profile_config.base_url:
            effective_base_url = profile_config.base_url
        effective_console_key = resolve_console_key(config)
    # Source-of-truth: assets.difyctl in ~/.harness-ai-kit/config.yaml
    if not effective_console_key:
        try:
            unified = get_config()
        except Exception:
            unified = {}
        if isinstance(unified, dict):
            effective_console_key = str(unified.get("console_key", "") or "").strip()
    # Env fallback (CI/automation only)
    if not effective_console_key:
        effective_console_key = os.environ.get("DIFY_CONSOLE_KEY", "").strip()
    # Auto-refresh an expired config/env cookie (skip when user passed --console-key
    # explicitly, and when --no-auto-refresh is set).
    if (
        effective_console_key
        and not getattr(args, "console_key", None)
        and not getattr(args, "no_auto_refresh", False)
    ):
        effective_console_key = _auto_refresh_console_key(effective_base_url, effective_console_key)
    # CLI arg override (highest priority)
    if getattr(args, "console_key", None):
        effective_console_key = args.console_key
    return effective_base_url, effective_console_key


def _auto_refresh_console_key(base_url: str, console_key: str) -> str:
    """Re-login and rewrite config.yaml when the console_key cookie is expired.

    Returns the freshest key available: a newly captured cookie on success,
    otherwise the original (expired) key so the caller's API call surfaces the
    real 401. Requires base_url + studio_username/password (from config.yaml or
    env). Best-effort: any failure degrades to a stderr warning.
    """
    if not console_key or not cookie_expired(console_key):
        return console_key
    try:
        cfg = get_config()
    except Exception:
        cfg = {}
    if not isinstance(cfg, dict):
        cfg = {}
    uname = os.environ.get("DIFY_STUDIO_USERNAME") or str(cfg.get("studio_username", "") or "").strip()
    pwd = os.environ.get("DIFY_STUDIO_PASSWORD") or str(cfg.get("studio_password", "") or "").strip()
    if not (base_url and uname and pwd):
        print(
            warning_line("console_key expired", "cannot auto-refresh (missing base_url/studio credentials); run `difyctl provider login`"),
            file=sys.stderr,
        )
        return console_key
    try:
        os.environ["DIFY_STUDIO_USERNAME"] = uname
        os.environ["DIFY_STUDIO_PASSWORD"] = pwd
        payload = capture_console_cookie(base_url=base_url, headless=True)
        fresh = str(payload.get("full_cookie_header", "") or "")
        if fresh:
            try:
                write_unified_config_value("console_key", fresh)
            except Exception:
                pass
            print(
                warning_line("console_key expired", "auto-refreshed via studio login and saved to config.yaml"),
                file=sys.stderr,
            )
            return fresh
    except Exception as exc:
        print(warning_line("console_key auto-refresh failed", str(exc)), file=sys.stderr)
    return console_key



def _dsl_import_via_api(args, config, yaml_content: str) -> tuple[bool, dict]:
    """Attempt a Console API import.

    Returns (handled, payload). ``handled`` is False when the caller should
    fall back to the browser track (5xx / network errors under --via auto).
    """
    base_url, console_key = _resolve_console_credential(args, config)
    if not base_url:
        return True, {"ok": False, "track": "api", "error": "No base_url configured for Console API import"}
    if not console_key:
        return True, {"ok": False, "track": "api", "error": "No console_key configured (set config profile or --console-key)"}
    try:
        auth = ConsoleAuth.detect(console_key)
    except ValueError as exc:
        return True, {"ok": False, "track": "api", "error": str(exc)}

    client = ConsoleApiClient(base_url, auth, config.timeout_seconds)
    result = client.app_import_dsl(yaml_content, app_id=str(getattr(args, "app_id", "") or ""))

    if args.via == "auto" and (result.status_code == 0 or should_fallback(result.status_code)):
        return False, {"ok": False, "track": "api", "status_code": result.status_code, "error": result.text}

    payload = result.payload if isinstance(result.payload, dict) else {}
    status = str(payload.get("status", ""))
    import_id = str(payload.get("id", ""))
    if status == "pending" and import_id:
        confirm = client.app_import_confirm(import_id)
        payload = confirm.payload if isinstance(confirm.payload, dict) else payload
        result = confirm
    app_id = str(payload.get("app_id", ""))
    ok = 200 <= result.status_code < 300 and str(payload.get("status", "")).startswith("completed")
    return True, {
        "ok": ok,
        "track": "api",
        "status_code": result.status_code,
        "import_status": payload.get("status"),
        "app_id": app_id,
        "app_url": f"{base_url}/app/{app_id}/workflow" if app_id else "",
        "imported_dsl_version": payload.get("imported_dsl_version"),
    }


def _maybe_register_import(args, config, dsl_path, yaml_content: str, payload: dict) -> None:
    """After a successful import, archive the DSL + upsert the ledger (U5 closed loop).

    Mutates ``payload`` in place: adds ``registered`` on success or
    ``register_error`` on failure. Import success is never downgraded by a
    registration failure — the app already exists in Dify.
    """
    if getattr(args, "no_register", False):
        return
    try:
        import re as _re

        import yaml as _yaml

        root = workspace_root(config.workspace_dir) if getattr(config, "workspace_dir", "") else None
        if not root:
            payload["register_error"] = "no workspace_dir configured; skipped ledger registration"
            return
        document = _yaml.safe_load(yaml_content)
        app = document.get("app", {}) if isinstance(document, dict) else {}
        app_name = str(app.get("name", "") or "")
        mode = str(app.get("mode", "") or (document.get("kind", "") if isinstance(document, dict) else "") or "")
        version = str(document.get("version", "") if isinstance(document, dict) else "") or ""
        # resolve resource_id: --resource-id > derive from DSL app.name (validated)
        rid = getattr(args, "resource_id", None)
        if rid:
            rid = validate_resource_id(rid)
        else:
            rid = validate_resource_id(derive_resource_id(app_name))
        # app_id from API payload or browser final_url
        app_id = str(payload.get("app_id", "") or "")
        if not app_id:
            for key in ("app_url", "final_url"):
                match = _re.search(r"/app/([0-9a-fA-F-]{8,})", str(payload.get(key, "") or ""))
                if match:
                    app_id = match.group(1)
                    break
        # ensure the resource dir/metadata exists before capturing the DSL into it
        ensure_resource(root, resource_id=rid, mode=mode, title=app_name, app_id=app_id, app_name=app_name, tags=[])
        capture_dsl(root, rid, dsl_path, label="imported", promote=True)
        ledger_path = upsert_registry_resource(
            root,
            {
                "resource_id": rid,
                "mode": mode,
                "title": app_name,
                "app_id": app_id,
                "app_name": app_name,
                "dsl_path": canonical_dsl_path(rid),
                "dsl_version": version,
                "status": "development",
            },
        )
        payload["registered"] = {
            "resource_id": rid,
            "ledger_path": str(ledger_path),
            "dsl_path": canonical_dsl_path(rid),
            "app_id": app_id,
        }
    except Exception as exc:
        payload["register_error"] = (
            f"{exc}. Import succeeded but ledger registration failed; "
            "pass --resource-id <kebab-id> or --no-register."
        )


def _mask_token(token: str) -> str:
    """Mask a service token for safe display: keep a short prefix, hide the rest."""
    t = str(token or "")
    if len(t) <= 10:
        return "****"
    return t[:9] + "****"


def _console_client(args, config):
    """Build a Console API client from resolved cookie credential (or raise)."""
    base_url, console_key = _resolve_console_credential(args, config)
    if not base_url:
        raise RuntimeError("No base_url configured for Console API")
    if not console_key:
        raise RuntimeError("No console_key configured (run `difyctl provider login`)")
    return ConsoleApiClient(base_url, ConsoleAuth.detect(console_key), config.timeout_seconds)


def _ledger_entry_by_app_id(config, app_id: str):
    """Return (root, resource_id) for the ledger entry matching app_id, or (root|None, "")."""
    try:
        root = workspace_root(config.workspace_dir) if getattr(config, "workspace_dir", "") else None
    except Exception:
        root = None
    if not root or not app_id:
        return root, ""
    try:
        for entry in list_registry_resources(root):
            if str(entry.get("app_id", "")) == app_id:
                return root, str(entry.get("resource_id", ""))
    except Exception:
        pass
    return root, ""


def _cmd_app_keys(args, config) -> int:
    try:
        client = _console_client(args, config)
    except Exception as exc:
        eprint(error_line("app keys failed", str(exc)))
        return 1
    sub = args.keys_command
    if sub == "list":
        result = client.app_keys_list(args.app_id)
        ok = 200 <= result.status_code < 300
        data = result.payload.get("data") if isinstance(result.payload, dict) else result.payload
        keys = [
            {"id": k.get("id"), "prefix": _mask_token(str(k.get("token", ""))), "created_at": k.get("created_at")}
            for k in (data or []) if isinstance(k, dict)
        ]
        print_json({"ok": ok, "app_id": args.app_id, "keys": keys})
        return 0 if ok else 1
    if sub == "create":
        result = client.app_key_create(args.app_id)
        ok = 200 <= result.status_code < 300
        payload = result.payload if isinstance(result.payload, dict) else {}
        token = str(payload.get("token", "") or "")
        key_id = str(payload.get("id", "") or "")
        if ok and token:
            write_unified_app_key(args.app_id, token)
            root, resource_id = _ledger_entry_by_app_id(config, args.app_id)
            if root and resource_id:
                try:
                    upsert_registry_resource(root, {"resource_id": resource_id, "service_key": {"key_id": key_id, "prefix": _mask_token(token), "created_at": payload.get("created_at")}})
                except Exception:
                    pass
            print(warning_line("service key created", "full token shown once below; also saved to config.yaml assets.difyctl.app_keys"), file=sys.stderr)
            print_json({"ok": True, "app_id": args.app_id, "key_id": key_id, "token": token, "saved_to_config": True})
            return 0
        print_json({"ok": False, "app_id": args.app_id, "status_code": result.status_code, "error": result.text})
        return 1
    if sub == "delete":
        result = client.app_key_delete(args.app_id, args.key_id)
        ok = 200 <= result.status_code < 300
        if ok:
            forget_unified_app_key(args.app_id)
        print_json({"ok": ok, "app_id": args.app_id, "key_id": args.key_id, "status_code": result.status_code})
        return 0 if ok else 1
    return 1


_SECRET_KEY_RE = re.compile(r"key|token|secret|password|cookie|authorization|credential", re.IGNORECASE)
_SECRET_VALUE_RE = re.compile(r"(g2a_|sk-|xai-|app-|tvly-|fc-)[A-Za-z0-9_-]{4,}")


def _mask_credentials(value):
    """Recursively mask secret-looking values in a credentials structure.

    Keys matching key/token/secret/password/cookie/authorization/credential have
    their string values masked; known token prefixes (g2a_/sk-/app-/...) are
    masked anywhere they appear, including inside nested JSON strings such as
    the MCP SSE plugin's ``servers_config``.
    """
    if isinstance(value, dict):
        return {k: ("****" if isinstance(v, str) and v and _SECRET_KEY_RE.search(str(k)) else _mask_credentials(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [_mask_credentials(v) for v in value]
    if isinstance(value, str):
        return _SECRET_VALUE_RE.sub(lambda m: m.group(1) + "****", value)
    return value


def _cmd_plugin(args, config) -> int:
    from .role import require_role, check_dry_run_override

    sub = args.plugin_command
    # 写操作显式角色门（子命令名不以 add-/update-/remove- 开头，走不到统一前缀门）
    if sub == "auth-set" and not (getattr(args, "dry_run", False) and check_dry_run_override(args, "contributor")):
        require_role("contributor", f"plugin {sub}")
    if sub == "auth-remove" and not getattr(args, "dry_run", False):
        require_role("maintainer", f"plugin {sub}")
    try:
        client = _console_client(args, config)
    except Exception as exc:
        eprint(error_line(f"plugin {sub} failed", str(exc)))
        return 1

    if sub == "list":
        result = client.tool_providers_list(getattr(args, "type", "builtin"))
        ok = 200 <= result.status_code < 300
        items = result.payload if isinstance(result.payload, list) else (result.payload or {}).get("data", [])
        providers = [
            {
                "provider": p.get("provider") or p.get("id"),
                "name": p.get("name"),
                "is_team_authorization": p.get("is_team_authorization"),
                "allow_delete": p.get("allow_delete"),
            }
            for p in (items or []) if isinstance(p, dict)
        ]
        print_json({"ok": ok, "type": getattr(args, "type", "builtin"), "count": len(providers), "providers": providers})
        return 0 if ok else 1

    if sub == "tools":
        result = client.tool_builtin_tools(args.provider)
        ok = 200 <= result.status_code < 300
        items = result.payload if isinstance(result.payload, list) else (result.payload or {}).get("data", [])
        tools = [
            {"name": t.get("name"), "label": (t.get("label") or {}).get("zh_Hans") or (t.get("label") or {}).get("en_US") if isinstance(t.get("label"), dict) else t.get("label")}
            for t in (items or []) if isinstance(t, dict)
        ]
        print_json({"ok": ok, "provider": args.provider, "count": len(tools), "tools": tools})
        return 0 if ok else 1

    if sub == "auth-info":
        result = client.tool_builtin_credentials(args.provider)
        ok = 200 <= result.status_code < 300
        items = result.payload if isinstance(result.payload, list) else (result.payload or {}).get("data", [])
        entries = [
            {
                "id": c.get("id"),
                "name": c.get("name"),
                "credential_type": c.get("credential_type"),
                "is_default": c.get("is_default"),
                "credentials": _mask_credentials(c.get("credentials") or {}),
            }
            for c in (items or []) if isinstance(c, dict)
        ]
        print_json({"ok": ok, "provider": args.provider, "count": len(entries), "credentials": entries})
        return 0 if ok else 1

    if sub == "auth-set":
        raw = ""
        if getattr(args, "credentials_file", ""):
            raw = Path(args.credentials_file).read_text(encoding="utf-8")
        else:
            raw = str(getattr(args, "credentials", "") or "")
        try:
            credentials = json.loads(raw)
        except (ValueError, TypeError):
            eprint(error_line("plugin auth-set failed", "credentials must be a JSON object (use --credentials or --credentials-file)"))
            return 1
        if not isinstance(credentials, dict) or not credentials:
            eprint(error_line("plugin auth-set failed", "credentials JSON must be a non-empty object"))
            return 1
        credential_id = str(getattr(args, "credential_id", "") or "")
        if getattr(args, "dry_run", False):
            print_json({
                "_dry_run": True,
                "action": "update" if credential_id else "add",
                "provider": args.provider,
                "credential_id": credential_id or None,
                "name": getattr(args, "name", "") or None,
                "type": getattr(args, "type", "api-key"),
                "credentials": _mask_credentials(credentials),
            })
            return 0
        if credential_id:
            result = client.tool_builtin_credential_update(
                args.provider,
                credential_id,
                credentials=credentials,
                name=str(getattr(args, "name", "") or ""),
            )
        else:
            result = client.tool_builtin_credential_add(
                args.provider,
                credentials,
                name=str(getattr(args, "name", "") or ""),
                credential_type=str(getattr(args, "type", "api-key") or "api-key"),
            )
        ok = 200 <= result.status_code < 300
        out = {
            "ok": ok,
            "action": "update" if credential_id else "add",
            "provider": args.provider,
            "credential_id": credential_id or None,
            "status_code": result.status_code,
        }
        if not ok:
            out["error"] = (str(result.payload.get("message", "")) if isinstance(result.payload, dict) else result.text)[:300]
        print_json(out)
        return 0 if ok else 1

    if sub == "auth-remove":
        credential_id = str(args.credential_id)
        if getattr(args, "dry_run", False):
            print_json({"_dry_run": True, "action": "delete", "provider": args.provider, "credential_id": credential_id})
            return 0
        result = client.tool_builtin_credential_delete(args.provider, credential_id)
        ok = 200 <= result.status_code < 300
        print_json({"ok": ok, "action": "delete", "provider": args.provider, "credential_id": credential_id, "status_code": result.status_code})
        return 0 if ok else 1

    return 1


_CHAT_MODES = {"chat", "agent-chat", "advanced-chat", "chatflow", "agent"}


def _resolve_run_mode(args, config) -> str:
    mode = (getattr(args, "mode", "") or "").strip().lower()
    if mode:
        return mode
    _root, resource_id = _ledger_entry_by_app_id(config, getattr(args, "app_id", ""))
    if resource_id:
        try:
            for entry in list_registry_resources(workspace_root(config.workspace_dir)):
                if str(entry.get("resource_id", "")) == resource_id:
                    return str(entry.get("mode", "") or "").strip().lower() or "workflow"
        except Exception:
            pass
    return "workflow"


def _run_app_core(base_url: str, app_key: str, mode: str, inputs: dict, query: str, user: str, conversation_id: str, timeout: int, force_stream: bool = False, on_chunk=None) -> dict:
    """Invoke a Dify app via the correct /v1 endpoint for its mode. Returns a result dict (no printing).

    agent-chat apps only support streaming, so they are routed through post_sse;
    workflow/chat/advanced-chat/completion use blocking post_json unless force_stream
    is set (then chat/completion use post_sse and aggregate the answer).
    """
    mode = (mode or "workflow").strip().lower()
    _AGENT_MODES = {"agent-chat", "agent"}
    if mode in _CHAT_MODES:
        if not query:
            return {"ok": False, "mode": mode, "error": f"chat-type app ({mode}) requires a query"}
        body = {"query": query, "inputs": inputs or {}, "user": user}
        if conversation_id:
            body["conversation_id"] = conversation_id
        endpoint = "/v1/chat-messages"
        if mode in _AGENT_MODES or force_stream:
            # agent-chat rejects blocking mode -> stream + aggregate; --stream forces it too
            result = post_sse(base_url, app_key, endpoint, body, timeout, on_chunk=on_chunk)
            ok = 200 <= result.status_code < 300
            return {"ok": ok, "mode": mode, "endpoint": endpoint, "response_mode": "streaming", "status_code": result.status_code, "result": result.payload if ok else result.text}
        body["response_mode"] = "blocking"
    elif mode == "completion":
        inp = dict(inputs or {})
        if query:
            inp.setdefault("query", query)
        if force_stream:
            result = post_sse(base_url, app_key, "/v1/completion-messages", {"inputs": inp, "user": user}, timeout, on_chunk=on_chunk)
            ok = 200 <= result.status_code < 300
            return {"ok": ok, "mode": mode, "endpoint": "/v1/completion-messages", "response_mode": "streaming", "status_code": result.status_code, "result": result.payload if ok else result.text}
        body = {"inputs": inp, "response_mode": "blocking", "user": user}
        endpoint = "/v1/completion-messages"
    else:
        body = {"inputs": inputs or {}, "response_mode": "blocking", "user": user}
        endpoint = "/v1/workflows/run"
    result = post_json(base_url, app_key, endpoint, body, timeout)
    ok = 200 <= result.status_code < 300
    return {"ok": ok, "mode": mode, "endpoint": endpoint, "status_code": result.status_code, "result": result.payload if ok else result.text}


def _maybe_create_key_and_smoke(args, config, payload: dict) -> None:
    """After import, optionally create a service key (--create-key) and run a smoke
    invocation (--smoke). Folds masked results into payload; never fails the import."""
    if not (getattr(args, "create_key", False) or getattr(args, "smoke", False)):
        return
    app_id = str(payload.get("app_id", "") or "")
    if not app_id:
        payload["key_error"] = "no app_id from import; cannot create service key"
        return
    try:
        client = _console_client(args, config)
        result = client.app_key_create(app_id)
        if not (200 <= result.status_code < 300):
            payload["key_error"] = f"create key failed: {result.text}"
            return
        kp = result.payload if isinstance(result.payload, dict) else {}
        token = str(kp.get("token", "") or "")
        key_id = str(kp.get("id", "") or "")
        if not token:
            payload["key_error"] = "create key returned no token"
            return
        write_unified_app_key(app_id, token)
        payload["service_key"] = {"key_id": key_id, "prefix": _mask_token(token), "saved_to_config": True}
        root, resource_id = _ledger_entry_by_app_id(config, app_id)
        run_mode = ""
        if root and resource_id:
            try:
                upsert_registry_resource(root, {"resource_id": resource_id, "service_key": {"key_id": key_id, "prefix": _mask_token(token), "created_at": kp.get("created_at")}})
                for entry in list_registry_resources(root):
                    if str(entry.get("resource_id", "")) == resource_id:
                        run_mode = str(entry.get("mode", "") or "")
                        break
            except Exception:
                pass
        if getattr(args, "smoke", False):
            import json as _json

            smoke_inputs: dict = {}
            if getattr(args, "smoke_inputs", ""):
                raw = args.smoke_inputs
                if raw.startswith("@"):
                    raw = Path(raw[1:]).read_text(encoding="utf-8")
                smoke_inputs = _json.loads(raw) if raw.strip() else {}
            # workflow/advanced-chat apps must be published before /v1 run
            publish_note = None
            if (run_mode or "workflow").lower() in ("workflow", "advanced-chat", "chatflow"):
                pub = client.app_workflow_publish(app_id)
                publish_note = 200 <= pub.status_code < 300
            outcome = _run_app_core(config.base_url, token, run_mode or "workflow", smoke_inputs, getattr(args, "smoke_query", ""), "difyctl-smoke", "", config.timeout_seconds)
            if publish_note is not None:
                outcome["published"] = publish_note
            payload["smoke"] = outcome
    except Exception as exc:
        payload["key_error"] = str(exc)


def _cmd_app_run(args, config) -> int:
    import json as _json

    base_url = config.base_url
    if not base_url:
        eprint(error_line("app run failed", "No base_url configured"))
        return 1
    app_key = (getattr(args, "app_key", "") or "").strip() or resolve_app_key(getattr(args, "app_id", ""))
    if not app_key:
        eprint(error_line("app run failed", f"No service key for app {args.app_id}; run `difyctl app keys create --app-id {args.app_id}` or pass --app-key"))
        return 1
    inputs: dict = {}
    if args.inputs:
        raw = args.inputs
        if raw.startswith("@"):
            try:
                raw = Path(raw[1:]).read_text(encoding="utf-8")
            except Exception as exc:
                eprint(error_line("app run failed", f"cannot read --inputs file: {exc}"))
                return 1
        try:
            inputs = _json.loads(raw) if raw.strip() else {}
        except Exception as exc:
            eprint(error_line("app run failed", f"--inputs is not valid JSON: {exc}"))
            return 1
        if not isinstance(inputs, dict):
            eprint(error_line("app run failed", "--inputs must be a JSON object"))
            return 1
    mode = _resolve_run_mode(args, config)
    stream = getattr(args, "stream", False)
    live_writer = None
    if stream and not _QUIET:
        def live_writer(piece):  # noqa: E306 - print tokens live to stderr, stdout stays JSON
            print(piece, end="", file=sys.stderr, flush=True)
    run_timeout = getattr(args, "timeout", 0) or config.timeout_seconds
    outcome = _run_app_core(base_url, app_key, mode, inputs, args.query, args.user, args.conversation_id, run_timeout, force_stream=stream, on_chunk=live_writer)
    if stream and live_writer:
        print("", file=sys.stderr)  # newline after the live stream
    if not outcome.get("ok") and outcome.get("error"):
        eprint(error_line("app run failed", outcome["error"]))
        return 1
    print_json(outcome)
    return 0 if outcome.get("ok") else 1


def _cmd_app_lifecycle(args, config) -> int:
    try:
        client = _console_client(args, config)
    except Exception as exc:
        eprint(error_line(f"app {args.app_command} failed", str(exc)))
        return 1
    if args.app_command == "delete":
        if not getattr(args, "yes", False):
            eprint(error_line("app delete blocked", f"destructive: retiring app {args.app_id}.", "Re-run with --yes to confirm."))
            print_json({"ok": False, "stage": "confirm", "app_id": args.app_id, "requires": "--yes"})
            return 1
        result = client.app_delete(args.app_id)
        ok = 200 <= result.status_code < 300
        if ok:
            forget_unified_app_key(args.app_id)
            root, resource_id = _ledger_entry_by_app_id(config, args.app_id)
            if root and resource_id:
                try:
                    upsert_registry_resource(root, {"resource_id": resource_id, "status": "deprecated"})
                except Exception:
                    pass
        print_json({"ok": ok, "app_id": args.app_id, "action": "deleted", "status_code": result.status_code})
        return 0 if ok else 1
    # rename: GET current detail, merge name/description, PUT back (preserve icon fields)
    detail = client.app_get(args.app_id)
    fields: dict = {}
    if isinstance(detail.payload, dict):
        for k in ("icon", "icon_type", "icon_background", "description", "use_icon_as_answer_icon"):
            if k in detail.payload and detail.payload[k] is not None:
                fields[k] = detail.payload[k]
    fields["name"] = args.name
    if args.description is not None:
        fields["description"] = args.description
    result = client.app_update(args.app_id, fields)
    ok = 200 <= result.status_code < 300
    if ok:
        root, resource_id = _ledger_entry_by_app_id(config, args.app_id)
        if root and resource_id:
            patch = {"resource_id": resource_id, "title": args.name, "app_name": args.name}
            if args.description is not None:
                patch["description"] = args.description
            try:
                upsert_registry_resource(root, patch)
            except Exception:
                pass
    print_json({"ok": ok, "app_id": args.app_id, "action": "renamed", "name": args.name, "status_code": result.status_code})
    return 0 if ok else 1


def _cmd_app_publish(args, config) -> int:
    try:
        client = _console_client(args, config)
    except Exception as exc:
        eprint(error_line("app publish failed", str(exc)))
        return 1
    result = client.app_workflow_publish(args.app_id)
    ok = 200 <= result.status_code < 300
    print_json({"ok": ok, "app_id": args.app_id, "action": "published", "status_code": result.status_code, "result": result.payload if ok else result.text})
    return 0 if ok else 1


def _cmd_app_annotations(args, config) -> int:
    """List an app's annotations (Q&A cache) via the Console API."""
    try:
        client = _console_client(args, config)
    except Exception as exc:
        eprint(error_line("app annotations failed", str(exc)))
        return 1
    r = client.app_annotations(args.app_id, 1, int(getattr(args, "limit", "20") or "20"))
    ok = 200 <= r.status_code < 300
    data = r.payload.get("data") if isinstance(r.payload, dict) else []
    anns = [{"id": a.get("id"), "question": a.get("question"), "answer": a.get("answer"), "hit_count": a.get("hit_count")}
            for a in (data or []) if isinstance(a, dict)]
    print_json({"ok": ok, "status_code": r.status_code, "app_id": args.app_id, "total": len(anns), "annotations": anns})
    return 0 if ok else 1


_APP_RUNTIME_COMMANDS = frozenset({
    "run-status", "stop", "upload", "logs", "conversations", "messages",
    "conversation-rename", "conversation-delete", "feedback", "suggested",
    "audio-to-text", "text-to-audio",
})


def _cmd_app_runtime(args, config) -> int:
    """Dispatch all /v1 runtime app subcommands (service-token operations)."""
    import urllib.parse as _url

    base_url = config.base_url
    if not base_url:
        eprint(error_line("app command failed", "No base_url configured"))
        return 1
    app_key = (getattr(args, "app_key", "") or "").strip() or resolve_app_key(getattr(args, "app_id", ""))
    if not app_key:
        eprint(error_line("app command failed", f"No service key; run `difyctl app keys create --app-id {getattr(args, 'app_id', '')}` or pass --app-key"))
        return 1
    cmd = args.app_command
    t = config.timeout_seconds

    if cmd == "run-status":
        r = request_v1("GET", base_url, app_key, f"/v1/workflows/run/{args.run_id}", timeout_seconds=t)
    elif cmd == "stop":
        r = request_v1("POST", base_url, app_key, f"/v1/workflows/tasks/{args.task_id}/stop", {"user": args.user}, timeout_seconds=t)
    elif cmd == "upload":
        if not Path(args.file).exists():
            eprint(error_line("app upload failed", f"file not found: {args.file}"))
            return 1
        r = post_multipart(base_url, app_key, "/v1/files/upload", args.file, fields={"user": args.user}, file_field="file", timeout_seconds=max(t, 120))
    elif cmd == "logs":
        q = {"page": args.page, "limit": args.limit}
        if args.keyword:
            q["keyword"] = args.keyword
        r = request_v1("GET", base_url, app_key, "/v1/workflows/logs?" + _url.urlencode(q), timeout_seconds=t)
    elif cmd == "conversations":
        r = request_v1("GET", base_url, app_key, "/v1/conversations?" + _url.urlencode({"user": args.user, "limit": args.limit}), timeout_seconds=t)
    elif cmd == "messages":
        r = request_v1("GET", base_url, app_key, "/v1/messages?" + _url.urlencode({"conversation_id": args.conversation_id, "user": args.user, "limit": args.limit}), timeout_seconds=t)
    elif cmd == "conversation-rename":
        body = {"user": args.user, "auto_generate": bool(args.auto_generate)}
        if args.name:
            body["name"] = args.name
        r = request_v1("POST", base_url, app_key, f"/v1/conversations/{args.conversation_id}/name", body, timeout_seconds=t)
    elif cmd == "conversation-delete":
        r = request_v1("DELETE", base_url, app_key, f"/v1/conversations/{args.conversation_id}", {"user": args.user}, timeout_seconds=t)
    elif cmd == "feedback":
        rating = None if args.rating == "null" else args.rating
        body = {"rating": rating, "user": args.user}
        if args.content:
            body["content"] = args.content
        r = request_v1("POST", base_url, app_key, f"/v1/messages/{args.message_id}/feedbacks", body, timeout_seconds=t)
    elif cmd == "suggested":
        r = request_v1("GET", base_url, app_key, f"/v1/messages/{args.message_id}/suggested?" + _url.urlencode({"user": args.user}), timeout_seconds=t)
    elif cmd == "audio-to-text":
        if not Path(args.file).exists():
            eprint(error_line("app audio-to-text failed", f"file not found: {args.file}"))
            return 1
        r = post_multipart(base_url, app_key, "/v1/audio-to-text", args.file, fields={"user": args.user}, file_field="file", timeout_seconds=max(t, 120))
    elif cmd == "text-to-audio":
        if not (args.text or args.message_id):
            eprint(error_line("app text-to-audio failed", "provide --text or --message-id"))
            return 1
        body = {"user": args.user}
        if args.message_id:
            body["message_id"] = args.message_id
        else:
            body["text"] = args.text
        r = post_binary(base_url, app_key, "/v1/text-to-audio", body, args.output, timeout_seconds=max(t, 120))
    else:
        eprint(error_line("app command failed", f"unhandled runtime command: {cmd}"))
        return 1

    ok = 200 <= r.status_code < 300
    print_json({"ok": ok, "command": cmd, "status_code": r.status_code, "result": r.payload if ok else r.text})
    return 0 if ok else 1


def _list_all_apps(client, limit: int = 100, max_pages: int = 100) -> list[dict]:
    """Fetch ALL workspace apps across pages (apps_list is capped per page).

    Loops pages until fewer than `limit` rows come back, `has_more` is false, or
    `total` is reached. Instances with >100 apps otherwise only see page 1.
    """
    collected: list[dict] = []
    seen: set[str] = set()
    for page in range(1, max_pages + 1):
        res = client.apps_list(page, limit)
        if not (200 <= res.status_code < 300):
            break
        payload = res.payload if isinstance(res.payload, dict) else {}
        rows = payload.get("data") or []
        for a in rows:
            aid = str(a.get("id", "") or "")
            if aid and aid not in seen:
                seen.add(aid)
                collected.append(a)
        total = payload.get("total")
        has_more = payload.get("has_more")
        if has_more is False:
            break
        if isinstance(total, int) and len(collected) >= total:
            break
        if len(rows) < limit:
            break
    collected.sort(key=lambda a: (str(a.get("created_at", "") or ""), str(a.get("id", "") or "")))
    return collected


def _preflight_dedup_check(args, config, yaml_content: str) -> tuple[bool, dict]:
    """Guard against creating duplicate live apps by name before importing.

    Returns (proceed, info). proceed=False means block. Update modes bypass the
    guard: an explicit --app-id (update-in-place) always proceeds; --update-if-exists
    resolves a single same-name live app and sets args.app_id so the import updates
    it instead of creating a duplicate. Fails open (proceed=True with a warning) when
    the live-app listing can't be reached. Bypassed by --allow-duplicate.
    """
    # Explicit update target -> always proceed (updating is intentional same-name).
    if str(getattr(args, "app_id", "") or "").strip():
        return True, {"dedup": "update-in-place", "app_id": args.app_id}
    if getattr(args, "allow_duplicate", False):
        return True, {"dedup": "skipped (--allow-duplicate)"}
    try:
        import yaml as _yaml

        document = _yaml.safe_load(yaml_content)
        app_name = str((document.get("app", {}) if isinstance(document, dict) else {}).get("name", "") or "").strip()
    except Exception:
        app_name = ""
    if not app_name:
        return True, {"dedup": "no app.name in DSL; guard skipped"}
    try:
        client = _console_client(args, config)
        live = _list_all_apps(client)
        existing = find_live_apps_by_name(live or [], app_name)
    except Exception as exc:
        return True, {"dedup": f"check failed ({exc}); proceeding (fail-open)"}
    if existing:
        # --update-if-exists: auto-target a single same-name app for update.
        if getattr(args, "update_if_exists", False):
            if len(existing) == 1:
                args.app_id = existing[0]
                return True, {"dedup": "update-if-exists -> update", "app_name": app_name, "app_id": existing[0]}
            return False, {"dedup": "ambiguous", "app_name": app_name, "existing_app_ids": existing,
                           "hint": "multiple same-name apps; pass --app-id <id> to pick which to update"}
        return False, {"dedup": "blocked", "app_name": app_name, "existing_app_ids": existing}
    return True, {"dedup": "ok", "app_name": app_name}


def _cmd_dsl_import(args, config) -> int:
    dsl_path = Path(args.dsl)
    if not dsl_path.exists():
        eprint(error_line("DSL import failed", f"DSL file not found: {dsl_path}"))
        return 1
    yaml_content = dsl_path.read_text(encoding="utf-8")

    if not args.skip_validate:
        import yaml as _yaml

        try:
            document = _yaml.safe_load(yaml_content)
        except Exception as exc:
            eprint(error_line("DSL import failed", f"DSL is not valid YAML: {exc}"))
            return 1
        report = validate_dsl(document)
        if not report.ok:
            print_json({"ok": False, "stage": "validate", "errors": report.errors, "warnings": report.warnings})
            return 1

    # Pre-import dedup guard: block same-name apps unless an update mode / --allow-duplicate.
    proceed, dedup_info = _preflight_dedup_check(args, config, yaml_content)
    if not proceed:
        existing_ids = dedup_info.get("existing_app_ids") or []
        first_id = existing_ids[0] if existing_ids else "<app_id>"
        eprint(error_line(
            "DSL import blocked (duplicate name)",
            f"A live app named '{dedup_info.get('app_name')}' already exists: {existing_ids}.",
            f"To UPDATE it in place: --app-id {first_id} (or --update-if-exists for a single match). "
            "To create a separate copy anyway: --allow-duplicate. Or rename the app in the DSL.",
        ))
        print_json({"ok": False, "stage": "dedup", **dedup_info})
        return 1

    if args.via in ("auto", "api"):
        handled, payload = _dsl_import_via_api(args, config, yaml_content)
        if handled:
            if payload.get("ok"):
                _maybe_register_import(args, config, dsl_path, yaml_content, payload)
                _maybe_create_key_and_smoke(args, config, payload)
            print_json(payload)
            return 0 if payload.get("ok") else 1
        # fall through to browser fallback under --via auto

    # Browser track (explicit --via browser or auto fallback)
    try:
        if not config.base_url:
            raise StudioAutomationError("base_url is required before browser automation can run")
        payload = login_and_import_dsl(
            base_url=config.base_url,
            dsl_path=dsl_path,
            username_env=args.username_env,
            password_env=args.password_env,
            headless=not args.headed,
        )
    except Exception as exc:
        eprint(error_line("DSL import failed (browser track)", str(exc)))
        return 1
    payload = dict(payload) if isinstance(payload, dict) else {"result": payload}
    payload["track"] = "browser"
    _maybe_register_import(args, config, dsl_path, yaml_content, payload)
    _maybe_create_key_and_smoke(args, config, payload)
    print_json(payload)
    return 0


def _cmd_dsl_export(args, config) -> int:
    base_url, console_key = _resolve_console_credential(args, config)
    if not base_url:
        eprint(error_line("DSL export failed", "No base_url configured for Console API export"), file=sys.stderr)
        return 1
    if not console_key:
        eprint(error_line("DSL export failed", "No console_key configured (set config profile or --console-key)"), file=sys.stderr)
        return 1
    try:
        auth = ConsoleAuth.detect(console_key)
    except ValueError as exc:
        eprint(error_line("DSL export failed", str(exc)), file=sys.stderr)
        return 1
    client = ConsoleApiClient(base_url, auth, config.timeout_seconds)

    # --all: full backup of every live app's DSL into --output-dir
    if getattr(args, "all", False):
        out_dir = Path(args.output_dir or "dify-backup")
        out_dir.mkdir(parents=True, exist_ok=True)
        apps = _list_all_apps(client)
        exported, failed = [], []
        for app in apps:
            app_id = str(app.get("id", "") or "")
            if not app_id:
                continue
            res = client.app_export_dsl(app_id)
            if 200 <= res.status_code < 300:
                data = res.payload.get("data", "") if isinstance(res.payload, dict) else ""
                (out_dir / f"{app_id}.dify.yml").write_text(data, encoding="utf-8")
                exported.append(app_id)
            else:
                failed.append({"app_id": app_id, "status_code": res.status_code})
        print_json({"ok": not failed, "backup_dir": str(out_dir), "total_apps": len(apps),
                    "exported": len(exported), "failed": failed})
        return 0 if not failed else 1

    if not args.app_id:
        eprint(error_line("DSL export failed", "provide --app-id, or --all with --output-dir"), file=sys.stderr)
        return 1
    result = client.app_export_dsl(args.app_id)
    if not (200 <= result.status_code < 300):
        eprint(error_line("DSL export failed", f"status={result.status_code}", result.text), file=sys.stderr)
        return 1
    data = result.payload.get("data", "") if isinstance(result.payload, dict) else ""
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(data, encoding="utf-8")
        print_json({"ok": True, "app_id": args.app_id, "output": str(out_path), "bytes": len(data)})
    else:
        print(data)
    return 0


def _normalize_dsl_for_diff(text: str) -> list[str]:
    """Normalize a DSL YAML string to sorted-key canonical lines for a stable diff."""
    import yaml as _yaml

    try:
        doc = _yaml.safe_load(text)
    except Exception:
        return (text or "").splitlines()
    dumped = _yaml.safe_dump(doc, allow_unicode=True, sort_keys=True, default_flow_style=False)
    return dumped.splitlines()


def _cmd_dsl_diff(args, config) -> int:
    """Diff a local DSL file against the live app's exported DSL (preview an update)."""
    import difflib

    local_path = Path(args.dsl)
    if not local_path.exists():
        eprint(error_line("DSL diff failed", f"local DSL not found: {local_path}"))
        return 1
    try:
        client = _console_client(args, config)
    except Exception as exc:
        eprint(error_line("DSL diff failed", str(exc)))
        return 1
    exported = client.app_export_dsl(args.app_id)
    if not (200 <= exported.status_code < 300):
        eprint(error_line("DSL diff failed", f"export status={exported.status_code}", exported.text))
        return 1
    live_text = exported.payload.get("data", "") if isinstance(exported.payload, dict) else ""
    local_text = local_path.read_text(encoding="utf-8")
    live_lines = _normalize_dsl_for_diff(live_text)
    local_lines = _normalize_dsl_for_diff(local_text)
    diff = list(difflib.unified_diff(live_lines, local_lines, fromfile=f"live:{args.app_id}", tofile=f"local:{local_path.name}", lineterm=""))
    added = sum(1 for d in diff if d.startswith("+") and not d.startswith("+++"))
    removed = sum(1 for d in diff if d.startswith("-") and not d.startswith("---"))
    identical = not diff
    print_json({"ok": True, "app_id": args.app_id, "identical": identical, "added_lines": added, "removed_lines": removed})
    if diff:
        print("\n".join(diff))
    return 0


def _cmd_dsl_lint(args, config) -> int:
    """Static-analyze a local DSL: secrets, dangling var refs, empty model refs."""
    import yaml as _yaml

    path = Path(args.dsl)
    if not path.exists():
        eprint(error_line("DSL lint failed", f"file not found: {path}"))
        return 1
    try:
        document = _yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        eprint(error_line("DSL lint failed", f"not valid YAML: {exc}"))
        return 1
    report = lint_dsl(document)
    print_json(report)
    if report["errors"]:
        return 1
    if getattr(args, "strict", False) and report["warnings"]:
        return 1
    return 0


def _cmd_dsl_retarget(args, config) -> int:
    """Rewrite the model provider+name across a DSL's LLM/agent nodes."""
    import yaml as _yaml

    path = Path(args.dsl)
    if not path.exists():
        eprint(error_line("DSL retarget failed", f"file not found: {path}"))
        return 1
    try:
        document = _yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        eprint(error_line("DSL retarget failed", f"not valid YAML: {exc}"))
        return 1
    document, changed = retarget_dsl(document, args.provider, args.model, args.mode)
    out_path = Path(args.output) if args.output else path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(_yaml.safe_dump(document, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print_json({"ok": True, "dsl": str(path), "output": str(out_path), "provider": args.provider,
                "model": args.model, "models_changed": changed})
    return 0


def _cmd_dsl_apply(args, config) -> int:
    """Declaratively sync a folder of DSL files to live apps.

    For each DSL: resolve app by ``app.name`` against live apps -> update in place
    if exactly one match, create if none, skip if ambiguous. Idempotent (GitOps).
    """
    import yaml as _yaml

    src = Path(args.dir)
    if not src.is_dir():
        eprint(error_line("DSL apply failed", f"not a directory: {src}"))
        return 1
    files = sorted([p for p in src.iterdir() if p.suffix in (".yml", ".yaml") and p.is_file()])
    if not files:
        eprint(error_line("DSL apply failed", f"no *.yml/*.yaml files in {src}"))
        return 1
    try:
        client = _console_client(args, config)
    except Exception as exc:
        eprint(error_line("DSL apply failed", str(exc)))
        return 1
    live = _list_all_apps(client)
    results = []
    for f in files:
        text = f.read_text(encoding="utf-8")
        try:
            doc = _yaml.safe_load(text)
            name = str((doc.get("app", {}) if isinstance(doc, dict) else {}).get("name", "") or "").strip()
        except Exception as exc:
            results.append({"file": f.name, "action": "error", "error": f"invalid YAML: {exc}"})
            continue
        if not name:
            results.append({"file": f.name, "action": "skip", "reason": "no app.name"})
            continue
        matches = find_live_apps_by_name(live, name)
        if len(matches) > 1:
            results.append({"file": f.name, "name": name, "action": "skip", "reason": "ambiguous (multiple same-name apps)", "app_ids": matches})
            continue
        action = "update" if matches else "create"
        target_app_id = matches[0] if matches else ""
        if args.dry_run:
            results.append({"file": f.name, "name": name, "action": f"would-{action}", "app_id": target_app_id})
            continue
        res = client.app_import_dsl(text, app_id=target_app_id)
        payload = res.payload if isinstance(res.payload, dict) else {}
        ok = 200 <= res.status_code < 300 and str(payload.get("status", "")).startswith("completed")
        app_id = str(payload.get("app_id", "") or target_app_id)
        entry = {"file": f.name, "name": name, "action": action, "ok": ok, "app_id": app_id, "status_code": res.status_code}
        if ok and args.publish and app_id:
            pub = client.app_workflow_publish(app_id)
            entry["published"] = 200 <= pub.status_code < 300
        results.append(entry)
    summary = {"created": sum(1 for r in results if r.get("action") == "create" and r.get("ok")),
               "updated": sum(1 for r in results if r.get("action") == "update" and r.get("ok")),
               "skipped": sum(1 for r in results if str(r.get("action", "")).startswith(("skip", "would"))),
               "failed": sum(1 for r in results if r.get("ok") is False or r.get("action") == "error")}
    all_ok = summary["failed"] == 0
    print_json({"ok": all_ok, "dir": str(src), "dry_run": bool(args.dry_run), "files": len(files),
                "summary": summary, "results": results})
    return 0 if all_ok else 1


def _cmd_registry_sync(args, config) -> int:
    """Backfill the ledger from live apps: upsert any untracked live app as a ledger entry."""
    try:
        root = _require_workspace(config)
        client = _console_client(args, config)
    except Exception as exc:
        eprint(error_line("registry sync failed", str(exc)))
        return 1
    live = client.apps_list(1, 100)
    if not (200 <= live.status_code < 300):
        eprint(error_line("registry sync failed", f"apps_list status={live.status_code}", live.text))
        return 1
    live_data = _list_all_apps(client)
    tracked = {str(e.get("app_id", "") or "") for e in list_registry_resources(root) if e.get("app_id")}
    used_ids = {str(e.get("resource_id", "") or "") for e in list_registry_resources(root)}
    added: list[dict] = []
    for app in (live_data or []):
        app_id = str(app.get("id", "") or "")
        if not app_id or app_id in tracked:
            continue
        name = str(app.get("name", "") or "")
        try:
            rid = validate_resource_id(derive_resource_id(name))
        except Exception:
            rid = "app-" + app_id[:8]
        if rid in used_ids:  # avoid resource_id collision across same-name apps
            rid = f"{rid}-{app_id[:8]}"
        used_ids.add(rid)
        entry = {"resource_id": rid, "app_id": app_id, "app_name": name, "title": name,
                 "mode": str(app.get("mode", "") or ""), "status": args.status}
        added.append(entry)
        if not args.dry_run:
            try:
                upsert_registry_resource(root, entry)
            except Exception as exc:
                entry["error"] = str(exc)
    print_json({"ok": True, "dry_run": bool(args.dry_run), "already_tracked": len(tracked),
                "backfilled": len(added), "entries": [{"resource_id": e["resource_id"], "app_id": e["app_id"], "name": e["app_name"]} for e in added]})
    return 0


def _cmd_registry_prune_duplicates(args, config) -> int:
    """Plan (default) or apply cleanup of duplicate-name live apps, keeping one per name."""
    try:
        root = _require_workspace(config)
        client = _console_client(args, config)
    except Exception as exc:
        eprint(error_line("registry prune-duplicates failed", str(exc)))
        return 1
    live = client.apps_list(1, 100)
    if not (200 <= live.status_code < 300):
        eprint(error_line("registry prune-duplicates failed", f"apps_list status={live.status_code}", live.text))
        return 1
    live_data = _list_all_apps(client)
    groups: dict[str, list[dict]] = {}
    for app in (live_data or []):
        nm = str(app.get("name", "") or "")
        if nm:
            groups.setdefault(nm, []).append(app)
    plan: list[dict] = []
    for nm, apps in groups.items():
        if len(apps) < 2:
            continue
        ordered = sorted(apps, key=lambda a: str(a.get("created_at", "") or ""))
        keep = ordered[-1] if args.keep == "newest" else ordered[0]
        for a in apps:
            if str(a.get("id")) != str(keep.get("id")):
                plan.append({"name": nm, "delete_app_id": str(a.get("id")), "keep_app_id": str(keep.get("id"))})
    applied = []
    if args.apply:
        for item in plan:
            res = client.app_delete(item["delete_app_id"])
            ok = 200 <= res.status_code < 300
            if ok:
                forget_unified_app_key(item["delete_app_id"])
                r2, rid = _ledger_entry_by_app_id(config, item["delete_app_id"])
                if r2 and rid:
                    try:
                        upsert_registry_resource(r2, {"resource_id": rid, "status": "deprecated"})
                    except Exception:
                        pass
            applied.append({**item, "deleted": ok, "status_code": res.status_code})
    print_json({"ok": True, "apply": bool(args.apply), "keep": args.keep,
                "duplicate_groups": len({p["name"] for p in plan}), "surplus_apps": len(plan),
                "plan": plan if not args.apply else None, "applied": applied if args.apply else None})
    if not args.apply and plan:
        print(warning_line("dry-run", f"{len(plan)} surplus app(s) across {len({p['name'] for p in plan})} name group(s) would be deleted; re-run with --apply to execute."), file=sys.stderr)
    return 0


def _list_all_datasets(client, limit: int = 30, max_pages: int = 100) -> list[dict]:
    """Fetch ALL knowledge bases across pages (datasets list is capped per page)."""
    collected: list[dict] = []
    seen: set[str] = set()
    for page in range(1, max_pages + 1):
        res = client.datasets_list(page, limit)
        if not (200 <= res.status_code < 300):
            break
        payload = res.payload if isinstance(res.payload, dict) else {}
        rows = payload.get("data") or []
        for d in rows:
            did = str(d.get("id", "") or "")
            if did and did not in seen:
                seen.add(did)
                collected.append(d)
        if payload.get("has_more") is False:
            break
        total = payload.get("total")
        if isinstance(total, int) and len(collected) >= total:
            break
        if len(rows) < limit:
            break
    collected.sort(key=lambda d: (str(d.get("created_at", "") or ""), str(d.get("id", "") or "")))
    return collected


def _cmd_dataset(args, config) -> int:
    """Manage Dify knowledge bases (datasets) via the Console API."""
    try:
        client = _console_client(args, config)
    except Exception as exc:
        eprint(error_line("dataset command failed", str(exc)), file=sys.stderr)
        return 1
    sub = args.dataset_command
    limit = int(getattr(args, "limit", "30") or "30")

    if sub == "list":
        rows = _list_all_datasets(client, limit)
        name_filter = str(getattr(args, "name", "") or "").strip().lower()
        if name_filter:
            rows = [d for d in rows if name_filter in str(d.get("name", "") or "").lower()]
        items = [{"id": d.get("id"), "name": d.get("name"), "documents": d.get("document_count"),
                  "indexing": d.get("indexing_technique"), "permission": d.get("permission")} for d in rows]
        print_json({"ok": True, "total": len(items), "datasets": items})
        return 0
    if sub == "show":
        r = client.dataset_get(args.dataset_id)
        ok = 200 <= r.status_code < 300
        print_json({"ok": ok, "status_code": r.status_code, "dataset": r.payload if ok else r.text})
        return 0 if ok else 1
    if sub == "documents":
        r = client.dataset_documents(args.dataset_id, 1, limit)
        ok = 200 <= r.status_code < 300
        data = r.payload.get("data") if isinstance(r.payload, dict) else []
        docs = [{"id": d.get("id"), "name": d.get("name"), "status": d.get("indexing_status"),
                 "words": d.get("word_count")} for d in (data or [])]
        print_json({"ok": ok, "status_code": r.status_code, "dataset_id": args.dataset_id, "total": len(docs), "documents": docs})
        return 0 if ok else 1
    if sub == "create":
        r = client.dataset_create(args.name, args.indexing_technique, args.permission, args.description)
        ok = 200 <= r.status_code < 300
        payload = r.payload if isinstance(r.payload, dict) else {}
        print_json({"ok": ok, "status_code": r.status_code, "dataset_id": payload.get("id"), "name": payload.get("name"),
                    "indexing": payload.get("indexing_technique"), "result": payload if ok else r.text})
        return 0 if ok else 1
    if sub == "delete":
        if not getattr(args, "yes", False):
            eprint(error_line("dataset delete blocked", "destructive: deleting a knowledge base removes all its documents.", "Re-run with --yes to confirm."), file=sys.stderr)
            print_json({"ok": False, "stage": "confirm", "dataset_id": args.dataset_id, "requires": "--yes"})
            return 1
        r = client.dataset_delete(args.dataset_id)
        ok = 200 <= r.status_code < 300
        print_json({"ok": ok, "status_code": r.status_code, "dataset_id": args.dataset_id, "action": "deleted"})
        return 0 if ok else 1
    if sub == "add-doc":
        text = args.text
        if args.file:
            fp = Path(args.file)
            if not fp.exists():
                eprint(error_line("dataset add-doc failed", f"file not found: {fp}"))
                return 1
            text = fp.read_text(encoding="utf-8")
        if not text.strip():
            eprint(error_line("dataset add-doc failed", "provide --text or a non-empty --file"))
            return 1
        ds_key = str(getattr(args, "dataset_key", "") or "").strip()
        if not ds_key:
            kr = client.dataset_api_keys()
            kdata = kr.payload.get("data") if isinstance(kr.payload, dict) else []
            ds_key = str((kdata[0].get("token") if kdata else "") or "")
        if not ds_key:
            eprint(error_line("dataset add-doc failed", "no dataset service key; create one in Dify (Knowledge > API) or pass --dataset-key"))
            return 1
        body = {"name": args.name, "text": text, "indexing_technique": args.indexing_technique,
                "process_rule": {"mode": "automatic"}}
        r = post_json(config.base_url, ds_key, f"/v1/datasets/{args.dataset_id}/document/create-by-text", body, config.timeout_seconds)
        ok = 200 <= r.status_code < 300
        payload = r.payload if isinstance(r.payload, dict) else {}
        doc = payload.get("document") if isinstance(payload, dict) else {}
        print_json({"ok": ok, "status_code": r.status_code, "dataset_id": args.dataset_id,
                    "document_id": (doc or {}).get("id"), "batch": payload.get("batch"),
                    "result": payload if ok else r.text})
        return 0 if ok else 1
    eprint(error_line("dataset command failed", f"unhandled subcommand: {sub}"), file=sys.stderr)
    return 1


def _cmd_dsl_detect_version(args, config) -> int:
    """Detect DSL version by probing live Dify instance."""
    base_url, console_key = _resolve_console_credential(args, config)
    if not base_url:
        eprint(error_line("detect-version failed", "No base_url configured"))
        return 1
    if not console_key:
        eprint(error_line("detect-version failed", "No console_key configured"))
        return 1
    try:
        auth = ConsoleAuth.detect(console_key)
    except ValueError as exc:
        eprint(error_line("detect-version failed", str(exc)))
        return 1
    client = ConsoleApiClient(base_url, auth, config.timeout_seconds)
    app_id = args.app_id.strip() or None
    try:
        dsl_version, source = detect_dsl_version(client, app_id=app_id, fallback_mode=args.fallback_mode)
    except RuntimeError as exc:
        eprint(error_line("detect-version failed", str(exc)))
        return 1
    print_json(
        {
            "ok": True,
            "dsl_version": dsl_version,
            "source": source,
            "message": (
                "Use this value via `--dsl-version <version>` or save to config for future scaffolding."
            ),
        }
    )
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    global _QUIET
    _QUIET = bool(getattr(args, "quiet", False))
    if getattr(args, "verbose", False):
        eprint(f"[verbose] difyctl {__version__} command={getattr(args, 'command', '')}")

    # ── Role-based access control（Dify 资源治理场景）───────────
    # difyctl 命令面大（40+ 子命令），按 Dify 资源治理语义分层：
    # - 破坏性动作（remove）：删应用/资源/注册表条目 → maintainer
    # - 登记/创建/导入/草稿类（add/create*/import*/upsert/update/intake/
    #   scaffold/draft/duplicate*/edit*/workflow-create/reconcile 执行）：
    #   可重入的资源治理日常 → contributor
    # - 读操作（list/show/info/diff/export*/plan/validate*/meta 等）与
    #   本地 config → 开放
    from .role import require_role, check_dry_run_override
    _DESTS = ("app_command", "dsl_command", "resource_command", "registry_command",
              "batch_command", "reconcile_command", "workflow_command",
              "studio_command", "provider_command", "plugin_command")
    _sub = None
    for _d in _DESTS:
        _sub = getattr(args, _d, None)
        if _sub:
            break
    if _sub and args.command != "config":
        _write_prefixes = ("add", "create", "import", "upsert", "update", "intake",
                           "scaffold", "draft", "duplicate", "edit", "capture", "apply")
        if _sub == "remove" or _sub.startswith("remove-"):
            require_role("maintainer", f"{args.command} {_sub}")
        elif any(_sub == p or _sub.startswith(p + "-") for p in _write_prefixes):
            if not check_dry_run_override(args, "contributor"):
                require_role("contributor", f"{args.command} {_sub}")

    config_path, config = _resolve_runtime_config(args)

    if args.command == "config" and args.config_command == "init":
        if config_path.exists() and not args.force:
            eprint(error_line("Config init refused", "Config file already exists", "rerun with --force to overwrite"))
            return 1
        initial = AppConfig(
            base_url=normalize_base_url(args.base_url),
            app_api_key=args.app_api_key.strip(),
            workspace_dir=args.workspace_dir.strip(),
            timeout_seconds=args.timeout_seconds,
        )
        save_config(initial, config_path)
        payload = {"status": "initialized", "config_path": str(config_path)}
        if args.json:
            print_json(payload)
        else:
            print(success_line("Config initialized", str(config_path), "run difyctl doctor"))
        return 0

    if args.command == "config" and args.config_command == "show":
        payload = config.to_dict()
        payload["config_path"] = str(config_path)
        payload["config_exists"] = config_path.exists()
        if args.json:
            print_json(payload)
        else:
            print_json(payload)
        return 0

    if args.command == "doctor":
        payload = _doctor_payload(config_path, config)
        if args.json:
            print_json(payload)
        else:
            ready = payload["ready_for_remote_inspect"] or payload["ready_for_resource_capture"]
            if ready:
                print(success_line("Doctor complete", f"config={payload['config_exists']}; workspace={payload['workspace_dir'] or '<unset>'}"))
            else:
                print(warning_line("Doctor complete", "Neither remote inspect nor local workspace capture is fully configured", "run difyctl config init"))
        return 0

    if args.command == "plugin":
        return _cmd_plugin(args, config)

    if args.command == "app" and args.app_command == "keys":
        return _cmd_app_keys(args, config)
    if args.command == "app" and args.app_command == "run":
        return _cmd_app_run(args, config)
    if args.command == "app" and args.app_command == "publish":
        return _cmd_app_publish(args, config)

    if args.command == "app" and args.app_command == "annotations":
        return _cmd_app_annotations(args, config)
    if args.command == "app" and args.app_command in _APP_RUNTIME_COMMANDS:
        return _cmd_app_runtime(args, config)
    if args.command == "app" and args.app_command in ("delete", "rename"):
        return _cmd_app_lifecycle(args, config)

    if args.command == "app" and args.app_command in APP_ENDPOINTS:
        try:
            _require_remote(config)
            effective_base_url, effective_app_api_key, _ = _resolve_effective_remote_config(config)
            result = get_json(effective_base_url, effective_app_api_key, APP_ENDPOINTS[args.app_command], config.timeout_seconds)
        except Exception as exc:
            eprint(error_line("App inspect failed", str(exc)))
            return 1
        payload = {
            "command": args.app_command,
            "status_code": result.status_code,
            "payload": result.payload,
        }
        if args.json:
            print_json(payload)
        else:
            print_json(payload)
        return 0 if 200 <= result.status_code < 300 else 1

    if args.command == "dsl" and args.dsl_command == "summarize":
        try:
            payload = summarize_dsl(Path(args.path))
        except Exception as exc:
            eprint(error_line("DSL summarize failed", str(exc)))
            return 1
        if args.json:
            print_json(payload)
        else:
            print_json(payload)
        return 0

    if args.command == "dsl" and args.dsl_command == "validate":
        try:
            import yaml as _yaml

            document = _yaml.safe_load(Path(args.path).read_text(encoding="utf-8"))
        except Exception as exc:
            eprint(error_line("DSL validate failed", str(exc)))
            return 1
        report = validate_dsl(document, target_version=args.target_version or None)
        payload = report.to_dict()
        payload["path"] = str(args.path)
        strict_fail = args.strict and bool(report.warnings)
        print_json(payload)
        return 0 if report.ok and not strict_fail else 1

    if args.command == "dsl" and args.dsl_command == "import":
        return _cmd_dsl_import(args, config)

    if args.command == "dsl" and args.dsl_command == "export":
        return _cmd_dsl_export(args, config)

    if args.command == "dsl" and args.dsl_command == "diff":
        return _cmd_dsl_diff(args, config)

    if args.command == "dsl" and args.dsl_command == "lint":
        return _cmd_dsl_lint(args, config)

    if args.command == "dsl" and args.dsl_command == "retarget":
        return _cmd_dsl_retarget(args, config)

    if args.command == "dsl" and args.dsl_command == "apply":
        return _cmd_dsl_apply(args, config)

    if args.command == "dsl" and args.dsl_command == "detect-version":
        return _cmd_dsl_detect_version(args, config)

    if args.command == "resource" and args.resource_command == "init":
        try:
            root = _require_workspace(config)
            validate_resource_id(args.resource_id)
            record = ensure_resource(
                root,
                resource_id=args.resource_id,
                mode=args.mode,
                title=args.title,
                app_id=args.app_id,
                app_name=args.app_name,
                tags=list(args.tag),
            )
            registry_written = upsert_registry_resource(
                root,
                {
                    "resource_id": args.resource_id,
                    "mode": args.mode,
                    "title": args.title or args.resource_id,
                    "app_id": args.app_id,
                    "app_name": args.app_name,
                    "tags": list(args.tag),
                    "dsl_path": canonical_dsl_path(args.resource_id) if args.dsl else "",
                },
            )
            captured = None
            if args.dsl:
                captured = capture_dsl(root, args.resource_id, Path(args.dsl), label="init", promote=True)
        except Exception as exc:
            eprint(error_line("Resource init failed", str(exc)))
            return 1
        payload = {
            "resource": {
                "resource_id": record.resource_id,
                "mode": record.mode,
                "title": record.title,
                "path": str(record.path),
                "app_id": record.app_id,
                "app_name": record.app_name,
                "tags": list(record.tags),
                "updated_at": record.updated_at,
            },
            "captured": captured,
            "registry_path": str(registry_written),
        }
        if args.json:
            print_json(payload)
        else:
            print_json(payload)
        return 0

    if args.command == "resource" and args.resource_command == "capture":
        try:
            root = _require_workspace(config)
            payload = capture_dsl(root, args.resource_id, Path(args.dsl), label=args.label, promote=not args.no_promote)
        except Exception as exc:
            eprint(error_line("Resource capture failed", str(exc)))
            return 1
        if args.json:
            print_json(payload)
        else:
            print_json(payload)
        return 0

    if args.command == "resource" and args.resource_command == "list":
        try:
            root = _require_workspace(config)
            records = scan_resources(root)
        except Exception as exc:
            eprint(error_line("Resource list failed", str(exc)))
            return 1
        payload = [
            {
                "resource_id": item.resource_id,
                "mode": item.mode,
                "title": item.title,
                "app_id": item.app_id,
                "app_name": item.app_name,
                "tags": list(item.tags),
                "updated_at": item.updated_at,
            }
            for item in records
        ]
        if args.json:
            print_json(payload)
        else:
            print_json(payload)
        return 0

    if args.command == "resource" and args.resource_command == "show":
        try:
            root = _require_workspace(config)
            record = read_resource(resource_dir(root, args.resource_id))
        except Exception as exc:
            eprint(error_line("Resource show failed", str(exc)))
            return 1
        payload = {
            "resource_id": record.resource_id,
            "mode": record.mode,
            "title": record.title,
            "path": str(record.path),
            "app_id": record.app_id,
            "app_name": record.app_name,
            "tags": list(record.tags),
            "updated_at": record.updated_at,
        }
        if args.json:
            print_json(payload)
        else:
            print_json(payload)
        return 0

    if args.command == "registry" and args.registry_command == "init":
        try:
            root = _require_workspace(config)
            path = init_registry(root, force=args.force)
        except Exception as exc:
            eprint(error_line("Registry init failed", str(exc)))
            return 1
        print_json({"registry_path": str(path)})
        return 0

    if args.command == "registry" and args.registry_command == "audit":
        try:
            root = _require_workspace(config)
            client = _console_client(args, config)
            live_data = _list_all_apps(client)
            report = audit_against_live(list_registry_resources(root), live_data or [])
            report["ok"] = True
            print_json(report)
            return 0
        except Exception as exc:
            eprint(error_line("registry audit failed", str(exc)))
            return 1

    if args.command == "registry" and args.registry_command == "sync":
        return _cmd_registry_sync(args, config)

    if args.command == "registry" and args.registry_command == "prune-duplicates":
        return _cmd_registry_prune_duplicates(args, config)

    if args.command == "dataset":
        return _cmd_dataset(args, config)

    if args.command == "registry" and args.registry_command == "list":
        try:
            root = _require_workspace(config)
            entries = list_registry_resources(root)
        except Exception as exc:
            eprint(error_line("Registry list failed", str(exc)))
            return 1
        print_json(entries)
        return 0

    if args.command == "registry" and args.registry_command == "show":
        try:
            root = _require_workspace(config)
            entry = get_registry_resource(root, args.resource_id)
            if entry is None:
                raise FileNotFoundError(f"Registry entry not found: {args.resource_id}")
        except Exception as exc:
            eprint(error_line("Registry show failed", str(exc)))
            return 1
        print_json(entry)
        return 0

    if args.command == "registry" and args.registry_command == "upsert":
        try:
            root = _require_workspace(config)
            validate_resource_id(args.resource_id)
            if registry_is_legacy_only(root):
                print(warning_line("Legacy ledger", "reading resources.yml; it will be migrated to ledger.yaml on this write."), file=sys.stderr)
            path = upsert_registry_resource(
                root,
                {
                    "resource_id": args.resource_id,
                    "mode": args.mode,
                    "title": args.title,
                    "app_id": args.app_id,
                    "app_name": args.app_name,
                    "tags": list(args.tag),
                    "dsl_path": args.dsl_path,
                },
            )
        except Exception as exc:
            eprint(error_line("Registry upsert failed", str(exc)))
            return 1
        print_json({"registry_path": str(path), "resource_id": args.resource_id})
        return 0

    if args.command == "batch" and args.batch_command == "plan":
        try:
            root = _require_workspace(config)
            entries = list_registry_resources(root)
            filtered = batch_filter(entries, mode=args.mode, tag=args.tag, selector=args.selector)
        except Exception as exc:
            eprint(error_line("Batch plan failed", str(exc)))
            return 1
        print_json(
            {
                "filters": {"mode": args.mode, "tag": args.tag, "selector": args.selector},
                "count": len(filtered),
                "items": filtered,
            }
        )
        return 0

    if args.command == "reconcile" and args.reconcile_command == "show":
        try:
            payload = _build_reconcile_payload(config, args.resource_id)
        except Exception as exc:
            eprint(error_line("Reconcile failed", str(exc)))
            return 1
        print_json(payload)
        return 0

    if args.command == "reconcile" and args.reconcile_command == "diff-only":
        try:
            payload = _build_reconcile_payload(config, args.resource_id)
            diff_payload = _build_reconcile_diff_payload(payload)
        except Exception as exc:
            eprint(error_line("Reconcile diff failed", str(exc)))
            return 1
        print_json(diff_payload)
        return 0

    if args.command == "workflow-create" and args.workflow_command == "intake":
        try:
            payload = default_spec_payload(
                name=args.name,
                mode=args.mode,
                goal=args.goal,
                inputs=list(args.input),
                outputs=list(args.output),
                steps=list(args.step),
            )
            spec_path = write_spec(Path(args.spec_out), payload, force=args.force)
        except Exception as exc:
            eprint(error_line("Workflow intake failed", str(exc)))
            return 1
        print_json({"spec_path": str(spec_path), "payload": payload})
        return 0

    if args.command == "workflow-create" and args.workflow_command == "validate-spec":
        try:
            payload = load_spec(Path(args.spec))
            errors = validate_spec_payload(payload)
        except Exception as exc:
            eprint(error_line("Workflow spec validation failed", str(exc)))
            return 1
        print_json({"valid": not errors, "errors": errors})
        return 0 if not errors else 1

    if args.command == "workflow-create" and args.workflow_command == "scaffold":
        # Resolve DSL version priority: --dsl-version arg > config.yaml dsl_version
        # > runtime auto-detect (when 'auto') > DEFAULT_DSL_VERSION.
        cli_dsl_version = (args.dsl_version or "").strip()
        try:
            _unified = get_config()
        except Exception:
            _unified = {}
        config_dsl_version = str(_unified.get("dsl_version", "") or "").strip() if isinstance(_unified, dict) else ""

        resolved_version = ""
        detect_info: dict = {}
        want_auto = cli_dsl_version.lower() == "auto" or (not cli_dsl_version and config_dsl_version.lower() == "auto")

        if cli_dsl_version and cli_dsl_version.lower() != "auto":
            resolved_version = cli_dsl_version
        elif config_dsl_version and config_dsl_version.lower() != "auto":
            resolved_version = config_dsl_version
        elif want_auto:
            # Best-effort live detection; fall back to DEFAULT on any failure.
            base_url, console_key = _resolve_console_credential(args, config)
            try:
                if not base_url or not console_key:
                    raise RuntimeError("base_url/console_key required for auto detect")
                auth = ConsoleAuth.detect(console_key)
                client = ConsoleApiClient(base_url, auth, config.timeout_seconds)
                detected_version, source = detect_dsl_version(client, app_id=None, fallback_mode="auto")
                resolved_version = detected_version
                detect_info = {"source": source}
            except Exception as exc:
                resolved_version = DEFAULT_DSL_VERSION
                detect_info = {"source": "default-fallback", "note": f"auto-detect failed: {exc}"}
        else:
            resolved_version = DEFAULT_DSL_VERSION

        try:
            spec_payload = load_spec(Path(args.spec))
            errors = validate_spec_payload(spec_payload)
            if errors:
                raise ValueError("; ".join(errors))
            dsl_payload = scaffold_dsl_from_spec(spec_payload, dsl_version=resolved_version)
            dsl_path = write_dsl(Path(args.output), dsl_payload, force=args.force)
        except Exception as exc:
            eprint(error_line("Workflow scaffold failed", str(exc)))
            return 1

        result = {"dsl_path": str(dsl_path), "payload": dsl_payload, "dsl_version": resolved_version}
        if detect_info:
            result["detect"] = detect_info
        print_json(result)
        return 0


    if args.command == "workflow-create" and args.workflow_command == "draft":
        try:
            demand_text = Path(args.from_demand).read_text(encoding="utf-8")
            demand_lines = [line.strip("- ").strip() for line in demand_text.splitlines() if line.strip()]
            steps = demand_lines[:3] if demand_lines else ["Clarify input", "Process business logic", "Produce output"]
            payload = default_spec_payload(
                name=args.name,
                mode=args.mode,
                goal=demand_lines[0] if demand_lines else f"Implement workflow for {args.name}",
                inputs=["user_input"],
                outputs=["final_output"],
                steps=steps,
            )
            payload["workflow"]["source_demand"] = str(Path(args.from_demand))
            spec_path = write_spec(Path(args.spec_out), payload, force=args.force)
        except Exception as exc:
            eprint(error_line("Workflow draft failed", str(exc)))
            return 1
        print_json({"spec_path": str(spec_path), "payload": payload})
        return 0

    if args.command == "studio" and args.studio_command == "create-plan":
        payload = build_create_plan(
            base_url=config.base_url,
            name=args.name,
            mode=args.mode,
            description=args.description,
            dsl_path=args.dsl,
        )
        print_json(payload)
        return 0

    if args.command == "studio" and args.studio_command in {"export-plan", "duplicate-plan"}:
        try:
            root = _require_workspace(config)
            entry = get_registry_resource(root, args.resource_id)
            if entry is None:
                raise FileNotFoundError(f"Registry entry not found: {args.resource_id}")
            if args.studio_command == "export-plan":
                payload = build_export_plan(
                    base_url=config.base_url,
                    resource_id=args.resource_id,
                    app_name=str(entry.get("app_name", "")),
                    app_id=str(entry.get("app_id", "")),
                )
            else:
                payload = build_duplicate_plan(
                    base_url=config.base_url,
                    resource_id=args.resource_id,
                    app_name=str(entry.get("app_name", "")),
                    app_id=str(entry.get("app_id", "")),
                )
        except Exception as exc:
            eprint(error_line("Studio plan failed", str(exc)))
            return 1
        print_json(payload)
        return 0

    if args.command == "studio" and args.studio_command == "browser-doctor":
        effective_base_url, _, _ = _resolve_effective_remote_config(config)
        payload = browser_doctor(
            base_url=effective_base_url,
            username_env=args.username_env,
            password_env=args.password_env,
        )
        print_json(payload.__dict__)
        return 0

    if args.command == "studio" and args.studio_command == "import-dsl-run":
        try:
            if not config.base_url:
                raise StudioAutomationError("base_url is required before browser automation can run")
            payload = login_and_import_dsl(
                base_url=config.base_url,
                dsl_path=Path(args.dsl),
                username_env=args.username_env,
                password_env=args.password_env,
                headless=not args.headed,
            )
        except Exception as exc:
            eprint(error_line("Studio import run failed", str(exc)))
            return 1
        print_json(payload)
        return 0

    if args.command == "studio" and args.studio_command == "create-empty-run":
        try:
            if not config.base_url:
                raise StudioAutomationError("base_url is required before browser automation can run")
            payload = create_empty_app(
                base_url=config.base_url,
                name=args.name,
                mode=args.mode,
                description=args.description,
                username_env=args.username_env,
                password_env=args.password_env,
                headless=not args.headed,
            )
            if args.resource_id:
                root = _require_workspace(config)
                ensure_resource(
                    root,
                    resource_id=args.resource_id,
                    mode=args.mode,
                    title=args.name,
                    app_id=str(payload.get("app_id", "")),
                    app_name=args.name,
                    tags=list(args.tag),
                )
                upsert_registry_resource(
                    root,
                    {
                        "resource_id": args.resource_id,
                        "mode": args.mode,
                        "title": args.name,
                        "app_id": str(payload.get("app_id", "")),
                        "app_name": args.name,
                        "tags": list(args.tag),
                        "dsl_path": "",
                    },
                )
                payload["resource_id"] = args.resource_id
        except Exception as exc:
            eprint(error_line("Studio create run failed", str(exc)))
            return 1
        print_json(payload)
        return 0

    if args.command == "studio" and args.studio_command == "export-dsl-run":
        try:
            if not config.base_url:
                raise StudioAutomationError("base_url is required before browser automation can run")
            root = _require_workspace(config)
            entry = get_registry_resource(root, args.resource_id)
            if entry is None:
                raise FileNotFoundError(f"Registry entry not found: {args.resource_id}")
            app_name = str(entry.get("app_name", "")).strip() or str(entry.get("title", "")).strip()
            if not app_name:
                raise ValueError(f"Registry entry {args.resource_id} is missing app_name/title for Studio export")
            output_path = Path(args.output) if args.output else (resource_dir(root, args.resource_id) / "dsl" / "current.yml")
            payload = export_dsl_from_apps(
                base_url=config.base_url,
                app_name=app_name,
                output_path=output_path,
                username_env=args.username_env,
                password_env=args.password_env,
                headless=not args.headed,
            )
            if not args.no_capture:
                capture_result = capture_dsl(root, args.resource_id, Path(payload["output_path"]), label="studio-export", promote=True)
                payload["capture"] = capture_result
                upsert_registry_resource(
                    root,
                    {
                        "resource_id": str(entry.get("resource_id", args.resource_id)),
                        "mode": str(entry.get("mode", "")),
                        "title": str(entry.get("title", app_name)),
                        "app_id": str(entry.get("app_id", "")),
                        "app_name": app_name,
                        "tags": list(entry.get("tags", [])) if isinstance(entry.get("tags", []), list) else [],
                        "dsl_path": f"resources/{args.resource_id}/dsl/current{Path(payload['output_path']).suffix or '.yml'}",
                    },
                )
        except Exception as exc:
            eprint(error_line("Studio export run failed", str(exc)))
            return 1
        print_json(payload)
        return 0

    if args.command == "studio" and args.studio_command == "duplicate-run":
        try:
            if not config.base_url:
                raise StudioAutomationError("base_url is required before browser automation can run")
            root = _require_workspace(config)
            entry = get_registry_resource(root, args.resource_id)
            if entry is None:
                raise FileNotFoundError(f"Registry entry not found: {args.resource_id}")
            source_app_name = str(entry.get("app_name", "")).strip() or str(entry.get("title", "")).strip()
            if not source_app_name:
                raise ValueError(f"Registry entry {args.resource_id} is missing app_name/title for Studio duplicate")
            new_name = args.name.strip() or f"{source_app_name} Copy"
            payload = duplicate_app_from_apps(
                base_url=config.base_url,
                source_app_name=source_app_name,
                new_name=new_name,
                username_env=args.username_env,
                password_env=args.password_env,
                headless=not args.headed,
            )
            if args.new_resource_id:
                ensure_resource(
                    root,
                    resource_id=args.new_resource_id,
                    mode=str(entry.get("mode", "")),
                    title=new_name,
                    app_id=str(payload.get("app_id", "")),
                    app_name=new_name,
                    tags=list(args.tag),
                )
                upsert_registry_resource(
                    root,
                    {
                        "resource_id": args.new_resource_id,
                        "mode": str(entry.get("mode", "")),
                        "title": new_name,
                        "app_id": str(payload.get("app_id", "")),
                        "app_name": new_name,
                        "tags": list(args.tag),
                        "dsl_path": "",
                    },
                )
                payload["resource_id"] = args.new_resource_id
        except Exception as exc:
            eprint(error_line("Studio duplicate run failed", str(exc)))
            return 1
        print_json(payload)
        return 0

    if args.command == "studio" and args.studio_command == "edit-info-run":
        try:
            if not config.base_url:
                raise StudioAutomationError("base_url is required before browser automation can run")
            root = _require_workspace(config)
            entry = get_registry_resource(root, args.resource_id)
            if entry is None:
                raise FileNotFoundError(f"Registry entry not found: {args.resource_id}")
            current_app_name = str(entry.get("app_name", "")).strip() or str(entry.get("title", "")).strip()
            if not current_app_name:
                raise ValueError(f"Registry entry {args.resource_id} is missing app_name/title for Studio edit")
            new_name = args.name.strip() or current_app_name
            payload = edit_app_info_from_apps(
                base_url=config.base_url,
                app_name=current_app_name,
                new_name=new_name,
                description=args.description,
                max_active_requests=args.max_active_requests,
                username_env=args.username_env,
                password_env=args.password_env,
                headless=not args.headed,
            )
            updated_tags = list(entry.get("tags", [])) if isinstance(entry.get("tags", []), list) else []
            upsert_registry_resource(
                root,
                {
                    "resource_id": str(entry.get("resource_id", args.resource_id)),
                    "mode": str(entry.get("mode", "")),
                    "title": new_name,
                    "app_id": str(entry.get("app_id", "")),
                    "app_name": new_name,
                    "tags": updated_tags,
                    "dsl_path": str(entry.get("dsl_path", "")),
                },
            )
            ensure_resource(
                root,
                resource_id=args.resource_id,
                mode=str(entry.get("mode", "")),
                title=new_name,
                app_id=str(entry.get("app_id", "")),
                app_name=new_name,
                tags=updated_tags,
            )
        except Exception as exc:
            eprint(error_line("Studio edit run failed", str(exc)))
            return 1
        print_json(payload)
        return 0

    # ── provider handlers ──
    if args.command == "provider":
        # Resolve effective base_url and console_key
        effective_base_url = config.base_url
        effective_console_key = ""
        profile_config = resolve_active_profile(config)
        if profile_config:
            if profile_config.base_url:
                effective_base_url = profile_config.base_url
            effective_console_key = resolve_console_key(config)
        # CLI overrides
        if getattr(args, "console_key", None):
            effective_console_key = args.console_key
        if not effective_base_url:
            eprint(error_line("Provider command failed", "No base_url configured (set via config profile or --base-url)"))
            return 1
        if args.provider_command == "login":
            try:
                if not effective_base_url:
                    effective_base_url = config.base_url
                # Config governance: seed studio credentials from assets.difyctl
                # in ~/.harness-ai-kit/config.yaml so login works without env vars.
                _uname_env = getattr(args, "username_env", "DIFY_STUDIO_USERNAME")
                _pwd_env = getattr(args, "password_env", "DIFY_STUDIO_PASSWORD")
                try:
                    _cfg = get_config()
                except Exception:
                    _cfg = {}
                if isinstance(_cfg, dict):
                    if not os.environ.get(_uname_env) and str(_cfg.get("studio_username", "") or "").strip():
                        os.environ[_uname_env] = str(_cfg["studio_username"]).strip()
                    if not os.environ.get(_pwd_env) and str(_cfg.get("studio_password", "") or "").strip():
                        os.environ[_pwd_env] = str(_cfg["studio_password"]).strip()
                payload = capture_console_cookie(
                    base_url=effective_base_url,
                    username_env=_uname_env,
                    password_env=_pwd_env,
                    headless=not getattr(args, "headed", False),
                )
                # Persist the fresh cookie to config.yaml (assets.difyctl.console_key)
                # so subsequent commands work without --console-key. Skippable via
                # --no-save-console-key for one-off/ephemeral logins.
                fresh_key = str(payload.get("full_cookie_header", "") or "")
                if fresh_key and not getattr(args, "no_save_console_key", False):
                    try:
                        saved_path = write_unified_config_value("console_key", fresh_key)
                        payload["console_key_saved_to"] = str(saved_path)
                    except Exception as exc:
                        payload["console_key_save_error"] = str(exc)
                print_json(payload)
                return 0
            except StudioAutomationError as exc:
                eprint(error_line("Provider login failed", str(exc)))
                return 1

        # add-model --dry-run only builds a payload preview; no console access needed.
        if args.provider_command == "add-model" and getattr(args, "dry_run", False):
            effective_api_key = resolve_env_vars(args.api_key) if args.api_key else ""
            payload = build_model_credential_payload(
                model_name=args.model,
                model_type=args.model_type,
                api_key=effective_api_key,
                endpoint_url=args.endpoint_url,
                context_size=args.context_size,
                max_tokens=args.max_tokens,
            )
            print_json({"_dry_run": True, "provider": args.provider, "model": args.model, "payload": payload})
            return 0

        if not effective_console_key:
            eprint(error_line("Provider command failed", "No console_key configured (set via config profile or --console-key)"))
            return 1

        try:
            auth = ConsoleAuth.detect(effective_console_key)
        except ValueError as exc:
            eprint(error_line("Provider command failed", str(exc)))
            return 1

        client = ConsoleApiClient(effective_base_url, auth, config.timeout_seconds)
        no_fallback = getattr(args, "no_browser_fallback", False)

        if args.provider_command == "add":
            try:
                yaml_path = Path(args.from_yaml)
                provider = load_provider_yaml(yaml_path)
                # CLI overrides
                effective_type = args.type or provider.provider
                effective_api_key = args.api_key or provider.credentials.api_key
                effective_api_base = args.api_base or provider.credentials.api_base
                cred_name = args.name or provider.name

                # Build dry-run preview for ALL models
                if args.dry_run:
                    models_preview = []
                    for m in provider.models:
                        p = build_model_credential_payload(
                            model_name=m.model,
                            model_type="llm",
                            credential_name=cred_name,
                            api_key=effective_api_key,
                            endpoint_url=effective_api_base,
                            display_name=f"{cred_name}-{m.model}",
                        )
                        models_preview.append({"model": m.model, "payload": p})
                    print_json({"_dry_run": True, "provider_type": effective_type, "credential_name": cred_name, "model_count": len(models_preview), "models": models_preview})
                    return 0

                # Add each model via the correct credentials endpoint
                results = []
                for m in provider.models:
                    result = client.provider_add_model(
                        provider=effective_type,
                        model_name=m.model,
                        model_type="llm",
                        credential_name=cred_name,
                        api_key=effective_api_key,
                        endpoint_url=effective_api_base,
                    )
                    ok = 200 <= result.status_code < 300
                    results.append({"model": m.model, "status": "added" if ok else "failed", "status_code": result.status_code})
                    if not ok:
                        err_msg = str(result.payload.get("message", "")) if isinstance(result.payload, dict) else result.text
                        results[-1]["error"] = err_msg[:200]

                all_ok = all(r["status"] == "added" for r in results)
                print_json({"status": "completed" if all_ok else "partial", "credential_name": cred_name, "results": results})
                return 0 if all_ok else 1
            except Exception as exc:
                eprint(error_line("Provider add failed", str(exc)))
                return 1

        elif args.provider_command == "list":
            try:
                # List providers with their configured models per type
                result = client.provider_list()
                if not (200 <= result.status_code < 300):
                    print_json({"status": "error", "status_code": result.status_code, "payload": result.payload})
                    return 1
                providers = result.payload.get("data", []) if isinstance(result.payload, dict) else []
                summary = []
                for p in providers:
                    cc = p.get("custom_configuration", {}) if isinstance(p, dict) else {}
                    entry = {
                        "provider": p.get("provider", ""),
                        "label": (p.get("label", {}) or {}).get("en_US", ""),
                        "status": cc.get("status", p.get("status", "")),
                        "custom_models": [m.get("model", "") for m in (cc.get("custom_models", []) or [])],
                    }
                    summary.append(entry)
                if args.json:
                    print_json(summary)
                else:
                    for s in summary:
                        models_str = ", ".join(s["custom_models"][:10]) if s["custom_models"] else "(none)"
                        print(f"{s['label']:30s} [{s['status']:10s}] {len(s['custom_models'])} models: {models_str}")
                return 0
            except Exception as exc:
                eprint(error_line("Provider list failed", str(exc)))
                return 1

        elif args.provider_command == "test":
            try:
                result = client.provider_validate_model(
                    provider=args.provider,
                    model_name=args.model,
                    model_type=getattr(args, "model_type", "llm"),
                    api_key=getattr(args, "api_key", ""),
                    endpoint_url=getattr(args, "api_base", ""),
                )
                print_json({"provider": args.provider, "model": args.model, "status_code": result.status_code, "payload": result.payload})
                return 0 if result.status_code < 400 else 1
            except Exception as exc:
                eprint(error_line("Provider test failed", str(exc)))
                return 1

        elif args.provider_command == "remove":
            try:
                if args.dry_run:
                    print_json({"status": "dry_run", "provider": args.provider, "model": getattr(args, "model", ""), "action": "remove"})
                    return 0
                if not args.force:
                    print(warning_line("Provider remove", f"Will remove model from '{args.provider}'. Use --force to confirm."))
                    return 1
                result = client.provider_remove_model(args.provider, getattr(args, "model", ""))
                if result.status_code == 404:
                    print(warning_line("Provider remove", "Model not found — already removed"))
                    return 0
                print_json({"status": "removed" if 200 <= result.status_code < 300 else "error", "provider": args.provider})
                return 0 if 200 <= result.status_code < 300 else 1
            except Exception as exc:
                eprint(error_line("Provider remove failed", str(exc)))
                return 1

        elif args.provider_command == "update":
            try:
                yaml_path = Path(args.from_yaml)
                provider = load_provider_yaml(yaml_path)
                payload = build_add_payload(provider)
                if args.dry_run:
                    payload["_dry_run"] = True
                    payload["_target_provider"] = args.provider
                    print_json(payload)
                    return 0
                result = client.provider_update(args.provider, payload)
                print_json({"status": "updated" if 200 <= result.status_code < 300 else "error", "provider": args.provider, "status_code": result.status_code})
                return 0 if 200 <= result.status_code < 300 else 1
            except Exception as exc:
                eprint(error_line("Provider update failed", str(exc)))
                return 1

        elif args.provider_command == "batch":
            try:
                manifest_path = Path(args.manifest)
                providers = load_manifest_yaml(manifest_path)
                if args.dry_run or not args.apply:
                    summary = [{"name": p.name, "type": p.provider, "models_count": len(p.models)} for p in providers]
                    print_json({"status": "dry_run" if args.dry_run else "preview", "count": len(providers), "providers": summary})
                    return 0

                if args.apply:
                    results = []
                    for p in providers:
                        payload = build_add_payload(p)
                        result = client.provider_add(payload)
                        results.append({
                            "name": p.name,
                            "status": "created" if 200 <= result.status_code < 300 else "failed",
                            "status_code": result.status_code,
                        })
                    all_ok = all(r["status"] == "created" for r in results)
                    print_json({"status": "batch_complete", "results": results})
                    return 0 if all_ok else 1
            except Exception as exc:
                eprint(error_line("Provider batch failed", str(exc)))
                return 1

        elif args.provider_command == "models":
            try:
                result = client.provider_list_models(args.provider, model_type=args.model_type)
                if not (200 <= result.status_code < 300):
                    print_json({"status": "error", "status_code": result.status_code, "payload": result.payload})
                    return 1
                data = result.payload.get("data", []) if isinstance(result.payload, dict) else []
                models = []
                for m in data:
                    if isinstance(m, dict):
                        models.append({
                            "model": m.get("model", ""),
                            "model_type": m.get("model_type", args.model_type),
                            "status": m.get("status", ""),
                        })
                if args.json:
                    print_json({"provider": args.provider, "model_type": args.model_type, "count": len(models), "models": models})
                else:
                    print(f"{args.provider}  ({args.model_type}, {len(models)} models)")
                    for m in models:
                        print(f"  - {m['model']:40s} [{m['status']}]")
                return 0
            except Exception as exc:
                eprint(error_line("Provider models failed", str(exc)))
                return 1

        elif args.provider_command == "add-model":
            try:
                effective_api_key = resolve_env_vars(args.api_key) if args.api_key else ""
                if args.dry_run:
                    payload = build_model_credential_payload(
                        model_name=args.model,
                        model_type=args.model_type,
                        api_key=effective_api_key,
                        endpoint_url=args.endpoint_url,
                        context_size=args.context_size,
                        max_tokens=args.max_tokens,
                    )
                    print_json({"_dry_run": True, "provider": args.provider, "model": args.model, "payload": payload})
                    return 0
                result = client.provider_add_model(
                    provider=args.provider,
                    model_name=args.model,
                    model_type=args.model_type,
                    api_key=effective_api_key,
                    endpoint_url=args.endpoint_url,
                )
                ok = 200 <= result.status_code < 300
                out = {"status": "added" if ok else "error", "provider": args.provider, "model": args.model, "status_code": result.status_code}
                if not ok:
                    out["error"] = (str(result.payload.get("message", "")) if isinstance(result.payload, dict) else result.text)[:200]
                print_json(out)
                return 0 if ok else 1
            except Exception as exc:
                eprint(error_line("Provider add-model failed", str(exc)))
                return 1

        parser.print_help()
        return 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
