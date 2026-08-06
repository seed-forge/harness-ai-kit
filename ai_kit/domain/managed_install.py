from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Callable

from ai_kit.domain.lockfile import Lockfile, LockNode
from ai_kit.domain.manifest_io import load_skill_manifest
from ai_kit.domain.policies import SOURCE_REPO
from ai_kit.domain.runtime_install import managed_asset_install_destination
from ai_kit.domain.versions import compare_versions_safe


ManagedAssetVersionReader = Callable[[Path, str, str, str], str]
ManagedAssetChecksumReader = Callable[[Path, str, str, str], str]
SameVersionDriftWarner = Callable[[LockNode, str, str, str, str], bool]


def install_managed_asset_directory(asset_dir: Path, target_dir: Path, runtime_id: str, asset_directory_names: dict[str, str]) -> Path:
    manifest = load_skill_manifest(asset_dir)
    destination = managed_asset_install_destination(target_dir, manifest.package_type, manifest.id, asset_directory_names)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(asset_dir, destination)
    return destination


def apply_managed_asset_lockfile(
    lockfile: Lockfile,
    target_dir: Path,
    runtime_id: str,
    asset_directory_names: dict[str, str],
    *,
    installed_version: ManagedAssetVersionReader,
    installed_materialized_checksum: ManagedAssetChecksumReader,
    warn_same_version_drift: SameVersionDriftWarner,
) -> list[tuple[LockNode, Path]]:
    installed: list[tuple[LockNode, Path]] = []
    backups: list[tuple[Path, Path | None]] = []
    managed_nodes = [node for node in lockfile.nodes if node.type in {"plugin", "hook", "subagent", "mcp", "loop"}]
    try:
        for node in managed_nodes:
            if node.source not in {SOURCE_REPO, "local"}:
                continue
            source_ref = Path(node.source_ref or "")
            destination = managed_asset_install_destination(target_dir, node.type, node.id, asset_directory_names)
            backup_path: Path | None = None
            if destination.exists():
                current_version = installed_version(target_dir, node.type, node.id, runtime_id)
                if current_version and compare_versions_safe(current_version, node.version) == 0:
                    warn_same_version_drift(
                        node,
                        runtime_id,
                        "target",
                        current_version,
                        installed_materialized_checksum(target_dir, node.type, node.id, runtime_id),
                    )
                    installed.append((node, destination))
                    backups.append((destination, None))
                    continue
                backup_root = Path(tempfile.mkdtemp(prefix=f"ai-kit-asset-backup-{node.id}-"))
                backup_path = backup_root / destination.name
                shutil.move(str(destination), str(backup_path))
            backups.append((destination, backup_path))
            installed.append((node, install_managed_asset_directory(source_ref, target_dir, runtime_id, asset_directory_names)))
    except Exception:
        for destination, backup_path in reversed(backups):
            if backup_path is None:
                continue
            if destination.exists():
                shutil.rmtree(destination, ignore_errors=True)
            shutil.move(str(backup_path), str(destination))
        raise
    finally:
        for _, backup_path in backups:
            if backup_path is not None:
                shutil.rmtree(backup_path.parent, ignore_errors=True)
    return installed
