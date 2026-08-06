"""Asset inventory loading and record construction."""
from __future__ import annotations

import io
import json
import os
import re
import time
import urllib.error
import zipfile
from pathlib import Path
from typing import Any, Iterable

from ai_kit import package_manager as pm
from ai_kit.domain import cli_assets
from ai_kit.domain.models import (
    ASSET_DIRECTORY_NAMES, REFERENCE_DOC_RE, REQUIRED_CLI_FIELDS, REQUIRED_SKILL_FIELDS,
    USAGE_PROMPT_CJK_RE, USAGE_PROMPT_SECTION_RE,
    CliAssetRecord, CliConfig, ProjectRootSpec,
    ProjectVersionedAssetSpec, SkillRecord,
)
from ai_kit.infrastructure.http_client import (
    http_request, registry_auth_headers, skill_registry_headers, slash_join,
)
from ai_kit.infrastructure.config_io import read_json_file
from ai_kit.infrastructure.registry_cli import cli_registry_metadata_url, load_cli_registry_index, normalize_cli_versions
from ai_kit.infrastructure.registry_skill import download_skill_metadata, load_skill_registry_index, registry_skill_metadata_url


def skill_record_from_payload(
    metadata: dict[str, object],
    *,
    path: Path | None,
    source: str,
    metadata_url: str = "",
) -> SkillRecord:
    manifest = pm.SkillManifest.model_validate(metadata)
    return SkillRecord(
        skill_id=manifest.id,
        path=path,
        name=manifest.name,
        status=manifest.status,
        owner=manifest.owner,
        version=manifest.version,
        summary=manifest.summary,
        source=source,
        metadata_url=metadata_url,
        asset_type=manifest.package_type,
    )




def load_skill_record(skill_dir: Path) -> SkillRecord:
    return skill_record_from_payload(
        json.loads(pm.manifest_metadata_path(skill_dir).read_text(encoding="utf-8")),
        path=skill_dir,
        source="local",
    )




def load_skill_metadata(skill_dir: Path) -> dict[str, object]:
    return read_json_file(pm.manifest_metadata_path(skill_dir))




def iter_skill_dirs(skills_dir: Path) -> Iterable[Path]:
    if not skills_dir.exists():
        raise FileNotFoundError(f"Source directory not found: {skills_dir}")

    for child in sorted(skills_dir.iterdir(), key=lambda item: item.name):
        if child.is_dir() and child.name != "_template":
            yield child




def iter_managed_asset_dirs(asset_root: Path) -> Iterable[Path]:
    if not asset_root.exists():
        return []
    return [child for child in sorted(asset_root.iterdir(), key=lambda item: item.name) if child.is_dir() and child.name != "_template"]




def load_managed_asset_inventory(repo_root: Path, asset_type: str) -> dict[str, SkillRecord]:
    asset_root = repo_root / ASSET_DIRECTORY_NAMES[asset_type]
    inventory: dict[str, SkillRecord] = {}
    for asset_dir in iter_managed_asset_dirs(asset_root):
        record = load_skill_record(asset_dir)
        if record.asset_type != asset_type:
            continue
        inventory[record.skill_id] = record
    return inventory




def load_skill_inventory(repo_root: Path) -> dict[str, SkillRecord]:
    return load_managed_asset_inventory(repo_root, "skill")




def load_skill_record_by_id(
    repo_root: Path, skill_id: str, *, skill_dir_override: Path | None = None,
) -> SkillRecord:
    skill_dir = skill_dir_override or (repo_root / "skills" / skill_id)
    if not skill_dir.exists():
        available = sorted(
            child.name
            for child in (repo_root / "skills").iterdir()
            if child.is_dir()
        ) if (repo_root / "skills").exists() else []
        available_display = ", ".join(available)
        raise KeyError(f"Unknown skill ID(s): {skill_id}. Available skills: {available_display}")
    return load_skill_record(skill_dir)




def load_managed_asset_record_by_id(repo_root: Path, asset_type: str, asset_id: str) -> SkillRecord:
    asset_dir = repo_root / ASSET_DIRECTORY_NAMES[asset_type] / asset_id
    if not asset_dir.exists():
        available_root = repo_root / ASSET_DIRECTORY_NAMES[asset_type]
        available = sorted(child.name for child in available_root.iterdir() if child.is_dir()) if available_root.exists() else []
        available_display = ", ".join(available)
        raise KeyError(f"Unknown {asset_type} ID(s): {asset_id}. Available {asset_type}s: {available_display}")
    return load_skill_record(asset_dir)




def load_skill_registry_inventory(config: CliConfig) -> dict[str, SkillRecord]:
    if not config.skill_registry_index_url.strip():
        return {}

    registry_index = load_skill_registry_index(config)
    inventory: dict[str, SkillRecord] = {}
    for item in registry_index.get("skills", []):
        latest_version = str(item.get("latest_version", "")).strip()
        if not latest_version:
            raise ValueError(f"Skill registry entry is missing latest_version for {item.get('id', '<unknown>')}")
        raw_versions = item.get("versions", [])
        versions = raw_versions if isinstance(raw_versions, list) else []
        entry = next((version for version in versions if isinstance(version, dict) and version.get("version") == latest_version), None)
        if entry is None:
            raise ValueError(
                f"Skill registry entry {item.get('id', '<unknown>')} is missing version metadata for {latest_version}"
            )
        metadata_url = registry_skill_metadata_url(entry)
        payload = http_request(metadata_url, headers=skill_registry_headers())
        metadata = json.loads(payload.decode("utf-8"))
        record = skill_record_from_payload(metadata, path=None, source="registry", metadata_url=metadata_url)
        inventory[record.skill_id] = record
    return inventory




def load_combined_skill_inventory(repo_root: Path | None, config: CliConfig) -> dict[str, SkillRecord]:
    local_inventory = load_skill_inventory(repo_root) if repo_root is not None else {}
    try:
        registry_inventory = load_skill_registry_inventory(config)
    except urllib.error.URLError:
        if local_inventory:
            return local_inventory
        raise
    combined = dict(registry_inventory)
    combined.update(local_inventory)
    return combined


# HTTP/registry helpers (slash_join, http_request, registry_auth_headers, etc.)
# are imported from infrastructure.http_client (see import block above).




def cli_record_from_payload(
    metadata: dict[str, object],
    *,
    path: Path | None,
    source: str,
    metadata_url: str = "",
) -> CliAssetRecord:
    missing = [field for field in REQUIRED_CLI_FIELDS if not str(metadata.get(field, "")).strip()]
    if missing:
        missing_display = ", ".join(missing)
        source_display = metadata_url or str(path) or "<unknown>"
        raise ValueError(f"CLI metadata is missing required field(s): {missing_display}. Source: {source_display}")
    publish_paths_value = metadata.get("publish_paths", [])
    publish_paths = tuple(str(item) for item in publish_paths_value) if publish_paths_value else ()
    return CliAssetRecord(
        cli_id=str(metadata.get("id", "")).strip(),
        path=path,
        name=str(metadata.get("name", "")).strip(),
        status=str(metadata.get("status", "")).strip(),
        owner=str(metadata.get("owner", "")).strip(),
        version=str(metadata.get("version", "")).strip(),
        summary=str(metadata.get("summary", "")).strip(),
        package_name=str(metadata.get("package_name", "")).strip(),
        install_type=str(metadata.get("install_type", "")).strip(),
        command_name=str(metadata.get("command_name", "")).strip() or str(metadata.get("package_name", "")).strip(),
        publish_paths=publish_paths,
        source=source,
        metadata_url=metadata_url,
    )




def load_cli_record(cli_dir: Path) -> CliAssetRecord:
    metadata_path = cli_dir / "cli.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    publish_paths_default = [f"cli/{cli_dir.name}"]
    metadata.setdefault("publish_paths", publish_paths_default)
    return cli_record_from_payload(metadata, path=cli_dir, source="local")




def load_cli_metadata(cli_dir: Path) -> dict[str, object]:
    return read_json_file(cli_dir / "cli.json")




def load_cli_metadata_for_record(record: CliAssetRecord) -> dict[str, object]:
    if record.path is not None:
        return load_cli_metadata(record.path)
    if record.metadata_url:
        payload = http_request(record.metadata_url, headers=skill_registry_headers())
        return json.loads(payload.decode("utf-8"))
    raise ValueError(f"CLI metadata is unavailable for {record.cli_id}.")




def iter_cli_dirs(cli_root: Path) -> Iterable[Path]:
    if not cli_root.exists():
        return
    for child in sorted(cli_root.iterdir(), key=lambda item: item.name):
        if child.is_dir() and (child / "cli.json").exists():
            yield child




def load_cli_inventory(repo_root: Path) -> dict[str, CliAssetRecord]:
    cli_root = repo_root / "cli"
    inventory: dict[str, CliAssetRecord] = {}
    for cli_dir in iter_cli_dirs(cli_root):
        record = load_cli_record(cli_dir)
        inventory[record.cli_id] = record
    return inventory




# ── TTL cache for CLI registry inventory (avoids 30+ serial HTTP requests per call) ──
_CLI_REGISTRY_CACHE_TTL = 300  # 5 minutes
_cli_registry_cache: dict[str, Any] | None = None
_cli_registry_cache_ts: float = 0.0


def load_cli_registry_inventory(config: CliConfig) -> dict[str, CliAssetRecord]:
    global _cli_registry_cache, _cli_registry_cache_ts
    if not config.cli_registry_index_url.strip():
        return {}
    # Return cached result if still fresh.
    now = time.monotonic()
    if _cli_registry_cache is not None and (now - _cli_registry_cache_ts) < _CLI_REGISTRY_CACHE_TTL:
        return _cli_registry_cache

    registry_index = load_cli_registry_index(config)
    inventory: dict[str, CliAssetRecord] = {}
    for item in registry_index.get("clis", []):
        latest_version = str(item.get("latest_version", "")).strip()
        if not latest_version:
            raise ValueError(f"CLI registry entry is missing latest_version for {item.get('id', '<unknown>')}")
        versions = normalize_cli_versions(item, config)
        entry = next((version for version in versions if version.get("version") == latest_version), None)
        if entry is None:
            raise ValueError(
                f"CLI registry entry {item.get('id', '<unknown>')} is missing version metadata for {latest_version}"
            )
        metadata_url = cli_registry_metadata_url(entry)
        payload = http_request(metadata_url, headers=registry_auth_headers())
        metadata = json.loads(payload.decode("utf-8"))
        record = cli_record_from_payload(metadata, path=None, source="registry", metadata_url=metadata_url)
        inventory[record.cli_id] = record
    _cli_registry_cache = inventory
    _cli_registry_cache_ts = time.monotonic()
    return inventory




def load_combined_cli_inventory(repo_root: Path | None, config: CliConfig) -> dict[str, CliAssetRecord]:
    local_inventory = load_cli_inventory(repo_root) if repo_root is not None else {}
    try:
        registry_inventory = load_cli_registry_inventory(config)
    except urllib.error.URLError:
        if local_inventory:
            return local_inventory
        raise
    combined = dict(registry_inventory)
    combined.update(local_inventory)
    return combined




def select_records(
    inventory: dict[str, SkillRecord], skill_ids: list[str], install_all: bool
) -> list[SkillRecord]:
    if install_all:
        return list(inventory.values())

    missing = [skill_id for skill_id in skill_ids if skill_id not in inventory]
    if missing:
        available = ", ".join(sorted(inventory))
        missing_display = ", ".join(missing)
        raise KeyError(f"Unknown skill ID(s): {missing_display}. Available skills: {available}")

    return [inventory[skill_id] for skill_id in skill_ids]




def select_cli_records(
    inventory: dict[str, CliAssetRecord], cli_ids: list[str], install_all: bool
) -> list[CliAssetRecord]:
    if install_all:
        return list(inventory.values())

    missing = [cli_id for cli_id in cli_ids if cli_id not in inventory]
    if missing:
        available = ", ".join(sorted(inventory))
        missing_display = ", ".join(missing)
        raise KeyError(f"Unknown CLI ID(s): {missing_display}. Available CLIs: {available}")

    return cli_assets.expand_cli_records_with_dependencies(
        [inventory[cli_id] for cli_id in cli_ids],
        inventory,
        load_cli_metadata_for_record,
    )




def select_target_cli_record(records: list[CliAssetRecord], cli_id: str) -> CliAssetRecord:
    """Pick the requested CLI record from a dependency-expanded record list."""
    return cli_assets.select_target_cli_record(records, cli_id)




def load_skill_metadata_for_record(record: SkillRecord, config: CliConfig) -> dict[str, object]:
    if record.path is not None:
        return load_skill_metadata(record.path)
    if record.metadata_url:
        payload = http_request(record.metadata_url, headers=skill_registry_headers())
        return json.loads(payload.decode("utf-8"))
    metadata, _ = download_skill_metadata(config, record.skill_id, version=record.version)
    return metadata




def load_skill_document_for_record(
    record: SkillRecord,
    config: CliConfig,
    *,
    document: str,
    offline: bool = False,
) -> str:
    if record.path is not None:
        target = record.path / document
        if not target.exists():
            raise FileNotFoundError(f"Skill document not found: {target}")
        return target.read_text(encoding="utf-8")

    payload, _ = pm.download_registry_artifact(
        config.skill_registry_index_url,
        record.skill_id,
        version=record.version,
        offline=offline,
    )
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        for name in archive.namelist():
            normalized = name.strip("/")
            if not normalized:
                continue
            parts = Path(normalized).parts
            if len(parts) >= 2 and parts[-1] == document:
                with archive.open(name) as handle:
                    return handle.read().decode("utf-8")
    raise FileNotFoundError(f"Skill document not found in registry artifact: {record.skill_id}/{document}")




def load_skill_inventory_for_source(
    repo_root: Path | None,
    config: CliConfig,
    source: str,
) -> dict[str, SkillRecord]:
    if source == "repo":
        if repo_root is None:
            raise FileNotFoundError("Local ai-kit repository is not available. Bootstrap first or pass --repo-root.")
        return load_skill_inventory(repo_root)
    if source == "registry":
        return load_skill_registry_inventory(config)
    return load_combined_skill_inventory(repo_root, config)




def load_managed_asset_inventory_for_source(
    repo_root: Path | None,
    asset_type: str,
) -> dict[str, SkillRecord]:
    if repo_root is None:
        raise FileNotFoundError("Local ai-kit repository is not available. Bootstrap first or pass --repo-root.")
    return load_managed_asset_inventory(repo_root, asset_type)




def managed_asset_document_paths(asset_dir: Path, manifest: pm.SkillManifest) -> list[tuple[str, Path, bool]]:
    docs = [
        ("entry", asset_dir / manifest.entry, True),
        ("usage", asset_dir / manifest.companion_docs.usage, True),
        ("example", asset_dir / manifest.companion_docs.example, manifest.companion_docs.example_required),
        ("changelog", asset_dir / "CHANGELOG.md", True),
    ]
    return docs




def validate_usage_doc(asset_dir: Path, usage_path: Path) -> list[str]:
    errors: list[str] = []
    if not usage_path.exists():
        return errors
    content = usage_path.read_text(encoding="utf-8").strip()
    if not content:
        errors.append(f"{asset_dir.name}: USAGE.md is empty")
    if len(content.splitlines()) > 80:
        errors.append(f"{asset_dir.name}: USAGE.md should stay concise (<= 80 lines)")
    prompt_match = USAGE_PROMPT_SECTION_RE.search(content)
    if prompt_match is None:
        errors.append(f"{asset_dir.name}: USAGE.md must include a `## 可直接复制的中文 Prompt` section")
        return errors
    prompt_section = prompt_match.group(1).strip()
    if "```" not in prompt_section:
        errors.append(f"{asset_dir.name}: USAGE.md Chinese prompt section must include a copyable fenced code block")
    if not USAGE_PROMPT_CJK_RE.search(prompt_section):
        errors.append(f"{asset_dir.name}: USAGE.md Chinese prompt section must contain Chinese prompt text")
    return errors




def reference_doc_paths(asset_dir: Path) -> list[Path]:
    paths: list[Path] = []
    for child in sorted(asset_dir.glob("REFERENCE-*.md")):
        if child.is_file():
            paths.append(child)
    references_dir = asset_dir / "references"
    if references_dir.exists():
        for child in sorted(references_dir.glob("*.md")):
            if child.is_file():
                paths.append(child)
    return paths




def skill_entry_text(skill_dir: Path) -> tuple[str, str]:
    metadata = load_skill_metadata(skill_dir)
    entry_name = str(metadata.get("entry", "SKILL.md"))
    entry_path = skill_dir / entry_name
    if not entry_path.exists():
        raise FileNotFoundError(f"Skill entry not found: {entry_path}")
    return entry_name, entry_path.read_text(encoding="utf-8")




