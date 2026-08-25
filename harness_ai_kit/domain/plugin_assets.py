"""Plugin asset domain: metadata validation and inventory loading.

A plugin asset lives in ``plugins/<id>/`` with a ``plugin.json`` (package_type
"plugin", hosts, plus one host-adapter block per declared host). The first host
adapter is DeepSeek Harness (``dsh``); ``pi`` (Pi Coding Agent, npm package
adapter) is the second. More hosts can be added later.
"""

from __future__ import annotations

import json
from pathlib import Path

from harness_ai_kit.domain.models.records import PluginRecord

PLUGIN_TEMPLATE_DIR_NAME = "_template"
REQUIRED_PLUGIN_KEYS = ("id", "name", "package_type", "hosts")
KNOWN_PLUGIN_HOSTS = ("dsh", "pi")
REQUIRED_DSH_BUNDLE_KEYS = ("npm_name", "patch")
REQUIRED_PI_PACKAGE_KEYS = ("npm_name",)
PI_PACKAGE_SCOPES = ("global", "project")


def load_plugin_record(plugin_dir: Path) -> PluginRecord | None:
    plugin_json = plugin_dir / "plugin.json"
    asset_json = plugin_dir / "asset.json"
    metadata_path = plugin_json if plugin_json.exists() else asset_json
    if not metadata_path.exists():
        return None
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(metadata, dict):
        return None
    if str(metadata.get("package_type", metadata.get("asset_type", ""))) not in ("plugin",):
        return None
    plugin_id = str(metadata.get("id", "")).strip()
    if not plugin_id:
        return None
    dsh_bundle = metadata.get("dsh", {}).get("bundle", {}) if isinstance(metadata.get("dsh"), dict) else {}
    pi_package = metadata.get("pi", {}).get("package", {}) if isinstance(metadata.get("pi"), dict) else {}
    hosts = tuple(str(h) for h in metadata.get("hosts", [])) if isinstance(metadata.get("hosts"), list) else ()
    default_scope = str(pi_package.get("default_scope", "global")) or "global"
    return PluginRecord(
        plugin_id=plugin_id,
        path=plugin_dir,
        name=str(metadata.get("name", plugin_id)),
        status=str(metadata.get("status", "draft")),
        owner=str(metadata.get("owner", "team")),
        version=str(metadata.get("version", "0.0.0")),
        summary=str(metadata.get("summary", metadata.get("description", ""))),
        hosts=hosts,
        npm_name=str(dsh_bundle.get("npm_name") or pi_package.get("npm_name") or plugin_id),
        default_profile=str(dsh_bundle.get("default_profile", "web")),
        default_scope=default_scope,
    )


def load_plugin_inventory(repo_root: Path) -> dict[str, PluginRecord]:
    plugins_root = repo_root / "plugins"
    inventory: dict[str, PluginRecord] = {}
    if not plugins_root.is_dir():
        return inventory
    for child in sorted(plugins_root.iterdir()):
        if not child.is_dir() or child.name == PLUGIN_TEMPLATE_DIR_NAME:
            continue
        record = load_plugin_record(child)
        if record is not None:
            inventory[record.plugin_id] = record
    return inventory


def validate_plugin_metadata(plugin_dir: Path) -> list[str]:
    """Validate plugin.json shape. Returns a list of human-readable errors."""
    errors: list[str] = []
    plugin_json = plugin_dir / "plugin.json"
    if not plugin_json.exists():
        return [f"missing plugin.json in {plugin_dir}"]
    try:
        metadata = json.loads(plugin_json.read_text(encoding="utf-8"))
    except ValueError as exc:
        return [f"plugin.json is not valid JSON: {exc}"]
    if not isinstance(metadata, dict):
        return ["plugin.json must be a JSON object"]
    for key in REQUIRED_PLUGIN_KEYS:
        if key not in metadata:
            errors.append(f"plugin.json missing required key: {key}")
    if metadata.get("package_type") != "plugin":
        errors.append("package_type must be 'plugin'")
    hosts = metadata.get("hosts")
    if not isinstance(hosts, list) or not hosts:
        errors.append("hosts must be a non-empty list")
        hosts = []
    unknown_hosts = [str(h) for h in hosts if str(h) not in KNOWN_PLUGIN_HOSTS]
    if unknown_hosts:
        errors.append(f"unknown host adapters: {', '.join(unknown_hosts)} (known: {', '.join(KNOWN_PLUGIN_HOSTS)})")
    if "dsh" in hosts:
        dsh_block = metadata.get("dsh")
        if isinstance(dsh_block, dict):
            bundle = dsh_block.get("bundle")
            if not isinstance(bundle, dict):
                errors.append("dsh.bundle must be an object")
            else:
                for key in REQUIRED_DSH_BUNDLE_KEYS:
                    if key not in bundle:
                        errors.append(f"dsh.bundle missing required key: {key}")
                npm_name = str(bundle.get("npm_name", ""))
                if npm_name != str(metadata.get("id", "")):
                    errors.append("dsh.bundle.npm_name must equal the asset id")
        else:
            errors.append("dsh block is required when hosts include 'dsh'")
    if "pi" in hosts:
        pi_block = metadata.get("pi")
        if isinstance(pi_block, dict):
            package = pi_block.get("package")
            if not isinstance(package, dict):
                errors.append("pi.package must be an object")
            else:
                for key in REQUIRED_PI_PACKAGE_KEYS:
                    if key not in package:
                        errors.append(f"pi.package missing required key: {key}")
                npm_name = str(package.get("npm_name", ""))
                if npm_name != str(metadata.get("id", "")):
                    errors.append("pi.package.npm_name must equal the asset id")
                default_scope = str(package.get("default_scope", "global"))
                if default_scope not in PI_PACKAGE_SCOPES:
                    errors.append(f"pi.package.default_scope must be one of {PI_PACKAGE_SCOPES}")
        else:
            errors.append("pi block is required when hosts include 'pi'")
    return errors


def validate_plugin_assets(repo_root: Path) -> list[dict[str, object]]:
    """Validate all plugin assets under plugins/. Used by `validate`."""
    results: list[dict[str, object]] = []
    plugins_root = repo_root / "plugins"
    if not plugins_root.is_dir():
        return results
    for child in sorted(plugins_root.iterdir()):
        if not child.is_dir() or child.name == PLUGIN_TEMPLATE_DIR_NAME:
            continue
        errors = validate_plugin_metadata(child)
        results.append(
            {
                "subject": f"plugin:{child.name}",
                "status": "success" if not errors else "error",
                "message": "ok" if not errors else "; ".join(errors),
            }
        )
    return results
