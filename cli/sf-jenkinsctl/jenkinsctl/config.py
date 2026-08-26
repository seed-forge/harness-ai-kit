"""jenkinsctl unified config — thin wrapper over asset_config_loader."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from harness_ai_kit.infrastructure.asset_config_loader import (
    discover_config_keys,
    load_asset_config,
    state_dir,
)

ASSET_ID = "jenkinsctl"
ASSET_DIR = Path(__file__).parent
_USER_CONFIG = Path.home() / ".harness-ai-kit" / "config.yaml"
LEGACY_PATHS = [Path.home() / ".config" / "jenkinsctl" / "config.yaml"]


def get_config(cli_overrides: dict[str, str] | None = None) -> dict[str, Any]:
    """Return effective config (L1 defaults → L2 unified → L3 overrides)."""
    return load_asset_config(
        ASSET_ID,
        asset_dir=ASSET_DIR,
        legacy_config_paths=LEGACY_PATHS,
        user_config_path=_USER_CONFIG,
        env_tak_path=Path.home() / ".harness-ai-kit" / ".env.tak",
        cli_overrides=cli_overrides,
    )


def load_config(cli_overrides: dict | None = None) -> dict:
    """Load config with required-field validation (backward-compatible API)."""
    config = get_config(cli_overrides)

    # Validate required fields from config.defaults.yaml
    keys = discover_config_keys(ASSET_DIR)
    for item in keys:
        if item.get("required") and config.get(item["key"]) is None:
            raise ValueError(
                f"缺少必填配置: {item['key']}\n"
                f"  说明: {item.get('description', '')}\n"
                f"  请在 ~/.harness-ai-kit/config.yaml 的 assets.jenkinsctl 段中配置"
            )

    return config


def get_state_dir() -> Path:
    """Return ~/.harness-ai-kit/state/jenkinsctl/, creating if needed."""
    return state_dir(ASSET_ID)
