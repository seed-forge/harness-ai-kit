"""ragflowctl unified config — thin wrapper over asset_config_loader."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from harness_ai_kit.infrastructure.asset_config_loader import (
    load_asset_config,
    state_dir,
)

ASSET_ID = "ragflowctl"
ASSET_DIR = Path(__file__).parent
LEGACY_PATHS = [Path.home() / '.config' / 'ragflowctl' / 'config.yaml']


def get_config(cli_overrides: dict[str, str] | None = None) -> dict[str, Any]:
    """Return effective config (L1 defaults → L2 unified → L3 overrides)."""
    return load_asset_config(
        ASSET_ID,
        asset_dir=ASSET_DIR,
        legacy_config_paths=LEGACY_PATHS,
        user_config_path=Path.home() / ".harness-ai-kit" / "config.yaml",
        env_tak_path=Path.home() / ".harness-ai-kit" / ".env.tak",
        cli_overrides=cli_overrides,
    )


def get_state_dir() -> Path:
    """Return ~/.harness-ai-kit/state/ragflowctl/, creating if needed."""
    return state_dir(ASSET_ID)
