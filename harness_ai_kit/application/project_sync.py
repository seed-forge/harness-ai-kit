"""Project sync orchestration: lockfile, asset resolution, sync execution."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from harness_ai_kit import package_manager as pm
from harness_ai_kit.domain.models import (
    ASSET_DIRECTORY_NAMES, CliAssetRecord, CliConfig, CliInstallState,
    ProjectManifest, ProjectRootSpec, ProjectVersionedAssetSpec,
    SkillInstallState, SkillRecord, effective_role,
)
from harness_ai_kit.domain.models.constants import (
    MANAGED_ASSET_TYPES, PROJECT_MANIFEST_SCHEMA_VERSION, VERSIONED_ASSET_TYPES,
)
from harness_ai_kit.domain.runtime_install import RUNTIME_PROFILES
from harness_ai_kit.domain import project_manifest_state
from harness_ai_kit.domain import project_sync_presentation
from harness_ai_kit.domain import project_state
from harness_ai_kit.domain import project_locking
from harness_ai_kit.domain import managed_install
from harness_ai_kit.domain import skill_install
from harness_ai_kit.domain.dependency_expansion import current_cli_versions, ordered_unique
from harness_ai_kit.domain.inventory import (
    load_cli_metadata_for_record,
    load_skill_metadata_for_record,
)
from harness_ai_kit.infrastructure.config_io import resolve_repo_root_if_available
from harness_ai_kit.infrastructure.cli_installer import install_cli_packages
from harness_ai_kit.infrastructure.git_ops_extra import maybe_sync_repo
from harness_ai_kit.domain.manifest_ops import (
    declared_skill_specs, declared_plugin_specs, declared_hook_specs,
    declared_subagent_specs, declared_mcp_specs, declared_loop_specs,
    declared_cli_specs, project_lock_path_for_manifest,
    project_manifest_path, project_manifest_root_requests,
    project_root_ids, manifest_declared_features,
    manifest_skill_source_policy, manifest_skill_root_sources,
    manifest_skill_version_specifiers, save_project_manifest,
)
from harness_ai_kit.domain.install_state import (
    current_materialized_checksum_for_node,
    current_source_checksum_for_node,
    evaluate_installed_asset_drift,
    install_skill_directory,
    installed_managed_asset_materialized_checksum,
    installed_managed_asset_version,
    installed_skill_ids,
    installed_skill_locations,
    installed_skill_materialized_checksum,
    installed_skill_payload_dir,
    installed_skill_version,
    installed_managed_asset_ids,
    managed_asset_install_destination,
    manual_invocation_hint,
    render_cursor_rule,
    render_kiro_steering,
    runtime_install_destination,
    runtime_managed_asset_root,
    source_materialized_checksum,
)
from harness_ai_kit.domain import cli_assets
from harness_ai_kit.domain import managed_assets
from harness_ai_kit.domain.inventory import load_combined_cli_inventory, load_managed_asset_inventory
from harness_ai_kit.domain.runtime_install import (
    discover_available_runtimes,
    install_skill_archive_bytes,
    resolve_target_dir as _runtime_resolve_target_dir,
    runtime_profile,
)
from harness_ai_kit.domain import project_sync as _domain_project_sync
from harness_ai_kit.domain import project_sync_results
from harness_ai_kit.product import active_product_profile as _active_product_profile

_ACTIVE = _active_product_profile()
CONFIG_DIRNAME = _ACTIVE.config_dirname
LOCKFILE_NAME = _ACTIVE.lockfile_name


def warn_same_version_drift(
    node: pm.LockNode,
    runtime_id: str,
    scope: str,
    installed_version: str,
    actual_materialized_checksum: str,
) -> bool:
    drift_status, drift_message = evaluate_installed_asset_drift(
        node=node,
        runtime_id=runtime_id,
        installed_version=installed_version,
        actual_materialized_checksum=actual_materialized_checksum,
        current_source_checksum=current_source_checksum_for_node(node, runtime_id),
        current_materialized_checksum=current_materialized_checksum_for_node(node, runtime_id),
    )
    if drift_status == "drift-detected":
        print(
            f"Warning: detected drift for {node.type} {node.id}@{node.version} in {runtime_id}/{scope}; "
            f"skipping overwrite because the installed copy differs while the version is unchanged. {drift_message}"
        )
        return True
    if drift_status == "checksum-unknown":
        print(
            f"Warning: could not verify drift for {node.type} {node.id}@{node.version} in {runtime_id}/{scope}; "
            f"skipping overwrite because the version is unchanged. {drift_message}"
        )
    return False




def apply_managed_asset_lockfile(lockfile: pm.Lockfile, target_dir: Path, runtime_id: str) -> list[tuple[pm.LockNode, Path]]:
    return managed_install.apply_managed_asset_lockfile(
        lockfile,
        target_dir,
        runtime_id,
        ASSET_DIRECTORY_NAMES,
        installed_version=installed_managed_asset_version,
        installed_materialized_checksum=installed_managed_asset_materialized_checksum,
        warn_same_version_drift=warn_same_version_drift,
    )




def refresh_existing_local_skill_installs(
    repo_root: Path,
    record: SkillRecord,
    home_dir: Path | None = None,
) -> tuple[list[tuple[str, str, Path]], list[tuple[str, str, Path, str]]]:
    refreshed: list[tuple[str, str, Path]] = []
    failures: list[tuple[str, str, Path, str]] = []
    for runtime_id in RUNTIME_PROFILES:
        for scope_name, target_dir in installed_skill_locations(repo_root, runtime_id, home_dir=home_dir):
            if record.skill_id not in installed_skill_ids(target_dir, runtime_id):
                continue
            destination = runtime_install_destination(target_dir, record.skill_id, runtime_id)
            try:
                install_skill_directory(record.path, target_dir, runtime_id)
            except Exception as exc:
                failures.append((runtime_id, scope_name, destination, str(exc)))
                continue
            refreshed.append((runtime_id, scope_name, destination))
    return refreshed, failures




def print_local_skill_refresh_summary(
    record: SkillRecord,
    refreshed: list[tuple[str, str, Path]],
    failures: list[tuple[str, str, Path, str]],
) -> None:
    if not refreshed and not failures:
        print(
            f"Post-publish hook: no existing local installs of `{record.skill_id}` were found on this machine, so no runtime copies were refreshed."
        )
        return
    if refreshed:
        print(f"Post-publish hook: refreshed local runtime copies for `{record.skill_id}`:")
        for runtime_id, scope_name, destination in refreshed:
            print(f"- {runtime_id}/{scope_name} -> {destination}")
    if failures:
        print(f"Post-publish hook: failed to refresh some local runtime copies for `{record.skill_id}`:")
        for runtime_id, scope_name, destination, message in failures:
            print(f"- {runtime_id}/{scope_name} -> {destination} ({message})")




def resolve_lock_path(target_dir: Path | None = None, scope: str = "project") -> Path:
    if scope == "project" and target_dir is not None:
        if target_dir.name == "skills" and target_dir.parent.name in {".agents", ".claude"}:
            return pm.lockfile_path(target_dir.parent.parent)
        if target_dir.name in {"steering", "rules"} and target_dir.parent.name in {".kiro", ".cursor"}:
            return pm.lockfile_path(target_dir.parent.parent)
    if scope == "global":
        if target_dir is not None and target_dir.parent.name in {".codex", ".claude", ".kiro", ".cursor"}:
            state_root = target_dir.parent.parent / CONFIG_DIRNAME / "state"
            state_root.mkdir(parents=True, exist_ok=True)
            return state_root / LOCKFILE_NAME
        state_root = pm.state_dir()
        state_root.mkdir(parents=True, exist_ok=True)
        return state_root / LOCKFILE_NAME
    return pm.lockfile_path(Path.cwd())




def apply_skill_lockfile(
    repo_root: Path,
    config: CliConfig,
    lockfile: pm.Lockfile,
    target_dir: Path,
    runtime_id: str,
    offline: bool,
) -> list[Path]:
    def install_registry_skill(node: pm.LockNode) -> Path:
        registry_index_url = (
            config.public_skill_registry_index_url
            if node.source == pm.SOURCE_PUBLIC_REGISTRY
            else config.skill_registry_index_url
        )
        payload, entry = pm.download_registry_artifact(
            registry_index_url,
            node.id,
            version=node.version,
            offline=offline,
        )
        expected_checksum = (node.checksum or "").strip()
        actual_checksum = pm.hash_bytes(payload)
        if expected_checksum and actual_checksum != expected_checksum:
            raise ValueError(
                f"Checksum mismatch for {node.id}@{node.version}: expected {expected_checksum}, got {actual_checksum}"
            )
        return install_skill_archive_bytes(
            payload, target_dir, runtime_id,
            render_kiro_steering=render_kiro_steering,
            render_cursor_rule=render_cursor_rule,
        )

    return skill_install.apply_skill_lockfile(
        lockfile,
        target_dir,
        runtime_id,
        installed_version=installed_skill_version,
        installed_materialized_checksum=installed_skill_materialized_checksum,
        install_skill_directory=install_skill_directory,
        install_registry_skill=install_registry_skill,
        warn_same_version_drift=warn_same_version_drift,
    )




def print_non_skill_requirements(lockfile: pm.Lockfile) -> None:
    for asset_type, label in (
        ("cli", "Companion CLIs"),
        ("plugin", "Companion plugins"),
        ("hook", "Companion hooks"),
        ("subagent", "Companion subagents"),
        ("mcp", "Companion MCPs"),
    ):
        nodes = [node for node in lockfile.nodes if node.type == asset_type]
        if nodes:
            print(f"{label} in lockfile: " + ", ".join(f"{node.id}@{node.version}" for node in nodes))
    hints = []
    verify_commands = []
    for node in lockfile.nodes:
        hints.extend(node.runtime_requirements)
        hints.extend(node.post_install_hints)
        environment = dict(node.environment or {})
        verify_commands.extend(environment.get("verify_commands", []))
    for hint in ordered_unique(hints):
        print(f"Dependency note: {hint}")
    for command in ordered_unique(verify_commands):
        print(f"Verify command: {command}")


_INJECT_MARKER_BEGIN = "<!-- ai-kit:inject {skill_id} -->"
_INJECT_MARKER_END = "<!-- /ai-kit:inject {skill_id} -->"
_INJECT_BLOCK_RE = re.compile(
    r"<!-- ai-kit:inject (\S+) -->.*?<!-- /ai-kit:inject \1 -->",
    re.DOTALL,
)


def apply_agents_md_injections(lockfile: pm.Lockfile, project_root: Path) -> list[str]:
    """Scan installed skills for ``agents_md_inject`` and update AGENTS.md.

    Uses HTML comment markers for idempotent insert/update and auto-removal
    of blocks belonging to skills that are no longer installed.
    """
    agents_md = project_root / "AGENTS.md"
    if not agents_md.exists():
        return []
    content = agents_md.read_text(encoding="utf-8")
    original = content
    desired_ids: set[str] = set()
    injected: list[str] = []

    for node in lockfile.nodes:
        if node.type != "skill":
            continue
        text = (getattr(node, "agents_md_inject", "") or "").strip()
        if not text:
            continue
        desired_ids.add(node.id)
        marker_begin = _INJECT_MARKER_BEGIN.format(skill_id=node.id)
        marker_end = _INJECT_MARKER_END.format(skill_id=node.id)
        block = f"{marker_begin}\n{text}\n{marker_end}"
        if marker_begin in content:
            # Replace existing block (idempotent update)
            pattern = re.compile(
                re.escape(marker_begin) + r".*?" + re.escape(marker_end),
                re.DOTALL,
            )
            content = pattern.sub(block, content)
        else:
            # Append at end
            content = content.rstrip() + "\n\n" + block + "\n"
        injected.append(node.id)

    # Remove blocks for skills no longer installed (or that lost agents_md_inject)
    for match in _INJECT_BLOCK_RE.finditer(content):
        if match.group(1) not in desired_ids:
            content = content.replace(match.group(0), "")

    # Clean up excess blank lines left after removal
    content = re.sub(r"\n{3,}", "\n\n", content).rstrip() + "\n"

    if content != original:
        agents_md.write_text(content, encoding="utf-8")
        for skill_id in injected:
            print(f"AGENTS.md: injected section for {skill_id}")
    return injected


def resolve_asset_plan(
    repo_root: Path,
    config: CliConfig,
    *,
    asset_kind: str,
    root_ids: list[str],
    runtime_id: str,
    install_scope: str,
    features: list[str],
    offline: bool,
    source_selector: str | None = None,
    preferred_sources: list[str] | None = None,
    root_sources: dict[str, tuple[str, str | None, str | None]] | None = None,
    root_specifiers: dict[str, str] | None = None,
) -> pm.ResolutionPlan:
    selected_source = pm.selectable_install_source(source_selector)
    registry_index_url = config.skill_registry_index_url
    if asset_kind != "skill" and selected_source == pm.SOURCE_PUBLIC_REGISTRY:
        raise ValueError("Public registry resolution is only supported for skills right now.")
    if selected_source == pm.SOURCE_PUBLIC_REGISTRY:
        registry_index_url = config.public_skill_registry_index_url.strip()
        if not registry_index_url:
            raise ValueError(
                "No public skill registry index URL is configured. "
                "Set `--public-skill-registry-index-url` via `harness-ai-kit config set` or omit `--from public-registry`."
            )
    from resolvelib.resolvers.exceptions import ResolutionImpossible as _ResolutionImpossible
    from resolvelib.resolvers.exceptions import InconsistentCandidate as _InconsistentCandidate
    # Role-based source default: consumers (and unset machines) resolve
    # registry-only, never depending on a local repo checkout. An explicit
    # ``preferred_sources`` or ``--from`` selector always wins.
    role_default_sources = (
        pm.consumer_source_order() if effective_role(config) == "consumer" else None
    )
    current_ids = list(root_ids)
    current_root_sources = dict(root_sources) if root_sources else None
    current_root_specifiers = dict(root_specifiers) if root_specifiers else None
    accumulated_failed: set[str] = set()
    _inconsistent_retry_done = False
    _cli_versions_override: dict[str, str] | None = None
    while True:
        try:
            effective_cli_versions = _cli_versions_override if _cli_versions_override is not None else current_cli_versions(repo_root, config)
            plan = pm.build_resolution_plan(
                repo_root,
                registry_index_url,
                current_ids,
                root_asset_kind=asset_kind,
                runtime=runtime_id,
                install_scope=install_scope,
                selected_features=features,
                offline=offline,
                cli_versions=effective_cli_versions,
                preferred_sources=preferred_sources or pm.source_order_for_selector(selected_source) or role_default_sources,
                public_registry_index_url=config.public_skill_registry_index_url.strip(),
                cli_registry_index_url=config.cli_registry_index_url.strip(),
                root_sources=current_root_sources,
                root_specifiers=current_root_specifiers,
            )
            break  # Success
        except (_ResolutionImpossible, RuntimeError) as exc:
            # build_resolution_plan wraps ResolutionImpossible into RuntimeError;
            # handle both so the skip-and-retry logic works for unresolvable root skills.
            failed_ids: set[str] = set()
            # Try to extract causes from the original ResolutionImpossible (if unwrapped)
            raw_causes = getattr(exc, "causes", None) or []
            if not raw_causes and hasattr(exc, "__cause__"):
                raw_causes = getattr(exc.__cause__, "causes", None) or getattr(exc.__cause__, "backtrack_causes", None) or []
            for info in raw_causes:
                req = getattr(info, "requirement", None)
                parent = getattr(info, "parent", None)
                if req is not None:
                    pkg_id = getattr(req, "package_id", "") or ""
                    if pkg_id:
                        failed_ids.add(pkg_id)
                    req_ns = getattr(req, "namespace", None)
                    if pkg_id and req_ns:
                        failed_ids.add(pm.canonical_package_id(pkg_id, req_ns))
                # Also mark the parent (root skill that declared this dependency)
                # so it can be removed from current_ids on retry.
                if parent is not None:
                    parent_id = getattr(parent, "package_id", "") or ""
                    parent_ns = getattr(parent, "namespace", None)
                    if parent_id:
                        failed_ids.add(parent_id)
                        failed_ids.add(pm.canonical_package_id(parent_id, parent_ns))
            # Fallback: parse failed package IDs from the RuntimeError message
            if not failed_ids and isinstance(exc, RuntimeError):
                import re
                for match in re.finditer(r"- ([\w/.-]+)(?:>=|==|~=|!=|<|>)", str(exc)):
                    failed_ids.add(match.group(1))
            if not failed_ids or failed_ids.issubset(accumulated_failed):
                raise  # No new IDs to remove, re-raise
            accumulated_failed.update(failed_ids)
            for fid in sorted(failed_ids):
                print(f"WARNING: {asset_kind} '{fid}' declared in ai-kit.yml could not be resolved (not found in local repo or registry). Skipping.")
            current_ids = [rid for rid in current_ids if rid not in failed_ids]
            if not current_ids:
                raise
            if current_root_sources:
                current_root_sources = {k: v for k, v in current_root_sources.items() if k not in failed_ids}
            if current_root_specifiers:
                current_root_specifiers = {k: v for k, v in current_root_specifiers.items() if k not in failed_ids}
        except _InconsistentCandidate as exc:
            # lockfile 旧约束与新 manifest 冲突 → 清除 cli_versions 重试一次
            if not _inconsistent_retry_done:
                _inconsistent_retry_done = True
                candidate = getattr(exc, "candidate", None)
                candidate_id = getattr(candidate, "package_id", "?") if candidate else "?"
                candidate_ver = getattr(candidate, "version", "?") if candidate else "?"
                print(
                    f"WARNING: 版本冲突 — {candidate_id}@{candidate_ver} 无法满足所有约束。"
                    f"正在清除旧约束重新解析..."
                )
                _cli_versions_override = {}  # 清除旧 CLI 版本约束
                continue
            raise
    return _domain_project_sync.refresh_repo_node_checksums(
        plan,
        runtime_id,
        path_exists=Path.exists,
        source_checksum=pm.hash_skill_directory,
        materialized_checksum=source_materialized_checksum,
    )




def resolve_skill_plan(
    repo_root: Path,
    config: CliConfig,
    *,
    root_ids: list[str],
    runtime_id: str,
    install_scope: str,
    features: list[str],
    offline: bool,
    asset_kind: str = "skill",
    source_selector: str | None = None,
    preferred_sources: list[str] | None = None,
    root_sources: dict[str, tuple[str, str | None, str | None]] | None = None,
    root_specifiers: dict[str, str] | None = None,
) -> pm.ResolutionPlan:
    return resolve_asset_plan(
        repo_root,
        config,
        asset_kind=asset_kind,
        root_ids=root_ids,
        runtime_id=runtime_id,
        install_scope=install_scope,
        features=features,
        offline=offline,
        source_selector=source_selector,
        preferred_sources=preferred_sources,
        root_sources=root_sources,
        root_specifiers=root_specifiers,
    )




def resolve_asset_root(record: CliAssetRecord, repo_root: Path) -> Path:
    if record.path is None:
        raise ValueError(f"CLI {record.cli_id} does not have a local repository path.")
    return repo_root / "cli" / record.path.name




def resolve_cli_publish_root(record: CliAssetRecord, repo_root: Path) -> Path:
    asset_root = resolve_asset_root(record, repo_root)
    repo_pyproject = repo_root / "pyproject.toml"
    if repo_pyproject.exists():
        payload = repo_pyproject.read_text(encoding="utf-8")
        pattern = rf'(?m)^\s*name\s*=\s*"{re.escape(record.package_name)}"\s*$'
        if re.search(pattern, payload):
            return repo_root
    return asset_root




def manifest_target_dir(manifest_path: Path, runtime_id: str, install_scope: str, target_dir: str | None = None) -> Path:
    return _runtime_resolve_target_dir(manifest_path.parent, target_dir, cwd=manifest_path.parent, runtime_id=runtime_id, scope=install_scope)




def select_cli_record_for_spec(inventory: dict[str, CliAssetRecord], spec: ProjectVersionedAssetSpec) -> CliAssetRecord:
    return cli_assets.select_cli_record_for_spec(inventory, spec)




def select_managed_asset_record_for_spec(
    repo_root: Path,
    asset_type: str,
    spec: ProjectVersionedAssetSpec,
) -> SkillRecord:
    inventory = load_managed_asset_inventory(repo_root, asset_type)
    return managed_assets.select_managed_asset_record_for_spec(inventory, asset_type, spec)





def project_lockfile_from_manifest(
    repo_root: Path,
    config: CliConfig,
    manifest: ProjectManifest,
    runtime_id: str,
    install_scope: str,
    *,
    offline: bool,
) -> pm.Lockfile:
    skill_root_ids = project_root_ids(manifest)
    loop_root_ids = [pm.canonical_package_id(item.id, item.namespace) for item in declared_loop_specs(manifest)]
    features = manifest_declared_features(manifest)
    skill_source_policy = manifest_skill_source_policy(manifest)
    skill_root_sources = manifest_skill_root_sources(manifest)
    skill_root_specifiers = manifest_skill_version_specifiers(manifest)
    if skill_root_ids:
        plan = resolve_skill_plan(
            repo_root,
            config,
            root_ids=skill_root_ids,
            runtime_id=runtime_id,
            install_scope=install_scope,
            features=features,
            offline=offline,
            preferred_sources=skill_source_policy,
            root_sources=skill_root_sources,
            root_specifiers=skill_root_specifiers,
        )
        lockfile = plan.to_lockfile()
        nodes = list(lockfile.nodes)
        root_requests = list(lockfile.root_requests)
        roots = list(lockfile.roots)
    else:
        nodes = []
        root_requests = []
        roots = []
    if loop_root_ids:
        loop_specifiers = {
            pm.canonical_package_id(item.id, item.namespace): item.version
            for item in declared_loop_specs(manifest)
        }
        plan = resolve_asset_plan(
            repo_root,
            config,
            asset_kind="loop",
            root_ids=loop_root_ids,
            runtime_id=runtime_id,
            install_scope=install_scope,
            features=features,
            offline=offline,
            root_specifiers=loop_specifiers,
        )
        lockfile = plan.to_lockfile()
        existing = {
            pm.package_key_for(node.type, node.id, node.namespace): node
            for node in nodes
        }
        for node in lockfile.nodes:
            key = pm.package_key_for(node.type, node.id, node.namespace)
            existing[key] = node
        nodes = list(existing.values())
        root_requests.extend(lockfile.root_requests)
        roots.extend(lockfile.roots)
    cli_entries: list[project_locking.CliLockEntry] = []
    cli_specs = declared_cli_specs(manifest)
    if cli_specs:
        inventory = load_combined_cli_inventory(repo_root, config)
        for spec in cli_specs:
            record = select_cli_record_for_spec(inventory, spec)
            cli_entries.append(project_locking.CliLockEntry(spec=spec, record=record))
    managed_entries: list[project_locking.ManagedAssetLockEntry] = []
    for asset_type, specs in (
        ("plugin", declared_plugin_specs(manifest)),
        ("hook", declared_hook_specs(manifest)),
        ("subagent", declared_subagent_specs(manifest)),
        ("mcp", declared_mcp_specs(manifest)),
    ):
        for spec in specs:
            record = select_managed_asset_record_for_spec(repo_root, asset_type, spec)
            metadata = load_skill_metadata_for_record(record, config)
            manifest_payload = pm.SkillManifest.model_validate(metadata)
            managed_entries.append(
                project_locking.ManagedAssetLockEntry(
                    asset_type=asset_type,
                    spec=spec,
                    record=record,
                    companion_docs=manifest_payload.companion_docs.model_dump(mode="json"),
                    environment=manifest_payload.environment.model_dump(mode="json"),
                    runtime_requirements=list(manifest_payload.runtime_requirements),
                    post_install_hints=list(manifest_payload.post_install_hints),
                    recommended_tools=list(manifest_payload.recommended_tools),
                    contributors=list(manifest_payload.contributors),
                    skill_type=manifest_payload.skill_type,
                    agents_md_inject=manifest_payload.agents_md_inject,
                    config_schema=manifest_payload.config_schema,
                )
            )
    return project_locking.assemble_project_lockfile(
        generated_at=pm.utc_now_iso(),
        runtime=runtime_id,
        install_scope=install_scope,
        roots=roots,
        features=features,
        root_requests=root_requests or project_manifest_root_requests(manifest),
        base_nodes=nodes,
        cli_entries=cli_entries,
        managed_entries=managed_entries,
    )





def remove_installed_skill(target_dir: Path, skill_id: str, runtime_id: str) -> bool:
    removed = False
    destination = runtime_install_destination(target_dir, skill_id, runtime_id)
    payload_dir = installed_skill_payload_dir(target_dir, skill_id, runtime_id)
    if destination.exists():
        if destination.is_dir():
            shutil.rmtree(destination, ignore_errors=True)
        else:
            destination.unlink(missing_ok=True)
        removed = True
    if payload_dir.exists() and payload_dir != destination:
        shutil.rmtree(payload_dir, ignore_errors=True)
        removed = True
    return removed





def remove_installed_managed_asset(target_dir: Path, asset_type: str, asset_id: str, runtime_id: str) -> bool:
    destination = managed_asset_install_destination(target_dir, asset_type, asset_id, runtime_id)
    if not destination.exists():
        return False
    shutil.rmtree(destination, ignore_errors=True)
    return True




def prune_orphaned_project_skills(
    target_dir: Path,
    runtime_id: str,
    desired_skill_ids: Iterable[str],
    managed_skill_ids: Iterable[str] | None = None,
) -> list[str]:
    removed: list[str] = []
    for skill_id in project_state.orphan_skill_ids(installed_skill_ids(target_dir, runtime_id), desired_skill_ids, managed_skill_ids):
        if remove_installed_skill(target_dir, skill_id, runtime_id):
            removed.append(skill_id)
    return removed




def prune_orphaned_project_managed_assets(
    target_dir: Path,
    runtime_id: str,
    desired_assets: dict[str, set[str]],
    managed_assets: dict[str, set[str]] | None = None,
) -> list[str]:
    removed: list[str] = []
    installed_assets = {
        asset_type: installed_managed_asset_ids(target_dir, asset_type, runtime_id)
        for asset_type in ("plugin", "hook", "subagent", "mcp", "loop")
    }
    for asset_ref in project_state.orphan_managed_asset_ids(installed_assets, desired_assets, managed_assets):
        asset_type, asset_id = asset_ref.split(":", 1)
        if remove_installed_managed_asset(target_dir, asset_type, asset_id, runtime_id):
            removed.append(asset_ref)
    return removed




def managed_project_skill_ids(lock_path: Path, desired_skill_ids: Iterable[str]) -> set[str]:
    if not lock_path.exists():
        return _domain_project_sync.managed_project_skill_ids_from_lock(None, desired_skill_ids)
    try:
        existing_lock = pm.read_lockfile(lock_path)
    except Exception:
        return _domain_project_sync.managed_project_skill_ids_from_lock(None, desired_skill_ids)
    return _domain_project_sync.managed_project_skill_ids_from_lock(existing_lock, desired_skill_ids)





def managed_project_asset_ids(lock_path: Path, desired_assets: dict[str, set[str]]) -> dict[str, set[str]]:
    if not lock_path.exists():
        return _domain_project_sync.managed_project_asset_ids_from_lock(None, desired_assets)
    try:
        existing_lock = pm.read_lockfile(lock_path)
    except Exception:
        return _domain_project_sync.managed_project_asset_ids_from_lock(None, desired_assets)
    return _domain_project_sync.managed_project_asset_ids_from_lock(existing_lock, desired_assets)




def cli_nodes_from_lock(lockfile: pm.Lockfile) -> list[pm.LockNode]:
    return cli_assets.cli_nodes_from_lock(lockfile)





def select_cli_records_for_lock(lockfile: pm.Lockfile, repo_root: Path | None, config: CliConfig) -> list[CliAssetRecord]:
    if not cli_nodes_from_lock(lockfile):
        return []
    inventory = load_combined_cli_inventory(repo_root, config)
    records = cli_assets.select_cli_records_for_lock(lockfile, inventory)
    return cli_assets.expand_cli_records_with_dependencies(records, inventory, load_cli_metadata_for_record)




def compute_extends_summary(lockfile: Any, nodes: Any) -> dict[str, Any]:
    """Compute extends chain summary from a lockfile.

    Returns a dict with:
        extends_count: number of skills that have extends edges
        base_count: number of unique base skills referenced
        extends_summary_line: human-readable summary string
        merge_lines: list of per-skill merge progress lines
    """
    extends_nodes = [node for node in nodes if getattr(node, "extends", None)]
    if not extends_nodes:
        return {
            "extends_count": 0,
            "base_count": 0,
            "extends_summary_line": None,
            "merge_lines": [],
        }

    base_ids: set[str] = set()
    merge_lines: list[str] = []
    for node in extends_nodes:
        for ext_edge in (node.extends or []):
            base_id = str(ext_edge.get("base_skill_id", ""))
            strategy = str(ext_edge.get("merge_strategy", "prepend"))
            if base_id:
                base_ids.add(base_id)
            merge_lines.append(
                project_sync_presentation.extends_merge_progress_line(
                    skill_id=node.id,
                    base_id=base_id or "?",
                    strategy=strategy,
                )
            )

    extends_count = len(extends_nodes)
    base_count = len(base_ids)
    extends_summary_line = project_sync_presentation.extends_chain_summary_line(
        extends_count=extends_count,
        base_count=base_count,
    )

    return {
        "extends_count": extends_count,
        "base_count": base_count,
        "extends_summary_line": extends_summary_line,
        "merge_lines": merge_lines,
    }




def fanout_canonical_to_runtime(
    canonical_dir: Path,
    target_dir: Path,
    desired_skill_ids: set[str],
    managed_skill_ids: set[str] | None = None,
) -> list[Path]:
    """从 .agents/skills（权威源）复制 skill 到次级 runtime 目录。

    只复制 desired_skill_ids 中的 skill。清理时仅删除 lockfile 曾记录
    （``managed_skill_ids``）且已不在 desired 集合中的目录，
    保留非 harness-ai-kit 管理的自定义 skill。

    Args:
        canonical_dir: 权威源目录（如 .agents/skills）。
        target_dir: 次级 runtime 目标目录（如 .claude/skills）。
        desired_skill_ids: 当前 lockfile 中声明的 skill 集合。
        managed_skill_ids: lockfile 历史追踪的 skill 全集
            （desired ∪ 旧 lockfile 中曾管理的），用于判断哪些目录
            是 harness-ai-kit 放置的。为 None 时回退到旧行为（按 SKILL.md 判断）。
    """
    installed = []
    target_dir.mkdir(parents=True, exist_ok=True)

    for skill_id in desired_skill_ids:
        src = canonical_dir / skill_id
        if not src.exists():
            continue
        dst = target_dir / skill_id
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        installed.append(dst)

    # 仅清理 lockfile 曾管理但已不再 desired 的 skill；
    # 保留非 harness-ai-kit 管理的自定义 skill（不删未知目录）。
    if managed_skill_ids is not None:
        orphans = managed_skill_ids - desired_skill_ids
        for skill_id in orphans:
            child = target_dir / skill_id
            if child.is_dir():
                shutil.rmtree(child)

    return installed




def run_project_sync(
    config: CliConfig,
    manifest_path: Path,
    manifest: ProjectManifest,
    *,
    repo_root_arg: str | None,
    target_dir_override: str | None,
    runtime_override: str | None,
    scope_override: str | None,
    sync_repo: bool,
    offline: bool,
    dry_run: bool,
    cli_upgrade: bool,
) -> dict[str, Any]:
    runtime_id = runtime_override or manifest.runtime
    install_scope = scope_override or manifest.scope
    repo_root = resolve_repo_root_if_available(repo_root_arg, config, cwd=manifest_path.parent)
    team_repo_skill_specs = [item for item in declared_skill_specs(manifest) if not item.source_ref]
    if repo_root is not None and sync_repo:
        maybe_sync_repo(argparse.Namespace(sync_repo=True), repo_root)
    elif repo_root is None and (
        team_repo_skill_specs
        or declared_plugin_specs(manifest)
        or declared_hook_specs(manifest)
        or declared_subagent_specs(manifest)
        or declared_mcp_specs(manifest)
        or declared_loop_specs(manifest)
    ):
        raise ValueError("Project sync needs a bootstrapped local repository or explicit --repo-root when managed assets are declared.")
    repo_root_for_target = repo_root or manifest_path.parent
    target_dir = manifest_target_dir(manifest_path, runtime_id, install_scope, target_dir_override)
    lockfile = project_lockfile_from_manifest(repo_root_for_target, config, manifest, runtime_id, install_scope, offline=offline)
    lock_path = project_lock_path_for_manifest(manifest_path, target_dir, install_scope)
    desired_skill_ids = _domain_project_sync.desired_skill_ids(lockfile)
    desired_managed_assets = _domain_project_sync.desired_managed_assets(lockfile)
    prune_scope_skill_ids = managed_project_skill_ids(lock_path, desired_skill_ids) if install_scope == "project" else set()
    prune_scope_managed_assets = managed_project_asset_ids(lock_path, desired_managed_assets) if install_scope == "project" else {}
    if dry_run:
        removed_skills, removed_assets = project_sync_results.project_prune_preview(
            install_scope=install_scope,
            installed_skill_ids=installed_skill_ids(target_dir, runtime_id),
            installed_assets={
                asset_type: installed_managed_asset_ids(target_dir, asset_type, runtime_id)
                for asset_type in ("plugin", "hook", "subagent", "mcp", "loop")
            },
            desired_skill_ids=desired_skill_ids,
            desired_assets=desired_managed_assets,
            managed_skill_ids=prune_scope_skill_ids,
            managed_assets=prune_scope_managed_assets,
        )
    else:
        pm.write_lockfile(_domain_project_sync.lockfile_to_resolution_plan(lockfile), lock_path)
        removed_skills = []
        removed_assets = []
    cli_records = select_cli_records_for_lock(lockfile, repo_root, config)
    if dry_run:
        return project_sync_results.base_project_sync_summary(
            lockfile=lockfile,
            lock_path=lock_path,
            target_dir=target_dir,
            runtime=runtime_id,
            scope=install_scope,
            cli_records=cli_records,
            removed_skills=removed_skills,
            removed_assets=removed_assets,
            installed_paths=[],
            installed_asset_paths=[],
        )
    installed_paths = []
    if any(node.type == "skill" for node in lockfile.nodes):
        installed_paths = apply_skill_lockfile(repo_root_for_target, config, lockfile, target_dir, runtime_id, offline)
    installed_asset_paths = apply_managed_asset_lockfile(lockfile, target_dir, runtime_id)
    if install_scope == "project":
        removed_skills = prune_orphaned_project_skills(
            target_dir,
            runtime_id,
            desired_skill_ids,
            prune_scope_skill_ids,
        )
        removed_assets = prune_orphaned_project_managed_assets(
            target_dir,
            runtime_id,
            desired_managed_assets,
            prune_scope_managed_assets,
        )
    # 注入 agents_md_inject 内容到项目 AGENTS.md（幂等更新 + 卸载自动清除）
    if install_scope == "project":
        apply_agents_md_injections(lockfile, manifest_path.parent)
    cli_outputs = install_cli_packages(cli_records, config, upgrade=cli_upgrade, dry_run=False)

    # 多 runtime 扇出：从 canonical .agents 同步到所有已发现的 runtime 目录
    multi_runtime_results: dict[str, list[Path]] = {}
    if install_scope == "project":
        project_root = manifest_path.parent
        # 确定要同步的目标 runtime 列表
        sync_targets = getattr(manifest, "sync_targets", None)
        if sync_targets:
            if sync_targets == ["all"]:
                discovered = list(RUNTIME_PROFILES.keys())
            else:
                discovered = list(sync_targets)
        else:
            discovered = discover_available_runtimes(project_root)

        for secondary_runtime in discovered:
            if secondary_runtime == runtime_id:
                continue  # 跳过主 runtime（已安装）
            try:
                secondary_profile = runtime_profile(secondary_runtime)
            except ValueError:
                continue
            if secondary_profile.install_mode != "skill_dir":
                continue  # 暂只扇出 skill_dir 模式（跳过 kiro/cursor wrapper）
            try:
                secondary_target = _runtime_resolve_target_dir(
                    project_root, None, cwd=project_root,
                    runtime_id=secondary_runtime, scope=install_scope,
                )
            except ValueError:
                continue
            if not secondary_target.exists():
                continue  # 不创建不存在的目录
            fanout_paths = fanout_canonical_to_runtime(
                canonical_dir=target_dir,
                target_dir=secondary_target,
                desired_skill_ids=desired_skill_ids,
                managed_skill_ids=prune_scope_skill_ids,
            )
            if fanout_paths:
                multi_runtime_results[secondary_runtime] = fanout_paths

    elif install_scope == "global":
        # Global fan-out: only when --all-runtimes or sync_targets is set
        global_sync_targets = getattr(manifest, "sync_targets", None)
        should_fanout = global_sync_targets and len(global_sync_targets) > 0
        if should_fanout:
            # Copy from ~/.agents/skills/ (canonical global) to each runtime's global_target
            from harness_ai_kit.infrastructure.config_io import default_home_dir
            base_home = default_home_dir().resolve()
            for secondary_runtime, secondary_profile in RUNTIME_PROFILES.items():
                if not secondary_profile.global_target:
                    continue  # 跳过无全局路径的 runtime
                if secondary_profile.install_mode != "skill_dir":
                    continue  # 暂只扇出 skill_dir 模式
                # Resolve runtime-specific global target directly from profile
                gt = secondary_profile.global_target
                if gt.startswith("~/"):
                    secondary_target = (base_home / gt[2:]).resolve()
                else:
                    secondary_target = Path(gt).expanduser().resolve()
                # Skip if it's the same as the canonical dir
                if secondary_target == target_dir:
                    continue
                # 确保目标目录存在
                secondary_target.mkdir(parents=True, exist_ok=True)
                fanout_paths = fanout_canonical_to_runtime(
                    canonical_dir=target_dir,
                    target_dir=secondary_target,
                    desired_skill_ids=desired_skill_ids,
                    managed_skill_ids=None,
                )
                if fanout_paths:
                    multi_runtime_results[secondary_runtime] = fanout_paths

    return project_sync_results.base_project_sync_summary(
        lockfile=lockfile,
        lock_path=lock_path,
        target_dir=target_dir,
        runtime=runtime_id,
        scope=install_scope,
        cli_records=cli_records,
        cli_outputs=cli_outputs,
        removed_skills=removed_skills,
        removed_assets=removed_assets,
        installed_paths=installed_paths,
        installed_asset_paths=installed_asset_paths,
        multi_runtime_results=multi_runtime_results,
    )





def ensure_project_manifest(path: Path | None, manifest: ProjectManifest | None, *, runtime: str, scope: str) -> tuple[Path, ProjectManifest]:
    if path is not None and manifest is not None:
        return path, manifest
    manifest_path = project_manifest_path(Path.cwd())
    manifest = ProjectManifest(schema_version=PROJECT_MANIFEST_SCHEMA_VERSION, runtime=runtime, scope=scope)
    save_project_manifest(manifest_path, manifest)
    return manifest_path, manifest




def add_skill_to_manifest(manifest: ProjectManifest, spec: ProjectRootSpec) -> bool:
    return project_manifest_state.add_skill_to_manifest(manifest, spec)




def add_versioned_asset_to_manifest(items: list[ProjectVersionedAssetSpec], spec: ProjectVersionedAssetSpec) -> bool:
    return project_manifest_state.add_versioned_asset_to_manifest(items, spec)




def manifest_bucket_for_asset(manifest: ProjectManifest, asset_kind: str) -> list[ProjectVersionedAssetSpec] | list[ProjectRootSpec]:
    return project_manifest_state.manifest_bucket_for_asset(manifest, asset_kind)




def remove_asset_from_manifest(manifest: ProjectManifest, asset_kind: str, asset_id: str) -> bool:
    return project_manifest_state.remove_asset_from_manifest(manifest, asset_kind, asset_id)




def project_sync_skill_preview_items(summary: dict[str, Any]) -> list[tuple[pm.LockNode, Path, str, str]]:
    return [
        (
            node,
            runtime_install_destination(summary["target_dir"], node.id, summary["runtime"]),
            summary["runtime"],
            summary["scope"],
        )
        for node in pm.topological_skill_nodes_from_lock(summary["lockfile"])
    ]




def project_sync_managed_preview_items(summary: dict[str, Any]) -> list[tuple[pm.LockNode, Path]]:
    return [
        (
            node,
            managed_asset_install_destination(summary["target_dir"], node.type, node.id, summary["runtime"]),
        )
        for node in summary["lockfile"].nodes
        if node.type in {"plugin", "hook", "subagent", "mcp", "loop"}
    ]




def print_project_sync_dry_run_summary(summary: dict[str, Any], *, external_dependency_lines: Sequence[str] = ()) -> None:
    for line in project_sync_presentation.project_sync_dry_run_lines(
        skill_items=project_sync_skill_preview_items(summary),
        cli_records=summary["cli_records"],
        managed_items=project_sync_managed_preview_items(summary),
        removed_skills=summary["removed_skills"],
        removed_assets=summary["removed_assets"],
        external_dependency_lines=external_dependency_lines,
    ):
        print(line)
    print_non_skill_requirements(summary["lockfile"])
    print(project_sync_presentation.project_sync_lockfile_line(summary["lock_path"], dry_run=True))




def print_project_sync_applied_summary(
    summary: dict[str, Any],
    *,
    action: str = "synced",
    external_dependency_lines: Sequence[str] = (),
) -> None:
    skill_items = [
        (node, destination, manual_invocation_hint(summary["runtime"], node.id))
        for node, destination in zip(pm.topological_skill_nodes_from_lock(summary["lockfile"]), summary["installed_paths"])
    ]
    cli_items = list(zip(summary.get("cli_records", []), summary.get("cli_outputs", [])))
    for line in project_sync_presentation.project_sync_applied_lines(
        skill_items=skill_items,
        cli_items=cli_items,
        managed_items=summary.get("installed_asset_paths", []),
        removed_skills=summary.get("removed_skills", []),
        removed_assets=summary.get("removed_assets", []),
        action=action,
        external_dependency_lines=external_dependency_lines,
    ):
        print(line)
    print_non_skill_requirements(summary["lockfile"])
    print(project_sync_presentation.project_sync_lockfile_line(summary["lock_path"], dry_run=False))




def standalone_install_skill_preview_items(lockfile: pm.Lockfile, target_dir: Path, runtime_id: str, install_scope: str) -> list[tuple[pm.LockNode, Path, str, str]]:
    return [
        (
            node,
            runtime_install_destination(target_dir, node.id, runtime_id),
            runtime_id,
            install_scope,
        )
        for node in pm.topological_skill_nodes_from_lock(lockfile)
    ]




def standalone_install_managed_preview_items(lockfile: pm.Lockfile, target_dir: Path, runtime_id: str) -> list[tuple[pm.LockNode, Path]]:
    return [
        (
            node,
            managed_asset_install_destination(target_dir, node.type, node.id, runtime_id),
        )
        for node in lockfile.nodes
        if node.type in {"plugin", "hook", "subagent", "mcp", "loop"}
    ]




def standalone_install_should_initialize_manifest(
    *,
    manifest: ProjectManifest | None,
    install_scope: str,
    asset_ids: Sequence[str],
    install_all: bool,
) -> bool:
    return manifest is None and install_scope == "project" and bool(asset_ids) and not install_all


_EXPORTED_COMMAND_HANDLER_NAMES = [
    'command_diff', 'command_doctor', 'command_outdated', 'command_prune',
    'command_publish', 'command_publish_cli', 'command_publish_skill',
    'command_release', 'command_sync', 'command_uninstall', 'command_upgrade',
    'command_validate',
]
__all__ = [name for name in globals() if not name.startswith('_') and name not in _EXPORTED_COMMAND_HANDLER_NAMES]




