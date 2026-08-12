#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.metadata
import io
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import zipfile
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from pydantic import ValidationError
import yaml

if __package__:
    from . import package_manager as pm
    from .product import PRODUCT_ENV_VAR, ProductProfile, active_product_profile
    from .application.project_manifest import ProjectManifestPorts, ProjectManifestService
    from .commands.bootstrap import BootstrapCommandContext, build_bootstrap_handlers
    from .commands.cache import command_cache
    from .commands.dispatch import CommandRouter
    from .commands.errors import HANDLED_COMMAND_EXCEPTIONS, command_error_message
    from .commands.inspect import InspectCommandContext, build_inspect_handlers
    from .commands.project import ProjectCommandContext, build_project_config_handlers, build_project_plain_handlers
    from .commands.resolution import ResolutionCommandContext, build_resolution_handlers
    from .commands.routes import register_command_routes
    from .domain import cli_assets
    from .domain import managed_assets
    from .domain import managed_install
    from .domain import materialization
    from .domain import project_state
    from .domain import project_manifest_state
    from .domain import project_locking
    from .domain import project_sync
    from .domain import project_sync_presentation
    from .domain import project_sync_results
    from .domain import report_presentation
    from .domain import doctor_registry_lock
    from .domain import runtime_install
    from .domain import skill_install
    from .domain.models import (
        ALL_ASSET_TYPES,
        ASSET_DIRECTORY_NAMES,
        CONFIG_FILENAME,
        DEFAULT_CLI_REGISTRY_INDEX_URL,
        DEFAULT_CLI_REGISTRY_UPLOAD_URL,
        DEFAULT_REGISTRY_INDEX_URL,
        DEFAULT_REGISTRY_UPLOAD_URL,
        DEFAULT_SKILL_REGISTRY_INDEX_URL,
        DEFAULT_SKILL_REGISTRY_UPLOAD_URL,
        DEFAULT_TAG_PREFIX,
        DEFAULT_TRUSTED_HOST,
        LEGACY_PROJECT_MANIFEST_SCHEMA_VERSION,
        MANAGED_ASSET_TYPES,
        PROJECT_MANIFEST_SCHEMA_VERSION,
        REFERENCE_DOC_RE,
        REQUIRED_CLI_FIELDS,
        REQUIRED_SKILL_FIELDS,
        USAGE_PROMPT_CJK_RE,
        USAGE_PROMPT_SECTION_RE,
        VERSIONED_ASSET_TYPES,
        CliAssetRecord,
        CliConfig,
        CliInstallState,
        InstalledManagedAssetLocation,
        InstalledSkillLocation,
        ManagedAssetInstallState,
        ProjectManifest,
        ProjectManifestAssets,
        ProjectRootSpec,
        ProjectVersionedAssetSpec,
        SkillInstallState,
        SkillRecord,
    )
    from .infrastructure.config_io import (
        console_safe_text,
        default_checkout_dir,
        default_config_path,
        default_home_dir,
        default_repo_root,
        discover_repo_root,
        effective_config,
        load_config,
        pyproject_path,
        read_project_name,
        read_project_version,
        repo_looks_valid,
        resolve_config_path,
        resolve_repo_root,
        resolve_repo_root_if_available,
        save_config,
    )
    from .infrastructure.http_client import (
        http_request,
        registry_auth_headers,
        skill_registry_headers,
        skill_registry_write_ready,
        slash_join,
        upload_file,
    )
    from .infrastructure.cli_installer import (
        binary_release_checksum,
        binary_release_checksum_urls,
        binary_release_download,
        binary_release_install_path,
        binary_release_platform_spec,
        binary_release_urls,
        install_binary_release_cli,
        install_cli_packages,
        installed_cli_records,
        is_python_package_installed,
        is_self_cli_package,
        pip_install_command,
        self_upgrade_recovery_command,
    )
    from .domain.scaffold import scaffold_cli, scaffold_managed_asset, scaffold_skill
    from .domain.doctor_checks import (
        current_platform_tags,
        doctor_assets_results,
        doctor_drift_results,
        doctor_env_results,
        doctor_extends_results,
        doctor_sources_payload,
        doctor_versions_results,
        environment_records_for_lockfile,
        environment_requirements_for_records,
        executable_matches_platform,
        find_lock_node_by_root,
        install_environment_requirements,
        managed_asset_records,
        missing_environment_requirements,
        python_import_name,
        registry_items_by_key,
        source_selection_reason,
        version_for_skill_record,
    )
    from .commands.validate import run_repo_validation
    from .domain.inventory import (
        cli_record_from_payload,
        iter_cli_dirs,
        iter_managed_asset_dirs,
        iter_skill_dirs,
        load_cli_inventory,
        load_cli_metadata,
        load_cli_metadata_for_record,
        load_cli_record,
        load_cli_registry_inventory,
        load_combined_cli_inventory,
        load_combined_skill_inventory,
        load_managed_asset_inventory,
        load_managed_asset_inventory_for_source,
        load_managed_asset_record_by_id,
        load_skill_document_for_record,
        load_skill_inventory,
        load_skill_inventory_for_source,
        load_skill_metadata,
        load_skill_metadata_for_record,
        load_skill_record,
        load_skill_record_by_id,
        load_skill_registry_inventory,
        managed_asset_document_paths,
        reference_doc_paths,
        select_cli_records,
        select_records,
        select_target_cli_record,
        skill_entry_text,
        skill_record_from_payload,
        validate_usage_doc,
    )
    from .infrastructure.registry_skill import (
        build_skill_archive,
        download_skill_archive,
        download_skill_metadata,
        install_skill_archive_bytes,
        load_skill_registry_index,
        registry_skill_metadata_url,
        save_skill_registry_index,
        skill_archive_name,
        skill_archive_url,
        skill_metadata_url,
        update_skill_registry_index_payload,
    )
    from .infrastructure.registry_cli import (
        cli_metadata_url,
        cli_registry_metadata_url,
        load_cli_registry_index,
        merge_manifest_cli_into_refresh_lockfile,
        resolve_cli_record_from_registry,
        save_cli_registry_index,
        update_cli_registry_index_payload,
    )
    from .domain.install_state import (
        _extract_extends_attribution,
        cli_install_state,
        companion_doc_requirements,
        current_materialized_checksum_for_node,
        current_source_checksum_for_node,
        effective_materialized_checksum,
        effective_source_checksum,
        evaluate_installed_asset_drift,
        hash_directory_with_root,
        install_managed_asset_directory,
        install_skill_directory,
        installed_cli_version,
        installed_managed_asset_ids,
        installed_managed_asset_materialized_checksum,
        installed_managed_asset_version,
        installed_skill_ids,
        installed_skill_locations,
        installed_skill_materialized_checksum,
        installed_skill_payload_dir,
        installed_skill_version,
        list_has_upgrade_available,
        managed_asset_install_destination,
        managed_asset_install_state,
        manual_invocation_hint,
        payload_has_required_docs,
        read_lockfile_if_present,
        render_cursor_rule,
        render_kiro_steering,
        runtime_install_destination,
        runtime_managed_asset_root,
        skill_install_state,
        source_materialized_checksum,
        sync_records,
        worst_drift_status,
    )
    from .infrastructure.git_ops_extra import (
        clone_repo,
        command_available,
        ensure_checkout,
        git_available,
        maybe_sync_repo,
        normalize_module_name,
        parse_asset_selector,
        python_module_available,
        run_git,
        sync_repo,
    )
    from .domain.manifest_ops import (
        bootstrap_project_manifest_from_lockfile,
        declared_cli_specs,
        declared_hook_specs,
        declared_loop_specs,
        declared_mcp_specs,
        declared_plugin_specs,
        declared_skill_specs,
        declared_subagent_specs,
        detect_current_runtime,
        explicit_feature_selection,
        find_project_lockfile,
        find_project_manifest,
        infer_project_root_from_target_dir,
        load_contextual_project_manifest,
        load_project_manifest,
        load_project_manifest_if_present,
        manifest_aware_runtime,
        manifest_aware_scope,
        manifest_declared_features,
        manifest_has_declared_assets,
        manifest_skill_root_sources,
        manifest_skill_source_policy,
        manifest_skill_version_specifiers,
        project_lock_path_for_manifest,
        project_manifest_from_lockfile,
        project_manifest_path,
        project_manifest_root_requests,
        project_root_ids,
        validate_sync_selection,
    )
    from .domain.lifecycle import (
        apply_cli_lifecycle_status,
        apply_managed_asset_lifecycle_status,
        apply_skill_lifecycle_status,
        governance_summary,
        merge_governance_summary,
    )
    from .infrastructure.release_ops import (
        append_note_to_top_changelog,
        build_artifacts,
        clean_release_artifacts,
        commit_and_optionally_push,
        create_git_tag,
        dist_files,
        ensure_catalog_entry,
        has_staged_changes,
        prepend_document_banner,
        publish_selection,
        release_subprocess_env,
        release_workspace_dir,
        render_catalog_row,
        stage_publish_paths,
        twine_check_artifacts,
        twine_environment_ready,
        twine_subprocess_env,
        twine_upload_command,
        upload_artifacts,
        validate_publish_selection,
    )
    from .application.project_sync import (
        add_skill_to_manifest,
        add_versioned_asset_to_manifest,
        apply_managed_asset_lockfile,
        apply_skill_lockfile,
        cli_nodes_from_lock,
        compute_extends_summary,
        ensure_project_manifest,
        fanout_canonical_to_runtime,
        managed_project_asset_ids,
        managed_project_skill_ids,
        manifest_bucket_for_asset,
        manifest_target_dir,
        print_local_skill_refresh_summary,
        print_non_skill_requirements,
        print_project_sync_applied_summary,
        print_project_sync_dry_run_summary,
        project_lockfile_from_manifest,
        project_sync_managed_preview_items,
        project_sync_skill_preview_items,
        prune_orphaned_project_managed_assets,
        prune_orphaned_project_skills,
        refresh_existing_local_skill_installs,
        remove_asset_from_manifest,
        remove_installed_managed_asset,
        remove_installed_skill,
        resolve_asset_plan,
        resolve_asset_root,
        resolve_cli_publish_root,
        resolve_lock_path,
        resolve_skill_plan,
        run_project_sync,
        select_cli_record_for_spec,
        select_cli_records_for_lock,
        select_managed_asset_record_for_spec,
        standalone_install_managed_preview_items,
        standalone_install_should_initialize_manifest,
        standalone_install_skill_preview_items,
        warn_same_version_drift,
    )
    from .domain.validation import (
        skill_has_reference_section,
        validate_reference_docs,
        validate_companion_docs,
        validate_cli_companion_docs,
    )
    from .domain.manifest_ops import (
        parse_project_root_ref,
        skill_manifest_item_payload,
        versioned_manifest_item_payload,
        project_manifest_payload,
        save_project_manifest,
    )
    from .infrastructure.cli_installer import (
        normalize_cli_platform_os,
        normalize_cli_platform_arch,
        current_cli_platform,
        catalog_versions,
    )
    from .infrastructure.config_io import (
        read_top_changelog_version,
        read_json_file,
        write_project_version,
    )
    from .domain.report_presentation import (
        format_table,
        format_skill_table,
        format_managed_asset_table,
        format_cli_table,
    )
    from .commands.install_git_select import choose_git_skill_interactively
    from .domain.runtime_install import resolve_target_dir
    from .domain.dependency_expansion import (
        ordered_unique,
        skill_dependency_payload,
        expand_skill_ids_with_dependencies,
        dependency_followups,
        current_cli_versions,
        sync_cli_metadata_versions,
    )
    from .domain.versions import (
        bump_version_string,
        compare_versions,
        compare_versions_safe,
        highest_version,
        parse_version_from_text,
        sort_versions,
        spec_matches_version,
        upgrade_status_for_versions,
        version_to_compatible_range,
        version_to_pinned,
    )
    from .usage_docs import render_usage_doc
else:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from harness_ai_kit import package_manager as pm
    from harness_ai_kit.product import PRODUCT_ENV_VAR, ProductProfile, active_product_profile
    from harness_ai_kit.application.project_manifest import ProjectManifestPorts, ProjectManifestService
    from harness_ai_kit.commands.bootstrap import BootstrapCommandContext, build_bootstrap_handlers
    from harness_ai_kit.commands.cache import command_cache
    from harness_ai_kit.commands.dispatch import CommandRouter
    from harness_ai_kit.commands.errors import HANDLED_COMMAND_EXCEPTIONS, command_error_message
    from harness_ai_kit.commands.inspect import InspectCommandContext, build_inspect_handlers
    from harness_ai_kit.commands.project import ProjectCommandContext, build_project_config_handlers, build_project_plain_handlers
    from harness_ai_kit.commands.resolution import ResolutionCommandContext, build_resolution_handlers
    from harness_ai_kit.commands.routes import register_command_routes
    from harness_ai_kit.domain import cli_assets
    from harness_ai_kit.domain import managed_assets
    from harness_ai_kit.domain import managed_install
    from harness_ai_kit.domain import materialization
    from harness_ai_kit.domain import project_state
    from harness_ai_kit.domain import project_manifest_state
    from harness_ai_kit.domain import project_locking
    from harness_ai_kit.domain import project_sync
    from harness_ai_kit.domain import project_sync_presentation
    from harness_ai_kit.domain import project_sync_results
    from harness_ai_kit.domain import report_presentation
    from harness_ai_kit.domain import doctor_registry_lock
    from harness_ai_kit.domain import runtime_install
    from harness_ai_kit.domain import skill_install
    from harness_ai_kit.domain.models import (
        ALL_ASSET_TYPES,
        ASSET_DIRECTORY_NAMES,
        CONFIG_FILENAME,
        DEFAULT_CLI_REGISTRY_INDEX_URL,
        DEFAULT_CLI_REGISTRY_UPLOAD_URL,
        DEFAULT_REGISTRY_INDEX_URL,
        DEFAULT_REGISTRY_UPLOAD_URL,
        DEFAULT_SKILL_REGISTRY_INDEX_URL,
        DEFAULT_SKILL_REGISTRY_UPLOAD_URL,
        DEFAULT_TAG_PREFIX,
        DEFAULT_TRUSTED_HOST,
        LEGACY_PROJECT_MANIFEST_SCHEMA_VERSION,
        MANAGED_ASSET_TYPES,
        PROJECT_MANIFEST_SCHEMA_VERSION,
        REFERENCE_DOC_RE,
        REQUIRED_CLI_FIELDS,
        REQUIRED_SKILL_FIELDS,
        USAGE_PROMPT_CJK_RE,
        USAGE_PROMPT_SECTION_RE,
        VERSIONED_ASSET_TYPES,
        CliAssetRecord,
        CliConfig,
        CliInstallState,
        InstalledManagedAssetLocation,
        InstalledSkillLocation,
        ManagedAssetInstallState,
        ProjectManifest,
        ProjectManifestAssets,
        ProjectRootSpec,
        ProjectVersionedAssetSpec,
        SkillInstallState,
        SkillRecord,
    )
    from harness_ai_kit.infrastructure.config_io import (
        console_safe_text,
        default_checkout_dir,
        default_config_path,
        default_home_dir,
        default_repo_root,
        discover_repo_root,
        effective_config,
        load_config,
        pyproject_path,
        read_project_name,
        read_project_version,
        repo_looks_valid,
        resolve_config_path,
        resolve_repo_root,
        resolve_repo_root_if_available,
        save_config,
    )
    from harness_ai_kit.infrastructure.http_client import (
        http_request,
        registry_auth_headers,
        skill_registry_headers,
        skill_registry_write_ready,
        slash_join,
        upload_file,
    )
    from harness_ai_kit.infrastructure.cli_installer import (
        binary_release_checksum,
        binary_release_checksum_urls,
        binary_release_download,
        binary_release_install_path,
        binary_release_platform_spec,
        binary_release_urls,
        install_binary_release_cli,
        install_cli_packages,
        installed_cli_records,
        is_python_package_installed,
        is_self_cli_package,
        pip_install_command,
        self_upgrade_recovery_command,
    )
    from harness_ai_kit.domain.scaffold import scaffold_cli, scaffold_managed_asset, scaffold_skill
    from harness_ai_kit.domain.doctor_checks import (
        current_platform_tags,
        doctor_assets_results,
        doctor_drift_results,
        doctor_env_results,
        doctor_extends_results,
        doctor_sources_payload,
        doctor_versions_results,
        environment_records_for_lockfile,
        environment_requirements_for_records,
        executable_matches_platform,
        find_lock_node_by_root,
        install_environment_requirements,
        managed_asset_records,
        missing_environment_requirements,
        python_import_name,
        registry_items_by_key,
        source_selection_reason,
        version_for_skill_record,
    )
    from harness_ai_kit.commands.validate import run_repo_validation
    from harness_ai_kit.domain.inventory import (
        cli_record_from_payload, iter_cli_dirs, iter_managed_asset_dirs, iter_skill_dirs,
        load_cli_inventory, load_cli_metadata, load_cli_metadata_for_record, load_cli_record,
        load_cli_registry_inventory, load_combined_cli_inventory, load_combined_skill_inventory,
        load_managed_asset_inventory, load_managed_asset_inventory_for_source,
        load_managed_asset_record_by_id, load_skill_document_for_record,
        load_skill_inventory, load_skill_inventory_for_source, load_skill_metadata,
        load_skill_metadata_for_record, load_skill_record, load_skill_record_by_id,
        load_skill_registry_inventory, managed_asset_document_paths, reference_doc_paths,
        select_cli_records, select_records, select_target_cli_record,
        skill_entry_text, skill_record_from_payload,
        validate_usage_doc,
    )
    from harness_ai_kit.infrastructure.registry_skill import (
        build_skill_archive, download_skill_archive, download_skill_metadata,
        install_skill_archive_bytes, load_skill_registry_index, registry_skill_metadata_url,
        save_skill_registry_index, skill_archive_name, skill_archive_url, skill_metadata_url,
        update_skill_registry_index_payload,
    )
    from harness_ai_kit.infrastructure.registry_cli import (
        cli_metadata_url, cli_registry_metadata_url, load_cli_registry_index,
        merge_manifest_cli_into_refresh_lockfile, resolve_cli_record_from_registry,
        save_cli_registry_index, update_cli_registry_index_payload,
    )
    from harness_ai_kit.domain.install_state import (
        _extract_extends_attribution, cli_install_state, companion_doc_requirements,
        current_materialized_checksum_for_node, current_source_checksum_for_node,
        effective_materialized_checksum, effective_source_checksum,
        evaluate_installed_asset_drift, hash_directory_with_root,
        install_managed_asset_directory, install_skill_directory,
        installed_cli_version, installed_managed_asset_ids,
        installed_managed_asset_materialized_checksum, installed_managed_asset_version,
        installed_skill_ids, installed_skill_locations, installed_skill_materialized_checksum,
        installed_skill_payload_dir, installed_skill_version, list_has_upgrade_available,
        managed_asset_install_destination, managed_asset_install_state,
        manual_invocation_hint, payload_has_required_docs, read_lockfile_if_present, render_cursor_rule,
        render_kiro_steering, runtime_install_destination, runtime_managed_asset_root,
        skill_install_state, source_materialized_checksum, sync_records, worst_drift_status,
    )
    from harness_ai_kit.infrastructure.git_ops_extra import (
        clone_repo, command_available, ensure_checkout, git_available, maybe_sync_repo,
        normalize_module_name, parse_asset_selector, python_module_available, run_git, sync_repo,
    )
    from harness_ai_kit.domain.manifest_ops import (
        bootstrap_project_manifest_from_lockfile, declared_cli_specs, declared_hook_specs,
        declared_loop_specs, declared_mcp_specs, declared_plugin_specs, declared_skill_specs,
        declared_subagent_specs, detect_current_runtime, explicit_feature_selection,
        find_project_lockfile, find_project_manifest, infer_project_root_from_target_dir,
        load_contextual_project_manifest, load_project_manifest,
        load_project_manifest_if_present, manifest_aware_runtime, manifest_aware_scope,
        manifest_declared_features, manifest_has_declared_assets, manifest_skill_root_sources,
        manifest_skill_source_policy, manifest_skill_version_specifiers,
        project_lock_path_for_manifest, project_manifest_from_lockfile,
        project_manifest_path, project_manifest_root_requests, project_root_ids,
        validate_sync_selection,
    )
    from harness_ai_kit.domain.lifecycle import (
        apply_cli_lifecycle_status, apply_managed_asset_lifecycle_status,
        apply_skill_lifecycle_status, governance_summary, merge_governance_summary,
    )
    from harness_ai_kit.infrastructure.release_ops import (
        append_note_to_top_changelog, build_artifacts, clean_release_artifacts,
        commit_and_optionally_push, create_git_tag, dist_files, ensure_catalog_entry,
        has_staged_changes, prepend_document_banner, publish_selection,
        release_subprocess_env, release_workspace_dir, render_catalog_row,
        stage_publish_paths, twine_check_artifacts, twine_environment_ready,
        twine_subprocess_env, twine_upload_command, upload_artifacts, validate_publish_selection,
    )
    from harness_ai_kit.application.project_sync import (
        add_skill_to_manifest, add_versioned_asset_to_manifest, apply_managed_asset_lockfile,
        apply_skill_lockfile, cli_nodes_from_lock, compute_extends_summary,
        ensure_project_manifest, fanout_canonical_to_runtime, managed_project_asset_ids,
        managed_project_skill_ids, manifest_bucket_for_asset, manifest_target_dir,
        print_local_skill_refresh_summary, print_non_skill_requirements,
        print_project_sync_applied_summary, print_project_sync_dry_run_summary,
        project_lockfile_from_manifest, project_sync_managed_preview_items,
        project_sync_skill_preview_items, prune_orphaned_project_managed_assets,
        prune_orphaned_project_skills, refresh_existing_local_skill_installs,
        remove_asset_from_manifest, remove_installed_managed_asset, remove_installed_skill,
        resolve_asset_plan, resolve_asset_root, resolve_cli_publish_root, resolve_lock_path,
        resolve_skill_plan, run_project_sync, select_cli_record_for_spec,
        select_cli_records_for_lock, select_managed_asset_record_for_spec,
        standalone_install_managed_preview_items,
        standalone_install_should_initialize_manifest, standalone_install_skill_preview_items,
        warn_same_version_drift,
    )
    from harness_ai_kit.domain.validation import (
        skill_has_reference_section, validate_reference_docs,
        validate_companion_docs, validate_cli_companion_docs,
    )
    from harness_ai_kit.domain.manifest_ops import (
        parse_project_root_ref, skill_manifest_item_payload,
        versioned_manifest_item_payload, project_manifest_payload,
        save_project_manifest,
    )
    from harness_ai_kit.infrastructure.cli_installer import (
        normalize_cli_platform_os, normalize_cli_platform_arch,
        current_cli_platform, catalog_versions,
    )
    from harness_ai_kit.infrastructure.config_io import (
        read_top_changelog_version, read_json_file, write_project_version,
    )
    from harness_ai_kit.domain.report_presentation import (
        format_table, format_skill_table, format_managed_asset_table, format_cli_table,
    )
    from harness_ai_kit.commands.install_git_select import choose_git_skill_interactively
    from harness_ai_kit.domain.runtime_install import resolve_target_dir
    from harness_ai_kit.domain.dependency_expansion import (
        ordered_unique, skill_dependency_payload, expand_skill_ids_with_dependencies,
        dependency_followups, current_cli_versions, sync_cli_metadata_versions,
    )
    from harness_ai_kit.domain.versions import (
        bump_version_string,
        compare_versions,
        compare_versions_safe,
        highest_version,
        parse_version_from_text,
        sort_versions,
        spec_matches_version,
        upgrade_status_for_versions,
        version_to_compatible_range,
        version_to_pinned,
    )
    from harness_ai_kit.usage_docs import render_usage_doc


# Constants are imported from domain.models (see import block above).

ACTIVE_PRODUCT_PROFILE = active_product_profile()
CONFIG_DIRNAME = ACTIVE_PRODUCT_PROFILE.config_dirname
DEFAULT_CHECKOUT_DIRNAME = ACTIVE_PRODUCT_PROFILE.default_checkout_dirname
DEFAULT_TEAM_REPO_URL = ACTIVE_PRODUCT_PROFILE.default_repo_url
LOCKFILE_NAME = ACTIVE_PRODUCT_PROFILE.lockfile_name
PROJECT_MANIFEST_FILENAME = ACTIVE_PRODUCT_PROFILE.project_manifest_filename
SELF_CLI_PACKAGE_NAME = ACTIVE_PRODUCT_PROFILE.self_cli_package_name
MANAGED_ASSET_BUNDLE_ROOT = ACTIVE_PRODUCT_PROFILE.managed_asset_bundle_root
RUNTIME_SKILL_BUNDLE_ROOT = ACTIVE_PRODUCT_PROFILE.runtime_skill_bundle_root
RUNTIME_WRAPPER_PREFIX = ACTIVE_PRODUCT_PROFILE.runtime_wrapper_prefix


def apply_product_profile(profile: ProductProfile | None = None) -> ProductProfile:
    global ACTIVE_PRODUCT_PROFILE
    global CONFIG_DIRNAME
    global DEFAULT_CHECKOUT_DIRNAME
    global DEFAULT_TEAM_REPO_URL
    global LOCKFILE_NAME
    global PROJECT_MANIFEST_FILENAME
    global SELF_CLI_PACKAGE_NAME
    global MANAGED_ASSET_BUNDLE_ROOT
    global RUNTIME_SKILL_BUNDLE_ROOT
    global RUNTIME_WRAPPER_PREFIX

    ACTIVE_PRODUCT_PROFILE = profile or active_product_profile()
    os.environ[PRODUCT_ENV_VAR] = ACTIVE_PRODUCT_PROFILE.key
    CONFIG_DIRNAME = ACTIVE_PRODUCT_PROFILE.config_dirname
    DEFAULT_CHECKOUT_DIRNAME = ACTIVE_PRODUCT_PROFILE.default_checkout_dirname
    DEFAULT_TEAM_REPO_URL = ACTIVE_PRODUCT_PROFILE.default_repo_url
    LOCKFILE_NAME = ACTIVE_PRODUCT_PROFILE.lockfile_name
    PROJECT_MANIFEST_FILENAME = ACTIVE_PRODUCT_PROFILE.project_manifest_filename
    SELF_CLI_PACKAGE_NAME = ACTIVE_PRODUCT_PROFILE.self_cli_package_name
    MANAGED_ASSET_BUNDLE_ROOT = ACTIVE_PRODUCT_PROFILE.managed_asset_bundle_root
    RUNTIME_SKILL_BUNDLE_ROOT = ACTIVE_PRODUCT_PROFILE.runtime_skill_bundle_root
    RUNTIME_WRAPPER_PREFIX = ACTIVE_PRODUCT_PROFILE.runtime_wrapper_prefix
    return ACTIVE_PRODUCT_PROFILE


# Data models (SkillRecord, CliConfig, CliAssetRecord, ProjectManifest, etc.)
# are imported from domain.models (see import block above).


RuntimeProfile = runtime_install.RuntimeProfile
RUNTIME_PROFILES = runtime_install.RUNTIME_PROFILES
discover_available_runtimes = runtime_install.discover_available_runtimes



def normalize_namespace(namespace: object) -> str:
    return str(namespace or "").strip()


def namespaced_asset_id(namespace: str, asset_id: str) -> str:
    normalized = normalize_namespace(namespace)
    return f"{normalized}/{asset_id}" if normalized else asset_id


def input_is_interactive() -> bool:
    return bool(sys.stdin.isatty() and sys.stdout.isatty())


def backup_file_once(path: Path) -> Path:
    backup_path = path.with_suffix(path.suffix + ".bak")
    if not backup_path.exists():
        backup_path.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    return backup_path


_EXPORTED_COMMAND_HANDLER_NAMES = [
    'command_diff', 'command_doctor', 'command_outdated', 'command_prune',
    'command_publish', 'command_publish_cli', 'command_publish_skill',
    'command_release', 'command_sync', 'command_uninstall', 'command_upgrade',
    'command_validate',
]
__all__ = [name for name in globals() if not name.startswith('_') and name not in _EXPORTED_COMMAND_HANDLER_NAMES]


