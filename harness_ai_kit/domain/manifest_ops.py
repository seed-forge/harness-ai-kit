"""Project manifest operations: loading, querying, feature selection."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

import yaml

from harness_ai_kit import package_manager as pm
from harness_ai_kit.domain.models import (
    PROJECT_MANIFEST_SCHEMA_VERSION,
    ProjectManifest, ProjectManifestAssets,
    ProjectRootSpec, ProjectVersionedAssetSpec,
)
from harness_ai_kit.domain import project_manifest_state
from harness_ai_kit.product import active_product_profile


def project_manifest_path(base_dir: Path) -> Path:
    return base_dir.resolve() / active_product_profile().project_manifest_filename




def find_project_manifest(start_dir: Path | None = None) -> Path | None:
    current = (start_dir or Path.cwd()).resolve()
    for probe in [current, *current.parents]:
        candidate = project_manifest_path(probe)
        if candidate.exists():
            return candidate
    return None




def find_project_lockfile(start_dir: Path | None = None) -> Path | None:
    current = (start_dir or Path.cwd()).resolve()
    for probe in [current, *current.parents]:
        candidate = pm.lockfile_path(probe)
        if candidate.exists():
            return candidate
    return None




def load_project_manifest(path: Path) -> ProjectManifest:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"Project manifest must be a YAML mapping: {path}")
    return ProjectManifest.model_validate(payload)




def load_project_manifest_if_present(start_dir: Path | None = None) -> tuple[Path | None, ProjectManifest | None]:
    manifest_path = find_project_manifest(start_dir)
    if manifest_path is None:
        return None, None
    return manifest_path, load_project_manifest(manifest_path)




def project_manifest_from_lockfile(lockfile: pm.Lockfile) -> ProjectManifest:
    return project_manifest_state.project_manifest_from_lockfile(
        lockfile,
        create_manifest=lambda runtime, scope, features: ProjectManifest(
            schema_version=PROJECT_MANIFEST_SCHEMA_VERSION,
            runtime=runtime,
            scope=scope,
            features=features,
        ),
        create_root_spec=lambda namespace, skill_id, features, sources, source_ref, ref, subpath, version: ProjectRootSpec(
            namespace=namespace,
            id=skill_id,
            features=features,
            sources=sources,
            source_ref=source_ref,
            ref=ref,
            subpath=subpath,
            version=version,
        ),
        create_versioned_spec=lambda namespace, asset_id, version: ProjectVersionedAssetSpec(
            namespace=namespace,
            id=asset_id,
            version=version,
        ),
    )




def bootstrap_project_manifest_from_lockfile(manifest_path: Path, lockfile: pm.Lockfile) -> ProjectManifest:
    manifest = project_manifest_from_lockfile(lockfile)
    save_project_manifest(manifest_path, manifest)
    return manifest




def infer_project_root_from_target_dir(target_dir: str | Path | None) -> Path | None:
    if not target_dir:
        return None
    candidate = target_dir if isinstance(target_dir, Path) else Path(target_dir)
    candidate = (candidate if candidate.is_absolute() else Path.cwd() / candidate).resolve()
    if candidate.name == "skills" and candidate.parent.name in {".agents", ".claude"}:
        return candidate.parent.parent
    if candidate.name in {"steering", "rules"} and candidate.parent.name in {".kiro", ".cursor"}:
        return candidate.parent.parent
    return candidate




def load_contextual_project_manifest(target_dir: str | Path | None = None) -> tuple[Path | None, ProjectManifest | None]:
    project_root = infer_project_root_from_target_dir(target_dir)
    if project_root is not None:
        manifest_path = project_manifest_path(project_root)
        if manifest_path.exists():
            return manifest_path, load_project_manifest(manifest_path)
        return None, None
    return load_project_manifest_if_present()




def declared_skill_specs(manifest: ProjectManifest) -> list[ProjectRootSpec]:
    return project_manifest_state.declared_skill_specs(manifest)




def declared_cli_specs(manifest: ProjectManifest) -> list[ProjectVersionedAssetSpec]:
    return project_manifest_state.declared_versioned_specs(manifest, "cli")




def declared_plugin_specs(manifest: ProjectManifest) -> list[ProjectVersionedAssetSpec]:
    return project_manifest_state.declared_versioned_specs(manifest, "plugin")




def declared_hook_specs(manifest: ProjectManifest) -> list[ProjectVersionedAssetSpec]:
    return project_manifest_state.declared_versioned_specs(manifest, "hook")




def declared_subagent_specs(manifest: ProjectManifest) -> list[ProjectVersionedAssetSpec]:
    return project_manifest_state.declared_versioned_specs(manifest, "subagent")




def declared_mcp_specs(manifest: ProjectManifest) -> list[ProjectVersionedAssetSpec]:
    return project_manifest_state.declared_versioned_specs(manifest, "mcp")




def declared_loop_specs(manifest: ProjectManifest) -> list[ProjectVersionedAssetSpec]:
    return project_manifest_state.declared_versioned_specs(manifest, "loop")




def manifest_has_declared_assets(manifest: ProjectManifest) -> bool:
    return project_manifest_state.manifest_has_declared_assets(manifest)




def project_root_ids(manifest: ProjectManifest) -> list[str]:
    return project_manifest_state.project_root_ids(manifest)




def manifest_declared_features(manifest: ProjectManifest) -> list[str]:
    return project_manifest_state.manifest_declared_features(manifest)




def manifest_skill_source_policy(manifest: ProjectManifest) -> list[str] | None:
    specs = declared_skill_specs(manifest)
    explicit_policies = [list(item.sources) for item in specs if item.sources]
    if not explicit_policies:
        return None
    if len(explicit_policies) != len(specs):
        return None
    first = explicit_policies[0]
    if any(policy != first for policy in explicit_policies[1:]):
        return None
    return first




def manifest_skill_root_sources(manifest: ProjectManifest) -> dict[str, tuple[str, str | None, str | None]]:
    root_sources: dict[str, tuple[str, str | None, str | None]] = {}
    for item in declared_skill_specs(manifest):
        if not item.source_ref:
            continue
        key = pm.canonical_package_id(item.id, item.namespace)
        root_sources[key] = (item.source_ref, item.ref, item.subpath)
    return root_sources




def manifest_skill_version_specifiers(manifest: ProjectManifest) -> dict[str, str]:
    specifiers: dict[str, str] = {}
    for item in declared_skill_specs(manifest):
        if not item.version:
            continue
        key = pm.canonical_package_id(item.id, item.namespace)
        specifiers[key] = item.version
    return specifiers




def project_manifest_root_requests(manifest: ProjectManifest) -> list[pm.RootRequest]:
    return project_manifest_state.project_manifest_root_requests(manifest)




def explicit_feature_selection(args: argparse.Namespace, manifest: ProjectManifest | None = None) -> list[str]:
    features = list(getattr(args, "feature", []))
    if not features and manifest is not None:
        features = manifest_declared_features(manifest)
    if getattr(args, "with_recommended", False):
        features.append("recommended")
    deduped: list[str] = []
    for item in features:
        feature = str(item).strip()
        if feature and feature not in deduped:
            deduped.append(feature)
    return deduped




def detect_current_runtime() -> str | None:
    """从环境变量检测当前 runtime。"""
    env_map = {
        "CLAUDE_CODE": "claude-code",
        "CODEX_HOME": "codex",
        "OPENAI_CODEX": "codex",
        "CURSOR_TRACE_ID": "cursor",
        "CURSOR_SESSION": "cursor",
        "KIRO_SESSION": "kiro",
        "OPENCODE_SESSION": "opencode",
        "QODER_SESSION": "qoder",
    }
    for env_var, runtime_id in env_map.items():
        if os.environ.get(env_var):
            return runtime_id
    return None




def manifest_aware_runtime(args: argparse.Namespace, manifest: ProjectManifest | None = None) -> str:
    explicit = getattr(args, "runtime", None)
    if explicit:
        return explicit
    detected = detect_current_runtime()
    if detected:
        return detected
    if manifest is not None:
        return manifest.runtime
    return "codex"




def manifest_aware_scope(args: argparse.Namespace, manifest: ProjectManifest | None = None) -> str:
    explicit = getattr(args, "scope", None)
    if explicit:
        return explicit
    if manifest is not None:
        return manifest.scope
    return "project"




def validate_sync_selection(args: argparse.Namespace, has_manifest: bool = False) -> None:
    skill_ids = list(getattr(args, "skill_ids", []))
    install_all = bool(getattr(args, "all", False))
    if install_all and skill_ids:
        raise ValueError("`--all` cannot be combined with explicit skill or CLI ids.")
    if not install_all and not skill_ids and not has_manifest:
        raise ValueError("Specify one or more skill/CLI ids, or pass `--all`. Alternatively, create ai-kit.yml.")




def project_lock_path_for_manifest(manifest_path: Path | None, target_dir: Path | None, scope: str) -> Path:
    from harness_ai_kit.application.project_sync import resolve_lock_path
    if scope == "project" and manifest_path is not None:
        return pm.lockfile_path(manifest_path.parent)
    return resolve_lock_path(target_dir, scope)


def parse_project_root_ref(value: str) -> ProjectRootSpec:
    if pm.is_git_source_selector(value):
        return ProjectRootSpec.model_validate(value)
    namespace, root_id = pm.split_canonical_id(value)
    return ProjectRootSpec(namespace=namespace, id=root_id)


def skill_manifest_item_payload(item: ProjectRootSpec) -> dict[str, object]:
    payload = {"id": item.id}
    if item.namespace:
        payload["namespace"] = item.namespace
    if item.features:
        payload["features"] = list(item.features)
    if item.sources:
        payload["sources"] = list(item.sources)
    if item.source_ref:
        payload["source_ref"] = item.source_ref
    if item.ref:
        payload["ref"] = item.ref
    if item.subpath:
        payload["subpath"] = item.subpath
    if item.version:
        payload["version"] = item.version
    return payload


def versioned_manifest_item_payload(item: ProjectVersionedAssetSpec) -> dict[str, object]:
    payload = {"id": item.id, "version": item.version}
    if item.namespace:
        payload["namespace"] = item.namespace
    return payload


def project_manifest_payload(manifest: ProjectManifest) -> dict[str, object]:
    return {
        "schema_version": PROJECT_MANIFEST_SCHEMA_VERSION,
        "runtime": manifest.runtime,
        "scope": manifest.scope,
        "features": list(manifest.features),
        "assets": {
            "skills": [skill_manifest_item_payload(item) for item in declared_skill_specs(manifest)],
            "clis": [versioned_manifest_item_payload(item) for item in declared_cli_specs(manifest)],
            "plugins": [versioned_manifest_item_payload(item) for item in declared_plugin_specs(manifest)],
            "hooks": [versioned_manifest_item_payload(item) for item in declared_hook_specs(manifest)],
            "subagents": [versioned_manifest_item_payload(item) for item in declared_subagent_specs(manifest)],
            "mcps": [versioned_manifest_item_payload(item) for item in declared_mcp_specs(manifest)],
            "loops": [versioned_manifest_item_payload(item) for item in declared_loop_specs(manifest)],
        },
    }


def save_project_manifest(manifest_path: Path, manifest: ProjectManifest) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        yaml.safe_dump(project_manifest_payload(manifest), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )




