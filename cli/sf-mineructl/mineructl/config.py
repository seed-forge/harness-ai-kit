"""mineructl unified config — thin wrapper over harness_ai_kit's asset_config_loader.

Exposes:
  - get_config(): raw merged config dict (L1 defaults < L2 unified < L3 overrides)
  - load_config(): resolved MinerUConfig object with a guaranteed base_url
  - get_state_dir(): per-asset state directory
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness_ai_kit.infrastructure.asset_config_loader import (
    load_asset_config,
    state_dir,
)

ASSET_ID = "mineructl"
ASSET_DIR = Path(__file__).parent
LEGACY_PATHS = [
    Path.home() / ".config" / "mineructl" / "config.yaml",
    Path.home() / ".config" / "mineructl" / "profiles.yaml",
]


def get_config(
    cli_overrides: dict[str, str] | None = None,
    env_file: str | None = None,
) -> dict[str, Any]:
    """Return the effective config dict (L1 defaults < L2 unified < L3 overrides)."""
    return load_asset_config(
        ASSET_ID,
        asset_dir=ASSET_DIR,
        legacy_config_paths=LEGACY_PATHS,
        user_config_path=Path.home() / ".harness-ai-kit" / "config.yaml",
        env_tak_path=Path(env_file) if env_file else Path.home() / ".harness-ai-kit" / ".env.tak",
        cli_overrides=cli_overrides,
    )


@dataclass
class MinerUConfig:
    """Resolved mineructl configuration."""

    base_url: str
    profile: str


def load_config(
    profile: str = "default",
    base_url: str | None = None,
    env_file: str | None = None,
) -> MinerUConfig:
    """Resolve config into a MinerUConfig. ``--base-url`` overrides the stored value.

    Raises ValueError if no base URL can be resolved, since no endpoint ships by default.
    """
    overrides: dict[str, str] = {}
    if profile:
        overrides["profile"] = profile
    if base_url:
        overrides["base_url"] = base_url
    cfg = get_config(cli_overrides=overrides, env_file=env_file)
    resolved = base_url or cfg.get("base_url") or ""
    if not resolved:
        raise ValueError(
            "No MinerU base URL configured. Pass --base-url <url> or set 'base_url' "
            "under the 'mineructl' asset key in ~/.harness-ai-kit/config.yaml."
        )
    return MinerUConfig(base_url=str(resolved), profile=profile or "default")


def get_state_dir() -> Path:
    """Return ~/.harness-ai-kit/state/mineructl/, creating if needed."""
    return state_dir(ASSET_ID)
