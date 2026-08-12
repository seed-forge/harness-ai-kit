from __future__ import annotations

import argparse

from .. import package_manager as pm
from ..domain import project_sync_presentation


def command_cache(args: argparse.Namespace) -> int:
    if args.cache_command == "list":
        items = pm.cache_inventory()
        if not items:
            print(project_sync_presentation.cache_empty_line())
            return 0
        for item in items:
            print(item)
        return 0
    if args.cache_command == "clean":
        removed = pm.clean_cache()
        print(project_sync_presentation.cache_clean_success_line(removed_count=removed))
        return 0
    raise ValueError(f"Unsupported cache command: {args.cache_command}")

