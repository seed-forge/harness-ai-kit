"""Dependency expansion and CLI version tracking utilities."""
from __future__ import annotations

import importlib.metadata
import json
from pathlib import Path
from typing import Any, Iterable, Sequence

from ai_kit import package_manager as pm
from ai_kit.domain.models import CliConfig, SkillRecord
from ai_kit.domain.inventory import (
    load_cli_inventory,
    load_combined_cli_inventory,
    load_skill_metadata,
)
from ai_kit.infrastructure.config_io import pyproject_path, read_project_version
from ai_kit.infrastructure.http_client import http_request, registry_auth_headers
from ai_kit.infrastructure.registry_cli import load_cli_registry_index
from ai_kit.product import active_product_profile


SELF_CLI_PACKAGE_NAME = active_product_profile().self_cli_package_name


def ordered_unique(values: Iterable[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        item = str(value).strip()
        if not item or item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def skill_dependency_payload(metadata: dict[str, object]) -> dict[str, object]:
    manifest = pm.SkillManifest.model_validate(metadata)
    return pm.dependency_summary(manifest)


def expand_skill_ids_with_dependencies(
    inventory: dict[str, SkillRecord],
    requested_ids: Sequence[str],
    include_recommended: bool = False,
    config: CliConfig | None = None,
) -> tuple[list[str], list[str], dict[str, str]]:
    from ai_kit.infrastructure.registry_skill import download_skill_metadata

    ordered_ids: list[str] = []
    queued_ids = list(requested_ids)
    seen: set[str] = set()
    recommended_only: list[str] = []
    registry_versions: dict[str, str] = {}
    metadata_cache: dict[str, dict[str, object] | None] = {}

    while queued_ids:
        skill_id = queued_ids.pop(0)
        if skill_id in seen:
            continue
        seen.add(skill_id)
        ordered_ids.append(skill_id)

        record = inventory.get(skill_id)
        metadata: dict[str, object] | None = metadata_cache.get(skill_id)
        if metadata is None:
            if record is not None:
                metadata = load_skill_metadata(record.path)
            elif config and config.skill_registry_index_url:
                metadata, resolved_version = download_skill_metadata(config, skill_id)
                registry_versions[skill_id] = resolved_version
            metadata_cache[skill_id] = metadata
        if metadata is None:
            continue

        dependencies = skill_dependency_payload(metadata)
        queued_ids.extend(dependencies["required_skills"])
        if include_recommended:
            queued_ids.extend(dependencies["recommended_skills"])
        else:
            for dependency_id in dependencies["recommended_skills"]:
                if dependency_id not in seen and dependency_id not in recommended_only:
                    recommended_only.append(dependency_id)

    return ordered_ids, recommended_only, registry_versions


def dependency_followups(skill_dirs: Sequence[Path]) -> dict[str, list[str]]:
    required_clis: list[str] = []
    recommended_clis: list[str] = []
    required_mcps: list[str] = []
    recommended_mcps: list[str] = []
    notes: list[str] = []

    for skill_dir in skill_dirs:
        dependencies = skill_dependency_payload(load_skill_metadata(skill_dir))
        required_clis.extend(item["id"] for item in dependencies["clis"]["required"])
        recommended_clis.extend(item["id"] for item in dependencies["clis"]["optional"])
        required_mcps.extend(item["id"] for item in dependencies["mcps"]["required"])
        recommended_mcps.extend(item["id"] for item in dependencies["mcps"]["optional"])
        notes.extend(dependencies["runtime_requirements"])
        notes.extend(dependencies["post_install_hints"])

    return {
        "required_clis": ordered_unique(required_clis),
        "recommended_clis": ordered_unique(recommended_clis),
        "required_mcps": ordered_unique(required_mcps),
        "recommended_mcps": ordered_unique(recommended_mcps),
        "notes": ordered_unique(notes),
    }


def _load_cli_versions_from_index(config: CliConfig) -> dict[str, str]:
    """Fast-path: extract CLI id→version from the index JSON only (1 HTTP request, no per-CLI metadata fetch)."""
    import urllib.error
    try:
        index_payload = load_cli_registry_index(config)
    except (urllib.error.URLError, urllib.error.HTTPError):
        return {}
    # Defensive: handle both {"clis": [...]} (expected) and [{"clis": [...]}] (legacy list wrap)
    if isinstance(index_payload, list):
        clis_items: list[dict] = []
        for chunk in index_payload:
            if isinstance(chunk, dict):
                clis_items.extend(chunk.get("clis", []))
    elif isinstance(index_payload, dict):
        clis_items = list(index_payload.get("clis", []))
    else:
        clis_items = []
    versions: dict[str, str] = {}
    for item in clis_items:
        cli_id = str(item.get("id", "")).strip()
        latest_version = str(item.get("latest_version", "")).strip()
        if cli_id and latest_version:
            versions[cli_id] = latest_version
    return versions


def current_cli_versions(repo_root: Path | None, config: CliConfig | None = None) -> dict[str, str]:
    """Return a mapping of CLI id → latest version.

    Uses the lightweight index-only path first (1 HTTP request) for resolution
    commands that only need version numbers.  Falls back to the full inventory
    (N+1 HTTP requests) only when the index is unavailable.
    """
    import urllib.error

    versions: dict[str, str] = {}

    # Fast-path: local repo inventory (no network).
    if repo_root is not None:
        local_inv = load_cli_inventory(repo_root)
        versions.update({r.cli_id: r.version for r in local_inv.values()})

    # Fast-path: index-only (1 HTTP call vs 31 per-CLI metadata calls).
    if config is not None and config.cli_registry_index_url.strip():
        index_versions = _load_cli_versions_from_index(config)
        for cli_id, ver in index_versions.items():
            versions.setdefault(cli_id, ver)

    # Self-CLI version from pyproject or installed package.
    if repo_root is not None:
        project_file = pyproject_path(repo_root)
        if project_file.exists():
            versions.setdefault(SELF_CLI_PACKAGE_NAME, read_project_version(project_file))
    try:
        versions.setdefault(SELF_CLI_PACKAGE_NAME, importlib.metadata.version(SELF_CLI_PACKAGE_NAME))
    except importlib.metadata.PackageNotFoundError:
        pass
    return versions


def sync_cli_metadata_versions(repo_root: Path, package_name: str, version: str) -> None:
    for record in load_cli_inventory(repo_root).values():
        if record.package_name != package_name or record.path is None:
            continue
        metadata_path = record.path / "cli.json"
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        payload["version"] = version
        metadata_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
