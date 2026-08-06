from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from base64 import b64encode
from pathlib import Path
from typing import Any, Sequence

from .main_compat import bridged_main_function

_PROTECTED_INFRA = {'registry_auth_headers', 'upload_file', 'download_skill_archive', 'registry_skill_metadata_url', 'download_skill_metadata'}


def registry_auth_headers() -> dict[str, str]:
    username = os.environ.get("AI_KIT_REGISTRY_USERNAME") or os.environ.get("TWINE_USERNAME")
    password = os.environ.get("AI_KIT_REGISTRY_PASSWORD") or os.environ.get("TWINE_PASSWORD")
    if not username or not password:
        return {}
    token = b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {token}"}


def upload_file(url: str, source_path: Path, content_type: str) -> None:
    http_request(
        url,
        method="PUT",
        headers={"Content-Type": content_type, **skill_registry_headers()},
        data=source_path.read_bytes(),
    )


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


registry_auth_headers = bridged_main_function(globals(), _PROTECTED_INFRA)(registry_auth_headers)
upload_file = bridged_main_function(globals(), _PROTECTED_INFRA)(upload_file)
download_skill_archive = bridged_main_function(globals(), _PROTECTED_INFRA)(download_skill_archive)
registry_skill_metadata_url = bridged_main_function(globals(), _PROTECTED_INFRA)(registry_skill_metadata_url)
download_skill_metadata = bridged_main_function(globals(), _PROTECTED_INFRA)(download_skill_metadata)
