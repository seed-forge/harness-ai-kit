from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PublishReleaseService:
    publish_skill_command: Callable[[Any, Path], int]
    publish_cli_command: Callable[[Any, Path], int]
    publish_command: Callable[[Any, Path], int]
    release_command: Callable[[Any, Path], int]

    def publish_skill(self, args: Any, config_path: Path) -> int:
        return self.publish_skill_command(args, config_path)

    def publish_cli(self, args: Any, config_path: Path) -> int:
        return self.publish_cli_command(args, config_path)

    def publish(self, args: Any, config_path: Path) -> int:
        return self.publish_command(args, config_path)

    def release(self, args: Any, config_path: Path) -> int:
        return self.release_command(args, config_path)
