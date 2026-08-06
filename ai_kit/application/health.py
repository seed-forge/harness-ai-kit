from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class HealthService:
    doctor_command: Callable[[Any, Path], int]
    validate_command: Callable[[Any, Path], int]

    def doctor(self, args: Any, config_path: Path) -> int:
        return self.doctor_command(args, config_path)

    def validate(self, args: Any, config_path: Path) -> int:
        return self.validate_command(args, config_path)

