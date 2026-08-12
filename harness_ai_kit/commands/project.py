from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from ..application.project_manifest import (
    InitProjectRequest,
    ManifestMigrateRequest,
    ProjectAddRequest,
    ProjectManifestService,
    ProjectRemoveRequest,
)
from ..domain import project_sync_presentation


@dataclass(frozen=True)
class ProjectCommandContext:
    service: ProjectManifestService
    current_working_directory: Callable[[], Path]


def build_project_config_handlers(context: ProjectCommandContext) -> Mapping[str, Callable[[argparse.Namespace, Path], int]]:
    return {
        "add": lambda args, config_path: command_add(args, config_path, context),
        "remove": lambda args, config_path: command_remove(args, config_path, context),
    }


def build_project_plain_handlers(context: ProjectCommandContext) -> Mapping[str, Callable[[argparse.Namespace], int]]:
    return {
        "init-project": lambda args: command_init_project(args, context),
        "manifest": lambda args: command_manifest(args, context),
    }


def command_manifest(args: argparse.Namespace, context: ProjectCommandContext) -> int:
    if args.manifest_command == "migrate":
        return command_manifest_migrate(args, context)
    raise ValueError(f"Unsupported manifest command: {args.manifest_command}")


def command_init_project(args: argparse.Namespace, context: ProjectCommandContext) -> int:
    result = context.service.init_project(
        InitProjectRequest(
            cwd=context.current_working_directory(),
            runtime=args.runtime,
            scope=args.scope,
            root_refs=list(getattr(args, "root", [])),
            features=list(getattr(args, "feature", [])),
            force=args.force,
        )
    )
    for line in project_sync_presentation.init_project_success_lines(manifest_path=result.manifest_path):
        print(line)
    return 0


def command_manifest_migrate(args: argparse.Namespace, context: ProjectCommandContext) -> int:
    result = context.service.migrate_manifest(
        ManifestMigrateRequest(
            target_dir=getattr(args, "target_dir", None),
            dry_run=args.dry_run,
        )
    )
    if result.payload_text is not None:
        print(result.payload_text, end="")
        return 0
    if result.lock_path is not None:
        for line in project_sync_presentation.manifest_bootstrapped_from_lock_lines(
            manifest_path=result.manifest_path,
            lock_path=result.lock_path,
        ):
            print(line)
        return 0
    if result.backup_path is None:
        raise RuntimeError("Manifest migration completed without a backup or lock source.")
    for line in project_sync_presentation.manifest_migrate_success_lines(
        manifest_path=result.manifest_path,
        backup_path=result.backup_path,
    ):
        print(line)
    return 0


def command_add(args: argparse.Namespace, config_path: Path, context: ProjectCommandContext) -> int:
    result = context.service.add_asset(
        ProjectAddRequest(
            config_path=config_path,
            target_dir=getattr(args, "target_dir", None),
            runtime=getattr(args, "runtime", None),
            scope=getattr(args, "scope", None),
            repo_root=getattr(args, "repo_root", None),
            asset_kind=args.asset_kind,
            asset_id=args.asset_id,
            version=getattr(args, "version", None),
            source_ref=getattr(args, "source_ref", None),
            ref=getattr(args, "ref", None),
            subpath=getattr(args, "subpath", None),
            override_id=getattr(args, "override_id", None),
            no_install=getattr(args, "no_install", False),
            sync_repo=getattr(args, "sync_repo", False),
            offline=getattr(args, "offline", False),
            no_input=getattr(args, "no_input", False),
            extends=getattr(args, "extends", None),
            extends_version=getattr(args, "extends_version", None),
            extends_strategy=getattr(args, "extends_strategy", None),
        )
    )
    if not result.changed:
        print(
            project_sync_presentation.project_add_no_change_line(
                asset_kind=result.asset_kind,
                asset_id=result.asset_id,
                manifest_path=result.manifest_path,
            )
        )
        return 0
    for line in project_sync_presentation.project_add_success_lines(
        asset_kind=result.asset_kind,
        asset_id=result.asset_id,
        manifest_path=result.manifest_path,
        no_install=result.no_install,
    ):
        print(line)
    if result.lock_path is not None:
        print(project_sync_presentation.project_lockfile_synced_line(result.lock_path))
    return 0


def command_remove(args: argparse.Namespace, config_path: Path, context: ProjectCommandContext) -> int:
    result = context.service.remove_asset(
        ProjectRemoveRequest(
            config_path=config_path,
            target_dir=getattr(args, "target_dir", None),
            runtime=getattr(args, "runtime", None),
            scope=getattr(args, "scope", None),
            repo_root=getattr(args, "repo_root", None),
            asset_kind=args.asset_kind,
            asset_id=args.asset_id,
            no_install=getattr(args, "no_install", False),
            sync_repo=getattr(args, "sync_repo", False),
            offline=getattr(args, "offline", False),
        )
    )
    for line in project_sync_presentation.project_remove_success_lines(
        asset_kind=result.asset_kind,
        asset_id=result.asset_id,
        manifest_path=result.manifest_path,
        no_install=result.no_install,
    ):
        print(line)
    if result.lock_path is not None:
        for line in project_sync_presentation.project_remove_followup_lines(
            asset_kind=result.asset_kind,
            asset_id=result.asset_id,
            removed_skills=result.removed_skills,
            removed_assets=result.removed_assets,
        ):
            print(line)
        print(project_sync_presentation.project_lockfile_synced_line(result.lock_path))
    return 0
