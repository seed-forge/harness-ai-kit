from __future__ import annotations

import io
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path
from pathlib import PurePosixPath
from typing import Callable

from harness_ai_kit.domain.lockfile import Lockfile, LockNode
from harness_ai_kit.domain.manifest_io import load_skill_manifest
from harness_ai_kit.domain.policies import SOURCE_PUBLIC_REGISTRY, SOURCE_REGISTRY, SOURCE_REPO
from harness_ai_kit.domain.runtime_install import managed_asset_install_destination
from harness_ai_kit.domain.versions import compare_versions_safe


ManagedAssetVersionReader = Callable[[Path, str, str, str], str]
ManagedAssetChecksumReader = Callable[[Path, str, str, str], str]
SameVersionDriftWarner = Callable[[LockNode, str, str, str, str], bool]
RegistryManagedAssetInstaller = Callable[[LockNode], Path]


def install_managed_asset_directory(asset_dir: Path, target_dir: Path, runtime_id: str, asset_directory_names: dict[str, str]) -> Path:
    manifest = load_skill_manifest(asset_dir)
    destination = managed_asset_install_destination(target_dir, manifest.package_type, manifest.id, asset_directory_names)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(asset_dir, destination)
    return destination


def install_managed_asset_archive_bytes(
    payload: bytes,
    node: LockNode,
    target_dir: Path,
    runtime_id: str,
    asset_directory_names: dict[str, str],
) -> Path:
    """Safely materialize one registry archive into its managed-asset destination."""
    destination = managed_asset_install_destination(target_dir, node.type, node.id, asset_directory_names)
    destination.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        members: list[tuple[zipfile.ZipInfo, tuple[str, ...]]] = []
        seen_paths: set[tuple[str, ...]] = set()
        for info in archive.infolist():
            if not info.filename or "\\" in info.filename:
                raise ValueError(f"Managed asset archive contains an invalid path: {info.filename!r}")
            member_path = PurePosixPath(info.filename)
            parts = member_path.parts
            if (
                member_path.is_absolute()
                or not parts
                or any(part in {"", ".", ".."} for part in parts)
                or parts[0] != node.id
            ):
                raise ValueError(
                    f"Managed asset archive for {node.id} must contain only the '{node.id}/' top-level directory."
                )
            if stat.S_ISLNK(info.external_attr >> 16):
                raise ValueError(f"Managed asset archive contains a symbolic link: {info.filename!r}")
            if parts in seen_paths:
                raise ValueError(f"Managed asset archive contains a duplicate path: {info.filename!r}")
            seen_paths.add(parts)
            members.append((info, parts))

        with tempfile.TemporaryDirectory(
            prefix=f"harness-ai-kit-{node.type}-{node.id}-",
            dir=destination.parent,
        ) as staging_dir:
            staging_root = Path(staging_dir)
            for info, parts in members:
                target = staging_root.joinpath(*parts)
                if info.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output)

            asset_dir = staging_root / node.id
            if not asset_dir.is_dir():
                raise ValueError(f"Managed asset archive for {node.id} does not contain an asset directory.")
            manifest = load_skill_manifest(asset_dir)
            if manifest.id != node.id or manifest.package_type != node.type:
                raise ValueError(
                    f"Managed asset archive metadata mismatch for {node.id}: "
                    f"id={manifest.id!r}, package_type={manifest.package_type!r}."
                )
            if manifest.version != node.version:
                raise ValueError(
                    f"Managed asset archive version mismatch for {node.id}: "
                    f"expected {node.version}, got {manifest.version}."
                )
            if destination.exists():
                raise ValueError(f"Managed asset destination already exists: {destination}")
            shutil.move(str(asset_dir), str(destination))
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
    install_registry_asset: RegistryManagedAssetInstaller | None = None,
) -> list[tuple[LockNode, Path]]:
    installed: list[tuple[LockNode, Path]] = []
    backups: list[tuple[Path, Path | None]] = []
    managed_nodes = [node for node in lockfile.nodes if node.type in {"plugin", "hook", "subagent", "mcp", "loop"}]
    try:
        for node in managed_nodes:
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
                backup_root = Path(tempfile.mkdtemp(prefix=f"harness-ai-kit-asset-backup-{node.id}-"))
                backup_path = backup_root / destination.name
                shutil.move(str(destination), str(backup_path))
            backups.append((destination, backup_path))
            if node.source in {SOURCE_REPO, "local"}:
                source_ref = Path(node.source_ref or "")
                installed.append((node, install_managed_asset_directory(source_ref, target_dir, runtime_id, asset_directory_names)))
            elif node.source in {SOURCE_REGISTRY, SOURCE_PUBLIC_REGISTRY}:
                if install_registry_asset is None:
                    raise ValueError(
                        f"No registry installer is configured for {node.type} {node.id}@{node.version}."
                    )
                installed.append((node, install_registry_asset(node)))
            else:
                raise ValueError(f"Unsupported install source for {node.type} {node.id}: {node.source}")
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
