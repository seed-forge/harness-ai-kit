"""``ai-kit config`` command: show effective config for an asset."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ai_kit.infrastructure.asset_config_loader import (
    discover_config_keys,
    load_asset_config,
)
from ai_kit.infrastructure.config_io import resolve_repo_root
from ai_kit.infrastructure.config_io import load_config as load_cli_config


def _default_user_config_path() -> Path:
    return Path.home() / ".ai-kit" / "config.yaml"


def _default_env_tak_path() -> Path:
    return Path.home() / ".ai-kit" / ".env.tak"


def command_config(args: argparse.Namespace, config_path: Path) -> int:
    """Show the effective merged configuration for a given asset."""
    cli_cfg = load_cli_config(config_path)
    repo_root = resolve_repo_root(
        getattr(args, "repo_root", None), cli_cfg
    )

    asset_id = args.asset_id
    # Locate asset directory (try skills/ first, then plugins/, etc.)
    asset_dir: Path | None = None
    for subdir in ("skills", "plugins", "hooks", "subagents", "loops"):
        candidate = repo_root / subdir / asset_id
        if candidate.is_dir():
            asset_dir = candidate
            break

    if asset_dir is None:
        print(f"Error: asset '{asset_id}' not found under {repo_root}")
        return 1

    user_config = _default_user_config_path()
    env_tak = _default_env_tak_path()

    if args.keys:
        # Show declared config keys (metadata only)
        items = discover_config_keys(asset_dir)
        if not items:
            print(f"No config.defaults.yaml found for {asset_id}")
            return 0
        for item in items:
            req = "required" if item.get("required") else "optional"
            sens = item.get("sensitivity", "public")
            default = item.get("default", "<none>")
            env = item.get("env_var", "")
            line = f"  {item['key']} ({item.get('type', '?')}, {req}, {sens})"
            if default != "<none>":
                line += f"  default={default}"
            if env:
                line += f"  env={env}"
            print(line)
        return 0

    # Show effective merged config
    effective = load_asset_config(
        asset_id,
        asset_dir=asset_dir,
        user_config_path=user_config if user_config.exists() else None,
        env_tak_path=env_tak if env_tak.exists() else None,
    )

    if not effective:
        print(f"No configuration found for {asset_id}")
        return 0

    # Mask sensitive values
    items = discover_config_keys(asset_dir)
    sensitive_keys = {
        item["key"] for item in items if item.get("sensitivity") == "sensitive"
    }

    if args.json:
        output = {
            k: ("****" if k in sensitive_keys else v)
            for k, v in effective.items()
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(f"Effective config for {asset_id}:")
        for key, value in sorted(effective.items()):
            display = "****" if key in sensitive_keys else value
            print(f"  {key} = {display}")

    # Warn about unconfigured required fields
    missing = []
    for item in items:
        if item.get("required") and item["key"] not in effective:
            env_hint = f" (env: {item['env_var']})" if item.get("env_var") else ""
            missing.append(f"  {item['key']} [{item.get('sensitivity', '?')}]{env_hint}")
    if missing:
        print(f"\nUnconfigured required fields (set in ~/.ai-kit/config.yaml or .env.tak):")
        for line in missing:
            print(line)
    return 0
