"""mineructl — MinerU ops CLI."""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from . import __version__
from .client import MinerUClient
from .config import load_config


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="mineructl",
        description="MinerU ops: doctor, probe, version, submit, status, result, tasks.",
    )
    p.add_argument("--version", action="version", version=f"mineructl {__version__}")
    p.add_argument("--profile", default="default", help="Profile name (default: default).")
    p.add_argument("--base-url", help="Override MinerU base URL.")
    p.add_argument("--env-file", help="Env file with MINERU_ENDPOINT.")
    p.add_argument("--timeout", type=int, default=30, help="HTTP timeout in seconds.")
    p.add_argument("--json", action="store_true", dest="json_output", help="Machine-readable JSON output.")
    sub = p.add_subparsers(dest="command", required=True, metavar="command")

    # doctor
    sub.add_parser("doctor", help="Check connectivity, health, and version.")

    # probe
    sub.add_parser("probe", help="Quick health probe (no auth required).")

    # version
    sub.add_parser("version", help="Show server version.")

    # submit
    submit_p = sub.add_parser("submit", help="Submit a document parsing task.")
    submit_p.add_argument("--url", required=True, help="Document URL to parse.")
    submit_p.add_argument("--format", default="markdown", choices=["markdown", "json"], help="Output format.")

    # status
    status_p = sub.add_parser("status", help="Query task status.")
    status_p.add_argument("task_id", help="Task ID to query.")

    # result
    result_p = sub.add_parser("result", help="Get task result.")
    result_p.add_argument("task_id", help="Task ID to get result for.")

    # tasks
    tasks_p = sub.add_parser("tasks", help="List recent tasks.")
    tasks_p.add_argument("--limit", type=int, default=20, help="Max number of tasks.")
    tasks_p.add_argument("--status", choices=["pending", "processing", "completed", "failed"], help="Filter by status.")

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        config = load_config(
            profile=args.profile,
            base_url=args.base_url,
            env_file=args.env_file,
        )
        client = MinerUClient(base_url=config.base_url, timeout=args.timeout)
        payload = _dispatch(args, client)
        _print(args, payload)
        return 0 if payload.get("ok", True) else 1
    except Exception as exc:
        payload = {"ok": False, "error": str(exc)}
        if getattr(args, "json_output", False):
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"error: {exc}", file=sys.stderr)
        return 1


def _dispatch(args: argparse.Namespace, client: MinerUClient) -> dict[str, Any]:
    if args.command == "doctor":
        return client.doctor()
    if args.command == "probe":
        return client.probe()
    if args.command == "version":
        return {"ok": True, **client.version()}
    if args.command == "submit":
        return {"ok": True, **client.submit(url=args.url, output_format=args.format)}
    if args.command == "status":
        return {"ok": True, **client.status(args.task_id)}
    if args.command == "result":
        return {"ok": True, **client.result(args.task_id)}
    if args.command == "tasks":
        return {"ok": True, **client.tasks(limit=args.limit, status=args.status)}
    raise ValueError(f"Unhandled command: {args.command}")


def _print(args: argparse.Namespace, payload: dict[str, Any]) -> None:
    if getattr(args, "json_output", False):
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    # human-readable for common commands
    if args.command == "doctor":
        for check in payload.get("checks", []):
            status = "OK" if check["ok"] else "FAIL"
            detail = check.get("error") or check.get("version") or check.get("base_url") or ""
            print(f"  [{status}] {check['name']}  {detail}")
        return
    if args.command == "probe":
        status = "OK" if payload.get("ok") else "FAIL"
        info = payload.get("info", {})
        ver = info.get("version", "") if isinstance(info, dict) else ""
        print(f"  [{status}] MinerU  {ver}")
        return
    if args.command == "version":
        print(f"  version: {payload.get('version', '?')}")
        print(f"  status:  {payload.get('status', '?')}")
        return
    # fallback: JSON
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    raise SystemExit(main())
