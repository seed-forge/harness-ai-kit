"""Skill registry operations: index, archive, download."""
from __future__ import annotations

import json
import urllib.error
import zipfile
from pathlib import Path
from typing import Any

from harness_ai_kit import package_manager as pm
from harness_ai_kit.domain.models import CliConfig, SkillRecord
from harness_ai_kit.infrastructure.http_client import (
    http_request, skill_registry_headers, slash_join, upload_file,
)


def skill_archive_name(record: SkillRecord) -> str:
    return f"{record.skill_id}-{record.version}.zip"




def skill_archive_url(config: CliConfig, record: SkillRecord) -> str:
    return slash_join(
        config.skill_registry_upload_url,
        "skills",
        record.skill_id,
        record.version,
        skill_archive_name(record),
    )




def skill_metadata_url(config: CliConfig, record: SkillRecord) -> str:
    return slash_join(
        config.skill_registry_upload_url,
        "skills",
        record.skill_id,
        record.version,
        "skill.json",
    )




def load_skill_registry_index(config: CliConfig) -> dict[str, object]:
    try:
        payload = http_request(config.skill_registry_index_url, headers=skill_registry_headers())
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return {"skills": []}
        raise
    return json.loads(payload.decode("utf-8"))




def save_skill_registry_index(config: CliConfig, payload: dict[str, object]) -> None:
    body = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    http_request(
        config.skill_registry_index_url,
        method="PUT",
        headers={"Content-Type": "application/json", **skill_registry_headers()},
        data=body,
    )




# Directories excluded from published skill archives (producer-side working material,
# not part of the installable asset). Convention: <asset>/visual/ holds visual
# promotion kits (cnt-aikit-visual); consumers must not receive them.
PUBLISH_EXCLUDE_DIR_NAMES = frozenset({"visual", "__pycache__"})


def _is_publishable(file_path: Path, root: Path) -> bool:
    rel_parts = file_path.relative_to(root).parts
    return not any(part in PUBLISH_EXCLUDE_DIR_NAMES for part in rel_parts)


def build_skill_archive(repo_root: Path, record: SkillRecord, output_dir: Path | None = None) -> Path:
    target_dir = output_dir or (repo_root / "dist" / "skills")
    target_dir.mkdir(parents=True, exist_ok=True)
    archive_path = target_dir / skill_archive_name(record)
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in sorted(record.path.rglob("*")):
            if file_path.is_file() and _is_publishable(file_path, record.path):
                archive.write(file_path, arcname=str(file_path.relative_to(record.path.parent)).replace("\\", "/"))
    return archive_path




def update_skill_registry_index_payload(
    current_index: dict[str, object],
    config: CliConfig,
    record: SkillRecord,
) -> dict[str, object]:
    archive_url = skill_archive_url(config, record)
    metadata_url = skill_metadata_url(config, record)
    skill_entry = {
        "version": record.version,
        "url": archive_url,
        "metadata_url": metadata_url,
    }
    skills = list(current_index.get("skills", []))
    replaced = False
    for item in skills:
        if item.get("id") == record.skill_id:
            versions = [version for version in item.get("versions", []) if version.get("version") != record.version]
            versions.append(skill_entry)
            versions.sort(key=lambda version: version["version"])
            item["name"] = record.name
            item["latest_version"] = record.version
            item["summary"] = record.summary
            item["versions"] = versions
            replaced = True
            break
    if not replaced:
        skills.append(
            {
                "id": record.skill_id,
                "name": record.name,
                "latest_version": record.version,
                "summary": record.summary,
                "versions": [skill_entry],
            }
        )
    return {"skills": sorted(skills, key=lambda item: item["id"])}




def download_skill_archive(config: CliConfig, skill_id: str, version: str | None = None) -> tuple[bytes, str]:
    registry_index = load_skill_registry_index(config)
    for item in registry_index.get("skills", []):
        if item.get("id") != skill_id:
            continue
        candidate_version = version or item.get("latest_version")
        for item_version in item.get("versions", []):
            if item_version.get("version") == candidate_version:
                payload = http_request(item_version["url"], headers=skill_registry_headers())
                return payload, candidate_version
        raise KeyError(f"Version not found for skill {skill_id}: {candidate_version}")
    raise KeyError(f"Skill not found in registry index: {skill_id}")




def registry_skill_metadata_url(item_version: dict[str, object]) -> str:
    explicit = str(item_version.get("metadata_url", "")).strip()
    if explicit:
        return explicit
    archive_url = str(item_version.get("url", "")).strip()
    if not archive_url:
        raise KeyError("Registry skill version entry is missing both url and metadata_url.")
    base_url = archive_url.rsplit("/", 1)[0]
    return f"{base_url}/skill.json"




def download_skill_metadata(config: CliConfig, skill_id: str, version: str | None = None) -> tuple[dict[str, object], str]:
    registry_index = load_skill_registry_index(config)
    for item in registry_index.get("skills", []):
        if item.get("id") != skill_id:
            continue
        candidate_version = version or item.get("latest_version")
        for item_version in item.get("versions", []):
            if item_version.get("version") == candidate_version:
                payload = http_request(registry_skill_metadata_url(item_version), headers=skill_registry_headers())
                return json.loads(payload.decode("utf-8")), str(candidate_version)
        raise KeyError(f"Version not found for skill {skill_id}: {candidate_version}")
    raise KeyError(f"Skill not found in registry index: {skill_id}")




def install_skill_archive_bytes(payload: bytes, target_dir: Path, runtime_id: str = "codex") -> Path:
    """Convenience wrapper that auto-passes renderers for kiro/cursor runtimes."""
    from harness_ai_kit.domain import runtime_install as _runtime_install
    from harness_ai_kit.domain.install_state import (
        render_kiro_steering as _render_kiro_steering,
        render_cursor_rule as _render_cursor_rule,
    )
    return _runtime_install.install_skill_archive_bytes(
        payload,
        target_dir,
        runtime_id,
        render_kiro_steering=_render_kiro_steering,
        render_cursor_rule=_render_cursor_rule,
    )




