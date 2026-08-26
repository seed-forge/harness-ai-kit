"""Unified configuration for woodpeckerctl.

The canonical user configuration is ``~/.harness-ai-kit/config.yaml`` under
``assets.woodpeckerctl``. Legacy Woodpecker config files are accepted only for
one-time migration by the shared asset loader.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from harness_ai_kit.infrastructure.asset_config_loader import (
    discover_config_keys,
    load_asset_config as _load_asset_config,
    state_dir as _state_dir,
)

_UNIFIED_ASSET_ID = "woodpeckerctl"
_ASSET_DIR = Path(__file__).parent
_USER_CONFIG = Path.home() / ".harness-ai-kit" / "config.yaml"
_UNIFIED_LEGACY_PATHS = [
    Path.home() / ".woodpeckerctl" / "profiles.yaml",
    Path.home() / ".woodpecker" / "config",
]


def get_config(cli_overrides: dict[str, str] | None = None) -> dict[str, Any]:
    """Return the effective unified configuration mapping."""
    return _load_asset_config(
        _UNIFIED_ASSET_ID,
        asset_dir=_ASSET_DIR,
        legacy_config_paths=_UNIFIED_LEGACY_PATHS,
        user_config_path=_USER_CONFIG,
        env_tak_path=Path.home() / ".harness-ai-kit" / ".env.tak",
        cli_overrides=cli_overrides,
    )


def load_config(cli_overrides: dict[str, str] | None = None) -> dict[str, Any]:
    """Load config and fail with an actionable unified-config message."""
    config = get_config(cli_overrides)
    for item in discover_config_keys(_ASSET_DIR):
        if item.get("required") and not config.get(item["key"]):
            raise ValueError(
                f"缺少必填配置: {item['key']}\n"
                f"  说明: {item.get('description', '')}\n"
                "  请在 ~/.harness-ai-kit/config.yaml 的 assets.woodpeckerctl 段中配置"
            )
    return config


def resolve_config(args: Any) -> dict[str, str]:
    """Resolve CLI overrides and return the API client's canonical keys."""
    overrides: dict[str, str] = {}
    if getattr(args, "server", None):
        overrides["woodpecker_url"] = args.server
    if getattr(args, "token", None):
        overrides["woodpecker_token"] = args.token
    config = load_config(overrides)
    return {
        "server": str(config.get("woodpecker_url") or config.get("server") or "").rstrip("/"),
        "token": str(config.get("woodpecker_token") or config.get("token") or ""),
    }


def get_state_dir() -> Path:
    """Return ``~/.harness-ai-kit/state/woodpeckerctl/``."""
    return _state_dir(_UNIFIED_ASSET_ID)
