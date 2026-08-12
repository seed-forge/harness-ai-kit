from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class InitProjectRequest:
    cwd: Path
    runtime: str
    scope: str
    root_refs: Sequence[str]
    features: Sequence[str]
    force: bool


@dataclass(frozen=True)
class InitProjectResult:
    manifest_path: Path


@dataclass(frozen=True)
class ManifestMigrateRequest:
    target_dir: str | Path | None
    dry_run: bool


@dataclass(frozen=True)
class ManifestMigrateResult:
    manifest_path: Path
    payload_text: str | None = None
    lock_path: Path | None = None
    backup_path: Path | None = None


@dataclass(frozen=True)
class ProjectAddRequest:
    config_path: Path
    target_dir: str | Path | None
    runtime: str | None
    scope: str | None
    repo_root: str | None
    asset_kind: str
    asset_id: str
    version: str | None
    source_ref: str | None
    ref: str | None
    subpath: str | None
    override_id: str | None
    no_install: bool
    sync_repo: bool
    offline: bool
    no_input: bool = False
    extends: list[str] | None = None
    extends_version: str | None = None
    extends_strategy: str | None = None


@dataclass(frozen=True)
class ProjectAddResult:
    manifest_path: Path
    asset_kind: str
    asset_id: str
    changed: bool
    no_install: bool
    lock_path: Path | None = None


@dataclass(frozen=True)
class ProjectRemoveRequest:
    config_path: Path
    target_dir: str | Path | None
    runtime: str | None
    scope: str | None
    repo_root: str | None
    asset_kind: str
    asset_id: str
    no_install: bool
    sync_repo: bool
    offline: bool


@dataclass(frozen=True)
class ProjectRemoveResult:
    manifest_path: Path
    asset_kind: str
    asset_id: str
    no_install: bool
    lock_path: Path | None = None
    removed_skills: Sequence[str] = ()
    removed_assets: Sequence[str] = ()
