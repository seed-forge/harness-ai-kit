"""Lockfile apply orchestration.

Re-exports from application.project_sync where the lockfile apply
functions are co-located with the sync orchestration logic.
"""
from ai_kit.application.project_sync import (
    apply_managed_asset_lockfile,
    apply_skill_lockfile,
)

__all__ = [
    "apply_managed_asset_lockfile",
    "apply_skill_lockfile",
]
