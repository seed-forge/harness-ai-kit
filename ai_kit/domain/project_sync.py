from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable

from ai_kit.domain.lockfile import Lockfile, LockNode
from ai_kit.domain.policies import SOURCE_GIT_REPO, SOURCE_REPO
from ai_kit.domain.resolution import ResolutionPlan


MANAGED_ASSET_TYPES = ("plugin", "hook", "subagent", "mcp", "loop")

PathExists = Callable[[Path], bool]
SourceChecksum = Callable[[Path], str]
MaterializedChecksum = Callable[[Path, str, str, str], str]


def desired_skill_ids(lockfile: Lockfile) -> set[str]:
    return {node.id for node in lockfile.nodes if node.type == "skill"}


def desired_managed_assets(lockfile: Lockfile) -> dict[str, set[str]]:
    return {
        asset_type: {node.id for node in lockfile.nodes if node.type == asset_type}
        for asset_type in MANAGED_ASSET_TYPES
    }


def managed_project_skill_ids_from_lock(existing_lockfile: Lockfile | None, desired_skill_ids: Iterable[str]) -> set[str]:
    managed = set(desired_skill_ids)
    if existing_lockfile is None:
        return managed
    for node in existing_lockfile.nodes:
        if node.type == "skill":
            managed.add(node.id)
    return managed


def managed_project_asset_ids_from_lock(
    existing_lockfile: Lockfile | None,
    desired_assets: dict[str, set[str]],
) -> dict[str, set[str]]:
    managed = {asset_type: set(values) for asset_type, values in desired_assets.items()}
    if existing_lockfile is None:
        return managed
    for node in existing_lockfile.nodes:
        if node.type in MANAGED_ASSET_TYPES:
            managed.setdefault(node.type, set()).add(node.id)
    return managed


def lockfile_to_resolution_plan(lockfile: Lockfile) -> ResolutionPlan:
    return ResolutionPlan(
        roots=list(lockfile.roots),
        features=list(lockfile.features),
        runtime=lockfile.runtime,
        install_scope=lockfile.install_scope,
        nodes=list(lockfile.nodes),
        manifest_map={},
        candidate_map={},
        dependency_edges={},
        root_requests=list(lockfile.root_requests),
    )


def refresh_repo_node_checksums(
    plan: ResolutionPlan,
    runtime_id: str,
    *,
    path_exists: PathExists,
    source_checksum: SourceChecksum,
    materialized_checksum: MaterializedChecksum,
) -> ResolutionPlan:
    updated_nodes: list[LockNode] = []
    for node in plan.nodes:
        if node.source not in {SOURCE_REPO, SOURCE_GIT_REPO} or not node.source_ref or node.type == "cli":
            updated_nodes.append(node)
            continue
        source_path = Path(node.source_ref)
        if not path_exists(source_path):
            updated_nodes.append(node)
            continue
        updated_nodes.append(
            node.model_copy(
                update={
                    "source_checksum": source_checksum(source_path),
                    "materialized_checksum": materialized_checksum(source_path, node.id, runtime_id, node.type),
                }
            )
        )
    return ResolutionPlan(
        roots=list(plan.roots),
        features=list(plan.features),
        runtime=plan.runtime,
        install_scope=plan.install_scope,
        nodes=updated_nodes,
        manifest_map=plan.manifest_map,
        candidate_map=plan.candidate_map,
        dependency_edges=plan.dependency_edges,
        root_requests=plan.root_requests,
    )
