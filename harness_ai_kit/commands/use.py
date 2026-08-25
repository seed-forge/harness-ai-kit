"""Use command: switch working directory to another project."""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from typing import Any


def command_use(args: argparse.Namespace, config_path: Path) -> int:
    """Switch working directory to target project."""
    target_dir = Path(args.target).resolve()

    if not target_dir.exists():
        print(f"错误：目标目录不存在：{target_dir}")
        return 1

    if not target_dir.is_dir():
        print(f"错误：目标路径不是目录：{target_dir}")
        return 1

    target_metadata = target_dir / ".platform" / "project-metadata.yml"
    current_metadata = Path.cwd() / ".platform" / "project-metadata.yml"

    # Check if target has metadata
    if not target_metadata.exists():
        print(f"目标目录无项目元数据：{target_metadata}")

        # Check if current directory has metadata
        if current_metadata.exists():
            response = input("是否从当前目录复制元数据？(Y/n): ").strip().lower()
            if response in ("", "y", "yes"):
                target_metadata.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(current_metadata, target_metadata)
                print(f"已复制元数据到：{target_metadata}")
        else:
            response = input("是否在目标目录初始化元数据？(Y/n): ").strip().lower()
            if response in ("", "y", "yes"):
                target_metadata.parent.mkdir(parents=True, exist_ok=True)
                # Create minimal metadata
                import yaml
                from datetime import datetime, timezone
                metadata = {
                    "schema_version": "1",
                    "project": {
                        "name": target_dir.name,
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
                with open(target_metadata, "w", encoding="utf-8") as f:
                    yaml.dump(metadata, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
                print(f"已初始化项目元数据：{target_metadata}")

    # Switch directory
    print(f"切换到：{target_dir}")
    print(f"提示：请使用 cd 命令手动切换目录")
    print(f"  cd {target_dir}")

    return 0


def build_use_parser(subparsers: Any) -> None:
    """Build the use subcommand parser."""
    use_parser = subparsers.add_parser(
        "use",
        help="Switch working directory to another project.",
    )
    use_parser.add_argument(
        "target",
        help="Target project directory path",
    )
