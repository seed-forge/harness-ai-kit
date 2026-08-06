from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from ai_kit.domain import project_state


def project_prune_preview(
    *,
    install_scope: str,
    installed_skill_ids: Iterable[str],
    installed_assets: Mapping[str, Iterable[str]],
    desired_skill_ids: Iterable[str],
    desired_assets: Mapping[str, Iterable[str]],
    managed_skill_ids: Iterable[str],
    managed_assets: Mapping[str, Iterable[str]],
) -> tuple[list[str], list[str]]:
    if install_scope != "project":
        return [], []
    return (
        project_state.orphan_skill_ids(installed_skill_ids, desired_skill_ids, managed_skill_ids),
        project_state.orphan_managed_asset_ids(installed_assets, desired_assets, managed_assets),
    )


def base_project_sync_summary(
    *,
    lockfile: Any,
    lock_path: Path,
    target_dir: Path,
    runtime: str,
    scope: str,
    cli_records: Sequence[Any],
    removed_skills: Sequence[str],
    removed_assets: Sequence[str],
    installed_paths: Sequence[Any],
    installed_asset_paths: Sequence[Any],
    cli_outputs: Sequence[str] | None = None,
    multi_runtime_results: dict[str, list[Any]] | None = None,
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "lockfile": lockfile,
        "lock_path": lock_path,
        "target_dir": target_dir,
        "runtime": runtime,
        "scope": scope,
        "cli_records": list(cli_records),
        "removed_skills": list(removed_skills),
        "removed_assets": list(removed_assets),
        "installed_paths": list(installed_paths),
        "installed_asset_paths": list(installed_asset_paths),
    }
    if cli_outputs is not None:
        summary["cli_outputs"] = list(cli_outputs)
    if multi_runtime_results:
        summary["multi_runtime_results"] = {
            rt: [str(p) for p in paths]
            for rt, paths in sorted(multi_runtime_results.items())
        }
    return summary
