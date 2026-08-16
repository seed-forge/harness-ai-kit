"""Lightweight role resolution for newapictl.

Reads ~/.harness-ai-kit/config.yaml directly (no dependency on harness-ai-kit).
Fallback priority:
  1. HARNESS_AI_KIT_ROLE environment variable
  2. ~/.harness-ai-kit/config.yaml role field
  3. Default "consumer"

Example usage:
    from .role import require_role, effective_role
    
    def main():
        role = effective_role()
        print(f"Current role: {role}")
        
        # Check if current role permits operation
        if not role_at_least("contributor"):
            require_role("contributor", "user-create")
            # User won't reach here if role insufficient
"""
from __future__ import annotations
import os
from pathlib import Path

VALID_ROLES = ("consumer", "contributor", "maintainer")
_ROLE_RANK = {"consumer": 0, "contributor": 1, "maintainer": 2}
_CONFIG_PATH = Path.home() / ".harness-ai-kit" / "config.yaml"


def effective_role() -> str:
    """Resolve role with priority: env > config.yaml > default(consumer)."""
    # 1. Env override (highest priority)
    env_role = os.environ.get("HARNESS_AI_KIT_ROLE", "").strip().lower()
    if env_role in VALID_ROLES:
        return env_role
    
    # 2. config.yaml persistent setting
    try:
        import yaml
        if _CONFIG_PATH.exists():
            data = yaml.safe_load(_CONFIG_PATH.read_text(encoding="utf-8")) or {}
            role = str(data.get("role", "")).strip().lower()
            if role in VALID_ROLES:
                return role
    except Exception:
        # Silently fall back to consumer on parse error
        pass
    
    # 3. Default
    return "consumer"


def role_at_least(minimum: str) -> bool:
    """Check if current role >= minimum privilege level."""
    return _ROLE_RANK.get(effective_role(), 0) >= _ROLE_RANK.get(minimum, 0)


def require_role(minimum: str, action: str) -> None:
    """Raise SystemExit with actionable guidance if role insufficient."""
    if role_at_least(minimum):
        return
    
    current = effective_role()
    unset_note = "" if current != "consumer" else " (unset defaults to consumer)"
    
    print(f"Error: '{action}' requires role '{minimum}' or higher; "
          f"your effective role is '{current}'{unset_note}.")
    print(f"Hint: Run 'harness-ai-kit config set --role {minimum}' to upgrade.")
    raise SystemExit(1)


def check_dry_run_override(args, minimum: str) -> bool:
    """Allow contributor to run write commands in --dry-run mode.
    
    Returns True if:
      - args.dry_run is True AND minimum == "contributor"
      OR
      - role_at_least(minimum) is True
    """
    if role_at_least(minimum):
        return True
    if getattr(args, "dry_run", False) and minimum == "contributor":
        return True
    return False
