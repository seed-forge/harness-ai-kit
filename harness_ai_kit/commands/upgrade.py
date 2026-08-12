from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness_ai_kit.domain.versions import is_latest_specifier
from harness_ai_kit.commands.install import resolve_install_external


@dataclass(frozen=True)
class UpgradeCommandContext:
    load_config: Callable[[Path], Any]
    effective_config: Callable[[Any], Any]
    load_project_manifest_if_present: Callable[[], tuple[Path | None, Any | None]]
    resolve_repo_root_if_available: Callable[..., Path | None]
    project_lockfile_from_manifest: Callable[..., Any]
    load_skill_inventory: Callable[[Path | None], dict[str, Any]]
    load_combined_cli_inventory: Callable[[Path | None, Any], dict[str, Any]]
    declared_skill_specs: Callable[[Any], list[Any]]
    declared_cli_specs: Callable[[Any], list[Any]]
    declared_plugin_specs: Callable[[Any], list[Any]]
    declared_hook_specs: Callable[[Any], list[Any]]
    declared_subagent_specs: Callable[[Any], list[Any]]
    declared_mcp_specs: Callable[[Any], list[Any]]
    load_managed_asset_inventory: Callable[[Path, str], dict[str, Any]]
    pm: Any
    spec_matches_version: Callable[[str, str], bool]
    format_table: Callable[[tuple[str, ...], list[tuple[str, ...]]], str]
    manifest_target_dir: Callable[[Path, str, str, str | None], Path]
    installed_skill_ids: Callable[[Path, str], list[str]]
    managed_project_skill_ids: Callable[[Path, Any], set[str]]
    project_lock_path_for_manifest: Callable[[Path | None, Path | None, str], Path]
    installed_managed_asset_ids: Callable[[Path, str, str], list[str]]
    managed_project_asset_ids: Callable[[Path, dict[str, set[str]]], dict[str, set[str]]]
    load_contextual_project_manifest: Callable[[str | None], tuple[Path | None, Any | None]]
    parse_asset_selector: Callable[[list[str], str], tuple[str, list[str]]]
    maybe_sync_repo: Callable[[argparse.Namespace, Path], None]
    load_cli_inventory: Callable[[Path | None], dict[str, Any]]
    installed_cli_records: Callable[[list[Any]], list[Any]]
    select_cli_records: Callable[[dict[str, Any], list[str], bool], list[Any]]
    is_self_cli_package: Callable[[str], bool]
    manifest_aware_runtime: Callable[[argparse.Namespace, Any | None], str]
    manifest_aware_scope: Callable[[argparse.Namespace, Any | None], str]
    explicit_feature_selection: Callable[[argparse.Namespace, Any | None], list[str]]
    resolve_target_dir: Callable[..., Path]
    read_lockfile: Callable[[Path], Any]
    runtime_install_destination: Callable[[Path, str, str], Path]
    select_records: Callable[[dict[str, Any], list[str], bool], list[Any]]
    project_sync_presentation: Any
    self_upgrade_recovery_command: Callable[[Any], str]
    install_cli_packages: Callable[[list[Any], Any], list[str]]
    project_root_ids: Callable[[Any], list[str]]
    resolve_skill_plan: Callable[..., Any]
    write_lockfile: Callable[[Any, Path], None]
    apply_skill_lockfile: Callable[[Path, Any, Any, Path, str, bool], list[Path]]
    prune_orphaned_project_skills: Callable[[Path, str, set[str], set[str]], list[str]]
    sync_records: Callable[[list[Any], Path, str], list[Path]]
    command_sync: Callable[[argparse.Namespace, Path], int]


def build_upgrade_handlers(context: UpgradeCommandContext) -> Mapping[str, Callable[[argparse.Namespace, Path], int]]:
    return {
        "outdated": lambda args, config_path: command_outdated(args, config_path, context),
        "diff": lambda args, config_path: command_diff(args, config_path, context),
        "upgrade": lambda args, config_path: command_upgrade(args, config_path, context),
    }


def command_outdated(args: argparse.Namespace, config_path: Path, context: UpgradeCommandContext) -> int:
    config = context.effective_config(context.load_config(config_path))
    manifest_path, manifest = context.load_project_manifest_if_present()
    if manifest_path is None or manifest is None:
        raise FileNotFoundError("No harness-ai-kit.yml found in the current project.")
    repo_root = context.resolve_repo_root_if_available(getattr(args, "repo_root", None), config, cwd=manifest_path.parent)
    repo_root_for_target = repo_root or manifest_path.parent
    lockfile = context.project_lockfile_from_manifest(
        repo_root_for_target,
        config,
        manifest,
        manifest.runtime,
        manifest.scope,
        offline=getattr(args, "offline", False),
    )
    skill_inventory = context.load_skill_inventory(repo_root) if repo_root is not None else {}
    cli_inventory = context.load_combined_cli_inventory(repo_root, config)
    rows: list[tuple[str, str, str, str]] = []
    for item in context.declared_skill_specs(manifest):
        key = context.pm.canonical_package_id(item.id, item.namespace)
        node = next(
            (
                candidate
                for candidate in lockfile.nodes
                if candidate.type == "skill"
                and (candidate.canonical_id or context.pm.canonical_package_id(candidate.id, candidate.namespace)) == key
            ),
            None,
        )
        if node is None:
            rows.append(("skill", key, "-", "unresolved"))
            continue
        declared_version = str(item.version) if hasattr(item, "version") else ""
        if is_latest_specifier(declared_version):
            available = skill_inventory.get(item.id)
            latest_ver = available.version if available is not None else node.version
            status = f"latest -> {latest_ver}"
            rows.append(("skill", key, "latest", status))
            continue
        if getattr(node, "source_url", None):
            local_commit = (node.source_commit or "")[:8] or node.version
            status = f"source_url (commit {local_commit})"
            rows.append(("skill", key, declared_version or node.version, status))
            continue
        available = skill_inventory.get(item.id)
        latest = available.version if available is not None else node.version
        status = "up-to-date" if latest == node.version else f"upgrade available -> {latest}"
        rows.append(("skill", key, node.version, status))
    for item in context.declared_cli_specs(manifest):
        key = context.pm.canonical_package_id(item.id, item.namespace)
        record = cli_inventory.get(item.id)
        latest = record.version if record is not None else "-"
        status = (
            "up-to-date"
            if record is not None and context.spec_matches_version(item.version, record.version)
            else (f"upgrade available -> {latest}" if record is not None else "unresolved")
        )
        rows.append(("cli", key, item.version, status))
    for asset_type, specs in (
        ("plugin", context.declared_plugin_specs(manifest)),
        ("hook", context.declared_hook_specs(manifest)),
        ("subagent", context.declared_subagent_specs(manifest)),
    ):
        inventory = context.load_managed_asset_inventory(repo_root, asset_type) if repo_root is not None else {}
        for item in specs:
            key = context.pm.canonical_package_id(item.id, item.namespace)
            record = inventory.get(item.id)
            latest = record.version if record is not None else "-"
            status = (
                "up-to-date"
                if record is not None and context.spec_matches_version(item.version, record.version)
                else (f"upgrade available -> {latest}" if record is not None else "unresolved")
            )
            rows.append((asset_type, key, item.version, status))
    for item in context.declared_mcp_specs(manifest):
        key = context.pm.canonical_package_id(item.id, item.namespace)
        rows.append(("mcp", key, item.version, "manual"))
    print(context.format_table(("TYPE", "ASSET", "DECLARED", "STATUS"), rows))
    return 0


def command_diff(args: argparse.Namespace, config_path: Path, context: UpgradeCommandContext) -> int:
    config = context.effective_config(context.load_config(config_path))
    manifest_path, manifest = context.load_project_manifest_if_present()
    if manifest_path is None or manifest is None:
        raise FileNotFoundError("No harness-ai-kit.yml found in the current project.")
    repo_root = context.resolve_repo_root_if_available(getattr(args, "repo_root", None), config, cwd=manifest_path.parent)
    repo_root_for_target = repo_root or manifest_path.parent
    runtime_id = getattr(args, "runtime", None) or manifest.runtime
    install_scope = getattr(args, "scope", None) or manifest.scope
    lockfile = context.project_lockfile_from_manifest(
        repo_root_for_target,
        config,
        manifest,
        runtime_id,
        install_scope,
        offline=getattr(args, "offline", False),
    )
    target_dir = context.manifest_target_dir(manifest_path, runtime_id, install_scope, getattr(args, "target_dir", None))
    installed = set(context.installed_skill_ids(target_dir, runtime_id)) if install_scope == "project" else set()
    locked_skills = {node.id for node in lockfile.nodes if node.type == "skill"}
    declared_skills = {item.id for item in context.declared_skill_specs(manifest)}
    managed_skills = context.managed_project_skill_ids(
        context.project_lock_path_for_manifest(manifest_path, target_dir, install_scope),
        locked_skills,
    )
    rows = [
        ("skills.declared", ", ".join(sorted(declared_skills)) or "-"),
        ("skills.locked", ", ".join(sorted(locked_skills)) or "-"),
        ("skills.installed", ", ".join(sorted(installed)) or "-"),
        ("skills.orphaned", ", ".join(sorted((installed & managed_skills) - locked_skills)) or "-"),
        ("clis.declared", ", ".join(sorted(item.id for item in context.declared_cli_specs(manifest))) or "-"),
        ("clis.locked", ", ".join(sorted(node.id for node in lockfile.nodes if node.type == "cli")) or "-"),
    ]
    for asset_type, specs in (
        ("plugin", context.declared_plugin_specs(manifest)),
        ("hook", context.declared_hook_specs(manifest)),
        ("subagent", context.declared_subagent_specs(manifest)),
    ):
        declared = {item.id for item in specs}
        locked = {node.id for node in lockfile.nodes if node.type == asset_type}
        installed_assets = set(context.installed_managed_asset_ids(target_dir, asset_type, runtime_id)) if install_scope == "project" else set()
        managed_assets = context.managed_project_asset_ids(
            context.project_lock_path_for_manifest(manifest_path, target_dir, install_scope),
            {asset_type: locked},
        ).get(asset_type, set())
        rows.extend(
            [
                (f"{asset_type}s.declared", ", ".join(sorted(declared)) or "-"),
                (f"{asset_type}s.locked", ", ".join(sorted(locked)) or "-"),
                (f"{asset_type}s.installed", ", ".join(sorted(installed_assets)) or "-"),
                (f"{asset_type}s.orphaned", ", ".join(sorted((installed_assets & managed_assets) - locked)) or "-"),
            ]
        )
    rows.extend(
        [
            ("mcps.declared", ", ".join(sorted(item.id for item in context.declared_mcp_specs(manifest))) or "-"),
            ("mcps.locked", ", ".join(sorted(node.id for node in lockfile.nodes if node.type == "mcp")) or "-"),
        ]
    )
    print(context.format_table(("STATE", "VALUE"), rows))
    return 0


def command_upgrade(args: argparse.Namespace, config_path: Path, context: UpgradeCommandContext) -> int:
    config = context.effective_config(context.load_config(config_path))
    repo_root = context.resolve_repo_root_if_available(getattr(args, "repo_root", None), config)
    install_scope_override = getattr(args, "scope", None)
    # For global scope, load the global manifest from state dir (mirrors command_sync behaviour).
    if install_scope_override == "global":
        from harness_ai_kit.domain.lockfile_io import state_dir
        from harness_ai_kit.domain.manifest_ops import load_project_manifest, save_project_manifest, project_manifest_from_lockfile
        global_state = state_dir()
        global_yml = global_state / "harness-ai-kit.yml"
        global_lock = global_state / "harness-ai-kit.lock"
        if global_yml.exists():
            manifest_path = global_yml
            manifest = load_project_manifest(global_yml)
        elif global_lock.exists():
            lockfile_obj = context.read_lockfile(global_lock)
            manifest = project_manifest_from_lockfile(lockfile_obj)
            save_project_manifest(global_yml, manifest)
            manifest_path = global_yml
        else:
            manifest_path, manifest = context.load_contextual_project_manifest(getattr(args, "target_dir", None))
    else:
        manifest_path, manifest = context.load_contextual_project_manifest(getattr(args, "target_dir", None))
    mode, asset_ids = context.parse_asset_selector(getattr(args, "asset_ids", []), "asset")
    if repo_root is not None:
        context.maybe_sync_repo(args, repo_root, force=bool(args.all))

    # Detect "latest" or source_url declarations — these always need a fresh resolve.
    has_latest_or_source_url = False
    if manifest is not None:
        for item in context.declared_skill_specs(manifest):
            if is_latest_specifier(str(getattr(item, "version", ""))):
                has_latest_or_source_url = True
                break
            if getattr(item, "source_url", None):
                has_latest_or_source_url = True
                break
    if has_latest_or_source_url and not args.all:
        args = argparse.Namespace(**vars(args), all=True)

    if args.all or mode == "asset":
        cli_inventory = context.load_cli_inventory(repo_root) if (repo_root is not None and args.all) else context.load_combined_cli_inventory(repo_root, config)
        cli_records = context.installed_cli_records(context.select_cli_records(cli_inventory, [], install_all=True))
        skipped_self_records = [record for record in cli_records if context.is_self_cli_package(record.package_name)]
        cli_records = [record for record in cli_records if not context.is_self_cli_package(record.package_name)]
        runtime_id = context.manifest_aware_runtime(args, manifest)
        install_scope = context.manifest_aware_scope(args, manifest)
        selected_features = context.explicit_feature_selection(args, manifest)
        repo_root_for_target = repo_root or Path.cwd()
        target_dir = context.resolve_target_dir(repo_root_for_target, getattr(args, "target_dir", None), runtime_id=runtime_id, scope=install_scope)
        lock_path = context.project_lock_path_for_manifest(manifest_path, target_dir, install_scope)
        lockfile = context.read_lockfile(lock_path) if lock_path.exists() else None
        if args.dry_run:
            lock_skill_items = []
            repo_skill_items = []
            if lockfile and target_dir is not None:
                lock_skill_items = [
                    (node, context.runtime_install_destination(target_dir, node.id, runtime_id), runtime_id, install_scope)
                    for node in context.pm.topological_skill_nodes_from_lock(lockfile)
                ]
            elif repo_root is not None and target_dir is not None:
                repo_skill_items = [
                    (record, context.runtime_install_destination(target_dir, record.path.name, runtime_id), runtime_id, install_scope, context.pm.SOURCE_REPO)
                    for record in context.select_records(context.load_skill_inventory(repo_root), [], install_all=True)
                ]
            for line in context.project_sync_presentation.bulk_upgrade_dry_run_lines(
                lock_skill_items=lock_skill_items,
                repo_skill_items=repo_skill_items,
                cli_items=list(zip(cli_records, context.install_cli_packages(cli_records, config, upgrade=True, dry_run=True))),
                skipped_self_records=skipped_self_records,
                recovery_command=context.self_upgrade_recovery_command(config),
            ):
                print(line)
            return 0
        upgraded_lock_skill_nodes = []
        upgraded_repo_skill_records = []
        removed_skills = []
        if lockfile and target_dir is not None and lock_path is not None:
            if manifest is not None:
                plan = context.resolve_skill_plan(
                    repo_root_for_target,
                    config,
                    root_ids=context.project_root_ids(manifest),
                    runtime_id=runtime_id,
                    install_scope=install_scope,
                    features=selected_features,
                    offline=False,
                )
                lockfile = plan.to_lockfile()
                context.write_lockfile(plan, lock_path)
            context.apply_skill_lockfile(repo_root_for_target, config, lockfile, target_dir, runtime_id, offline=False)
            prune_scope_skill_ids = context.managed_project_skill_ids(lock_path, {node.id for node in lockfile.nodes if node.type == "skill"})
            removed_skills = (
                context.prune_orphaned_project_skills(
                    target_dir,
                    runtime_id,
                    {node.id for node in lockfile.nodes if node.type == "skill"},
                    prune_scope_skill_ids,
                )
                if install_scope == "project"
                else []
            )
            upgraded_lock_skill_nodes = context.pm.topological_skill_nodes_from_lock(lockfile)
        elif manifest is not None and target_dir is not None and lock_path is not None:
            plan = context.resolve_skill_plan(
                repo_root_for_target,
                config,
                root_ids=context.project_root_ids(manifest),
                runtime_id=runtime_id,
                install_scope=install_scope,
                features=selected_features,
                offline=False,
            )
            lockfile = plan.to_lockfile()
            context.write_lockfile(plan, lock_path)
            context.apply_skill_lockfile(repo_root_for_target, config, lockfile, target_dir, runtime_id, offline=False)
            prune_scope_skill_ids = context.managed_project_skill_ids(lock_path, {node.id for node in lockfile.nodes if node.type == "skill"})
            removed_skills = (
                context.prune_orphaned_project_skills(
                    target_dir,
                    runtime_id,
                    {node.id for node in lockfile.nodes if node.type == "skill"},
                    prune_scope_skill_ids,
                )
                if install_scope == "project"
                else []
            )
            upgraded_lock_skill_nodes = context.pm.topological_skill_nodes_from_lock(lockfile)
        elif repo_root is not None and target_dir is not None:
            skill_records = context.select_records(context.load_skill_inventory(repo_root), [], install_all=True)
            context.sync_records(skill_records, target_dir, runtime_id=runtime_id)
            upgraded_repo_skill_records = skill_records
        cli_outputs = context.install_cli_packages(cli_records, config, upgrade=True, dry_run=False)
        for line in context.project_sync_presentation.bulk_upgrade_applied_lines(
            lock_skill_nodes=upgraded_lock_skill_nodes,
            repo_skill_records=upgraded_repo_skill_records,
            removed_skills=removed_skills,
            cli_items=list(zip(cli_records, cli_outputs)),
            skipped_self_records=skipped_self_records,
            recovery_command=context.self_upgrade_recovery_command(config),
            lock_path=lock_path if lockfile and lock_path is not None else None,
        ):
            print(line)
        return 0

    proxy_args = argparse.Namespace(
        command="update",
        skill_ids=args.asset_ids,
        all=args.all,
        target_dir=args.target_dir,
        runtime=args.runtime,
        scope=args.scope,
        with_recommended=False,
        feature=[],
        offline=False,
        refresh_lock=False,
        install_external=resolve_install_external(args, config),
        repo_root=args.repo_root,
        sync_repo=args.sync_repo,
        dry_run=args.dry_run,
    )
    return context.command_sync(proxy_args, config_path)
