"""Core record dataclasses for skills and CLI assets."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SkillRecord:
    skill_id: str
    path: Path | None
    name: str
    status: str
    owner: str
    version: str
    summary: str
    source: str = "local"
    metadata_url: str = ""
    asset_type: str = "skill"


@dataclass(frozen=True)
class CliAssetRecord:
    cli_id: str
    path: Path | None
    name: str
    status: str
    owner: str
    version: str
    summary: str
    package_name: str
    install_type: str
    command_name: str
    publish_paths: tuple[str, ...]
    source: str = "local"
    metadata_url: str = ""
    dependencies: tuple[dict[str, object], ...] = ()
    runtime_requirements: tuple[str, ...] = ()


@dataclass(frozen=True)
class PluginRecord:
    """Metadata for a plugin asset (package_type=plugin) with host adapters."""

    plugin_id: str
    path: Path | None
    name: str
    status: str
    owner: str
    version: str
    summary: str
    hosts: tuple[str, ...] = ()
    npm_name: str = ""
    default_profile: str = ""
    default_scope: str = "global"
    source: str = "local"
    metadata_url: str = ""
