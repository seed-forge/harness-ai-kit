from __future__ import annotations

import json


def print_json(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def success_line(title: str, detail: str = "", next_step: str = "") -> str:
    suffix = f" | {detail}" if detail else ""
    follow = f" | Next: {next_step}" if next_step else ""
    return f"[ok] {title}{suffix}{follow}"


def warning_line(title: str, detail: str = "", next_step: str = "") -> str:
    suffix = f" | {detail}" if detail else ""
    follow = f" | Next: {next_step}" if next_step else ""
    return f"[warn] {title}{suffix}{follow}"


def error_line(title: str, detail: str = "", next_step: str = "") -> str:
    suffix = f" | {detail}" if detail else ""
    follow = f" | Next: {next_step}" if next_step else ""
    return f"[error] {title}{suffix}{follow}"

