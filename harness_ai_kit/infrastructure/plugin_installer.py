"""Plugin installer: publish/install host plugins through the CLI registry.

Plugin artifacts are tracked in the configured CLI registry index used by
CLI assets (D4); the index file gains a ``plugins`` section alongside
``clis``. Installation is delegated per host adapter:

- ``dsh``: download tarball -> sha256 -> ``dsh plugin --profile <name> add`` (D6)
- ``pi``: ``pi install npm:<pkg>@<ver>`` against the configured npm registry, with a
  temporary npmrc carrying registry + auth (``NPM_CONFIG_USERCONFIG``).
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.parse
from pathlib import Path
from typing import Any

from harness_ai_kit import package_manager as pm
from harness_ai_kit.domain.models import CliConfig
from harness_ai_kit.domain.models.records import PluginRecord
from harness_ai_kit.infrastructure.http_client import http_request, registry_auth_headers, slash_join


def plugin_registry_metadata_url(config: CliConfig, plugin_id: str, version: str) -> str:
    return slash_join(config.cli_registry_upload_url, "plugins", plugin_id, version, "plugin.json")


def load_plugin_registry_index(config: CliConfig) -> dict[str, object]:
    """Load the shared raw-hosted-cli index, keeping both clis and plugins."""
    try:
        payload = http_request(config.cli_registry_index_url, headers=registry_auth_headers())
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return {"clis": [], "plugins": []}
        raise
    parsed = json.loads(payload.decode("utf-8"))
    if isinstance(parsed, list):
        merged_clis: list[dict[str, object]] = []
        merged_plugins: list[dict[str, object]] = []
        for chunk in parsed:
            if isinstance(chunk, dict):
                merged_clis.extend(chunk.get("clis", []))
                merged_plugins.extend(chunk.get("plugins", []))
        return {"clis": merged_clis, "plugins": merged_plugins}
    parsed.setdefault("clis", [])
    parsed.setdefault("plugins", [])
    return parsed


def save_plugin_registry_index(config: CliConfig, payload: dict[str, object]) -> None:
    body = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    http_request(
        config.cli_registry_index_url,
        method="PUT",
        headers={"Content-Type": "application/json", **registry_auth_headers()},
        data=body,
    )


def update_plugin_registry_index_payload(
    current_index: dict[str, object],
    config: CliConfig,
    record: PluginRecord,
    *,
    artifact_url: str,
    checksum: str,
) -> dict[str, object]:
    metadata_url = plugin_registry_metadata_url(config, record.plugin_id, record.version)
    plugin_entry: dict[str, object] = {
        "version": record.version,
        "metadata_url": metadata_url,
        "artifact_url": artifact_url,
        "checksum": checksum,
        "npm_name": record.npm_name,
        "default_profile": record.default_profile,
        "default_scope": record.default_scope,
        "published_at": pm.utc_now_iso(),
    }
    plugins = list(current_index.get("plugins", []))
    replaced = False
    for item in plugins:
        if item.get("id") == record.plugin_id:
            raw_versions = item.get("versions", [])
            versions = [v for v in raw_versions if isinstance(v, dict) and v.get("version") != record.version]
            versions.append(plugin_entry)
            versions.sort(key=lambda v: str(v["version"]))
            item["name"] = record.name
            item["latest_version"] = record.version
            item["summary"] = record.summary
            item["owner"] = record.owner
            item["status"] = record.status
            item["package_type"] = "plugin"
            item["hosts"] = list(record.hosts)
            item["npm_name"] = record.npm_name
            item["default_profile"] = record.default_profile
            item["default_scope"] = record.default_scope
            item["versions"] = versions
            replaced = True
            break
    if not replaced:
        plugins.append(
            {
                "id": record.plugin_id,
                "name": record.name,
                "owner": record.owner,
                "status": record.status,
                "latest_version": record.version,
                "summary": record.summary,
                "package_type": "plugin",
                "hosts": list(record.hosts),
                "npm_name": record.npm_name,
                "default_profile": record.default_profile,
                "default_scope": record.default_scope,
                "versions": [plugin_entry],
            }
        )
    return {"clis": list(current_index.get("clis", [])), "plugins": sorted(plugins, key=lambda item: str(item["id"]))}


def find_plugin_registry_entry(
    index: dict[str, object], plugin_id: str, version: str | None = None
) -> tuple[dict[str, object], dict[str, object]] | None:
    for item in index.get("plugins", []):
        if not isinstance(item, dict) or item.get("id") != plugin_id:
            continue
        versions = [v for v in item.get("versions", []) if isinstance(v, dict)]
        if version is None:
            selected = versions[-1] if versions else {}
        else:
            selected = next((v for v in versions if v.get("version") == version), {})
        if selected:
            return item, selected
    return None


def plugin_record_from_registry_entry(
    item: dict[str, object], entry: dict[str, object], *, source: str = "registry"
) -> PluginRecord:
    """Build a PluginRecord from a registry index entry (consumer-side install)."""
    hosts = [str(h) for h in item.get("hosts", [])] if isinstance(item.get("hosts"), list) else ["dsh"]
    return PluginRecord(
        plugin_id=str(item.get("id", "")),
        path=None,
        name=str(item.get("name", item.get("id", ""))),
        status=str(item.get("status", "active")),
        owner=str(item.get("owner", "team")),
        version=str(entry.get("version", "0.0.0")),
        summary=str(item.get("summary", "")),
        hosts=tuple(hosts),
        npm_name=str(entry.get("npm_name", item.get("npm_name", item.get("id", "")))),
        default_profile=str(entry.get("default_profile", item.get("default_profile", "web"))),
        default_scope=str(entry.get("default_scope", item.get("default_scope", "global"))) or "global",
        source=source,
    )


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _dsh_binary() -> str:
    binary = shutil.which("dsh")
    if binary is None:
        raise FileNotFoundError(
            "dsh CLI not found on PATH. Install the baseline with "
            "`npm i -g @deepseek-ai/dsh@0.1.0-rc.6` or run doctor: `harness-ai-kit doctor dsh`."
        )
    return binary


def _dsh_plugin_add_command(profile: str, tarball_path: str) -> list[str]:
    return [_dsh_binary(), "plugin", "--profile", profile, "add", tarball_path]


def _dsh_dump_config_command(profile: str) -> list[str]:
    return [_dsh_binary(), "--profile", profile, "--dump-config"]


def dsh_dump_config_contains(profile: str, npm_name: str) -> bool:
    try:
        proc = subprocess.run(
            _dsh_dump_config_command(profile),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return npm_name in (proc.stdout or "")


def install_dsh_plugin(
    record: PluginRecord,
    config: CliConfig,
    *,
    profile: str,
    dry_run: bool = False,
) -> str:
    """Download the plugin tarball from the CLI registry and delegate to dsh."""
    if "dsh" not in record.hosts:
        raise ValueError(f"Plugin {record.plugin_id} does not declare the dsh host adapter.")
    index = load_plugin_registry_index(config)
    found = find_plugin_registry_entry(index, record.plugin_id)
    if found is None:
        raise FileNotFoundError(
            f"Plugin {record.plugin_id} not found in the CLI registry index ({config.cli_registry_index_url})."
        )
    _item, entry = found
    artifact_url = str(entry.get("artifact_url", "")).strip()
    expected_checksum = str(entry.get("checksum", "")).strip()
    if not artifact_url:
        raise ValueError(f"Registry entry for {record.plugin_id} has no artifact_url.")

    if dry_run:
        return (
            f"[dry-run] download {artifact_url}\n"
            f"[dry-run] sha256 {expected_checksum or '<none>'} (verified)\n"
            f"[dry-run] dsh plugin --profile {profile} add <tarball>"
        )

    payload = http_request(artifact_url, headers=registry_auth_headers(), timeout=120)
    if not isinstance(payload, bytes):
        raise ValueError(f"Unexpected response payload from {artifact_url}")
    actual_checksum = _sha256_bytes(payload)
    if expected_checksum and actual_checksum != expected_checksum:
        raise ValueError(
            f"Checksum mismatch for {record.plugin_id}: expected {expected_checksum}, got {actual_checksum}."
        )

    with tempfile.TemporaryDirectory(prefix="harness-ai-kit-plugin-") as tmp:
        tarball_path = Path(tmp) / f"{record.npm_name}-{record.version}.tgz"
        tarball_path.write_bytes(payload)
        proc = subprocess.run(
            [_dsh_binary(), "plugin", "--profile", profile, "add", str(tarball_path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
            check=False,
        )
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "").strip().splitlines()
            raise RuntimeError(
                f"dsh plugin add failed (exit {proc.returncode}): {detail[-1] if detail else 'no output'}"
            )

    if not dsh_dump_config_contains(profile, record.npm_name):
        raise RuntimeError(
            f"Verification failed: `dsh --profile {profile} --dump-config` does not contain {record.npm_name}. "
            f"Roll back with: dsh plugin --profile {profile} remove {record.npm_name}"
        )
    return (
        f"Installed plugin {record.plugin_id}@{record.version} into dsh profile '{profile}' "
        f"(npm {record.npm_name}); --dump-config contains the bundle layer."
    )


def dsh_plugin_remove(npm_name: str, profile: str, *, dry_run: bool = False) -> str:
    command = [_dsh_binary(), "plugin", "--profile", profile, "remove", npm_name]
    if dry_run:
        return f"[dry-run] {' '.join(command)}"
    proc = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        check=False,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip().splitlines()
        raise RuntimeError(
            f"dsh plugin remove failed (exit {proc.returncode}): {detail[-1] if detail else 'no output'}"
        )
    return f"Removed {npm_name} from dsh profile '{profile}'."


# ---------------------------------------------------------------------------
# pi host adapter (Pi Coding Agent; packages distributed via the configured npm registry)
# ---------------------------------------------------------------------------


def _pi_binary() -> str:
    binary = shutil.which("pi")
    if binary is None:
        raise FileNotFoundError(
            "pi CLI not found on PATH. Install with "
            "`npm i -g --ignore-scripts @earendil-works/pi-coding-agent` or run `harness-ai-kit doctor pi`."
        )
    return binary


def _registry_basic_token() -> str | None:
    """Extract the base64 basic-auth token from the shared registry credentials."""
    headers = registry_auth_headers()
    auth = headers.get("Authorization", "")
    if auth.startswith("Basic "):
        return auth[len("Basic "):].strip() or None
    return None


def _write_temp_npmrc(registry_url: str, directory: Path) -> Path:
    """Write a temporary npmrc pinning the configured npm registry (+ auth when available)."""
    parsed = urllib.parse.urlparse(registry_url)
    host_path = f"{parsed.netloc}{parsed.path.rstrip('/')}"
    lines = [f"registry={registry_url}"]
    token = _registry_basic_token()
    if token:
        lines.append(f"//{host_path}/:_auth={token}")
    npmrc_path = Path(directory) / ".npmrc"
    npmrc_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return npmrc_path


def _pi_install_env(npmrc_path: Path, registry_url: str) -> dict[str, str]:
    env = dict(os.environ)
    env["NPM_CONFIG_USERCONFIG"] = str(npmrc_path)
    env["NPM_CONFIG_REGISTRY"] = registry_url
    return env


def _pi_package_dir(npm_name: str, scope: str, *, home_dir: Path | None = None, project_dir: Path | None = None) -> Path:
    if scope == "project":
        base = (project_dir or Path.cwd()) / ".pi" / "npm"
    else:
        base = (home_dir or Path.home()) / ".pi" / "agent" / "npm"
    return base / npm_name


def pi_npm_spec(record: PluginRecord) -> str:
    return f"npm:{record.npm_name}@{record.version}"


def install_pi_plugin(
    record: PluginRecord,
    config: CliConfig,
    *,
    scope: str,
    dry_run: bool = False,
) -> str:
    """Install a pi package from the configured npm registry via `pi install`.

    ``scope`` maps the pi package install target: ``global`` -> ~/.pi/agent/npm,
    ``project`` -> .pi/npm (pi ``-l`` flag, subject to pi project trust).
    """
    if "pi" not in record.hosts:
        raise ValueError(f"Plugin {record.plugin_id} does not declare the pi host adapter.")
    if scope not in ("global", "project"):
        raise ValueError(f"Invalid pi package scope: {scope} (expected global|project).")
    index = load_plugin_registry_index(config)
    found = find_plugin_registry_entry(index, record.plugin_id)
    if found is None:
        raise FileNotFoundError(
            f"Plugin {record.plugin_id} not found in the CLI registry index ({config.cli_registry_index_url})."
        )
    _item, entry = found
    version = str(entry.get("version", record.version))
    npm_name = str(entry.get("npm_name", record.npm_name))
    spec = f"npm:{npm_name}@{version}"
    install_url = config.npm_registry_install_url.strip()
    if not install_url:
        raise ValueError(
            "npm_registry_install_url is not configured; set it in ~/.harness-ai-kit/config.yaml "
            "(see docs/pi-integration.md)."
        )

    command_spec = ["pi", "install", spec]
    if scope == "project":
        command_spec.append("-l")
    if dry_run:
        return (
            f"[dry-run] npmrc registry={install_url} (auth from shared registry credentials)\n"
            f"[dry-run] NPM_CONFIG_USERCONFIG=<temp npmrc> {' '.join(command_spec)}\n"
            f"[dry-run] verify {_pi_package_dir(npm_name, scope)}"
        )

    command = [_pi_binary(), "install", spec]
    if scope == "project":
        command.append("-l")
    with tempfile.TemporaryDirectory(prefix="harness-ai-kit-npmrc-") as tmp:
        npmrc_path = _write_temp_npmrc(install_url, Path(tmp))
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
            check=False,
            env=_pi_install_env(npmrc_path, install_url),
        )
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "").strip().splitlines()
            raise RuntimeError(
                f"pi install failed (exit {proc.returncode}): {detail[-1] if detail else 'no output'}"
            )

    package_dir = _pi_package_dir(npm_name, scope)
    if not (package_dir / "package.json").exists():
        raise RuntimeError(
            f"Verification failed: {package_dir / 'package.json'} not found after pi install. "
            f"Roll back with: pi uninstall npm:{npm_name}"
            + (" -l" if scope == "project" else "")
        )
    return (
        f"Installed plugin {record.plugin_id}@{version} as pi package ({spec}, scope={scope}); "
        f"verified at {package_dir}."
    )


def pi_plugin_remove(npm_name: str, *, scope: str = "global", dry_run: bool = False) -> str:
    command = [_pi_binary(), "uninstall", f"npm:{npm_name}"]
    if scope == "project":
        command.append("-l")
    if dry_run:
        return f"[dry-run] {' '.join(command)}"
    proc = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
        check=False,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip().splitlines()
        raise RuntimeError(
            f"pi uninstall failed (exit {proc.returncode}): {detail[-1] if detail else 'no output'}"
        )
    return f"Removed npm:{npm_name} from pi (scope={scope})."
