from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class UpgradeService:
    outdated_command: Callable[[Any, Path], int]
    diff_command: Callable[[Any, Path], int]
    upgrade_command: Callable[[Any, Path], int]

    def outdated(self, args: Any, config_path: Path) -> int:
        return self.outdated_command(args, config_path)

    def diff(self, args: Any, config_path: Path) -> int:
        return self.diff_command(args, config_path)

    def upgrade(self, args: Any, config_path: Path) -> int:
        return self.upgrade_command(args, config_path)
