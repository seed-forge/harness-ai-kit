from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Iterable

from ai_kit.domain.artifacts import (
    IGNORED_HASH_FILENAMES,
    _should_ignore_hash_path,
    build_skill_archive_bytes,
    cache_inventory,
    cache_file_for_url,
    clean_cache,
    hash_bytes,
    hash_file,
    hash_named_bytes,
    hash_skill_directory,
    git_source_cache_path,
    manifest_cache_dir,
)
from ai_kit.domain.dependencies import DependencySpec
from ai_kit.domain.identity import (
    canonical_package_id,
    namespace_label,
    normalize_namespace,
    package_key,
    package_key_for,
    split_canonical_id,
)
from ai_kit.domain.lockfile import SCHEMA_VERSION, LockNode, Lockfile, RootRequest
from ai_kit.domain.lockfile_io import (
    LOCKFILE_NAME,
    lockfile_path,
    read_lockfile,
    reverse_dependencies,
    state_dir,
    topological_skill_nodes,
    topological_skill_nodes_from_lock,
    tree_lines,
    write_lockfile,
    write_lockfile_model,
)
from ai_kit.domain.manifest import (
    ASSET_METADATA_FILENAMES,
    DEPENDENCY_TYPES,
    MANAGED_ASSET_TYPES,
    CompanionDocs,
    EnvironmentRequirements,
    ExecutableRequirement,
    SkillManifest,
)
from ai_kit.domain.manifest_io import (
    dependency_summary,
    find_lock_node,
    load_skill_manifest,
    manifest_canonical_id,
    manifest_metadata_filename,
    manifest_metadata_path,
    manifest_validation_error,
)
from ai_kit.domain.policies import (
    INSTALL_SOURCE_SELECTORS,
    SOURCE_MANUAL,
    SOURCE_PUBLIC_REGISTRY,
    SOURCE_REGISTRY,
    SOURCE_REPO,
    SOURCE_WORKSPACE_REPO,
    SOURCE_INTERNAL_REGISTRY,
    SOURCE_GIT_REPO,
    SOURCE_LOCAL_CACHE,
    SOURCE_LOCKFILE,
    SUPPORTED_SOURCES,
    InstallationPolicy,
    SourcePolicy,
    consumer_source_order,
    display_source_name,
    normalize_source_name,
    selectable_install_source,
    source_order_for_selector,
)
from ai_kit.domain.registry import (
    download_registry_artifact,
    download_registry_manifest,
    http_request_bytes,
    http_request_json,
    load_registry_index,
    registry_artifact_url,
    registry_headers,
    registry_item_matches,
    registry_metadata_url,
    registry_skill_version_entry,
    update_registry_index_payload,
    upload_bytes,
)
from ai_kit.domain.resolver import DiscoveredGitSkill, GitRepoCheckout, GitSkillResolver, GitSourceSpec, ResolutionProvider
from ai_kit.domain.resolver import build_resolution_plan as _build_resolution_plan
from ai_kit.domain.resolver import (
    default_git_repo_checkout,
    default_git_skill_resolver,
    discover_git_skills,
    git_source_repo_name,
    git_source_commit,
    github_raw_metadata_url,
    is_git_source_selector,
    normalize_git_source_url,
    parse_git_source_ref,
    skill_dirs_under,
)
from ai_kit.domain.resolution import DependencyRequirement, PackageCandidate, ResolutionPlan, utc_now_iso
from ai_kit.domain.versions import PINNED_VERSION_PATTERN, ensure_version, is_pinned_specifier


PUBLIC_NAMESPACE = "public"


def build_resolution_plan(
    repo_root: Path,
    registry_index_url: str,
    root_skill_ids: list[str],
    *,
    root_asset_kind: str = "skill",
    runtime: str,
    install_scope: str,
    selected_features: Iterable[str] = (),
    offline: bool = False,
    cli_versions: dict[str, str] | None = None,
    preferred_sources: list[str] | None = None,
    public_registry_index_url: str = "",
    cli_registry_index_url: str = "",
    root_sources: dict[str, tuple[str, str | None, str | None]] | None = None,
    root_specifiers: dict[str, str] | None = None,
    git_skill_resolver: GitSkillResolver = default_git_skill_resolver,
) -> ResolutionPlan:
    return _build_resolution_plan(
        repo_root=repo_root,
        registry_index_url=registry_index_url,
        root_skill_ids=root_skill_ids,
        root_asset_kind=root_asset_kind,
        runtime=runtime,
        install_scope=install_scope,
        selected_features=selected_features,
        offline=offline,
        cli_versions=cli_versions or {},
        preferred_sources=preferred_sources,
        public_registry_index_url=public_registry_index_url,
        cli_registry_index_url=cli_registry_index_url,
        root_sources=root_sources,
        root_specifiers=root_specifiers,
        git_skill_resolver=git_skill_resolver,
        registry_manifest_downloader=lambda index_url, skill_id, version: download_registry_manifest(
            index_url,
            skill_id,
            version,
            offline=offline,
        ),
        registry_artifact_url_resolver=registry_artifact_url,
        registry_metadata_url_resolver=registry_metadata_url,
    )


