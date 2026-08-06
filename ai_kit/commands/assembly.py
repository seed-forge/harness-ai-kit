from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from types import ModuleType

from ..application.project_manifest import ProjectManifestPorts, ProjectManifestService
from .bootstrap import BootstrapCommandContext, build_bootstrap_handlers
from .health import HealthCommandContext, build_health_handlers
from .inspect import InspectCommandContext, build_inspect_handlers
from .install import InstallCommandContext, build_install_handlers
from .project import ProjectCommandContext
from .resolution import ResolutionCommandContext, build_resolution_handlers
from .upgrade import UpgradeCommandContext, build_upgrade_handlers


def build_project_command_context(core: ModuleType, pm: ModuleType, load_effective_config: Callable[[Path], object]) -> ProjectCommandContext:
    project_service = ProjectManifestService(
        ProjectManifestPorts(
            project_manifest_path=core.project_manifest_path,
            parse_project_root_ref=core.parse_project_root_ref,
            create_manifest=core.ProjectManifest,
            create_manifest_assets=core.ProjectManifestAssets,
            save_project_manifest=core.save_project_manifest,
            load_contextual_project_manifest=core.load_contextual_project_manifest,
            load_project_manifest_if_present=core.load_project_manifest_if_present,
            ensure_project_manifest=core.ensure_project_manifest,
            find_project_lockfile=core.find_project_lockfile,
            infer_project_root_from_target_dir=core.infer_project_root_from_target_dir,
            read_lockfile=pm.read_lockfile,
            project_manifest_from_lockfile=core.project_manifest_from_lockfile,
            project_manifest_payload_text=lambda manifest: core.yaml.safe_dump(
                core.project_manifest_payload(manifest),
                sort_keys=False,
                allow_unicode=True,
            ),
            backup_file_once=core.backup_file_once,
            load_effective_config=load_effective_config,
            resolve_repo_root_if_available=core.resolve_repo_root_if_available,
            load_combined_cli_inventory=core.load_combined_cli_inventory,
            load_managed_asset_inventory=core.load_managed_asset_inventory,
            is_git_source_selector=pm.is_git_source_selector,
            discover_git_skills=pm.discover_git_skills,
            version_to_pinned=core.version_to_pinned,
            version_to_compatible_range=core.version_to_compatible_range,
            create_project_root_spec=core.ProjectRootSpec,
            create_versioned_asset_spec=core.ProjectVersionedAssetSpec,
            add_skill_to_manifest=core.add_skill_to_manifest,
            add_versioned_asset_to_manifest=core.add_versioned_asset_to_manifest,
            manifest_bucket_for_asset=core.manifest_bucket_for_asset,
            remove_asset_from_manifest=core.remove_asset_from_manifest,
            run_project_sync=core.run_project_sync,
            input_is_interactive=core.input_is_interactive,
            choose_git_skill=core.choose_git_skill_interactively,
        )
    )
    return ProjectCommandContext(service=project_service, current_working_directory=Path.cwd)


def build_bootstrap_handler_map(core: ModuleType) -> Mapping[str, Callable]:
    return build_bootstrap_handlers(
        BootstrapCommandContext(
            load_config=core.load_config,
            effective_config=core.effective_config,
            save_config=core.save_config,
            create_config=core.CliConfig,
            default_checkout_dir=core.default_checkout_dir,
            ensure_checkout=core.ensure_checkout,
            resolve_repo_root=core.resolve_repo_root,
            sync_repo=core.sync_repo,
            defaults={
                "repo_url": core.DEFAULT_TEAM_REPO_URL,
                "registry_upload_url": core.DEFAULT_REGISTRY_UPLOAD_URL,
                "registry_index_url": core.DEFAULT_REGISTRY_INDEX_URL,
                "skill_registry_upload_url": core.DEFAULT_SKILL_REGISTRY_UPLOAD_URL,
                "skill_registry_index_url": core.DEFAULT_SKILL_REGISTRY_INDEX_URL,
                "public_skill_registry_upload_url": "",
                "public_skill_registry_index_url": "",
                "cli_registry_upload_url": core.DEFAULT_CLI_REGISTRY_UPLOAD_URL,
                "cli_registry_index_url": core.DEFAULT_CLI_REGISTRY_INDEX_URL,
                "trusted_host": core.DEFAULT_TRUSTED_HOST,
                "tag_prefix": core.DEFAULT_TAG_PREFIX,
            },
        )
    )


def build_resolution_handler_map(core: ModuleType, load_effective_config: Callable[[Path], object]) -> Mapping[str, Callable]:
    return build_resolution_handlers(
        ResolutionCommandContext(
            load_effective_config=load_effective_config,
            resolve_repo_root=core.resolve_repo_root,
            load_contextual_project_manifest=core.load_contextual_project_manifest,
            resolve_asset_plan=core.resolve_asset_plan,
            current_cli_versions=core.current_cli_versions,
            manifest_aware_runtime=core.manifest_aware_runtime,
            manifest_aware_scope=core.manifest_aware_scope,
            project_lockfile_from_manifest=core.project_lockfile_from_manifest,
        )
    )


def build_inspect_handler_map(core: ModuleType, load_effective_config: Callable[[Path], object]) -> Mapping[str, Callable]:
    return build_inspect_handlers(
        InspectCommandContext(
            load_effective_config=load_effective_config,
            resolve_repo_root_if_available=core.resolve_repo_root_if_available,
            maybe_sync_repo=core.maybe_sync_repo,
            load_combined_skill_inventory=core.load_combined_skill_inventory,
            load_combined_cli_inventory=core.load_combined_cli_inventory,
            load_managed_asset_inventory=core.load_managed_asset_inventory,
            load_skill_inventory_for_source=core.load_skill_inventory_for_source,
            load_managed_asset_inventory_for_source=core.load_managed_asset_inventory_for_source,
            select_records=core.select_records,
            skill_install_state=core.skill_install_state,
            cli_install_state=core.cli_install_state,
            managed_asset_install_state=core.managed_asset_install_state,
            load_skill_metadata_for_record=core.load_skill_metadata_for_record,
            skill_dependency_payload=core.skill_dependency_payload,
            list_has_upgrade_available=core.list_has_upgrade_available,
            format_skill_table=core.format_skill_table,
            format_cli_table=core.format_cli_table,
            format_managed_asset_table=core.format_managed_asset_table,
            load_skill_document_for_record=core.load_skill_document_for_record,
        )
    )


def build_install_handler_map(core: ModuleType, pm: ModuleType) -> Mapping[str, Callable]:
    return build_install_handlers(
        InstallCommandContext(
            load_config=core.load_config,
            effective_config=core.effective_config,
            load_contextual_project_manifest=core.load_contextual_project_manifest,
            load_project_manifest_if_present=core.load_project_manifest_if_present,
            manifest_target_dir=core.manifest_target_dir,
            project_lock_path_for_manifest=core.project_lock_path_for_manifest,
            resolve_repo_root_if_available=core.resolve_repo_root_if_available,
            project_lockfile_from_manifest=core.project_lockfile_from_manifest,
            write_lockfile=pm.write_lockfile,
            read_lockfile=pm.read_lockfile,
            project_sync=core.project_sync,
            run_project_sync=core.run_project_sync,
            prune_orphaned_project_skills=core.prune_orphaned_project_skills,
            prune_orphaned_project_managed_assets=core.prune_orphaned_project_managed_assets,
            managed_project_skill_ids=core.managed_project_skill_ids,
            managed_project_asset_ids=core.managed_project_asset_ids,
            project_sync_presentation=core.project_sync_presentation,
            resolve_target_dir=core.resolve_target_dir,
            load_combined_cli_inventory=core.load_combined_cli_inventory,
            load_cli_metadata_for_record=core.load_cli_metadata_for_record,
            binary_release_platform_spec=core.binary_release_platform_spec,
            binary_release_install_path=core.binary_release_install_path,
            remove_installed_skill=core.remove_installed_skill,
            remove_installed_managed_asset=core.remove_installed_managed_asset,
            runtime_managed_asset_root=core.runtime_managed_asset_root,
            pm=pm,
            runtime_install_destination=core.runtime_install_destination,
            managed_asset_install_destination=core.managed_asset_install_destination,
            print_non_skill_requirements=core.print_non_skill_requirements,
            manual_invocation_hint=core.manual_invocation_hint,
            validate_sync_selection=core.validate_sync_selection,
            parse_asset_selector=core.parse_asset_selector,
            maybe_sync_repo=core.maybe_sync_repo,
            load_cli_inventory=core.load_cli_inventory,
            select_cli_records=core.select_cli_records,
            is_self_cli_package=core.is_self_cli_package,
            self_upgrade_recovery_command=core.self_upgrade_recovery_command,
            install_cli_packages=core.install_cli_packages,
            load_skill_inventory=core.load_skill_inventory,
            manifest_aware_runtime=core.manifest_aware_runtime,
            manifest_aware_scope=core.manifest_aware_scope,
            project_root_ids=core.project_root_ids,
            explicit_feature_selection=core.explicit_feature_selection,
            manifest_skill_source_policy=core.manifest_skill_source_policy,
            manifest_skill_root_sources=core.manifest_skill_root_sources,
            manifest_skill_version_specifiers=core.manifest_skill_version_specifiers,
            is_git_source_selector=pm.is_git_source_selector,
            discover_git_skills=pm.discover_git_skills,
            stdin_isatty=core.sys.stdin.isatty,
            prompt_input=input,
            declared_cli_specs=core.declared_cli_specs,
            add_skill_to_manifest=core.add_skill_to_manifest,
            save_project_manifest=core.save_project_manifest,
            ProjectRootSpec=core.ProjectRootSpec,
            merge_manifest_cli_into_refresh_lockfile=core.merge_manifest_cli_into_refresh_lockfile,
            resolve_skill_plan=core.resolve_skill_plan,
            install_environment_requirements=core.install_environment_requirements,
            environment_records_for_lockfile=core.environment_records_for_lockfile,
            apply_skill_lockfile=core.apply_skill_lockfile,
            apply_managed_asset_lockfile=core.apply_managed_asset_lockfile,
            missing_environment_requirements=core.missing_environment_requirements,
            bootstrap_project_manifest_from_lockfile=core.bootstrap_project_manifest_from_lockfile,
            project_manifest_path=core.project_manifest_path,
            select_records=core.select_records,
            sync_records=core.sync_records,
            write_lockfile_model=pm.write_lockfile_model,
            compute_extends_summary=core.compute_extends_summary,
        )
    )


def build_upgrade_handler_map(core: ModuleType, pm: ModuleType, install_handlers: Mapping[str, Callable]) -> Mapping[str, Callable]:
    return build_upgrade_handlers(
        UpgradeCommandContext(
            load_config=core.load_config,
            effective_config=core.effective_config,
            load_project_manifest_if_present=core.load_project_manifest_if_present,
            resolve_repo_root_if_available=core.resolve_repo_root_if_available,
            project_lockfile_from_manifest=core.project_lockfile_from_manifest,
            load_skill_inventory=core.load_skill_inventory,
            load_combined_cli_inventory=core.load_combined_cli_inventory,
            declared_skill_specs=core.declared_skill_specs,
            declared_cli_specs=core.declared_cli_specs,
            declared_plugin_specs=core.declared_plugin_specs,
            declared_hook_specs=core.declared_hook_specs,
            declared_subagent_specs=core.declared_subagent_specs,
            declared_mcp_specs=core.declared_mcp_specs,
            load_managed_asset_inventory=core.load_managed_asset_inventory,
            pm=pm,
            spec_matches_version=core.spec_matches_version,
            format_table=core.format_table,
            manifest_target_dir=core.manifest_target_dir,
            installed_skill_ids=core.installed_skill_ids,
            managed_project_skill_ids=core.managed_project_skill_ids,
            project_lock_path_for_manifest=core.project_lock_path_for_manifest,
            installed_managed_asset_ids=core.installed_managed_asset_ids,
            managed_project_asset_ids=core.managed_project_asset_ids,
            load_contextual_project_manifest=core.load_contextual_project_manifest,
            parse_asset_selector=core.parse_asset_selector,
            maybe_sync_repo=core.maybe_sync_repo,
            load_cli_inventory=core.load_cli_inventory,
            installed_cli_records=core.installed_cli_records,
            select_cli_records=core.select_cli_records,
            is_self_cli_package=core.is_self_cli_package,
            manifest_aware_runtime=core.manifest_aware_runtime,
            manifest_aware_scope=core.manifest_aware_scope,
            explicit_feature_selection=core.explicit_feature_selection,
            resolve_target_dir=core.resolve_target_dir,
            read_lockfile=pm.read_lockfile,
            runtime_install_destination=core.runtime_install_destination,
            select_records=core.select_records,
            project_sync_presentation=core.project_sync_presentation,
            self_upgrade_recovery_command=core.self_upgrade_recovery_command,
            install_cli_packages=core.install_cli_packages,
            project_root_ids=core.project_root_ids,
            resolve_skill_plan=core.resolve_skill_plan,
            write_lockfile=pm.write_lockfile,
            apply_skill_lockfile=core.apply_skill_lockfile,
            prune_orphaned_project_skills=core.prune_orphaned_project_skills,
            sync_records=core.sync_records,
            command_sync=install_handlers["update"],
        )
    )


def build_health_handler_map(core: ModuleType) -> Mapping[str, Callable]:
    return build_health_handlers(
        HealthCommandContext(
            runtime_profiles=core.RUNTIME_PROFILES,
            format_table=core.format_table,
            report_presentation=core.report_presentation,
            load_config=core.load_config,
            effective_config=core.effective_config,
            resolve_repo_root=core.resolve_repo_root,
            installed_skill_locations=core.installed_skill_locations,
            installed_skill_ids=core.installed_skill_ids,
            manual_invocation_hint=core.manual_invocation_hint,
            skill_install_state=core.skill_install_state,
            skill_record_factory=core.SkillRecord,
            doctor_versions_results=core.doctor_versions_results,
            doctor_drift_results=core.doctor_drift_results,
            doctor_sources_payload=core.doctor_sources_payload,
            doctor_env_results=core.doctor_env_results,
            doctor_assets_results=core.doctor_assets_results,
            load_managed_asset_inventory=core.load_managed_asset_inventory,
            managed_asset_install_state=core.managed_asset_install_state,
            managed_asset_types=core.MANAGED_ASSET_TYPES,
            current_cli_versions=core.current_cli_versions,
            pm=core.pm,
            git_available=core.git_available,
            python_module_available=core.python_module_available,
            run_repo_validation=core.run_repo_validation,
            doctor_extends_results=core.doctor_extends_results,
        )
    )

