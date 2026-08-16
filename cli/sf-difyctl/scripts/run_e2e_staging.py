#!/usr/bin/env python3
"""Nightly end-to-end staging validation for difyctl (Q6 Option C).

Drives the full DSL lifecycle against a real (staging) Dify instance:

    scaffold spec -> scaffold DSL -> local validate -> API import
    -> verify app exists -> API export -> (optional) local capture

Credentials are read from ``~/.harness-ai-kit/config.yaml`` (assets.difyctl /
global) or from environment variables. NOTHING is
hard-coded. On completion the script prints a structured JSON report to
stdout, writes a JSONL run log, and optionally posts a summary to a
Mattermost / Apprise webhook.

Exit codes:
    0  all steps passed
    1  a validation or import/export step failed
    2  misconfiguration (missing base_url / console_key)

Usage:
    python scripts/run_e2e_staging.py \
        --base-url https://dify.staging.example.com \
        --console-key "access_token=...; csrf_token=..." \
        [--webhook https://mm.example.com/hooks/xxx] \
        [--keep-app] [--log ./logs/e2e.jsonl]

This is the CI-mock counterpart's real-machine sibling: unit tests in
``tests/`` exercise the same code paths with mocked responses, while this
script exercises them against a live Dify. It is intended to run from a
scheduled job (Qoder schedule MCP / cron / CI nightly), not in unit CI.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

# Make the difyctl package importable whether run from repo or installed.
_PKG_ROOT = Path(__file__).resolve().parents[1]
if str(_PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(_PKG_ROOT))

from difyctl.console_api import ConsoleApiClient, ConsoleAuth  # noqa: E402
from difyctl.dsl_validate import validate_dsl  # noqa: E402
from difyctl.workflow_create import (  # noqa: E402
    default_spec_payload,
    scaffold_dsl_from_spec,
)

try:  # config resolution is best-effort; CLI args always win
    from difyctl.config import get_config
except Exception:  # pragma: no cover - defensive
    get_config = None  # type: ignore

import yaml  # noqa: E402


def _utcnow() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _resolve(base_url: str, console_key: str) -> tuple[str, str]:
    """CLI args > config.yaml > environment."""
    if base_url and console_key:
        return base_url, console_key
    cfg = {}
    if get_config is not None:
        try:
            cfg = get_config() or {}
        except Exception:
            cfg = {}
    base_url = base_url or str(cfg.get("base_url", "")) or os.environ.get("DIFY_BASE_URL", "")
    console_key = (
        console_key
        or str(cfg.get("console_key", ""))
        or os.environ.get("DIFY_CONSOLE_KEY", "")
    )
    return base_url.rstrip("/"), console_key


class _Runner:
    def __init__(self, base_url: str, console_key: str, timeout: int) -> None:
        auth = ConsoleAuth.detect(console_key)
        self.base_url = base_url
        self.client = ConsoleApiClient(base_url, auth, timeout)
        self.steps: list[dict] = []

    def _record(self, name: str, ok: bool, detail: object = None) -> bool:
        self.steps.append({"step": name, "ok": ok, "detail": detail, "ts": _utcnow()})
        return ok

    def run(self, *, keep_app: bool) -> tuple[bool, dict]:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        app_name = f"difyctl-e2e-{stamp}"

        # 1) scaffold spec -> DSL
        spec = default_spec_payload(
            name=app_name,
            mode="workflow",
            goal="difyctl nightly e2e smoke",
            inputs=["probe_text"],
            outputs=["reply"],
            steps=["Echo probe"],
        )
        dsl = scaffold_dsl_from_spec(spec)
        self._record("scaffold", True, {"nodes": len(dsl["workflow"]["graph"]["nodes"])})

        # 2) local validate
        report = validate_dsl(dsl, target_version="0.6.0")
        if not self._record("validate", report.ok, {"errors": report.errors}):
            return False, self._summary(app_name, None)

        # 3) API import
        yaml_content = yaml.safe_dump(dsl, allow_unicode=True, sort_keys=False)
        result = self.client.app_import_dsl(yaml_content)
        payload = result.payload if isinstance(result.payload, dict) else {}
        status = str(payload.get("status", ""))
        import_id = str(payload.get("id", ""))
        if status == "pending" and import_id:
            confirm = self.client.app_import_confirm(import_id)
            payload = confirm.payload if isinstance(confirm.payload, dict) else payload
            result = confirm
        app_id = str(payload.get("app_id", ""))
        import_ok = 200 <= result.status_code < 300 and str(payload.get("status", "")).startswith("completed")
        if not self._record("import", import_ok, {"status_code": result.status_code, "import_status": payload.get("status"), "app_id": app_id}):
            return False, self._summary(app_name, app_id)

        # 4) verify app is listed
        apps = self.client.apps_list(page=1, limit=100)
        found = False
        if isinstance(apps.payload, dict):
            data = apps.payload.get("data", [])
            found = any(str(item.get("id")) == app_id for item in data if isinstance(item, dict))
        self._record("verify_listed", found, {"app_id": app_id})

        # 5) API export round-trip
        export = self.client.app_export_dsl(app_id)
        export_ok = 200 <= export.status_code < 300 and bool(
            isinstance(export.payload, dict) and export.payload.get("data")
        )
        exported_valid = False
        if export_ok:
            try:
                exported_doc = yaml.safe_load(export.payload["data"])
                exported_valid = validate_dsl(exported_doc).ok
            except Exception as exc:  # pragma: no cover
                self._record("export_parse", False, str(exc))
        self._record("export", export_ok and exported_valid, {"status_code": export.status_code})

        overall = all(s["ok"] for s in self.steps)
        summary = self._summary(app_name, app_id)
        summary["keep_app"] = keep_app
        if not keep_app and app_id:
            summary["cleanup_hint"] = f"Delete test app {app_id} via Studio; API delete not exercised by e2e."
        return overall, summary

    def _summary(self, app_name: str, app_id: str | None) -> dict:
        return {
            "ok": all(s["ok"] for s in self.steps),
            "base_url": self.base_url,
            "app_name": app_name,
            "app_id": app_id,
            "app_url": f"{self.base_url}/app/{app_id}/workflow" if app_id else "",
            "steps": self.steps,
            "finished_at": _utcnow(),
        }


def _notify(webhook: str, summary: dict) -> None:
    if not webhook:
        return
    status = "✅ PASS" if summary.get("ok") else "❌ FAIL"
    failed = [s["step"] for s in summary.get("steps", []) if not s["ok"]]
    text = (
        f"**difyctl nightly E2E** {status}\n"
        f"- base_url: `{summary.get('base_url')}`\n"
        f"- app: `{summary.get('app_name')}` ({summary.get('app_id') or 'n/a'})\n"
        f"- failed steps: {', '.join(failed) if failed else 'none'}\n"
        f"- finished: {summary.get('finished_at')}"
    )
    body = json.dumps({"text": text}).encode("utf-8")
    req = urllib.request.Request(webhook, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp.read()
    except Exception as exc:  # pragma: no cover - notification is best-effort
        print(f"[warn] webhook notify failed: {exc}", file=sys.stderr)


def _write_log(log_path: str, summary: dict) -> None:
    if not log_path:
        return
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(summary, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="difyctl nightly staging E2E validation")
    parser.add_argument("--base-url", default="", help="Staging Dify base URL (else config.yaml / DIFY_BASE_URL)")
    parser.add_argument("--console-key", default="", help="Console cookie header (else config.yaml / DIFY_CONSOLE_KEY)")
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout seconds")
    parser.add_argument("--webhook", default=os.environ.get("DIFYCTL_E2E_WEBHOOK", ""), help="Mattermost/Apprise incoming webhook URL")
    parser.add_argument("--log", default="", help="Append a JSONL run record to this path")
    parser.add_argument("--keep-app", action="store_true", help="Do not hint teardown of the created test app")
    args = parser.parse_args()

    base_url, console_key = _resolve(args.base_url, args.console_key)
    if not base_url or not console_key:
        report = {"ok": False, "error": "missing base_url or console_key (set --base-url/--console-key, config.yaml, or env)", "finished_at": _utcnow()}
        print(json.dumps(report, ensure_ascii=False, indent=2))
        _write_log(args.log, report)
        return 2

    runner = _Runner(base_url, console_key, args.timeout)
    ok, summary = runner.run(keep_app=args.keep_app)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    _write_log(args.log, summary)
    _notify(args.webhook, summary)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
