"""Shared resources management: global registry + project-level references."""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


def _get_shared_resources_path() -> Path:
    """Get the global shared resources file path."""
    return Path.home() / ".ai-kit" / "shared-resources.yml"


def _load_shared_resources() -> dict[str, Any]:
    """Load global shared resources from YAML file."""
    path = _get_shared_resources_path()
    if not path.exists():
        return {
            "schema_version": "1",
            "resources": {},
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {
            "schema_version": "1",
            "resources": {},
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }


def _save_shared_resources(data: dict[str, Any]) -> None:
    """Save global shared resources to YAML file."""
    path = _get_shared_resources_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    print(f"已保存: {path}")


def _set_nested(data: dict[str, Any], path: str, value: Any) -> None:
    """Set a nested value using dot-separated path."""
    keys = path.split(".")
    current = data
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value


def _get_nested(data: dict[str, Any], path: str) -> Any:
    """Get a nested value using dot-separated path."""
    keys = path.split(".")
    current = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


# ── Commands ──────────────────────────────────────────────────────────


def command_shared_resources_list(args: argparse.Namespace, config_path: Path) -> int:
    """List all shared resources."""
    data = _load_shared_resources()
    resources = data.get("resources", {})

    if not resources:
        print("全局共享资源为空")
        print(f"文件位置: {_get_shared_resources_path()}")
        print(f"使用 'ai-kit shared-resources add <type>.<name>' 添加资源")
        return 0

    if getattr(args, "json", False):
        import json
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0

    # Table output
    rows: list[tuple[str, str, str]] = []
    for resource_type, items in resources.items():
        if isinstance(items, dict):
            for name, details in items.items():
                summary = ""
                if isinstance(details, dict):
                    # Show first 2-3 key fields as summary
                    parts = []
                    for k, v in list(details.items())[:3]:
                        parts.append(f"{k}={v}")
                    summary = ", ".join(parts)
                else:
                    summary = str(details)
                rows.append((f"{resource_type}.{name}", resource_type, summary))

    if rows:
        # Simple table formatting
        max_ref = max(len(r[0]) for r in rows)
        max_type = max(len(r[1]) for r in rows)
        print(f"{'REF':<{max_ref + 2}} {'TYPE':<{max_type + 2}} DETAILS")
        print(f"{'-' * max_ref}  {'-' * max_type}  {'-' * 40}")
        for ref, rtype, details in rows:
            print(f"{ref:<{max_ref + 2}} {rtype:<{max_type + 2}} {details}")

    print(f"\n共 {len(rows)} 个共享资源")
    print(f"文件位置: {_get_shared_resources_path()}")
    return 0


def command_shared_resources_add(args: argparse.Namespace, config_path: Path) -> int:
    """Add a shared resource to the global registry."""
    ref = args.ref  # e.g., "mattermost-channels.ops-infra"
    fields = args.field  # e.g., ["channel_id=abc123", "purpose=运维通知"]

    parts = ref.split(".", 1)
    if len(parts) != 2:
        print(f"错误: ref 格式不正确，应为 '<type>.<name>'，例如 'mattermost-channels.ops-infra'")
        return 1

    resource_type, resource_name = parts

    # Parse fields
    resource_data: dict[str, str] = {}
    for field in fields:
        if "=" not in field:
            print(f"错误: field 格式不正确，应为 'key=value': {field}")
            return 1
        key, value = field.split("=", 1)
        resource_data[key.strip()] = value.strip()

    if not resource_data:
        print("错误: 至少需要一个 field (key=value)")
        return 1

    # Load and update
    data = _load_shared_resources()
    resources = data.setdefault("resources", {})
    type_bucket = resources.setdefault(resource_type, {})
    type_bucket[resource_name] = resource_data

    _save_shared_resources(data)
    print(f"已添加共享资源: {ref}")
    for k, v in resource_data.items():
        print(f"  {k}: {v}")
    return 0


def command_shared_resources_use(args: argparse.Namespace, config_path: Path) -> int:
    """Add a shared resource reference to the current project's metadata."""
    ref = args.ref  # e.g., "mattermost-channels.ops-infra"

    # Validate ref exists in global registry
    data = _load_shared_resources()
    resource = _get_nested(data, f"resources.{ref}")
    if resource is None:
        print(f"错误: 共享资源不存在: {ref}")
        print(f"使用 'ai-kit shared-resources list' 查看可用资源")
        return 1

    # Find project metadata
    cwd = Path.cwd()
    metadata_path = cwd / ".platform" / "project-metadata.yml"
    if not metadata_path.exists():
        print(f"当前目录无项目元数据: {metadata_path}")
        response = input("是否初始化？(Y/n): ").strip().lower()
        if response in ("", "y", "yes"):
            metadata = {
                "schema_version": "1",
                "project": {"name": "", "display_name": "", "description": ""},
                "bindings": {
                    "zentao": {}, "gitea": {},
                    "mattermost": {"channels": {}}, "jenkins": {},
                },
                "shared_resources": [],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            metadata_path.parent.mkdir(parents=True, exist_ok=True)
            with open(metadata_path, "w", encoding="utf-8") as f:
                yaml.dump(metadata, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            print(f"已初始化: {metadata_path}")
        else:
            print("已取消")
            return 0

    # Load project metadata
    with open(metadata_path, encoding="utf-8") as f:
        metadata = yaml.safe_load(f)

    # Add reference (avoid duplicates)
    shared = metadata.setdefault("shared_resources", [])
    ref_entry = {"ref": ref}
    if ref_entry not in shared:
        shared.append(ref_entry)
        metadata["updated_at"] = datetime.now(timezone.utc).isoformat()
        with open(metadata_path, "w", encoding="utf-8") as f:
            yaml.dump(metadata, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        print(f"已添加引用: {ref} → {metadata_path}")
    else:
        print(f"引用已存在: {ref}")

    return 0


def command_shared_resources_remove(args: argparse.Namespace, config_path: Path) -> int:
    """Remove a shared resource from the global registry."""
    ref = args.ref

    data = _load_shared_resources()
    parts = ref.split(".", 1)
    if len(parts) != 2:
        print(f"错误: ref 格式不正确: {ref}")
        return 1

    resource_type, resource_name = parts
    resources = data.get("resources", {})
    type_bucket = resources.get(resource_type, {})

    if resource_name not in type_bucket:
        print(f"错误: 共享资源不存在: {ref}")
        return 1

    del type_bucket[resource_name]
    if not type_bucket:
        del resources[resource_type]

    _save_shared_resources(data)
    print(f"已移除共享资源: {ref}")
    return 0


# ── Parser ────────────────────────────────────────────────────────────


def build_shared_resources_parser(subparsers: Any) -> None:
    """Build the shared-resources subcommand parser."""
    sr_parser = subparsers.add_parser(
        "shared-resources",
        help="Manage global shared resources (channels, repos, libraries).",
    )
    sr_subparsers = sr_parser.add_subparsers(dest="sr_command", required=True)

    # list
    list_parser = sr_subparsers.add_parser("list", help="List all shared resources.")
    list_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")

    # add
    add_parser = sr_subparsers.add_parser("add", help="Add a shared resource to the global registry.")
    add_parser.add_argument("ref", help="Resource reference (e.g., 'mattermost-channels.ops-infra')")
    add_parser.add_argument(
        "--field", "-f", action="append", default=[],
        help="Resource field (e.g., 'channel_id=abc123'). Can be specified multiple times.",
    )

    # use
    use_parser = sr_subparsers.add_parser("use", help="Add a shared resource reference to the current project.")
    use_parser.add_argument("ref", help="Resource reference (e.g., 'mattermost-channels.ops-infra')")

    # remove
    remove_parser = sr_subparsers.add_parser("remove", help="Remove a shared resource from the global registry.")
    remove_parser.add_argument("ref", help="Resource reference to remove.")
