from __future__ import annotations

from collections.abc import Iterable, Mapping

from harness_ai_kit.domain.materialization import worst_drift_status
from harness_ai_kit.domain.versions import highest_version, sort_versions, upgrade_status_for_versions


MANAGED_ASSET_TYPES = ("plugin", "hook", "subagent", "mcp", "loop")


def orphan_skill_ids(
    installed_skill_ids: Iterable[str],
    desired_skill_ids: Iterable[str],
    managed_skill_ids: Iterable[str] | None = None,
) -> list[str]:
    desired = set(desired_skill_ids)
    managed = set(managed_skill_ids) if managed_skill_ids is not None else None
    removed: list[str] = []
    for skill_id in installed_skill_ids:
        if managed is not None and skill_id not in managed:
            continue
        if skill_id in desired:
            continue
        removed.append(skill_id)
    return removed


def orphan_managed_asset_ids(
    installed_assets: Mapping[str, Iterable[str]],
    desired_assets: Mapping[str, Iterable[str]],
    managed_assets: Mapping[str, Iterable[str]] | None = None,
) -> list[str]:
    removed: list[str] = []
    for asset_type in MANAGED_ASSET_TYPES:
        desired = set(desired_assets.get(asset_type, set()))
        managed = set(managed_assets.get(asset_type, set())) if managed_assets is not None else None
        for asset_id in installed_assets.get(asset_type, []):
            if managed is not None and asset_id not in managed:
                continue
            if asset_id in desired:
                continue
            removed.append(f"{asset_type}:{asset_id}")
    return removed


def installed_versions_summary(installed_versions: Iterable[str]) -> tuple[bool, tuple[str, ...], str]:
    versions = tuple(version for version in installed_versions if version)
    sorted_versions = sort_versions(versions)
    return bool(versions), sorted_versions, highest_version(versions)


def skill_install_summary(
    installed_versions: Iterable[str],
    available_version: str,
    drift_statuses: Iterable[str],
) -> tuple[bool, tuple[str, ...], str, str]:
    installed, sorted_versions, highest_installed = installed_versions_summary(installed_versions)
    return (
        installed,
        sorted_versions,
        upgrade_status_for_versions(highest_installed, available_version),
        worst_drift_status(drift_statuses),
    )


def managed_asset_install_summary(
    installed_versions: Iterable[str],
    drift_statuses: Iterable[str],
) -> tuple[bool, tuple[str, ...], str]:
    installed, sorted_versions, _ = installed_versions_summary(installed_versions)
    return installed, sorted_versions, worst_drift_status(drift_statuses)
