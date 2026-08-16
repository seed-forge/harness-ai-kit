"""Cleanup policy management commands (read-only in v0.3.0)."""
from __future__ import annotations

import json

from ._api import api_call, get_cleanup_api


def _to_dict(obj) -> dict:
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if isinstance(obj, dict):
        return obj
    return {"raw": str(obj)}


def cmd_cleanup_list(args) -> int:
    api = get_cleanup_api(args)
    result = api_call(api.list_internal_cleanup_policies)
    policies = [_to_dict(p) for p in (result or [])]
    as_json = getattr(args, "json", False)
    if as_json:
        print(json.dumps(policies, ensure_ascii=False, indent=2, default=str))
    else:
        print(f"{'名称':<35} {'格式':<12} {'模式':<15} {'说明'}")
        print("-" * 80)
        for p in policies:
            name = p.get("name", "?")
            fmt = p.get("format", "?")
            mode = p.get("mode", "?")
            notes = p.get("notes", "")
            print(f"{name:<35} {fmt:<12} {mode:<15} {notes}")
    return 0


def cmd_cleanup_get(args) -> int:
    api = get_cleanup_api(args)
    result = api_call(api.get_internal_cleanup_policies, args.name)
    as_json = getattr(args, "json", False)
    data = _to_dict(result) if result else {}
    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2, default=str))
    else:
        for k, v in data.items():
            print(f"  {k}: {v}")
    return 0
