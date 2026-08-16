"""Configuration resolution: unified chain + legacy ~/.nexusctl/profiles.yaml.

Priority (lowest → highest):
    defaults < .env.tak < env vars < ~/.harness-ai-kit/config.yaml (assets.nexusctl)
    < legacy profile (~/.nexusctl/profiles.yaml) < CLI args

Legacy ``nexus_base_url`` key in assets.nexusctl is accepted as an alias of
``base_url`` for backward compatibility.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from .config import get_config

PROFILE_DIR = Path.home() / ".nexusctl"
PROFILE_FILE = PROFILE_DIR / "profiles.yaml"


def load_profile(name: str) -> dict:
    """Load a named profile from ~/.nexusctl/profiles.yaml.

    Returns an empty dict if the file or profile doesn't exist.
    """
    if not PROFILE_FILE.exists():
        return {}
    try:
        with open(PROFILE_FILE, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        return {}
    profiles = data.get("profiles", {})
    return profiles.get(name, {})


def resolve_config(args) -> dict:
    """Resolve configuration: CLI args > legacy profile > unified config chain.

    Returns dict with keys: base_url, user, password.
    """
    profile_name = getattr(args, "profile", None) or "default"
    profile = load_profile(profile_name) if profile_name != "default" else {}

    # Unified chain: defaults -> .env.tak -> env -> ~/.harness-ai-kit/config.yaml
    cfg = get_config()
    base_url = cfg.get("base_url") or cfg.get("nexus_base_url")
    user = cfg.get("user")
    password = cfg.get("password")

    base_url = (
        getattr(args, "base_url", None)
        or base_url
        or profile.get("base_url")
        or ""
    ).rstrip("/")

    user = (
        getattr(args, "user", None)
        or user
        or profile.get("user")
    )

    password = (
        getattr(args, "password", None)
        or password
        or profile.get("password")
    )

    return {"base_url": base_url, "user": user, "password": password}
