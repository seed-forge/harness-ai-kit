from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ai_kit.domain.identity import package_key_for, split_canonical_id
from ai_kit.domain.lockfile import Lockfile
from ai_kit.domain.manifest_ops import (
    find_project_lockfile,
    find_project_manifest,
    load_project_manifest,
    project_manifest_from_lockfile,
    save_project_manifest,
)
from ai_kit.domain.lockfile_io import state_dir
from ai_kit.domain.project_manifest_state import remove_asset_from_manifest
from ai_kit.domain.models import ProjectManifest
from ai_kit.domain.models.constants import PROJECT_MANIFEST_SCHEMA_VERSION

try:
    from resolvelib.resolvers import ResolutionImpossible
except ImportError:
    ResolutionImpossible = None  # type: ignore[misc,assignment]


def resolve_install_external(args: argparse.Namespace, config: Any) -> bool:
    """Resolve --install-external from CLI args and global config.

    Priority:
    1. ``--no-install-external`` on the command line  → False
    2. ``--install-external`` on the command line     → True
    3. ``config.defaults.install_external_immediately`` → config value
    4. default                                        → False
    """
    if getattr(args, "no_install_external", False):
        return False
    if getattr(args, "install_external", False):
        return True
    defaults = getattr(config, "defaults", None)
    if defaults is not None:
        return getattr(defaults, "install_external_immediately", False)
    return False


@dataclass(frozen=True)
class InstallCommandContext:
    load_config: Callable[[Path], Any]
    effective_config: Callable[[Any], Any]
    load_contextual_project_manifest: Callable[[str | None], tuple[Path | None, Any | None]]
    load_project_manifest_if_present: Callable[[], tuple[Path | None, Any | None]]
    manifest_target_dir: Callable[[Path, str, str, str | None], Path]
    project_lock_path_for_manifest: Callable[[Path | None, Path | None, str], Path]
    resolve_repo_root_if_available: Callable[..., Path | None]
    project_lockfile_from_manifest: Callable[..., Any]
    write_lockfile: Callable[[Any, Path], None]
    read_lockfile: Callable[[Path], Any]
    project_sync: Any
    run_project_sync: Callable[..., dict[str, Any]]
    prune_orphaned_project_skills: Callable[[Path, str, set[str], set[str]], list[str]]
    prune_orphaned_project_managed_assets: Callable[[Path, str, dict[str, set[str]], dict[str, set[str]]], dict[str, list[str]]]
    managed_project_skill_ids: Callable[[Path, Any], set[str]]
    managed_project_asset_ids: Callable[[Path, dict[str, set[str]]], dict[str, set[str]]]
    project_sync_presentation: Any
    resolve_target_dir: Callable[..., Path]
    load_combined_cli_inventory: Callable[[Path | None, Any], dict[str, Any]]
    load_cli_metadata_for_record: Callable[[Any], dict[str, object]]
    binary_release_platform_spec: Callable[[Any, dict[str, object]], dict[str, object]]
    binary_release_install_path: Callable[[Any, dict[str, object]], Path]
    remove_installed_skill: Callable[[Path, str, str], bool]
    remove_installed_managed_asset: Callable[[Path, str, str, str], bool]
    runtime_managed_asset_root: Callable[[Path, str], Path]
    pm: Any
    runtime_install_destination: Callable[[Path, str, str], Path]
    managed_asset_install_destination: Callable[[Path, str, str, str], Path]
    print_non_skill_requirements: Callable[[Any], None]
    manual_invocation_hint: Callable[[str, str], str]
    validate_sync_selection: Callable[[argparse.Namespace, bool], None]
    parse_asset_selector: Callable[[list[str], str], tuple[str, list[str]]]
    maybe_sync_repo: Callable[[argparse.Namespace, Path], None]
    load_cli_inventory: Callable[[Path | None], dict[str, Any]]
    select_cli_records: Callable[[dict[str, Any], list[str], bool], list[Any]]
    is_self_cli_package: Callable[[str], bool]
    self_upgrade_recovery_command: Callable[[Any], str]
    install_cli_packages: Callable[[list[Any], Any], list[str]]
    load_skill_inventory: Callable[[Path], dict[str, Any]]
    manifest_aware_runtime: Callable[[argparse.Namespace, Any | None], str]
    manifest_aware_scope: Callable[[argparse.Namespace, Any | None], str]
    project_root_ids: Callable[[Any], list[str]]
    explicit_feature_selection: Callable[[argparse.Namespace, Any | None], list[str]]
    manifest_skill_source_policy: Callable[[Any], list[str] | None]
    manifest_skill_root_sources: Callable[[Any], dict[str, tuple[str | None, str | None, str | None]]]
    manifest_skill_version_specifiers: Callable[[Any], dict[str, str]]
    is_git_source_selector: Callable[[str], bool]
    discover_git_skills: Callable[..., list[Any]]
    stdin_isatty: Callable[[], bool]
    prompt_input: Callable[[str], str]
    declared_cli_specs: Callable[[Any], list[Any]]
    add_skill_to_manifest: Callable[[Any, Any], bool]
    save_project_manifest: Callable[[Path, Any], None]
    ProjectRootSpec: type
    merge_manifest_cli_into_refresh_lockfile: Callable[..., Any]
    resolve_skill_plan: Callable[..., Any]
    install_environment_requirements: Callable[[list[dict[str, object]], bool], list[str]]
    environment_records_for_lockfile: Callable[[Any], list[dict[str, object]]]
    apply_skill_lockfile: Callable[[Path, Any, Any, Path, str, bool], list[Path]]
    apply_managed_asset_lockfile: Callable[[Any, Path, str], list[tuple[Any, Path]]]
    missing_environment_requirements: Callable[[list[dict[str, object]]], list[dict[str, str]]]
    bootstrap_project_manifest_from_lockfile: Callable[[Path, Any], Any]
    project_manifest_path: Callable[[Path], Path]
    select_records: Callable[[dict[str, Any], list[str], bool], list[Any]]
    sync_records: Callable[[list[Any], Path, str], list[Path]]
    write_lockfile_model: Callable[[Any, Path], Path]
    compute_extends_summary: Callable[[Any, Any], dict[str, Any]]


def build_install_handlers(context: InstallCommandContext) -> Mapping[str, Callable[[argparse.Namespace, Path], int]]:
    return {
        "prune": lambda args, config_path: command_prune(args, config_path, context),
        "uninstall": lambda args, config_path: command_uninstall(args, config_path, context),
        "sync": lambda args, config_path: command_sync(args, config_path, context),
        "install": lambda args, config_path: command_sync(args, config_path, context),
        "update": lambda args, config_path: command_sync(args, config_path, context),
    }


def command_prune(args: argparse.Namespace, config_path: Path, context: InstallCommandContext) -> int:
    config = context.effective_config(context.load_config(config_path))
    manifest_path, manifest = context.load_project_manifest_if_present()
    if manifest_path is None:
        raise FileNotFoundError("No ai-kit.yml found in the current project.")
    runtime_id = getattr(args, "runtime", None) or (manifest.runtime if manifest is not None else "codex")
    install_scope = getattr(args, "scope", None) or (manifest.scope if manifest is not None else "project")
    if install_scope != "project":
        raise ValueError("`prune` currently only supports project scope.")
    target_dir = context.manifest_target_dir(manifest_path, runtime_id, install_scope, getattr(args, "target_dir", None))
    lock_path = context.project_lock_path_for_manifest(manifest_path, target_dir, install_scope)
    if manifest is not None:
        repo_root = context.resolve_repo_root_if_available(getattr(args, "repo_root", None), config, cwd=manifest_path.parent)
        repo_root_for_target = repo_root or manifest_path.parent
        lockfile = context.project_lockfile_from_manifest(
            repo_root_for_target,
            config,
            manifest,
            runtime_id,
            install_scope,
            offline=getattr(args, "offline", False),
        )
        context.write_lockfile(context.project_sync.lockfile_to_resolution_plan(lockfile), lock_path)
    elif lock_path.exists():
        lockfile = context.read_lockfile(lock_path)
    else:
        raise FileNotFoundError("No manifest or lockfile is available for prune.")
    desired_skill_ids = context.project_sync.desired_skill_ids(lockfile)
    desired_assets = context.project_sync.desired_managed_assets(lockfile)
    prune_scope_skill_ids = context.managed_project_skill_ids(lock_path, desired_skill_ids)
    prune_scope_asset_ids = context.managed_project_asset_ids(lock_path, desired_assets)
    removed = context.prune_orphaned_project_skills(target_dir, runtime_id, desired_skill_ids, prune_scope_skill_ids)
    removed_assets = context.prune_orphaned_project_managed_assets(target_dir, runtime_id, desired_assets, prune_scope_asset_ids)
    # --- Prune from secondary (fan-out) runtimes ---
    base_root = manifest_path.parent
    secondary_pruned: list[str] = []
    for skill_id in removed:
        sec = _remove_from_secondary_runtimes(context, base_root, skill_id, runtime_id, install_scope)
        if sec:
            secondary_pruned.extend(sec)
    for line in context.project_sync_presentation.prune_result_lines(removed_skills=removed, removed_assets=removed_assets):
        print(line)
    if secondary_pruned:
        print(f"  also pruned from secondary runtimes: {', '.join(sorted(set(secondary_pruned)))}")
    return 0


def _compute_cascade_removals(
    lockfile: Lockfile,
    asset_kind: str,
    asset_id: str,
) -> list[str]:
    """Compute orphaned dependencies after removing an asset.

    Returns a list of canonical IDs for runtime-installed assets that
    should be removed because no remaining node depends on them.
    """
    target_ns, target_base = split_canonical_id(asset_id)
    target_key = package_key_for(asset_kind, target_base, target_ns)
    
    # Build node-key → LockNode mapping
    node_map: dict[str, Any] = {}
    for node in lockfile.nodes:
        key = package_key_for(node.type, node.id, node.namespace)
        node_map[key] = node
    
    target_node = node_map.get(target_key)
    if target_node is None:
        return []
    
    # Remaining nodes = everything except the target
    remaining_keys = {
        package_key_for(n.type, n.id, n.namespace)
        for n in lockfile.nodes
    }
    remaining_keys.discard(target_key)
    
    # Iterative convergence: mark orphan nodes whose only consumers
    # are themselves being removed, until the set stabilises.
    removed_keys: set[str] = {target_key}
    changed = True
    while changed:
        changed = False
        # Build "required by surviving nodes" each round
        required_by_survivors: set[str] = set()
        for key in remaining_keys:
            if key in removed_keys:
                continue
            node = node_map[key]
            required_by_survivors.update(node.requires or [])
        # Root requests from surviving roots are also "required"
        for req in lockfile.root_requests:
            req_key = package_key_for(req.type, req.id, req.namespace)
            if req_key not in removed_keys:
                required_by_survivors.add(req_key)
    
        for key in list(remaining_keys):
            if key in removed_keys:
                continue
            if key not in required_by_survivors:
                removed_keys.add(key)
                remaining_keys.discard(key)
                changed = True
    
    # Collect canonical IDs of orphaned nodes (excluding the target itself)
    orphans: list[str] = []
    for key in removed_keys:
        if key == target_key:
            continue
        node = node_map.get(key)
        if node is not None:
            orphans.append(node.canonical_id or node.id)
    return orphans


def _resolve_manifest_for_scope(
    scope: str | None,
    target_dir: Path,
) -> tuple[Path | None, Path | None]:
    """Resolve manifest yml and lockfile paths based on scope.

    Returns (manifest_path, lock_path). Either may be None if not found.
    """
    if scope == "global":
        global_state = state_dir()
        global_yml = global_state / "ai-kit.yml"
        global_lock = global_state / "ai-kit.lock"
        return (
            global_yml if global_yml.exists() else None,
            global_lock if global_lock.exists() else None,
        )
    return (
        find_project_manifest(target_dir),
        find_project_lockfile(target_dir),
    )


def _remove_from_secondary_runtimes(
    context: InstallCommandContext,
    base_root: Path,
    skill_id: str,
    primary_runtime: str,
    scope: str,
) -> list[str]:
    """Remove a skill from all secondary runtime directories (fan-out targets).

    Returns list of runtime_ids from which the skill was removed.
    """
    from ai_kit.domain.runtime_install import (
        RUNTIME_PROFILES,
        discover_available_runtimes,
        runtime_profile,
    )

    removed_from: list[str] = []

    if scope == "global":
        # Global scope: resolve each runtime's global_target directly
        from ai_kit.infrastructure.config_io import default_home_dir
        base_home = default_home_dir().resolve()
        for secondary_runtime, profile in RUNTIME_PROFILES.items():
            if secondary_runtime == primary_runtime:
                continue
            if not profile.global_target or profile.install_mode != "skill_dir":
                continue
            gt = profile.global_target
            if gt.startswith("~/"):
                secondary_target = (base_home / gt[2:]).resolve()
            else:
                secondary_target = Path(gt).expanduser().resolve()
            if not secondary_target.exists():
                continue
            if context.remove_installed_skill(secondary_target, skill_id, secondary_runtime):
                removed_from.append(secondary_runtime)
    else:
        # Project scope: discover available runtimes from project root
        discovered = discover_available_runtimes(base_root)
        for secondary_runtime in discovered:
            if secondary_runtime == primary_runtime:
                continue
            try:
                profile = runtime_profile(secondary_runtime)
            except ValueError:
                continue
            if profile.install_mode != "skill_dir":
                continue
            try:
                secondary_target = context.resolve_target_dir(
                    base_root, None, runtime_id=secondary_runtime, scope=scope,
                )
            except (ValueError, Exception):
                continue
            if not secondary_target.exists():
                continue
            if context.remove_installed_skill(secondary_target, skill_id, secondary_runtime):
                removed_from.append(secondary_runtime)
    return removed_from


def command_uninstall(args: argparse.Namespace, config_path: Path, context: InstallCommandContext) -> int:
    config = context.effective_config(context.load_config(config_path))
    if args.asset_kind == "skill":
        repo_root = context.resolve_repo_root_if_available(getattr(args, "repo_root", None), config)
        base_root = repo_root or Path.cwd()
        target_dir = context.resolve_target_dir(base_root, getattr(args, "target_dir", None), runtime_id=args.runtime, scope=args.scope)
        removed = context.remove_installed_skill(target_dir, args.asset_id, args.runtime)
        if not removed:
            print(context.project_sync_presentation.uninstall_skill_missing_line(asset_id=args.asset_id, target_dir=target_dir))
            return 0
        print(context.project_sync_presentation.uninstall_skill_success_line(asset_id=args.asset_id, target_dir=target_dir))

        # --- Phase 1b: Remove from secondary (fan-out) runtimes ---
        secondary_removed = _remove_from_secondary_runtimes(
            context, base_root, args.asset_id, args.runtime, args.scope,
        )
        for rt in secondary_removed:
            print(f"  removed {args.asset_id} from {rt} runtime")

        # --- Phase 2: Clean yml manifest declaration ---
        manifest_path, lock_path = _resolve_manifest_for_scope(args.scope, target_dir)
        if manifest_path is not None:
            manifest = load_project_manifest(manifest_path)
            if remove_asset_from_manifest(manifest, "skill", args.asset_id):
                save_project_manifest(manifest_path, manifest)
                print(context.project_sync_presentation.uninstall_manifest_removed_line(
                    asset_kind="skill", asset_id=args.asset_id, manifest_path=manifest_path,
                ))
            else:
                print(context.project_sync_presentation.uninstall_manifest_not_declared_line(
                    asset_kind="skill", asset_id=args.asset_id, manifest_path=manifest_path,
                ))
        else:
            print(context.project_sync_presentation.uninstall_manifest_not_found_line())

        # --- Phase 3: Dependency cascade removal ---
        if lock_path is not None and lock_path.exists():
            lockfile = context.read_lockfile(lock_path)
            orphan_ids = _compute_cascade_removals(lockfile, "skill", args.asset_id)
            if orphan_ids:
                removed_cascade: list[str] = []
                for orphan_id in orphan_ids:
                    if context.remove_installed_skill(target_dir, orphan_id, args.runtime):
                        removed_cascade.append(orphan_id)
                        # Also remove cascade orphans from secondary runtimes
                        _remove_from_secondary_runtimes(
                            context, base_root, orphan_id, args.runtime, args.scope,
                        )
                if removed_cascade:
                    print(context.project_sync_presentation.uninstall_cascade_removed_line(
                        removed_ids=removed_cascade, target_dir=target_dir,
                    ))
            else:
                print(context.project_sync_presentation.uninstall_cascade_none_line())
        return 0
    if args.asset_kind == "cli":
        repo_root = context.resolve_repo_root_if_available(getattr(args, "repo_root", None), config)
        inventory = context.load_combined_cli_inventory(repo_root, config)
        record = inventory.get(args.asset_id)
        if record is not None and record.install_type == "binary-release":
            metadata = context.load_cli_metadata_for_record(record)
            spec = context.binary_release_platform_spec(record, metadata)
            install_path = context.binary_release_install_path(record, spec)
            if getattr(args, "dry_run", False):
                print(context.project_sync_presentation.uninstall_cli_binary_dry_run_line(install_path=install_path))
                return 0
            if not install_path.exists():
                print(context.project_sync_presentation.uninstall_cli_binary_missing_line(install_path=install_path))
                return 0
            install_path.unlink()
            print(context.project_sync_presentation.uninstall_cli_binary_success_line(install_path=install_path))
            # --- Phase 2: Clean yml manifest declaration ---
            manifest_path, _ = _resolve_manifest_for_scope(args.scope, Path.cwd())
            if manifest_path is not None:
                manifest = load_project_manifest(manifest_path)
                if remove_asset_from_manifest(manifest, "cli", args.asset_id):
                    save_project_manifest(manifest_path, manifest)
                    print(context.project_sync_presentation.uninstall_manifest_removed_line(
                        asset_kind="cli", asset_id=args.asset_id, manifest_path=manifest_path,
                    ))
            return 0
        package_name = record.package_name if record is not None else args.asset_id
        command = [sys.executable, "-m", "pip", "uninstall", "-y", package_name]
        if getattr(args, "dry_run", False):
            print(context.project_sync_presentation.uninstall_cli_package_dry_run_line(command=command))
            return 0
        subprocess.run(command, check=True, capture_output=True, text=True, encoding="utf-8")
        print(context.project_sync_presentation.uninstall_cli_package_success_line(package_name=package_name))
        # --- Phase 2: Clean yml manifest declaration ---
        manifest_path, _ = _resolve_manifest_for_scope(args.scope, Path.cwd())
        if manifest_path is not None:
            manifest = load_project_manifest(manifest_path)
            if remove_asset_from_manifest(manifest, "cli", args.asset_id):
                save_project_manifest(manifest_path, manifest)
                print(context.project_sync_presentation.uninstall_manifest_removed_line(
                    asset_kind="cli", asset_id=args.asset_id, manifest_path=manifest_path,
                ))
        return 0
    if args.asset_kind in {"plugin", "hook", "subagent", "mcp", "loop"}:
        repo_root = context.resolve_repo_root_if_available(getattr(args, "repo_root", None), config)
        base_root = repo_root or Path.cwd()
        target_dir = context.resolve_target_dir(base_root, getattr(args, "target_dir", None), runtime_id=args.runtime, scope=args.scope)
        removed = context.remove_installed_managed_asset(target_dir, args.asset_kind, args.asset_id, args.runtime)
        managed_root = context.runtime_managed_asset_root(target_dir, args.runtime)
        if not removed:
            print(context.project_sync_presentation.uninstall_managed_missing_line(asset_kind=args.asset_kind, asset_id=args.asset_id, root=managed_root))
            return 0
        print(context.project_sync_presentation.uninstall_managed_success_line(asset_kind=args.asset_kind, asset_id=args.asset_id, root=managed_root))

        # --- Phase 2: Clean yml manifest declaration ---
        manifest_path, _ = _resolve_manifest_for_scope(args.scope, target_dir)
        if manifest_path is not None:
            manifest = load_project_manifest(manifest_path)
            if remove_asset_from_manifest(manifest, args.asset_kind, args.asset_id):
                save_project_manifest(manifest_path, manifest)
                print(context.project_sync_presentation.uninstall_manifest_removed_line(
                    asset_kind=args.asset_kind, asset_id=args.asset_id, manifest_path=manifest_path,
                ))
            else:
                print(context.project_sync_presentation.uninstall_manifest_not_declared_line(
                    asset_kind=args.asset_kind, asset_id=args.asset_id, manifest_path=manifest_path,
                ))
        return 0
    raise ValueError("MCP uninstall is manual right now; remove it from your external MCP configuration directly.")


def project_sync_skill_preview_items(summary: dict[str, Any], context: InstallCommandContext) -> list[tuple[Any, Path, str, str]]:
    return [
        (
            node,
            context.runtime_install_destination(summary["target_dir"], node.id, summary["runtime"]),
            summary["runtime"],
            summary["scope"],
        )
        for node in context.pm.topological_skill_nodes_from_lock(summary["lockfile"])
    ]


def project_sync_managed_preview_items(summary: dict[str, Any], context: InstallCommandContext) -> list[tuple[Any, Path]]:
    return [
        (
            node,
            context.managed_asset_install_destination(summary["target_dir"], node.type, node.id, summary["runtime"]),
        )
        for node in summary["lockfile"].nodes
        if node.type in {"plugin", "hook", "subagent", "mcp", "loop"}
    ]


def print_project_sync_dry_run_summary(
    summary: dict[str, Any],
    context: InstallCommandContext,
    *,
    external_dependency_lines: Sequence[str] = (),
) -> None:
    extends_info = summary.get("extends_summary", {})
    for line in context.project_sync_presentation.project_sync_dry_run_lines(
        skill_items=project_sync_skill_preview_items(summary, context),
        cli_records=summary["cli_records"],
        managed_items=project_sync_managed_preview_items(summary, context),
        removed_skills=summary["removed_skills"],
        removed_assets=summary["removed_assets"],
        external_dependency_lines=external_dependency_lines,
        extends_summary=extends_info.get("extends_summary_line"),
        extends_merge_lines=extends_info.get("merge_lines", []),
    ):
        print(line)
    context.print_non_skill_requirements(summary["lockfile"])
    print(context.project_sync_presentation.project_sync_lockfile_line(summary["lock_path"], dry_run=True))
    for line in context.project_sync_presentation.multi_runtime_sync_lines(summary.get("multi_runtime_results", {})):
        print(line)


def print_project_sync_applied_summary(
    summary: dict[str, Any],
    context: InstallCommandContext,
    *,
    action: str = "synced",
    external_dependency_lines: Sequence[str] = (),
) -> None:
    skill_items = [
        (node, destination, context.manual_invocation_hint(summary["runtime"], node.id))
        for node, destination in zip(context.pm.topological_skill_nodes_from_lock(summary["lockfile"]), summary["installed_paths"])
    ]
    cli_items = list(zip(summary.get("cli_records", []), summary.get("cli_outputs", [])))
    extends_info = summary.get("extends_summary", {})
    for line in context.project_sync_presentation.project_sync_applied_lines(
        skill_items=skill_items,
        cli_items=cli_items,
        managed_items=summary.get("installed_asset_paths", []),
        removed_skills=summary.get("removed_skills", []),
        removed_assets=summary.get("removed_assets", []),
        action=action,
        external_dependency_lines=external_dependency_lines,
        extends_summary=extends_info.get("extends_summary_line"),
        extends_merge_lines=extends_info.get("merge_lines", []),
    ):
        print(line)
    context.print_non_skill_requirements(summary["lockfile"])
    print(context.project_sync_presentation.project_sync_lockfile_line(summary["lock_path"], dry_run=False))
    for line in context.project_sync_presentation.multi_runtime_sync_lines(summary.get("multi_runtime_results", {})):
        print(line)


def standalone_install_skill_preview_items(lockfile: Any, target_dir: Path, runtime_id: str, install_scope: str, context: InstallCommandContext) -> list[tuple[Any, Path, str, str]]:
    return [
        (
            node,
            context.runtime_install_destination(target_dir, node.id, runtime_id),
            runtime_id,
            install_scope,
        )
        for node in context.pm.topological_skill_nodes_from_lock(lockfile)
    ]


def standalone_install_managed_preview_items(lockfile: Any, target_dir: Path, runtime_id: str, context: InstallCommandContext) -> list[tuple[Any, Path]]:
    return [
        (
            node,
            context.managed_asset_install_destination(target_dir, node.type, node.id, runtime_id),
        )
        for node in lockfile.nodes
        if node.type in {"plugin", "hook", "subagent", "mcp", "loop"}
    ]


def standalone_install_should_initialize_manifest(
    *,
    manifest: Any | None,
    install_scope: str,
    asset_ids: Sequence[str],
    install_all: bool,
) -> bool:
    return manifest is None and install_scope == "project" and bool(asset_ids) and not install_all


def _git_skill_key(skill: Any, context: InstallCommandContext) -> str:
    return context.pm.canonical_package_id(skill.id, skill.namespace)


def _git_skill_display_name(skill: Any, context: InstallCommandContext) -> str:
    summary = str(getattr(skill, "summary", "") or "").strip()
    key = _git_skill_key(skill, context)
    return f"{key} - {summary}" if summary else key


def _select_git_source_skills(discovered: list[Any], args: argparse.Namespace, context: InstallCommandContext) -> list[Any]:
    if not discovered:
        raise ValueError("No skills were found in the git source.")
    if len(discovered) == 1 or getattr(args, "all", False):
        return discovered
    if not context.stdin_isatty():
        available = ", ".join(_git_skill_key(item, context) for item in discovered)
        raise ValueError(
            "The git source contains multiple skills. "
            f"Use `--all`, pass a GitHub `/tree/<ref>/<subpath>` URL, or choose one of: {available}."
        )
    print("Select skills to install:")
    for index, item in enumerate(discovered, start=1):
        print(f"{index}. {_git_skill_display_name(item, context)}")
    answer = context.prompt_input("Enter numbers separated by comma, or `all`: ").strip()
    if answer.lower() == "all":
        return discovered
    indexes: list[int] = []
    for token in answer.replace(",", " ").split():
        try:
            index = int(token)
        except ValueError as exc:
            raise ValueError(f"Invalid selection: {token}") from exc
        if index < 1 or index > len(discovered):
            raise ValueError(f"Selection out of range: {index}")
        if index not in indexes:
            indexes.append(index)
    if not indexes:
        raise ValueError("No skills selected.")
    return [discovered[index - 1] for index in indexes]


def _looks_like_github_shorthand(value: str) -> bool:
    return "/" in value and not value.startswith((".", "/", "\\"))


def _is_explicit_git_source(value: str, args: argparse.Namespace, context: InstallCommandContext) -> bool:
    return context.is_git_source_selector(value) or (
        getattr(args, "source_selector", None) == context.pm.SOURCE_GIT_REPO and _looks_like_github_shorthand(value)
    )


def _expand_git_source_skill_ids(
    asset_ids: list[str],
    args: argparse.Namespace,
    context: InstallCommandContext,
) -> tuple[list[str], dict[str, tuple[str, str | None, str | None]]]:
    root_ids: list[str] = []
    root_sources: dict[str, tuple[str, str | None, str | None]] = {}
    for asset_id in asset_ids:
        if not _is_explicit_git_source(asset_id, args, context):
            root_ids.append(asset_id)
            continue
        selected = _select_git_source_skills(context.discover_git_skills(asset_id), args, context)
        for item in selected:
            key = _git_skill_key(item, context)
            if key in root_sources:
                continue
            root_ids.append(key)
            root_sources[key] = (item.source_ref, item.ref, item.subpath)
    return root_ids, root_sources


def command_sync(args: argparse.Namespace, config_path: Path, context: InstallCommandContext) -> int:
    config = context.effective_config(context.load_config(config_path))
    scope = getattr(args, "scope", None)

    # For global scope, always prefer the global state directory over project yml
    if scope == "global":
        global_state = state_dir()
        global_yml = global_state / "ai-kit.yml"
        global_lock = global_state / "ai-kit.lock"
        if global_yml.exists():
            manifest_path = global_yml
            manifest = load_project_manifest(global_yml)
        elif global_lock.exists():
            lockfile = context.read_lockfile(global_lock)
            manifest = project_manifest_from_lockfile(lockfile)
            save_project_manifest(global_yml, manifest)
            manifest_path = global_yml
            print(f"Bootstrapped global manifest from lockfile -> {global_yml}")
        else:
            explicit_global_ids = list(getattr(args, "skill_ids", []))
            if explicit_global_ids and not getattr(args, "all", False):
                # Standalone global install with explicit ids: auto-initialize an
                # empty global manifest (the requested skill is auto-added below).
                # This lets a fresh member (esp. consumer) run
                # `install skill <id> --scope global` without a prior `add`.
                runtime_id = context.manifest_aware_runtime(args, None)
                manifest = ProjectManifest(
                    schema_version=PROJECT_MANIFEST_SCHEMA_VERSION,
                    runtime=runtime_id,
                    scope="global",
                )
                save_project_manifest(global_yml, manifest)
                manifest_path = global_yml
                print(f"Initialized global manifest -> {global_yml}")
            else:
                raise FileNotFoundError(
                    f"No global ai-kit.yml or lockfile found. "
                    f"Run `ai-kit add skill <id> --scope global` first, "
                    f"or create {global_yml} manually."
                )
    else:
        manifest_path, manifest = context.load_contextual_project_manifest(getattr(args, "target_dir", None))

    explicit_tokens = list(getattr(args, "skill_ids", []))
    if args.command == "sync":
        if manifest_path is None or manifest is None:
            raise FileNotFoundError("No ai-kit.yml found in the current project.")
        # --all-runtimes flag overrides manifest sync_targets
        if getattr(args, "all_runtimes", False) and not manifest.sync_targets:
            manifest = manifest.model_copy(update={"sync_targets": ["all"]})
        summary = context.run_project_sync(
            config,
            manifest_path,
            manifest,
            repo_root_arg=getattr(args, "repo_root", None),
            target_dir_override=getattr(args, "target_dir", None),
            runtime_override=getattr(args, "runtime", None),
            scope_override=getattr(args, "scope", None),
            sync_repo=getattr(args, "sync_repo", False),
            offline=getattr(args, "offline", False),
            dry_run=getattr(args, "dry_run", False),
            cli_upgrade=True,
        )
        if getattr(args, "dry_run", False):
            external_lines = (
                context.install_environment_requirements(
                    context.environment_records_for_lockfile(summary["lockfile"]),
                    dry_run=True,
                )
                if resolve_install_external(args, config)
                else []
            )
            print_project_sync_dry_run_summary(summary, context, external_dependency_lines=external_lines)
            return 0
        print_project_sync_applied_summary(summary, context)
        return 0
    mode, asset_ids = context.parse_asset_selector(explicit_tokens, "skill")
    git_source_all = (
        getattr(args, "all", False)
        and mode == "skill"
        and bool(asset_ids)
        and all(_is_explicit_git_source(asset_id, args, context) for asset_id in asset_ids)
    )
    if not git_source_all:
        context.validate_sync_selection(args, has_manifest=manifest is not None)
    if manifest_path is not None and manifest is not None and not getattr(args, "all", False) and not asset_ids:
        summary = context.run_project_sync(
            config,
            manifest_path,
            manifest,
            repo_root_arg=getattr(args, "repo_root", None),
            target_dir_override=getattr(args, "target_dir", None),
            runtime_override=getattr(args, "runtime", None),
            scope_override=getattr(args, "scope", None),
            sync_repo=getattr(args, "sync_repo", False),
            offline=getattr(args, "offline", False),
            dry_run=getattr(args, "dry_run", False),
            cli_upgrade=args.command == "update",
        )
        if getattr(args, "dry_run", False):
            print_project_sync_dry_run_summary(summary, context)
            return 0
        action = "updated" if args.command == "update" else "synced"
        environment_records = context.environment_records_for_lockfile(summary["lockfile"])
        external_lines = []
        if resolve_install_external(args, config):
            external_lines = context.install_environment_requirements(environment_records, dry_run=False)
        missing_external = context.missing_environment_requirements(environment_records)
        required_missing_external = [item for item in missing_external if item["optional"] != "yes"]
        if required_missing_external:
            for line in context.project_sync_presentation.missing_external_dependency_warning_lines(required_missing_external):
                print(line)
            if resolve_install_external(args, config):
                raise ValueError("External dependency installation did not satisfy all required environment requirements.")
        print_project_sync_applied_summary(summary, context, action=action, external_dependency_lines=external_lines)
        return 0
    if mode == "cli":
        repo_root = context.resolve_repo_root_if_available(getattr(args, "repo_root", None), config)
        if repo_root is not None:
            context.maybe_sync_repo(args, repo_root)
        local_inventory = context.load_cli_inventory(repo_root) if repo_root is not None else {}
        if getattr(args, "all", False) or any(cli_id not in local_inventory for cli_id in asset_ids):
            inventory = context.load_combined_cli_inventory(repo_root, config)
        else:
            inventory = local_inventory
        records = context.select_cli_records(inventory, asset_ids, getattr(args, "all", False))
        if not args.dry_run and any(context.is_self_cli_package(record.package_name) for record in records):
            recovery = context.self_upgrade_recovery_command(config)
            raise ValueError(
                "Refusing to install or upgrade ai-kit from a running ai-kit process on Windows. "
                f"Run this manually instead: {recovery}. "
                "If you also want the operator workflow skill, install it separately with "
                "`ai-kit install skill ai-kit-ops`."
            )
        outputs = context.install_cli_packages(records, config, upgrade=args.command == "update", dry_run=args.dry_run)
        action = "upgrade" if args.command == "update" else "install"
        cli_items = list(zip(records, outputs))
        if args.dry_run:
            for line in context.project_sync_presentation.cli_install_dry_run_lines(cli_items=cli_items, action=action):
                print(line)
            return 0
        for line in context.project_sync_presentation.cli_install_applied_lines(
            cli_items=cli_items,
            action=action,
            include_operator_hint=any(record.cli_id == "ai-kit" for record in records),
        ):
            print(line)
        return 0
    if mode == "loop":
        repo_root = context.resolve_repo_root_if_available(getattr(args, "repo_root", None), config)
        if repo_root is not None:
            context.maybe_sync_repo(args, repo_root)
        elif getattr(args, "sync_repo", False):
            raise ValueError("`--sync-repo` requires a bootstrapped local repository or explicit --repo-root.")
        if not asset_ids:
            raise ValueError("No loop ids specified. Pass loop ids, e.g. `ai-kit install loop batch-migration-loop`.")
        runtime_id = context.manifest_aware_runtime(args, manifest)
        install_scope = context.manifest_aware_scope(args, manifest)
        target_dir_override = getattr(args, "target_dir", None)
        if target_dir_override:
            target_dir = Path(target_dir_override).expanduser().resolve()
        else:
            # Loop 物化落点是执行工作空间的项目根（ai-kit.yml 所在目录）
            # 的 .agents/loops；无 manifest 时退化为 cwd。资产解析来源的源仓
            # （repo_root）只用于 resolve_skill_plan，不作为落点——避免 lock 与
            # loop 副本被写进源仓库（factory-audit 2026-08-04 L2#4）。
            project_root = manifest_path.parent if manifest_path is not None else Path.cwd()
            target_dir = project_root / ".agents" / "loops"
        target_dir.mkdir(parents=True, exist_ok=True)
        root_ids = asset_ids
        lock_path = target_dir / "ai-kit.lock"
        plan_kwargs: dict[str, object] = {}
        if manifest is not None:
            plan_kwargs["preferred_sources"] = context.manifest_skill_source_policy(manifest)
            plan_kwargs["root_sources"] = context.manifest_skill_root_sources(manifest)
        unresolved_deps: list[str] = []
        try:
            plan = context.resolve_skill_plan(
                repo_root or Path.cwd(),
                config,
                root_ids=root_ids,
                runtime_id=runtime_id,
                install_scope=install_scope,
                features=[],
                offline=getattr(args, "offline", False),
                asset_kind="loop",
                **plan_kwargs,
            )
        except Exception as exc:
            if ResolutionImpossible is not None and isinstance(exc, ResolutionImpossible):
                unresolved_deps = sorted({
                    info.requirement.package_id
                    for info in (exc.causes or [])
                    if getattr(info, "requirement", None) is not None
                    and getattr(info.requirement, "dep_type", None) == "skill"
                })
                if unresolved_deps:
                    print(f"WARNING: Loop dependencies not found in local repo or registry: {', '.join(unresolved_deps)}")
                    print("Installing loop without unresolved skill dependencies.")
                    # Strip unresolved deps from the loop manifest for this install
                    _strip_unresolved_loop_deps(repo_root, root_ids, unresolved_deps)
                    try:
                        plan = context.resolve_skill_plan(
                            repo_root or Path.cwd(),
                            config,
                            root_ids=root_ids,
                            runtime_id=runtime_id,
                            install_scope=install_scope,
                            features=[],
                            offline=getattr(args, "offline", False),
                            asset_kind="loop",
                            **plan_kwargs,
                        )
                    finally:
                        _restore_loop_deps(repo_root, root_ids)
                else:
                    raise
            else:
                raise
        lockfile = plan.to_lockfile()
        context.write_lockfile(plan, lock_path)
        loop_nodes = [node for node in lockfile.nodes if node.type == "loop"]
        cli_dep_nodes = [node for node in lockfile.nodes if node.type == "cli"]
        if args.dry_run:
            print(f"[dry-run] Would install {len(loop_nodes)} loop(s) to {target_dir}")
            for node in loop_nodes:
                print(f"  - {node.canonical_id} {node.version} -> {target_dir / node.id}")
            for node in cli_dep_nodes:
                print(f"  - requires CLI {node.canonical_id} {node.version} (install separately: ai-kit install cli {node.id})")
            if unresolved_deps:
                print(f"[dry-run] Skipped unresolved dependencies: {', '.join(unresolved_deps)}")
            return 0
        # Loops are managed assets — materialize via the managed-asset installer
        # (apply_skill_lockfile only installs type=="skill" nodes and would
        # silently skip loop nodes). CLI deps are requirements, not loop assets:
        # they are reported as hints, never materialized into the loops dir.
        installed_asset_paths = context.apply_managed_asset_lockfile(lockfile, target_dir, runtime_id)
        action = "updated" if args.command == "update" else "installed"
        for node, destination in installed_asset_paths:
            print(f"{action} loop {node.canonical_id} {node.version} -> {destination}")
        for node in cli_dep_nodes:
            print(f"note: requires CLI {node.canonical_id} {node.version} (install separately: ai-kit install cli {node.id})")
        if unresolved_deps:
            print(f"WARNING: Skipped unresolved dependencies: {', '.join(unresolved_deps)}")
            print("Run `ai-kit install skill <id>` for each once they become available.")
        return 0

    repo_root = context.resolve_repo_root_if_available(getattr(args, "repo_root", None), config)
    if repo_root is not None:
        context.maybe_sync_repo(args, repo_root)
    elif getattr(args, "sync_repo", False):
        raise ValueError("`--sync-repo` requires a bootstrapped local repository or explicit --repo-root.")
    explicit_git_root_sources: dict[str, tuple[str, str | None, str | None]] = {}
    if asset_ids and mode == "skill":
        asset_ids, explicit_git_root_sources = _expand_git_source_skill_ids(asset_ids, args, context)
    if getattr(args, "all", False) and repo_root is None and not explicit_git_root_sources:
        raise ValueError("`ai-kit install skill --all` requires a bootstrapped local repository or explicit --repo-root.")
    if not getattr(args, "all", False) and not asset_ids and manifest is None:
        raise ValueError("No skill roots selected. Pass a skill id or create ai-kit.yml.")
    repo_root_for_target = repo_root or Path.cwd()
    runtime_id = context.manifest_aware_runtime(args, manifest)
    install_scope = context.manifest_aware_scope(args, manifest)
    target_dir = context.resolve_target_dir(repo_root_for_target, getattr(args, "target_dir", None), runtime_id=runtime_id, scope=install_scope)
    # --- runtime priority: skip skills already present in a higher-priority runtime ---
    runtime_priority = None
    if manifest is not None and getattr(manifest, "runtime_priority", None):
        runtime_priority = list(manifest.runtime_priority)
    if getattr(args, "all", False) and explicit_git_root_sources:
        root_ids = asset_ids
    elif getattr(args, "all", False) and repo_root is not None:
        root_ids = list(context.load_skill_inventory(repo_root))
    elif asset_ids:
        root_ids = asset_ids
    elif manifest is not None:
        root_ids = context.project_root_ids(manifest)
    else:
        root_ids = []
    if not root_ids:
        print(context.project_sync_presentation.no_skills_matched_line())
        return 0
    # Filter out skills already present in a higher-priority runtime
    if runtime_priority is not None and runtime_id in runtime_priority:
        from ai_kit.domain.runtime_install import should_skip_for_priority

        skipped: list[str] = []
        for sid in root_ids:
            skip, reason = should_skip_for_priority(target_dir, sid, runtime_id, runtime_priority)
            if skip:
                skipped.append(sid)
                print(reason)
        if skipped:
            root_ids = [sid for sid in root_ids if sid not in skipped]
            if not root_ids:
                print("All skills already present in higher-priority runtimes. Nothing to do.")
                return 0
    # Auto-add explicit skill_ids to manifest (in-memory only; persisted after successful install)
    _pending_manifest_new_ids: list[str] = []
    if manifest is not None and asset_ids and mode == "skill" and not getattr(args, "all", False):
        existing_ids = set(context.project_root_ids(manifest))
        new_ids = [sid for sid in root_ids if sid not in existing_ids]
        if new_ids:
            for sid in new_ids:
                spec = context.ProjectRootSpec(id=sid)
                context.add_skill_to_manifest(manifest, spec)
            _pending_manifest_new_ids = new_ids
    lock_path = context.project_lock_path_for_manifest(manifest_path, target_dir, install_scope)
    selected_features = context.explicit_feature_selection(args, manifest)
    source_selector = getattr(args, "source_selector", None)
    use_existing_lock = (
        lock_path.exists()
        and not getattr(args, "refresh_lock", False)
        and not getattr(args, "all", False)
        and not source_selector
    )
    if use_existing_lock:
        candidate_lock = context.read_lockfile(lock_path)
        if (
            candidate_lock.roots == root_ids
            and candidate_lock.runtime == runtime_id
            and candidate_lock.install_scope == install_scope
            and sorted(candidate_lock.features) == sorted(set(selected_features))
        ):
            lockfile = candidate_lock
        else:
            use_existing_lock = False
    if not use_existing_lock:
        plan_kwargs: dict[str, object] = {}
        if manifest is not None:
            plan_kwargs["preferred_sources"] = context.manifest_skill_source_policy(manifest)
            plan_kwargs["root_sources"] = context.manifest_skill_root_sources(manifest)
            root_specifiers = context.manifest_skill_version_specifiers(manifest)
            if root_specifiers:
                allowed = set(root_ids)
                plan_kwargs["root_specifiers"] = {
                    key: value for key, value in root_specifiers.items() if key in allowed
                }
        if explicit_git_root_sources:
            plan_kwargs["root_sources"] = {
                **dict(plan_kwargs.get("root_sources") or {}),
                **explicit_git_root_sources,
            }
        plan = context.resolve_skill_plan(
            repo_root or Path.cwd(),
            config,
            root_ids=root_ids,
            runtime_id=runtime_id,
            install_scope=install_scope,
            features=selected_features,
            offline=getattr(args, "offline", False),
            source_selector=source_selector,
            **plan_kwargs,
        )
        lockfile = plan.to_lockfile()
        if getattr(args, "refresh_lock", False) and manifest is not None and context.declared_cli_specs(manifest):
            lockfile = context.merge_manifest_cli_into_refresh_lockfile(
                lockfile,
                config,
                manifest,
                repo_root,
                offline=getattr(args, "offline", False),
            )
            context.write_lockfile_model(lockfile, lock_path)
        else:
            context.write_lockfile(plan, lock_path)
    if args.dry_run:
        external_lines = (
            context.install_environment_requirements(context.environment_records_for_lockfile(lockfile), dry_run=True)
            if resolve_install_external(args, config)
            else []
        )
        manifest_preview_path = (
            context.project_manifest_path(lock_path.parent)
            if standalone_install_should_initialize_manifest(
                manifest=manifest,
                install_scope=install_scope,
                asset_ids=asset_ids,
                install_all=getattr(args, "all", False),
            )
            else None
        )
        extends_info = context.compute_extends_summary(
            lockfile, context.pm.topological_skill_nodes_from_lock(lockfile)
        )
        lines = context.project_sync_presentation.standalone_install_dry_run_lines(
            skill_items=standalone_install_skill_preview_items(lockfile, target_dir, runtime_id, install_scope, context),
            managed_items=standalone_install_managed_preview_items(lockfile, target_dir, runtime_id, context),
            external_dependency_lines=external_lines,
            lock_path=lock_path,
            manifest_path=manifest_preview_path,
            extends_summary=extends_info.get("extends_summary_line"),
            extends_merge_lines=extends_info.get("merge_lines", []),
        )
        tail_count = 3 if manifest_preview_path is not None else 2
        for line in lines[:-tail_count]:
            print(line)
        context.print_non_skill_requirements(lockfile)
        for line in lines[-tail_count:]:
            print(line)
        return 0
    installed_paths = context.apply_skill_lockfile(repo_root or Path.cwd(), config, lockfile, target_dir, runtime_id, getattr(args, "offline", False))
    # Persist auto-added skills to manifest only after successful resolution and installation
    if _pending_manifest_new_ids:
        context.save_project_manifest(manifest_path, manifest)
        print(f"Auto-added {len(_pending_manifest_new_ids)} skill(s) to manifest: {', '.join(_pending_manifest_new_ids)}")
    installed_asset_paths = context.apply_managed_asset_lockfile(lockfile, target_dir, runtime_id)
    # 注入 agents_md_inject 内容到项目 AGENTS.md（幂等更新 + 卸载自动清除）
    if install_scope == "project":
        from ai_kit.application.project_sync import apply_agents_md_injections
        apply_agents_md_injections(lockfile, lock_path.parent)
    action = "updated" if args.command == "update" else "installed"
    environment_records = context.environment_records_for_lockfile(lockfile)
    external_lines = []
    if resolve_install_external(args, config):
        external_lines = context.install_environment_requirements(environment_records, dry_run=False)
    missing_external = context.missing_environment_requirements(environment_records)
    required_missing_external = [item for item in missing_external if item["optional"] != "yes"]
    if required_missing_external:
        for line in context.project_sync_presentation.missing_external_dependency_warning_lines(required_missing_external):
            print(line)
        if resolve_install_external(args, config):
            raise ValueError("External dependency installation did not satisfy all required environment requirements.")
    initialized_manifest_path = None
    if standalone_install_should_initialize_manifest(
        manifest=manifest,
        install_scope=install_scope,
        asset_ids=asset_ids,
        install_all=getattr(args, "all", False),
    ):
        manifest_path = context.project_manifest_path(lock_path.parent)
        context.bootstrap_project_manifest_from_lockfile(manifest_path, lockfile)
        initialized_manifest_path = manifest_path
    extends_info = context.compute_extends_summary(
        lockfile, context.pm.topological_skill_nodes_from_lock(lockfile)
    )
    lines = context.project_sync_presentation.standalone_install_applied_lines(
        skill_items=[
            (node, destination, context.manual_invocation_hint(runtime_id, node.id))
            for node, destination in zip(context.pm.topological_skill_nodes_from_lock(lockfile), installed_paths)
        ],
        managed_items=installed_asset_paths,
        action=action,
        external_dependency_lines=external_lines,
        initialized_manifest_path=initialized_manifest_path,
        lock_path=lock_path,
        runtime=runtime_id,
        extends_summary=extends_info.get("extends_summary_line"),
        extends_merge_lines=extends_info.get("merge_lines", []),
    )
    tail_count = 3 if runtime_id == "codex" else 2
    for line in lines[:-tail_count]:
        print(line)
    context.print_non_skill_requirements(lockfile)
    for line in lines[-tail_count:]:
        print(line)
    return 0


# ---------------------------------------------------------------------------
# Loop dependency fallback helpers
# ---------------------------------------------------------------------------

_LOOP_DEPS_BACKUP: dict[str, list[dict[str, Any]]] = {}


def _strip_unresolved_loop_deps(
    repo_root: Path | None,
    loop_ids: list[str],
    unresolved: list[str],
) -> None:
    """Temporarily remove unresolved skill deps from loop.json in the local repo."""
    if repo_root is None:
        return
    import json as _json

    unresolved_set = set(unresolved)
    for lid in loop_ids:
        loop_json = repo_root / "loops" / lid / "loop.json"
        if not loop_json.exists():
            continue
        data = _json.loads(loop_json.read_text(encoding="utf-8"))
        original_deps = data.get("dependencies", [])
        _LOOP_DEPS_BACKUP[lid] = original_deps
        data["dependencies"] = [
            d for d in original_deps
            if not (d.get("type") == "skill" and d.get("id") in unresolved_set)
        ]
        loop_json.write_text(_json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _restore_loop_deps(repo_root: Path | None, loop_ids: list[str]) -> None:
    """Restore loop.json dependencies from backup."""
    if repo_root is None:
        return
    import json as _json

    for lid in loop_ids:
        if lid not in _LOOP_DEPS_BACKUP:
            continue
        loop_json = repo_root / "loops" / lid / "loop.json"
        if not loop_json.exists():
            continue
        data = _json.loads(loop_json.read_text(encoding="utf-8"))
        data["dependencies"] = _LOOP_DEPS_BACKUP.pop(lid)
        loop_json.write_text(_json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

