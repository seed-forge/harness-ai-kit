"""Install state queries, drift evaluation, and runtime install helpers."""
from __future__ import annotations

import importlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

from ai_kit import package_manager as pm
from ai_kit.domain.models import (
    ASSET_DIRECTORY_NAMES, CliAssetRecord, CliConfig, CliInstallState,
    InstalledManagedAssetLocation, InstalledSkillLocation,
    ManagedAssetInstallState, SkillInstallState, SkillRecord,
)
from ai_kit.domain.models.constants import MANAGED_ASSET_TYPES
from ai_kit.domain import materialization
from ai_kit.domain import managed_install
from ai_kit.domain import project_state
from ai_kit.domain import runtime_install
from ai_kit.domain.dependency_expansion import ordered_unique
from ai_kit.domain.runtime_install import RUNTIME_PROFILES, resolve_target_dir, runtime_profile
from ai_kit.domain.inventory import load_skill_metadata, skill_entry_text
from ai_kit.domain.versions import parse_version_from_text, upgrade_status_for_versions
from ai_kit.infrastructure.config_io import default_home_dir, default_repo_root
from ai_kit.product import active_product_profile
from pydantic import ValidationError

ACTIVE_PRODUCT_PROFILE = active_product_profile()
RUNTIME_SKILL_BUNDLE_ROOT = ACTIVE_PRODUCT_PROFILE.runtime_skill_bundle_root


def _runtime_wrapper_prefix() -> str:
    return active_product_profile().runtime_wrapper_prefix


def runtime_managed_asset_root(target_dir: Path, runtime_id: str) -> Path:
    return runtime_install.runtime_managed_asset_root(target_dir)




def runtime_install_destination(target_dir: Path, skill_id: str, runtime_id: str) -> Path:
    return runtime_install.runtime_install_destination(target_dir, skill_id, runtime_id)




def manual_invocation_hint(runtime_id: str, skill_id: str) -> str:
    if runtime_id == "codex":
        return f"In Codex, prefer `${skill_id}` or natural-language requests; do not expect `/{skill_id}`."
    if runtime_id == "claude-code":
        return f"In Claude Code, describe the task or reference `{skill_id}` explicitly after opening a fresh session."
    if runtime_id == "kiro":
        return f"In Kiro, the installed steering file shapes behavior automatically; it is not a slash command."
    if runtime_id == "cursor":
        return f"In Cursor, the installed rule file guides the agent automatically; it is not a slash command."
    return f"Open a fresh session and reference `{skill_id}` explicitly."




def installed_skill_ids(target_dir: Path, runtime_id: str) -> list[str]:
    profile = runtime_profile(runtime_id)
    if not target_dir.exists():
        return []

    if profile.install_mode == "skill_dir":
        return sorted(
            child.name
            for child in target_dir.iterdir()
            if child.is_dir() and (child / "SKILL.md").exists()
        )

    if profile.install_mode == "kiro_steering":
        prefix = f"{_runtime_wrapper_prefix()}-"
        return sorted(
            path.stem[len(prefix):]
            for path in target_dir.glob(f"{prefix}*.md")
            if path.is_file() and path.stem.startswith(prefix)
        )

    if profile.install_mode == "cursor_rule":
        prefix = f"{_runtime_wrapper_prefix()}-"
        return sorted(
            path.stem[len(prefix):]
            for path in target_dir.glob(f"{prefix}*.mdc")
            if path.is_file() and path.stem.startswith(prefix)
        )

    return []




def managed_asset_install_destination(target_dir: Path, asset_type: str, asset_id: str, runtime_id: str) -> Path:
    return runtime_install.managed_asset_install_destination(target_dir, asset_type, asset_id, ASSET_DIRECTORY_NAMES)




def installed_managed_asset_ids(target_dir: Path, asset_type: str, runtime_id: str) -> list[str]:
    asset_root = runtime_managed_asset_root(target_dir, runtime_id) / ASSET_DIRECTORY_NAMES[asset_type]
    if not asset_root.exists():
        return []
    metadata_name = pm.manifest_metadata_filename(asset_type)
    return sorted(child.name for child in asset_root.iterdir() if child.is_dir() and (child / metadata_name).exists())




def installed_managed_asset_version(target_dir: Path, asset_type: str, asset_id: str, runtime_id: str) -> str:
    destination = managed_asset_install_destination(target_dir, asset_type, asset_id, runtime_id)
    try:
        return str(load_skill_metadata(destination).get("version", ""))
    except (FileNotFoundError, KeyError, json.JSONDecodeError, ValidationError):
        return ""




def installed_skill_locations(
    repo_root: Path | None,
    runtime_id: str,
    home_dir: Path | None = None,
) -> list[tuple[str, Path]]:
    locations: list[tuple[str, Path]] = []
    profile = runtime_profile(runtime_id)

    if repo_root and profile.project_target:
        if runtime_id == "codex":
            project_target = (repo_root / ".agents" / "skills").resolve()
        else:
            project_target = (repo_root / profile.project_target).resolve()
        locations.append(("project", project_target))

    if profile.global_target:
        base_home = home_dir or default_home_dir()
        global_dir = resolve_target_dir(
            repo_root or default_repo_root(),
            None,
            cwd=repo_root or default_repo_root(),
            runtime_id=runtime_id,
            scope="global",
            home_dir=base_home,
        )
        locations.append(("global", global_dir))

    return locations




def installed_skill_payload_dir(target_dir: Path, skill_id: str, runtime_id: str) -> Path:
    return runtime_install.installed_skill_payload_dir(target_dir, skill_id, runtime_id)




def installed_skill_version(target_dir: Path, skill_id: str, runtime_id: str) -> str:
    skill_dir = installed_skill_payload_dir(target_dir, skill_id, runtime_id)
    metadata_path = skill_dir / "skill.json"
    if not metadata_path.exists():
        return ""
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    return str(metadata.get("version", "")).strip()




def effective_source_checksum(node: pm.LockNode) -> str:
    return materialization.effective_source_checksum(node)




def effective_materialized_checksum(node: pm.LockNode, runtime_id: str) -> str:
    return materialization.effective_materialized_checksum(node, runtime_profile(runtime_id).install_mode)




def hash_directory_with_root(path: Path, root_name: str) -> str:
    return materialization.hash_directory_with_root(path, root_name)




def source_materialized_checksum(asset_dir: Path, asset_id: str, runtime_id: str, asset_type: str) -> str:
    profile = runtime_profile(runtime_id)
    destination_name = runtime_install_destination(Path("."), asset_id, runtime_id).name
    wrapper_content = None
    if profile.install_mode == "kiro_steering":
        wrapper_content = render_kiro_steering(asset_dir).encode("utf-8")
    elif profile.install_mode == "cursor_rule":
        wrapper_content = render_cursor_rule(asset_dir).encode("utf-8")
    return materialization.source_materialized_checksum(
        asset_dir,
        asset_id,
        install_mode=profile.install_mode,
        asset_type=asset_type,
        wrapper_name=destination_name,
        wrapper_content=wrapper_content,
    )




def installed_skill_materialized_checksum(target_dir: Path, skill_id: str, runtime_id: str) -> str:
    profile = runtime_profile(runtime_id)
    payload_dir = installed_skill_payload_dir(target_dir, skill_id, runtime_id)
    wrapper_path = None if profile.install_mode == "skill_dir" else runtime_install_destination(target_dir, skill_id, runtime_id)
    return materialization.installed_skill_materialized_checksum(
        payload_dir,
        skill_id,
        install_mode=profile.install_mode,
        wrapper_path=wrapper_path,
    )




def installed_managed_asset_materialized_checksum(target_dir: Path, asset_type: str, asset_id: str, runtime_id: str) -> str:
    destination = managed_asset_install_destination(target_dir, asset_type, asset_id, runtime_id)
    return materialization.installed_managed_asset_materialized_checksum(destination, asset_id)




def current_source_checksum_for_node(node: pm.LockNode, runtime_id: str) -> str:
    return materialization.current_source_checksum_for_node(node)




def current_materialized_checksum_for_node(node: pm.LockNode, runtime_id: str) -> str:
    if node.source not in {pm.SOURCE_REPO, pm.SOURCE_GIT_REPO} or not node.source_ref:
        return ""
    source_path = Path(node.source_ref)
    if not source_path.exists():
        return ""
    return source_materialized_checksum(source_path, node.id, runtime_id, node.type)




def evaluate_installed_asset_drift(
    *,
    node: pm.LockNode | None,
    runtime_id: str,
    installed_version: str,
    actual_materialized_checksum: str,
    current_source_checksum: str = "",
    current_materialized_checksum: str = "",
) -> tuple[str, str]:
    return materialization.evaluate_installed_asset_drift(
        node=node,
        install_mode=runtime_profile(runtime_id).install_mode,
        installed_version=installed_version,
        actual_materialized_checksum=actual_materialized_checksum,
        current_source_checksum=current_source_checksum,
        current_materialized_checksum=current_materialized_checksum,
    )




def worst_drift_status(statuses: Iterable[str]) -> str:
    return materialization.worst_drift_status(statuses)




def read_lockfile_if_present(path: Path) -> pm.Lockfile | None:
    if not path.exists():
        return None
    try:
        return pm.read_lockfile(path)
    except (OSError, ValidationError, json.JSONDecodeError, ValueError):
        return None




def companion_doc_requirements(entry_name: str, companion_docs: Mapping[str, Any], *, include_entry: bool = True) -> list[str]:
    required: list[str] = []
    if include_entry:
        required.append(str(entry_name or "SKILL.md").strip() or "SKILL.md")
    usage_name = str(companion_docs.get("usage", "USAGE.md")).strip() or "USAGE.md"
    required.append(usage_name)
    example_required = bool(companion_docs.get("example_required", False))
    if example_required:
        example_name = str(companion_docs.get("example", "EXAMPLE.md")).strip() or "EXAMPLE.md"
        required.append(example_name)
    return ordered_unique(required)




def payload_has_required_docs(payload_dir: Path, entry_name: str, companion_docs: Mapping[str, Any], *, include_entry: bool = True) -> bool:
    if not payload_dir.exists():
        return False
    for relative_name in companion_doc_requirements(entry_name, companion_docs, include_entry=include_entry):
        if not (payload_dir / relative_name).exists():
            return False
    return True




def skill_install_state(record: SkillRecord, repo_root: Path | None) -> SkillInstallState:
    from ai_kit.application.project_sync import resolve_lock_path
    installed_locations: list[InstalledSkillLocation] = []
    lock_cache: dict[tuple[Path, str], pm.Lockfile | None] = {}
    for runtime_id in RUNTIME_PROFILES:
        for scope_name, target_dir in installed_skill_locations(repo_root, runtime_id):
            if record.skill_id not in installed_skill_ids(target_dir, runtime_id):
                continue
            destination = runtime_install_destination(target_dir, record.skill_id, runtime_id)
            lock_key = (resolve_lock_path(target_dir, scope_name), scope_name)
            lockfile = lock_cache.setdefault(lock_key, read_lockfile_if_present(lock_key[0]))
            node = pm.find_lock_node(lockfile.nodes, "skill", record.skill_id) if lockfile is not None else None
            version = installed_skill_version(target_dir, record.skill_id, runtime_id)
            drift_status, drift_message = evaluate_installed_asset_drift(
                node=node,
                runtime_id=runtime_id,
                installed_version=version,
                actual_materialized_checksum=installed_skill_materialized_checksum(target_dir, record.skill_id, runtime_id),
                current_source_checksum=current_source_checksum_for_node(node, runtime_id) if node is not None else "",
                current_materialized_checksum=current_materialized_checksum_for_node(node, runtime_id) if node is not None else "",
            )
            installed_locations.append(
                InstalledSkillLocation(
                    runtime=runtime_id,
                    scope=scope_name,
                    path=destination,
                    version=version,
                    drift_status=drift_status,
                    drift_message=drift_message,
                )
            )
    installed, installed_versions, upgrade_status, drift_status = project_state.skill_install_summary(
        (location.version for location in installed_locations if location.version),
        record.version,
        (location.drift_status for location in installed_locations),
    )
    return SkillInstallState(
        installed=installed,
        installed_versions=installed_versions,
        installed_locations=tuple(installed_locations),
        upgrade_status=upgrade_status,
        drift_status=drift_status,
    )




def managed_asset_install_state(record: SkillRecord, repo_root: Path | None) -> ManagedAssetInstallState:
    from ai_kit.application.project_sync import resolve_lock_path
    installed_locations: list[InstalledManagedAssetLocation] = []
    lock_cache: dict[tuple[Path, str], pm.Lockfile | None] = {}
    for runtime_id in RUNTIME_PROFILES:
        for scope_name, target_dir in installed_skill_locations(repo_root, runtime_id):
            if record.skill_id not in installed_managed_asset_ids(target_dir, record.asset_type, runtime_id):
                continue
            destination = managed_asset_install_destination(target_dir, record.asset_type, record.skill_id, runtime_id)
            lock_key = (resolve_lock_path(target_dir, scope_name), scope_name)
            lockfile = lock_cache.setdefault(lock_key, read_lockfile_if_present(lock_key[0]))
            node = (
                pm.find_lock_node(lockfile.nodes, record.asset_type, record.skill_id)
                if lockfile is not None
                else None
            )
            version = installed_managed_asset_version(target_dir, record.asset_type, record.skill_id, runtime_id)
            drift_status, drift_message = evaluate_installed_asset_drift(
                node=node,
                runtime_id=runtime_id,
                installed_version=version,
                actual_materialized_checksum=installed_managed_asset_materialized_checksum(target_dir, record.asset_type, record.skill_id, runtime_id),
                current_source_checksum=current_source_checksum_for_node(node, runtime_id) if node is not None else "",
                current_materialized_checksum=current_materialized_checksum_for_node(node, runtime_id) if node is not None else "",
            )
            installed_locations.append(
                InstalledManagedAssetLocation(
                    runtime=runtime_id,
                    scope=scope_name,
                    path=destination,
                    version=version,
                    drift_status=drift_status,
                    drift_message=drift_message,
                )
            )
    installed, installed_versions, drift_status = project_state.managed_asset_install_summary(
        (location.version for location in installed_locations if location.version),
        (location.drift_status for location in installed_locations),
    )
    return ManagedAssetInstallState(
        installed=installed,
        installed_versions=installed_versions,
        installed_locations=tuple(installed_locations),
        drift_status=drift_status,
    )




def installed_cli_version(record: CliAssetRecord) -> str:
    if record.install_type == "python-package":
        try:
            return importlib.metadata.version(record.package_name)
        except importlib.metadata.PackageNotFoundError:
            return ""
    if record.install_type == "binary-release":
        try:
            result = subprocess.run(
                [record.command_name, "--version"],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except OSError:
            return ""
        if result.returncode != 0:
            return ""
        return parse_version_from_text(f"{result.stdout}\n{result.stderr}")
    return ""




def cli_install_state(record: CliAssetRecord) -> CliInstallState:
    version = installed_cli_version(record)
    installed = bool(version)
    if not installed and record.install_type not in {"python-package", "binary-release"}:
        return CliInstallState(installed=False, installed_version="", upgrade_status="unknown")
    return CliInstallState(
        installed=installed,
        installed_version=version,
        upgrade_status=upgrade_status_for_versions(version, record.version),
    )




def list_has_upgrade_available(
    skill_states: dict[str, SkillInstallState],
    cli_states: dict[str, CliInstallState],
    subject: str,
) -> bool:
    if subject not in {"cli", "clis"} and any(state.upgrade_status == "upgrade-available" for state in skill_states.values()):
        return True
    if subject not in {"skill", "skills"} and any(state.upgrade_status == "upgrade-available" for state in cli_states.values()):
        return True
    return False




def _extract_extends_attribution(skill_dir: Path) -> str | None:
    """Extract extends attribution from merged SKILL.md content.

    Returns a comma-separated attribution string like
    ``skill:team/base-skill@1.0.0 (prepend)``, or None if the skill
    has no extends edges.
    """
    try:
        _, entry_text = skill_entry_text(skill_dir)
    except (FileNotFoundError, KeyError):
        return None
    import re as _re
    matches = _re.findall(
        r"<!-- Extends: (.+?) -- Do not edit this line -->",
        entry_text,
    )
    if not matches:
        return None
    return ", ".join(matches)




def render_kiro_steering(skill_dir: Path) -> str:
    metadata = load_skill_metadata(skill_dir)
    skill_id = str(metadata["id"])
    name = str(metadata.get("name", skill_id))
    version = str(metadata.get("version", "0.0.0"))
    summary = str(metadata.get("summary", "")).strip() or f"Generated from {ACTIVE_PRODUCT_PROFILE.display_name} skill {skill_id}."
    extends_attr = _extract_extends_attribution(skill_dir)
    _, entry_text = skill_entry_text(skill_dir)
    extends_block = f"\n**Extended from**: {extends_attr}\n\n" if extends_attr else ""
    return (
        "---\n"
        "inclusion: auto\n"
        f"name: {_runtime_wrapper_prefix()}-{skill_id}\n"
        f"description: {summary}\n"
        "---\n\n"
        f"# {name}\n\n"
        f"Generated from `{ACTIVE_PRODUCT_PROFILE.command_name}` skill `{skill_id}@{version}` for Kiro steering.\n"
        f"{extends_block}"
        "## Original summary\n\n"
        f"{summary}\n\n"
        "## Instructions\n\n"
        f"{entry_text.rstrip()}\n\n"
        "## Supporting files\n\n"
        f"The original skill payload is stored under `../{RUNTIME_SKILL_BUNDLE_ROOT}/{skill_id}/`.\n"
    )




def render_cursor_rule(skill_dir: Path) -> str:
    metadata = load_skill_metadata(skill_dir)
    skill_id = str(metadata["id"])
    name = str(metadata.get("name", skill_id))
    version = str(metadata.get("version", "0.0.0"))
    summary = str(metadata.get("summary", "")).strip() or f"Generated from {ACTIVE_PRODUCT_PROFILE.display_name} skill {skill_id}."
    extends_attr = _extract_extends_attribution(skill_dir)
    _, entry_text = skill_entry_text(skill_dir)
    extends_yaml = f"extends_source: \"{extends_attr}\"\n" if extends_attr else ""
    return (
        "---\n"
        f"description: {summary}\n"
        "alwaysApply: false\n"
        f"{extends_yaml}"
        "---\n\n"
        f"# {name}\n\n"
        f"Generated from `{ACTIVE_PRODUCT_PROFILE.command_name}` skill `{skill_id}@{version}` for Cursor project rules.\n\n"
        "## When to use\n\n"
        f"{summary}\n\n"
        "## Instructions\n\n"
        f"{entry_text.rstrip()}\n\n"
        "## Supporting files\n\n"
        f"The original skill payload is stored under `../{RUNTIME_SKILL_BUNDLE_ROOT}/{skill_id}/`.\n"
    )




def install_skill_directory(
    skill_dir: Path,
    target_dir: Path,
    runtime_id: str,
    extends_edges: list[dict] | None = None,
    resolve_base_skill_md: Callable[[str], str | None] | None = None,
) -> Path:
    return runtime_install.install_skill_directory(
        skill_dir,
        target_dir,
        runtime_id,
        render_kiro_steering=render_kiro_steering,
        render_cursor_rule=render_cursor_rule,
        extends_edges=extends_edges,
        resolve_base_skill_md=resolve_base_skill_md,
    )




def sync_records(records: list[SkillRecord], target_dir: Path, runtime_id: str = "codex") -> list[Path]:
    synced_paths: list[Path] = []
    for record in records:
        synced_paths.append(install_skill_directory(record.path, target_dir, runtime_id))
    return synced_paths




def install_managed_asset_directory(asset_dir: Path, target_dir: Path, runtime_id: str) -> Path:
    return managed_install.install_managed_asset_directory(asset_dir, target_dir, runtime_id, ASSET_DIRECTORY_NAMES)




