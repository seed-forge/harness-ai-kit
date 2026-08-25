"""Bind command: update project metadata bindings."""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


def _load_metadata(metadata_path: Path) -> dict[str, Any]:
    """Load project metadata from YAML file."""
    if not metadata_path.exists():
        return {
            "schema_version": "1",
            "project": {
                "name": "",
                "display_name": "",
                "description": "",
            },
            "bindings": {
                "zentao": {},
                "gitea": {},
                "mattermost": {"channels": {}},
                "jenkins": {},
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    with open(metadata_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _save_metadata(metadata_path: Path, metadata: dict[str, Any]) -> None:
    """Save project metadata to YAML file."""
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata["updated_at"] = datetime.now(timezone.utc).isoformat()
    with open(metadata_path, "w", encoding="utf-8") as f:
        yaml.dump(metadata, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def _set_nested_value(data: dict[str, Any], path: str, value: Any) -> None:
    """Set a nested value using dot-separated path (e.g., 'zentao.project_id')."""
    keys = path.split(".")
    current = data
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value


def command_bind(args: argparse.Namespace, config_path: Path) -> int:
    """Update project metadata bindings in current directory."""
    cwd = Path.cwd()
    metadata_path = cwd / ".platform" / "project-metadata.yml"

    # Check if metadata exists
    if not metadata_path.exists():
        print(f"当前目录无项目元数据：{metadata_path}")
        response = input("是否初始化？(Y/n): ").strip().lower()
        if response in ("", "y", "yes"):
            metadata = _load_metadata(metadata_path)
            _save_metadata(metadata_path, metadata)
            print(f"已初始化项目元数据：{metadata_path}")
        else:
            print("已取消")
            return 0

    # Load metadata
    metadata = _load_metadata(metadata_path)

    # Parse binding path and value
    binding_path = args.path
    value = args.value

    # Try to convert value to appropriate type
    if value.isdigit():
        value = int(value)
    elif value.replace(".", "", 1).isdigit():
        value = float(value)
    elif value.lower() in ("true", "false"):
        value = value.lower() == "true"

    # Update binding
    full_path = f"bindings.{binding_path}"
    try:
        _set_nested_value(metadata, full_path, value)
    except (KeyError, TypeError) as e:
        print(f"错误：无法设置 {binding_path}: {e}")
        return 1

    # Save metadata
    _save_metadata(metadata_path, metadata)
    print(f"已更新绑定：{binding_path} = {value}")

    return 0


def build_bind_parser(subparsers: Any) -> None:
    """Build the bind subcommand parser."""
    bind_parser = subparsers.add_parser(
        "bind",
        help="Update project metadata bindings in current directory.",
    )
    bind_parser.add_argument(
        "path",
        help="Binding path (e.g., 'zentao.project_id', 'gitea.repo_url')",
    )
    bind_parser.add_argument(
        "value",
        help="Value to set",
    )
