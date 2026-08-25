from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class InstallSyncService:
    sync_command: Callable[[Any, Path], int]
    prune_command: Callable[[Any, Path], int]
    uninstall_command: Callable[[Any, Path], int]

    def sync_or_install(self, args: Any, config_path: Path) -> int:
        return self.sync_command(args, config_path)

    def prune(self, args: Any, config_path: Path) -> int:
        return self.prune_command(args, config_path)

    def uninstall(self, args: Any, config_path: Path) -> int:
        return self.uninstall_command(args, config_path)
