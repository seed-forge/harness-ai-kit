"""Asset configuration loader: L1 (defaults) → L2 (user config) → L3 (runtime override).

Loads and merges configuration for a given asset from three priority layers:
  L1: <asset_dir>/config.defaults.yaml  (asset author defaults, lowest priority)
  L2: ~/.harness-ai-kit/.env.tak           (optional sensitive values, KEY=VALUE)
      System environment variables      (matched via env_var declarations)
      ~/.harness-ai-kit/config.yaml        (user global config, HIGHEST user-level priority)
  L3: CLI overrides                     (highest priority, passed as dict)

Priority chain (lowest → highest):
  L1 defaults < L2a .env.tak < L2b env vars < L2c config.yaml < L3 CLI overrides

The config.yaml file (global + assets sections) is the **source of truth** and
overwrites environment variables. Users should configure via config.yaml first;
env vars serve only as fallback or CI/CD automation override.

Supports automatic migration from legacy per-CLI config directories
(e.g. ``~/.config/<tool>/config.yaml``) into the unified config file.

Returns a flat ``{key: effective_value}`` dict.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import yaml


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_yaml(path: Path) -> dict[str, Any]:
    """Safely load a YAML file, returning an empty dict on any error."""
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_yaml(path: Path, data: dict[str, Any]) -> None:
    """Write *data* to *path* as YAML, creating parent dirs as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def _migrate_legacy_config(
    asset_id: str,
    legacy_paths: list[Path],
    user_config_path: Path,
) -> None:
    """Detect legacy config files and merge them into the unified config.

    For each *legacy_paths* that exists:
    1. Read the legacy YAML.
    2. If ``assets.<asset_id>`` already exists in the unified config, skip
       (user has already configured this asset).
    3. Otherwise write the legacy values under ``assets.<asset_id>``.
    4. Rename the legacy file to ``<original>.migrated.bak``.
    5. Print a migration notice to stderr.
    """
    if not legacy_paths:
        return

    user_cfg = _load_yaml(user_config_path)
    assets_section = user_cfg.setdefault("assets", {})

    # Skip if asset already configured in unified file
    if asset_id in assets_section and assets_section[asset_id]:
        return

    for legacy_path in legacy_paths:
        if not legacy_path.exists():
            continue
        legacy_data = _load_yaml(legacy_path)
        if not legacy_data:
            continue

        # Flatten one level if the legacy file wraps under a single key
        assets_section[asset_id] = legacy_data
        _save_yaml(user_config_path, user_cfg)

        # Backup legacy file
        bak_path = legacy_path.with_suffix(legacy_path.suffix + ".migrated.bak")
        legacy_path.rename(bak_path)
        print(
            f"[tak] 已从 {legacy_path} 迁移配置到 {user_config_path} "
            f"(原文件保留为 {bak_path.name})",
            file=sys.stderr,
        )
        return  # Only migrate the first existing legacy file


def _load_env_tak(path: Path) -> dict[str, str]:
    """Parse a ``.env`` style file into a flat dict.

    Lines starting with ``#`` and blank lines are ignored.
    Values are *not* shell-expanded.
    """
    if not path.exists():
        return {}
    result: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        result[key.strip()] = value.strip()
    return result


def _parse_defaults(raw: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract the ``config`` list from a config.defaults.yaml payload."""
    items = raw.get("config")
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict) and "key" in item]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def state_dir(asset_id: str, *, create: bool = True) -> Path:
    """Return ``~/.harness-ai-kit/state/<asset_id>/``, creating it if *create* is True.

    This is the canonical location for runtime state files (session data,
    audit logs, probe history, etc.) that should NOT live in config.yaml.
    """
    d = Path.home() / ".harness-ai-kit" / "state" / asset_id
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return d


def load_asset_config(
    asset_id: str,
    *,
    asset_dir: Path,
    legacy_config_paths: list[Path] | None = None,
    user_config_path: Path | None = None,
    env_tak_path: Path | None = None,
    cli_overrides: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Load and merge configuration for *asset_id* across all layers.

    Parameters
    ----------
    asset_id:
        The skill / CLI identifier (e.g. ``infra-jenkins-pipeline-ops``).
    asset_dir:
        Directory containing ``config.defaults.yaml``.
    legacy_config_paths:
        Ordered list of legacy config file paths to check for auto-migration.
        The first existing file will be migrated into the unified config and
        renamed to ``*.migrated.bak``.
    user_config_path:
        Path to ``~/.harness-ai-kit/config.yaml``.  ``None`` skips L2 YAML.
    env_tak_path:
        Path to ``~/.harness-ai-kit/.env.tak``.  ``None`` skips .env layer.
    cli_overrides:
        Key-value pairs from CLI ``--config-key`` flags (L3, highest priority).

    Returns
    -------
    dict[str, Any]
        Merged ``{key: effective_value}`` dictionary.
    """
    effective: dict[str, Any] = {}
    env_var_map: dict[str, str] = {}  # key → env_var name

    # -- Auto-migration from legacy config paths -----------------------------
    if legacy_config_paths and user_config_path is not None:
        _migrate_legacy_config(asset_id, legacy_config_paths, user_config_path)

    # -- L1: Asset defaults --------------------------------------------------
    # Check both package root and data/ subdirectory for config.defaults.yaml
    defaults_path = asset_dir / "config.defaults.yaml"
    if not defaults_path.exists():
        alt_path = asset_dir / "data" / "config.defaults.yaml"
        if alt_path.exists():
            defaults_path = alt_path
    defaults_items = _parse_defaults(_load_yaml(defaults_path))
    for item in defaults_items:
        key = item["key"]
        if "default" in item and item["default"] is not None:
            effective[key] = item["default"]
        if item.get("env_var"):
            env_var_map[key] = item["env_var"]

    # -- L2a: .env.tak (lowest user-level priority) -----------------------
    if env_tak_path is not None:
        env_values = _load_env_tak(env_tak_path)
        # Direct key matches first (lower priority within .env.tak)
        for key in list(effective.keys()) + [item["key"] for item in defaults_items]:
            if key in env_values:
                effective[key] = env_values[key]
        # env_var mapping overrides direct key matches (higher priority)
        for key, env_name in env_var_map.items():
            if env_name in env_values:
                effective[key] = env_values[env_name]

    # -- L2b: System environment variables (fallback) ----------------------
    for key, env_name in env_var_map.items():
        env_val = os.environ.get(env_name)
        if env_val is not None:
            effective[key] = env_val

    # -- L2c: User global config.yaml (highest user-level priority) --------
    # Config file overwrites env vars — file is the source of truth
    if user_config_path is not None:
        user_cfg = _load_yaml(user_config_path)
        # global section
        global_section = user_cfg.get("global")
        if isinstance(global_section, dict):
            for k, v in global_section.items():
                effective[k] = v
        # assets.<asset_id> section
        assets_section = user_cfg.get("assets")
        if isinstance(assets_section, dict):
            asset_cfg = assets_section.get(asset_id)
            if isinstance(asset_cfg, dict):
                for k, v in asset_cfg.items():
                    effective[k] = v

    # -- L3: CLI overrides ---------------------------------------------------
    if cli_overrides:
        for k, v in cli_overrides.items():
            effective[k] = v

    return effective


def discover_config_keys(asset_dir: Path) -> list[dict[str, Any]]:
    """Return the raw config item declarations from config.defaults.yaml.

    Useful for tooling that needs to inspect metadata (required, sensitivity, etc.)
    without loading actual values.
    """
    defaults_path = asset_dir / "config.defaults.yaml"
    if not defaults_path.exists():
        alt_path = asset_dir / "data" / "config.defaults.yaml"
        if alt_path.exists():
            defaults_path = alt_path
    return _parse_defaults(_load_yaml(defaults_path))
