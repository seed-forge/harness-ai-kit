"""CLI registry operations: index, metadata, resolution."""
from __future__ import annotations

import json
import urllib.error
from pathlib import Path
from typing import Any

from ai_kit import package_manager as pm
from ai_kit.domain.models import CliAssetRecord, CliConfig, ProjectManifest, ProjectVersionedAssetSpec
from ai_kit.domain import cli_assets
from ai_kit.domain import project_locking
from ai_kit.domain.manifest_ops import declared_cli_specs
from ai_kit.domain.versions import spec_matches_version
from ai_kit.infrastructure.http_client import http_request, registry_auth_headers, slash_join


def cli_metadata_url(config: CliConfig, record: CliAssetRecord) -> str:
    return slash_join(
        config.cli_registry_upload_url,
        "clis",
        record.cli_id,
        record.version,
        "cli.json",
    )




def load_cli_registry_index(config: CliConfig) -> dict[str, object]:
    try:
        payload = http_request(config.cli_registry_index_url, headers=registry_auth_headers())
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return {"clis": []}
        raise
    parsed = json.loads(payload.decode("utf-8"))
    # Defensive: unwrap legacy list format [{"clis": [...]}] → {"clis": [...]}
    if isinstance(parsed, list):
        merged: list[dict] = []
        for chunk in parsed:
            if isinstance(chunk, dict):
                merged.extend(chunk.get("clis", []))
        return {"clis": merged}
    return parsed




def save_cli_registry_index(config: CliConfig, payload: dict[str, object]) -> None:
    body = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    http_request(
        config.cli_registry_index_url,
        method="PUT",
        headers={"Content-Type": "application/json", **registry_auth_headers()},
        data=body,
    )




def update_cli_registry_index_payload(
    current_index: dict[str, object],
    config: CliConfig,
    record: CliAssetRecord,
) -> dict[str, object]:
    metadata_url = cli_metadata_url(config, record)
    cli_entry = {
        "version": record.version,
        "metadata_url": metadata_url,
        "package_name": record.package_name,
        "published_at": pm.utc_now_iso(),
    }
    clis = list(current_index.get("clis", []))
    replaced = False
    for item in clis:
        if item.get("id") == record.cli_id:
            raw_versions = item.get("versions", [])
            existing_versions = raw_versions if isinstance(raw_versions, list) else []
            versions = [version for version in existing_versions if isinstance(version, dict) and version.get("version") != record.version]
            versions.append(cli_entry)
            versions.sort(key=lambda version: version["version"])
            item["name"] = record.name
            item["latest_version"] = record.version
            item["summary"] = record.summary
            item["owner"] = record.owner
            item["status"] = record.status
            item["package_name"] = record.package_name
            item["install_type"] = record.install_type
            item["versions"] = versions
            replaced = True
            break
    if not replaced:
        clis.append(
            {
                "id": record.cli_id,
                "name": record.name,
                "owner": record.owner,
                "status": record.status,
                "latest_version": record.version,
                "summary": record.summary,
                "package_name": record.package_name,
                "install_type": record.install_type,
                "versions": [cli_entry],
            }
        )
    return {"clis": sorted(clis, key=lambda item: item["id"])}




def cli_registry_metadata_url(entry: dict[str, object]) -> str:
    explicit = str(entry.get("metadata_url", "")).strip()
    if not explicit:
        raise KeyError("Registry CLI version entry is missing metadata_url.")
    return explicit


def normalize_cli_versions(item: dict[str, object], config: CliConfig) -> list[dict[str, object]]:
    """Normalize the ``versions`` field of a CLI index entry.

    Handles three legacy formats:
    - **list** (current): ``[{"version": "0.1.0", "metadata_url": "..."}]``
    - **dict** (old): ``{"0.1.0": {"cli_json": "clis/x/0.1.0/cli.json"}}``
    - **str/empty** (corrupt): ``""`` or other non type
    """
    raw = item.get("versions", [])
    if isinstance(raw, list):
        return [v for v in raw if isinstance(v, dict)]
    if isinstance(raw, dict):
        base_url = config.cli_registry_upload_url.rstrip("/")
        result: list[dict[str, object]] = []
        for ver, meta in raw.items():
            if not isinstance(meta, dict):
                continue
            cli_json = str(meta.get("cli_json", "")).strip()
            if not cli_json:
                continue
            metadata_url = base_url + "/" + cli_json.lstrip("/")
            result.append({"version": str(ver), "metadata_url": metadata_url})
        return result
    return []




def resolve_cli_record_from_registry(
    config: CliConfig,
    spec: ProjectVersionedAssetSpec,
) -> CliAssetRecord | None:
    from ai_kit.domain.inventory import cli_record_from_payload
    if not config.cli_registry_index_url.strip():
        return None
    try:
        registry_index = load_cli_registry_index(config)
    except urllib.error.URLError:
        return None
    for item in registry_index.get("clis", []):
        if str(item.get("id", "")).strip() != spec.id:
            continue
        for item_version in normalize_cli_versions(item, config):
            version = str(item_version.get("version", "")).strip()
            if not version or not spec_matches_version(spec.version, version):
                continue
            metadata_url = cli_registry_metadata_url(item_version)
            payload = http_request(metadata_url, headers=registry_auth_headers())
            metadata = json.loads(payload.decode("utf-8"))
            return cli_record_from_payload(metadata, path=None, source="registry", metadata_url=metadata_url)
    return None




def merge_manifest_cli_into_refresh_lockfile(
    lockfile: pm.Lockfile,
    config: CliConfig,
    manifest: ProjectManifest,
    repo_root: Path | None,
    *,
    offline: bool,
) -> pm.Lockfile:
    from ai_kit.domain.inventory import load_combined_cli_inventory
    if offline:
        return lockfile
    cli_specs = declared_cli_specs(manifest)
    if not cli_specs:
        return lockfile
    declared_ids = {spec.id for spec in cli_specs}
    entries: list[project_locking.CliLockEntry] = []
    for spec in cli_specs:
        record = resolve_cli_record_from_registry(config, spec)
        if record is None:
            inventory = load_combined_cli_inventory(repo_root, config)
            record = cli_assets.select_cli_record_for_spec(inventory, spec)
        entries.append(project_locking.CliLockEntry(spec=spec, record=record))
    new_nodes = project_locking.replace_declared_cli_lock_nodes(
        lockfile.nodes,
        entries,
        declared_cli_ids=declared_ids,
    )
    return lockfile.model_copy(update={"nodes": new_nodes})




