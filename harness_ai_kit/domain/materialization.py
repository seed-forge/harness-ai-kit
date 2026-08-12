from __future__ import annotations

from pathlib import Path
from typing import Iterable

from harness_ai_kit.domain.artifacts import hash_named_bytes, hash_skill_directory
from harness_ai_kit.domain.lockfile import LockNode
from harness_ai_kit.domain.policies import SOURCE_GIT_REPO, SOURCE_REPO
from harness_ai_kit.domain.versions import compare_versions_safe


def hash_directory_with_root(path: Path, root_name: str) -> str:
    entries: list[tuple[str, bytes]] = []
    for file_path in sorted(path.rglob("*")):
        if not file_path.is_file():
            continue
        relative = Path(root_name) / file_path.relative_to(path)
        entries.append((relative.as_posix(), file_path.read_bytes()))
    return hash_named_bytes(entries)


def effective_source_checksum(node: LockNode) -> str:
    return str(node.source_checksum or node.checksum or "").strip()


def effective_materialized_checksum(node: LockNode, install_mode: str) -> str:
    explicit = str(node.materialized_checksum or "").strip()
    if explicit:
        return explicit
    legacy = str(node.checksum or "").strip()
    if not legacy:
        return ""
    if node.type != "skill":
        return legacy
    if install_mode == "skill_dir":
        return legacy
    return ""


def source_materialized_checksum(
    asset_dir: Path,
    asset_id: str,
    *,
    install_mode: str,
    asset_type: str,
    wrapper_name: str = "",
    wrapper_content: bytes | None = None,
) -> str:
    if asset_type != "skill" or install_mode == "skill_dir":
        return hash_directory_with_root(asset_dir, asset_id)
    if wrapper_content is None or not wrapper_name:
        raise ValueError(f"Unsupported install mode for materialized checksum: {install_mode}")
    entries = _directory_entries(asset_dir, asset_id)
    entries.append((wrapper_name, wrapper_content))
    return hash_named_bytes(entries)


def installed_skill_materialized_checksum(
    payload_dir: Path,
    skill_id: str,
    *,
    install_mode: str,
    wrapper_path: Path | None = None,
) -> str:
    if not payload_dir.exists():
        return ""
    if install_mode == "skill_dir":
        return hash_directory_with_root(payload_dir, skill_id)
    if wrapper_path is None or not wrapper_path.exists():
        return ""
    entries = _directory_entries(payload_dir, skill_id)
    entries.append((wrapper_path.name, wrapper_path.read_bytes()))
    return hash_named_bytes(entries)


def installed_managed_asset_materialized_checksum(destination: Path, asset_id: str) -> str:
    if not destination.exists():
        return ""
    return hash_directory_with_root(destination, asset_id)


def current_source_checksum_for_node(node: LockNode) -> str:
    if node.source not in {SOURCE_REPO, SOURCE_GIT_REPO} or not node.source_ref:
        return ""
    source_path = Path(node.source_ref)
    if not source_path.exists():
        return ""
    return hash_skill_directory(source_path)


def evaluate_installed_asset_drift(
    *,
    node: LockNode | None,
    install_mode: str,
    installed_version: str,
    actual_materialized_checksum: str,
    current_source_checksum: str = "",
    current_materialized_checksum: str = "",
) -> tuple[str, str]:
    if node is None:
        return "checksum-unknown", "No lockfile node found for this installed asset."
    comparison = compare_versions_safe(installed_version, node.version)
    if comparison is None:
        return "checksum-unknown", "Installed version could not be compared to the lockfile version."
    if comparison != 0:
        return "version-mismatch", f"Installed version {installed_version} differs from locked version {node.version}."
    expected_source = effective_source_checksum(node)
    expected_materialized = effective_materialized_checksum(node, install_mode)
    if expected_source and current_source_checksum and current_source_checksum != expected_source:
        return (
            "drift-detected",
            f"Source drift detected: lockfile={expected_source}, current-source={current_source_checksum}.",
        )
    if expected_materialized and current_materialized_checksum and current_materialized_checksum != expected_materialized:
        return (
            "drift-detected",
            f"Desired materialized checksum drifted from lockfile: lockfile={expected_materialized}, current-source={current_materialized_checksum}.",
        )
    if not expected_materialized:
        return "checksum-unknown", "Lockfile does not include a materialized checksum for this runtime."
    if not actual_materialized_checksum:
        return "checksum-unknown", "Installed materialized checksum could not be computed."
    if actual_materialized_checksum != expected_materialized:
        return (
            "drift-detected",
            f"Installed materialized checksum drifted: expected {expected_materialized}, got {actual_materialized_checksum}.",
        )
    return "up-to-date", "Installed materialized checksum matches the lockfile."


def worst_drift_status(statuses: Iterable[str]) -> str:
    rank = {
        "drift-detected": 4,
        "version-mismatch": 3,
        "checksum-unknown": 2,
        "up-to-date": 1,
        "not-installed": 0,
    }
    current = "not-installed"
    for status in statuses:
        if rank.get(status, -1) > rank[current]:
            current = status
    return current


def _directory_entries(path: Path, root_name: str) -> list[tuple[str, bytes]]:
    entries: list[tuple[str, bytes]] = []
    for file_path in sorted(path.rglob("*")):
        if not file_path.is_file():
            continue
        relative = Path(root_name) / file_path.relative_to(path)
        entries.append((relative.as_posix(), file_path.read_bytes()))
    return entries
