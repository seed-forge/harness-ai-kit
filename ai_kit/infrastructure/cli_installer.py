"""CLI package installer: pip install, binary release download and install."""
from __future__ import annotations

import hashlib
import importlib.metadata
import io
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Sequence

from ai_kit.domain.models import CliAssetRecord, CliConfig
from ai_kit.domain.models.constants import ASSET_DIRECTORY_NAMES
from ai_kit.domain.dependency_expansion import SELF_CLI_PACKAGE_NAME, ordered_unique
from ai_kit.domain.install_state import installed_cli_version
from ai_kit.domain.inventory import load_cli_metadata_for_record
from ai_kit.infrastructure.config_io import console_safe_text
from ai_kit.infrastructure.http_client import http_request


def pip_install_command(
    package_name: str,
    registry_index_url: str,
    trusted_host: str,
    upgrade: bool,
) -> list[str]:
    command = [sys.executable, "-m", "pip", "install"]
    if upgrade:
        command.append("--upgrade")
    if registry_index_url:
        command.extend(["--index-url", registry_index_url])
    if trusted_host:
        command.extend(["--trusted-host", trusted_host])
    command.append(package_name)
    return command


def is_self_cli_package(package_name: str) -> bool:
    return package_name == SELF_CLI_PACKAGE_NAME


def self_upgrade_recovery_command(config: CliConfig) -> str:
    command = [sys.executable, "-m", "pip", "install", "--upgrade", SELF_CLI_PACKAGE_NAME]
    if config.registry_index_url:
        command.extend(["--index-url", config.registry_index_url])
    if config.trusted_host:
        command.extend(["--trusted-host", config.trusted_host])
    return " ".join(command)


def is_python_package_installed(package_name: str) -> bool:
    try:
        importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        return False
    return True


def installed_cli_records(records: list[CliAssetRecord]) -> list[CliAssetRecord]:
    installed: list[CliAssetRecord] = []
    for record in records:
        if installed_cli_version(record):
            installed.append(record)
    return installed


def binary_release_platform_spec(record: CliAssetRecord, metadata: dict[str, object]) -> dict[str, object]:
    binary_release = metadata.get("binary_release", {})
    if not isinstance(binary_release, dict):
        raise ValueError(f"CLI {record.cli_id} is missing a valid binary_release block.")
    platforms = binary_release.get("platforms", [])
    if not isinstance(platforms, list) or not platforms:
        raise ValueError(f"CLI {record.cli_id} does not declare any binary_release platforms.")
    current_os, current_arch = current_cli_platform()
    for item in platforms:
        if not isinstance(item, dict):
            continue
        item_os = normalize_cli_platform_os(str(item.get("os", "")))
        item_arch = normalize_cli_platform_arch(str(item.get("arch", "")))
        if item_os == current_os and item_arch == current_arch:
            return item
    raise ValueError(
        f"CLI {record.cli_id} does not support the current platform: {current_os}/{current_arch}."
    )


def binary_release_urls(spec: dict[str, object]) -> list[str]:
    urls: list[str] = []
    single = str(spec.get("url", "")).strip()
    if single:
        urls.append(single)
    values = spec.get("urls", [])
    if isinstance(values, list):
        urls.extend(str(item).strip() for item in values if str(item).strip())
    return ordered_unique(urls)


def binary_release_checksum_urls(spec: dict[str, object]) -> list[str]:
    urls: list[str] = []
    single = str(spec.get("checksum_url", "")).strip()
    if single:
        urls.append(single)
    values = spec.get("checksum_urls", [])
    if isinstance(values, list):
        urls.extend(str(item).strip() for item in values if str(item).strip())
    return ordered_unique(urls)


def binary_release_checksum(record: CliAssetRecord, spec: dict[str, object]) -> str:
    explicit = str(spec.get("sha256", "")).strip().lower()
    if explicit:
        return explicit
    for url in binary_release_checksum_urls(spec):
        try:
            payload = http_request(url)
        except (urllib.error.HTTPError, urllib.error.URLError):
            continue
        text = payload.decode("utf-8", errors="replace").strip()
        if not text:
            continue
        return text.split()[0].lower()
    raise ValueError(f"CLI {record.cli_id} is missing a usable SHA256 checksum declaration.")


def binary_release_install_path(record: CliAssetRecord, spec: dict[str, object]) -> Path:
    install_path = str(spec.get("install_path", "")).strip()
    if not install_path:
        raise ValueError(f"CLI {record.cli_id} is missing install_path for the current platform.")
    path = Path(install_path)
    if not path.is_absolute():
        raise ValueError(f"CLI {record.cli_id} install_path must be absolute: {install_path}")
    return path


def binary_release_download(record: CliAssetRecord, spec: dict[str, object]) -> tuple[bytes, str]:
    errors: list[str] = []
    for url in binary_release_urls(spec):
        try:
            return http_request(url, timeout=60), url
        except (urllib.error.HTTPError, urllib.error.URLError) as exc:
            errors.append(f"{url}: {exc}")
    raise ValueError(
        f"Failed to download binary-release CLI {record.cli_id}. Attempts: {'; '.join(errors) or '<none>'}"
    )


def install_binary_release_cli(record: CliAssetRecord, dry_run: bool) -> str:
    metadata = load_cli_metadata_for_record(record)
    spec = binary_release_platform_spec(record, metadata)
    install_path = binary_release_install_path(record, spec)
    preview_url = binary_release_urls(spec)
    if dry_run:
        source = preview_url[0] if preview_url else "<missing-url>"
        return f"download {source} -> {install_path}"

    payload, resolved_url = binary_release_download(record, spec)
    expected_checksum = binary_release_checksum(record, spec)
    actual_checksum = hashlib.sha256(payload).hexdigest().lower()
    if expected_checksum != actual_checksum:
        raise ValueError(
            f"Checksum mismatch for CLI {record.cli_id}: expected {expected_checksum}, got {actual_checksum}"
        )

    install_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = install_path.parent / f".ai-kit-{record.cli_id}.tmp"
    try:
        temp_path.write_bytes(payload)
        temp_path.chmod(0o755)
        os.replace(temp_path, install_path)
        install_path.chmod(0o755)
    finally:
        if temp_path.exists():
            temp_path.unlink()
    return f"Installed {record.cli_id} from {resolved_url} -> {install_path}"


def install_cli_packages(
    records: list[CliAssetRecord],
    config: CliConfig,
    upgrade: bool,
    dry_run: bool,
) -> list[str]:
    if not records:
        return []

    outputs: list[str] = []
    for record in records:
        if record.install_type == "python-package":
            command = pip_install_command(record.package_name, config.registry_index_url, config.trusted_host, upgrade)
            if dry_run:
                outputs.append(" ".join(command))
                continue
            result = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            outputs.append(console_safe_text(result.stdout.strip() or f"Installed {record.package_name}"))
            continue
        if record.install_type == "binary-release":
            outputs.append(install_binary_release_cli(record, dry_run))
            continue
        raise ValueError(f"Unsupported CLI install type for {record.cli_id}: {record.install_type}")
    return outputs


def normalize_cli_platform_os(value: str) -> str:
    current = value.strip().lower()
    if current.startswith("linux"):
        return "linux"
    if current.startswith("win"):
        return "windows"
    if current.startswith("darwin") or current.startswith("mac"):
        return "darwin"
    return current


def normalize_cli_platform_arch(value: str) -> str:
    current = value.strip().lower()
    aliases = {
        "x86_64": "amd64",
        "amd64": "amd64",
        "aarch64": "arm64",
        "arm64": "arm64",
    }
    return aliases.get(current, current)


def current_cli_platform() -> tuple[str, str]:
    return (
        normalize_cli_platform_os(platform.system()),
        normalize_cli_platform_arch(platform.machine()),
    )


def catalog_versions(catalog_path: Path) -> dict[str, str]:
    if not catalog_path.exists():
        return {}
    versions: dict[str, str] = {}
    version_idx: int | None = None
    for raw_line in catalog_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        # Header row: locate the version column by name (robust to column reorder).
        if version_idx is None and "`" not in line:
            for i, cell in enumerate(cells):
                if cell in ("版本", "version", "Version"):
                    version_idx = i
                    break
            continue
        if "`" not in line:
            continue
        idx = version_idx if version_idx is not None else 4
        if len(cells) <= idx:
            continue
        asset_id = cells[0]
        if not asset_id.startswith("`") or not asset_id.endswith("`"):
            continue
        version = cells[idx]
        if not version or version == "版本":
            continue
        versions[asset_id.strip("`")] = version
    return versions


