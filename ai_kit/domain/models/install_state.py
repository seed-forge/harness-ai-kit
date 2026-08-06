"""Install state and location dataclasses."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class InstalledSkillLocation:
    runtime: str
    scope: str
    path: Path
    version: str
    drift_status: str = "checksum-unknown"
    drift_message: str = ""


@dataclass(frozen=True)
class SkillInstallState:
    installed: bool
    installed_versions: tuple[str, ...]
    installed_locations: tuple[InstalledSkillLocation, ...]
    upgrade_status: str
    drift_status: str = "not-installed"


@dataclass(frozen=True)
class InstalledManagedAssetLocation:
    runtime: str
    scope: str
    path: Path
    version: str
    drift_status: str = "checksum-unknown"
    drift_message: str = ""


@dataclass(frozen=True)
class ManagedAssetInstallState:
    installed: bool
    installed_versions: tuple[str, ...]
    installed_locations: tuple[InstalledManagedAssetLocation, ...]
    drift_status: str = "not-installed"


@dataclass(frozen=True)
class CliInstallState:
    installed: bool
    installed_version: str
    upgrade_status: str
