from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path


CONFIG_DIRNAME = ".difyctl"
CONFIG_FILENAME = "config.json"


@dataclass(frozen=True)
class ProfileConfig:
    base_url: str = ""
    console_key: str = ""
    auth_type: str = "auto"  # "bearer" | "cookie" | "auto"
    providers_dir: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class AppConfig:
    base_url: str = ""
    app_api_key: str = ""
    workspace_dir: str = ""
    timeout_seconds: int = 120
    profiles: dict[str, ProfileConfig] = field(default_factory=dict)
    active_profile: str = ""

    def to_dict(self) -> dict[str, object]:
        d = asdict(self)
        d["profiles"] = {k: v.to_dict() if isinstance(v, ProfileConfig) else v for k, v in self.profiles.items()}
        return d


def default_config_path(home_dir: Path | None = None) -> Path:
    base = home_dir or Path.home()
    return base / CONFIG_DIRNAME / CONFIG_FILENAME


def normalize_base_url(value: str) -> str:
    normalized = value.strip().rstrip("/")
    if normalized.lower().endswith("/v1"):
        normalized = normalized[:-3].rstrip("/")
    return normalized


def env_base_url() -> str:
    return normalize_base_url(os.environ.get("DIFY_BASE_URL", ""))


def resolve_config_path(config_path: str | None) -> Path:
    if config_path:
        return Path(config_path).expanduser().resolve()
    return default_config_path().resolve()


def _parse_profiles(raw_profiles: object) -> dict[str, ProfileConfig]:
    if not isinstance(raw_profiles, dict):
        return {}
    result: dict[str, ProfileConfig] = {}
    for key, val in raw_profiles.items():
        if isinstance(val, dict):
            result[str(key)] = ProfileConfig(
                base_url=str(val.get("base_url", "")),
                console_key=str(val.get("console_key", "")),
                auth_type=str(val.get("auth_type", "auto")),
                providers_dir=str(val.get("providers_dir", "")),
            )
    return result


def load_config(config_path: Path) -> AppConfig:
    if not config_path.exists():
        return AppConfig()
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    return AppConfig(
        base_url=str(payload.get("base_url", "")),
        app_api_key=str(payload.get("app_api_key", "")),
        workspace_dir=str(payload.get("workspace_dir", "")),
        timeout_seconds=int(payload.get("timeout_seconds", 120)),
        profiles=_parse_profiles(payload.get("profiles")),
        active_profile=str(payload.get("active_profile", "")),
    )


def merge_config(
    saved: AppConfig,
    *,
    base_url: str | None = None,
    app_api_key: str | None = None,
    workspace_dir: str | None = None,
    timeout_seconds: int | None = None,
    profile: str | None = None,
) -> AppConfig:
    active = profile if profile is not None else saved.active_profile
    return AppConfig(
        base_url=(base_url if base_url is not None else saved.base_url).strip(),
        app_api_key=(app_api_key if app_api_key is not None else saved.app_api_key).strip(),
        workspace_dir=(workspace_dir if workspace_dir is not None else saved.workspace_dir).strip(),
        timeout_seconds=int(timeout_seconds if timeout_seconds is not None else saved.timeout_seconds),
        profiles=saved.profiles,
        active_profile=active,
    )


def save_config(config: AppConfig, config_path: Path) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def resolve_active_profile(config: AppConfig) -> ProfileConfig | None:
    """Return the active ProfileConfig, or None if no profile is active."""
    if not config.active_profile:
        return None
    return config.profiles.get(config.active_profile)


def resolve_providers_dir(config: AppConfig) -> Path:
    """Resolve the providers directory for the active profile.

    Defaults to ~/.difyctl/providers/{profile_name}/ if not configured.
    """
    profile = resolve_active_profile(config)
    if profile is None:
        return Path.home() / CONFIG_DIRNAME / "providers"
    if profile.providers_dir:
        return Path(profile.providers_dir).expanduser().resolve()
    return Path.home() / CONFIG_DIRNAME / "providers" / config.active_profile


def resolve_console_key(config: AppConfig) -> str:
    """Resolve the console_key for the active profile.

    Supports ${ENV_VAR} references. Returns empty string if no profile active or key is unset.
    """
    profile = resolve_active_profile(config)
    if profile is None:
        return ""
    raw = profile.console_key.strip()
    if not raw:
        return ""
    import re

    match = re.match(r"^\$\{([^}]+)\}$", raw)
    if match:
        return os.environ.get(match.group(1), "")
    return raw


# ── Unified config wrapper (added by config unification) ──────────────────
from harness_ai_kit.infrastructure.asset_config_loader import (
    load_asset_config as _load_asset_config,
    state_dir as _state_dir,
)

_UNIFIED_ASSET_ID = "difyctl"
_UNIFIED_LEGACY_PATHS = [
    Path.home() / '.difyctl' / 'config.json',
]


def get_config(cli_overrides=None):
    """Return effective config from unified ~/.harness-ai-kit/config.yaml.

    Reads ``assets.difyctl`` from the unified config (source of truth).
    """
    return _load_asset_config(
        _UNIFIED_ASSET_ID,
        asset_dir=Path(__file__).parent,
        legacy_config_paths=_UNIFIED_LEGACY_PATHS,
        user_config_path=Path.home() / ".harness-ai-kit" / "config.yaml",
        env_tak_path=Path.home() / ".harness-ai-kit" / ".env.tak",
        cli_overrides=cli_overrides,
    )


def get_state_dir():
    """Return ~/.harness-ai-kit/state/difyctl/."""
    return _state_dir(_UNIFIED_ASSET_ID)


def unified_config_path() -> Path:
    """Path to the harness-ai-kit source-of-truth config (~/.harness-ai-kit/config.yaml)."""
    return Path.home() / ".harness-ai-kit" / "config.yaml"


def write_unified_config_value(key: str, value: str, *, config_path: Path | None = None) -> Path:
    """Merge-preserving writeback of a single value under assets.difyctl in config.yaml.

    Preserves all other top-level keys and all other assets (governance rule:
    config.yaml writeback must merge-preserve global/assets sections). Creates the
    file/parents if missing.
    """
    import yaml  # lazy import; yaml is a runtime dep

    path = config_path or unified_config_path()
    data: dict = {}
    if path.exists():
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            data = loaded
    data.setdefault("assets", {})
    if not isinstance(data["assets"], dict):
        data["assets"] = {}
    data["assets"].setdefault(_UNIFIED_ASSET_ID, {})
    if not isinstance(data["assets"][_UNIFIED_ASSET_ID], dict):
        data["assets"][_UNIFIED_ASSET_ID] = {}
    data["assets"][_UNIFIED_ASSET_ID][key] = value
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


def write_unified_app_key(app_id: str, token: str, *, config_path: Path | None = None) -> Path:
    """Merge-preserving writeback of one app service token under assets.difyctl.app_keys.

    app_keys is an app_id->token map; other app_ids, other assets, and top-level
    keys are all preserved. Plaintext token is local-only (never Git-tracked).
    """
    import yaml

    path = config_path or unified_config_path()
    data: dict = {}
    if path.exists():
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            data = loaded
    data.setdefault("assets", {})
    if not isinstance(data["assets"], dict):
        data["assets"] = {}
    data["assets"].setdefault(_UNIFIED_ASSET_ID, {})
    if not isinstance(data["assets"][_UNIFIED_ASSET_ID], dict):
        data["assets"][_UNIFIED_ASSET_ID] = {}
    asset = data["assets"][_UNIFIED_ASSET_ID]
    if not isinstance(asset.get("app_keys"), dict):
        asset["app_keys"] = {}
    asset["app_keys"][app_id] = token
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


def forget_unified_app_key(app_id: str, *, config_path: Path | None = None) -> Path | None:
    """Remove an app's stored service token from config.yaml (used on key delete/app delete)."""
    import yaml

    path = config_path or unified_config_path()
    if not path.exists():
        return None
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        return None
    asset = (loaded.get("assets") or {}).get(_UNIFIED_ASSET_ID) or {}
    app_keys = asset.get("app_keys")
    if isinstance(app_keys, dict) and app_id in app_keys:
        del app_keys[app_id]
        path.write_text(yaml.safe_dump(loaded, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


def resolve_app_key(app_id: str = "") -> str:
    """Resolve an app service token: assets.difyctl.app_keys[app_id] > app_api_key.

    Returns the per-app token when present, else the single active app_api_key
    (legacy single-app config), else "".
    """
    try:
        unified = get_config()
    except Exception:
        unified = {}
    if not isinstance(unified, dict):
        return ""
    app_keys = unified.get("app_keys")
    if app_id and isinstance(app_keys, dict):
        token = str(app_keys.get(app_id, "") or "").strip()
        if token:
            return token
    return str(unified.get("app_api_key", "") or "").strip()


def cookie_expired(console_key: str, skew_seconds: int = 60) -> bool:
    """Return True if the access_token JWT inside the cookie header is expired.

    Parses the ``access_token=<JWT>`` segment and reads its ``exp`` claim (no
    signature verification). Returns False when expiry cannot be determined
    (e.g. bearer tokens, malformed JWT) so callers do not needlessly re-login.
    """
    import base64
    import re
    import time

    if not console_key:
        return False
    match = re.search(r"access_token=([^;]+)", console_key)
    token = match.group(1) if match else console_key.strip()
    parts = token.split(".")
    if len(parts) != 3:
        return False
    try:
        segment = parts[1] + "=" * (-len(parts[1]) % 4)
        claims = json.loads(base64.urlsafe_b64decode(segment))
        exp = int(claims.get("exp", 0))
    except Exception:
        return False
    return exp > 0 and time.time() >= (exp - skew_seconds)

