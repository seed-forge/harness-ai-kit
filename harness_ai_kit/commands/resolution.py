from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .. import package_manager as pm
from ..domain import project_sync_presentation


@dataclass(frozen=True)
class ResolutionCommandContext:
    load_effective_config: Callable[[Path], Any]
    resolve_repo_root: Callable[[str | None, Any], Path]
    load_contextual_project_manifest: Callable[[str | None], tuple[Path | None, Any]]
    resolve_asset_plan: Callable[..., pm.ResolutionPlan]
    current_cli_versions: Callable[[Path, Any], dict[str, str]]
    manifest_aware_runtime: Callable[[argparse.Namespace, Any], str]
    manifest_aware_scope: Callable[[argparse.Namespace, Any], str]
    project_lockfile_from_manifest: Callable[..., pm.Lockfile]


def plan_to_payload(plan: pm.ResolutionPlan) -> dict[str, object]:
    return plan.to_lockfile().model_dump(mode="json")


def build_resolution_handlers(context: ResolutionCommandContext) -> Mapping[str, Callable[[argparse.Namespace, Path], int]]:
    return {
        "resolve": lambda args, config_path: command_resolve(args, config_path, context),
        "lock": lambda args, config_path: command_lock(args, config_path, context),
        "graph": lambda args, config_path: command_graph(args, config_path, context),
        "why": lambda args, config_path: command_why(args, config_path, context),
    }


def command_resolve(args: argparse.Namespace, config_path: Path, context: ResolutionCommandContext) -> int:
    config = context.load_effective_config(config_path)
    repo_root = context.resolve_repo_root(getattr(args, "repo_root", None), config)
    plan = context.resolve_asset_plan(
        repo_root,
        config,
        asset_kind=args.asset_kind,
        root_ids=[args.asset_id],
        runtime_id="codex",
        install_scope="project",
        features=list(args.feature),
        offline=args.offline,
        source_selector=getattr(args, "source_selector", None),
    )
    if args.json:
        print(json.dumps(plan_to_payload(plan), ensure_ascii=False, indent=2))
    else:
        for line in pm.tree_lines(plan):
            print(line)
    return 0


def command_lock(args: argparse.Namespace, config_path: Path, context: ResolutionCommandContext) -> int:
    config = context.load_effective_config(config_path)
    repo_root = context.resolve_repo_root(getattr(args, "repo_root", None), config)
    manifest_path, manifest = context.load_contextual_project_manifest(getattr(args, "target_dir", None))
    if args.asset_kind and not args.asset_id:
        raise ValueError("lock requires an asset id when asset kind is provided.")
    if args.asset_id:
        lock_path = pm.write_lockfile(
            context.resolve_asset_plan(
                repo_root,
                config,
                asset_kind=args.asset_kind or "skill",
                root_ids=[args.asset_id],
                runtime_id=getattr(args, "runtime", None) or "codex",
                install_scope=getattr(args, "scope", None) or "project",
                features=list(args.feature),
                offline=args.offline,
                source_selector=getattr(args, "source_selector", None),
            ),
            pm.lockfile_path(repo_root),
        )
        print(project_sync_presentation.lockfile_written_line(lock_path))
        return 0
    if manifest is None or manifest_path is None:
        raise ValueError("lock requires `skill <id>` or a harness-ai-kit.yml in the current project.")
    runtime_id = context.manifest_aware_runtime(args, manifest)
    install_scope = context.manifest_aware_scope(args, manifest)
    lockfile = context.project_lockfile_from_manifest(
        repo_root or manifest_path.parent,
        config,
        manifest,
        runtime_id,
        install_scope,
        offline=args.offline,
        source_selector=getattr(args, "source_selector", None),
    )
    lock_path = pm.lockfile_path(manifest_path.parent)
    pm.write_lockfile(
        pm.ResolutionPlan(
            roots=list(lockfile.roots),
            features=list(lockfile.features),
            runtime=lockfile.runtime,
            install_scope=lockfile.install_scope,
            nodes=list(lockfile.nodes),
            manifest_map={},
            candidate_map={},
            dependency_edges={},
            root_requests=list(lockfile.root_requests),
        ),
        lock_path,
    )
    print(project_sync_presentation.lockfile_written_line(lock_path))
    return 0


def command_graph(args: argparse.Namespace, config_path: Path, context: ResolutionCommandContext) -> int:
    config = context.load_effective_config(config_path)
    repo_root = context.resolve_repo_root(getattr(args, "repo_root", None), config)
    plan = context.resolve_asset_plan(
        repo_root,
        config,
        asset_kind=args.asset_kind,
        root_ids=[args.asset_id],
        runtime_id="codex",
        install_scope="project",
        features=list(args.feature),
        offline=args.offline,
        source_selector=getattr(args, "source_selector", None),
    )
    if args.json:
        print(json.dumps(plan_to_payload(plan), ensure_ascii=False, indent=2))
    else:
        for line in pm.tree_lines(plan):
            print(line)
    return 0


def command_why(args: argparse.Namespace, config_path: Path, context: ResolutionCommandContext) -> int:
    config = context.load_effective_config(config_path)
    repo_root = context.resolve_repo_root(getattr(args, "repo_root", None), config)
    plan = context.resolve_asset_plan(
        repo_root,
        config,
        asset_kind=args.asset_kind,
        root_ids=[args.asset_id],
        runtime_id="codex",
        install_scope="project",
        features=list(args.feature),
        offline=args.offline,
        source_selector=getattr(args, "source_selector", None),
    )
    owners: list[str] = []
    for asset_kind in ("skill", "loop", "cli", "mcp", "plugin", "hook", "subagent"):
        owners = pm.reverse_dependencies(plan, pm.package_key(asset_kind, args.dependency_id))
        if owners:
            break
    if not owners:
        raise KeyError(f"Dependency not found in resolved graph: {args.dependency_id}")
    print(f"{args.dependency_id} is required by:")
    for owner in owners:
        print(f"- {owner}")
    return 0
