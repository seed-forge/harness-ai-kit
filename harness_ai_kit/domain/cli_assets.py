from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from harness_ai_kit.domain.identity import canonical_package_id
from harness_ai_kit.domain.lockfile import Lockfile, LockNode
from harness_ai_kit.domain.versions import spec_matches_version


def cli_nodes_from_lock(lockfile: Lockfile) -> list[LockNode]:
    return [node for node in lockfile.nodes if node.type == "cli"]


def select_cli_record_for_spec(inventory: Mapping[str, Any], spec: Any) -> Any:
    record = inventory.get(spec.id)
    if record is None:
        available = ", ".join(sorted(inventory))
        raise KeyError(f"Unknown CLI ID: {spec.id}. Available CLIs: {available}")
    if spec.namespace is not None:
        raise ValueError(
            f"CLI namespaces are not supported yet for project declarations: {canonical_package_id(spec.id, spec.namespace)}"
        )
    from packaging.specifiers import InvalidSpecifier, SpecifierSet
    from packaging.version import InvalidVersion, Version
    try:
        satisfied = Version(record.version) in SpecifierSet(spec.version)
    except (InvalidSpecifier, InvalidVersion) as exc:
        raise ValueError(
            f"CLI {spec.id} has invalid version specifier {spec.version}: {exc}"
        ) from exc
    if not satisfied:
        raise ValueError(_cli_version_mismatch_message(spec.id, spec.version, record.version))
    return record


def _cli_version_mismatch_message(cli_id: str, pinned: str, available: str) -> str:
    """Consumer-actionable message for a CLI pin the registry can't satisfy.

    The usual cause is a stale exact pin (``==x.y.z``) left in the project's
    ``harness-ai-kit.yml`` / ``.lock`` from when that version was current — not a
    missing publish. Lead with the consumer fix; keep the maintainer path last so
    a consumer isn't told to "publish" something they only need to repoint.
    """
    if pinned.strip().startswith("=="):
        fix = (
            f"多为本地 harness-ai-kit.yml / .lock 的陈旧精确 pin："
            f"`harness-ai-kit add cli {cli_id}` 重指为 latest，"
            f"或把 {cli_id} 的 version 改成 >= 兼容区间后 `harness-ai-kit sync`。"
        )
    else:
        fix = f"请把 {cli_id} 的版本约束调为与可用版本兼容（推荐 >=）后 `harness-ai-kit sync`。"
    return (
        f"CLI {cli_id} 声明版本 {pinned}，但可用版本是 {available}（不满足）。{fix}"
        f"（维护者若确需 {pinned}：先发布该版本到 registry。）"
    )


def _cli_dependency_mismatch_message(cli_id: str, dep_id: str, spec: str, available: str) -> str:
    """CLI→CLI 依赖 pin 无法被 registry 满足（元数据层）。口径与单体 pin 一致。"""
    return (
        f"CLI {cli_id} 依赖 {dep_id} {spec}，但可用版本是 {available}（不满足）。"
        f"requires `{dep_id}` {spec}; "
        f"多为 {cli_id} 元数据里的陈旧依赖 pin：`harness-ai-kit upgrade --all` 升级到已放宽依赖的新版；"
        f"维护者：把 {cli_id} 的 {dep_id} 依赖改为 >= 兼容区间并重发，或发布满足 {spec} 的 {dep_id}。"
    )


def _cli_lockfile_mismatch_message(cli_id: str, locked: str, available: str) -> str:
    """Lockfile 钉死的精确版本 registry 不再供应。口径与单体 pin 一致。"""
    return (
        f"lock 文件钉住 {cli_id}@{locked}，但可用版本是 {available}（registry 已更新）。"
        f"刷新 lock：`harness-ai-kit sync`（或 `harness-ai-kit upgrade --all`）重解；"
        f"仍不符再 `harness-ai-kit install --refresh-lock`。"
    )


def required_cli_dependency_entries(metadata: Mapping[str, object]) -> list[dict[str, str]]:
    raw_dependencies = metadata.get("dependencies", [])
    if not isinstance(raw_dependencies, list):
        return []

    entries: list[dict[str, str]] = []
    for item in raw_dependencies:
        if not isinstance(item, Mapping):
            continue
        dependency_type = str(item.get("type", "")).strip()
        if dependency_type != "cli":
            continue
        scope = str(item.get("scope", "required")).strip() or "required"
        if scope != "required":
            continue
        dependency_id = str(item.get("id", "")).strip()
        if not dependency_id:
            raise ValueError("CLI dependency entry is missing `id`.")
        namespace = str(item.get("namespace", "")).strip()
        if namespace:
            raise ValueError(
                f"CLI dependency namespaces are not supported yet: {canonical_package_id(dependency_id, namespace)}"
            )
        version = str(item.get("version", "")).strip()
        if not version:
            raise ValueError(f"CLI dependency `{dependency_id}` is missing `version`.")
        entries.append({"id": dependency_id, "version": version})
    return entries


def expand_cli_records_with_dependencies(
    records: list[Any],
    inventory: Mapping[str, Any],
    metadata_loader: Callable[[Any], Mapping[str, object]],
) -> list[Any]:
    ordered: list[Any] = []
    seen: set[str] = set()
    visiting: set[str] = set()

    def visit(record: Any) -> None:
        cli_id = str(record.cli_id)
        if cli_id in seen:
            return
        if cli_id in visiting:
            cycle = " -> ".join([*visiting, cli_id])
            raise ValueError(f"Cyclic CLI dependency detected: {cycle}")

        visiting.add(cli_id)
        metadata = metadata_loader(record)
        for dependency in required_cli_dependency_entries(metadata):
            dependency_id = dependency["id"]
            dependency_record = inventory.get(dependency_id)
            if dependency_record is None:
                available = ", ".join(sorted(inventory))
                raise KeyError(
                    f"CLI `{cli_id}` depends on unknown CLI `{dependency_id}`. Available CLIs: {available}"
                )
            if not spec_matches_version(dependency["version"], dependency_record.version):
                raise ValueError(
                    _cli_dependency_mismatch_message(
                        cli_id, dependency_id, dependency["version"], dependency_record.version
                    )
                )
            visit(dependency_record)

        visiting.remove(cli_id)
        seen.add(cli_id)
        ordered.append(record)

    for record in records:
        visit(record)
    return ordered


def select_target_cli_record(records: list[Any], cli_id: str) -> Any:
    """Pick the requested CLI record from a dependency-expanded record list.

    `expand_cli_records_with_dependencies` returns records in dependency-first
    topological order, so the requested CLI is never guaranteed to be at index 0.
    Publish/submit flows must use this helper instead of `records[0]` to avoid
    silently operating on a dependency instead of the requested asset.
    """
    for record in records:
        if str(record.cli_id) == cli_id:
            return record
    resolved = ", ".join(str(record.cli_id) for record in records)
    raise KeyError(f"CLI `{cli_id}` was not found in the resolved records: {resolved}")


def select_cli_records_for_lock(lockfile: Lockfile, inventory: Mapping[str, Any]) -> list[Any]:
    records: list[Any] = []
    seen: set[str] = set()
    for node in cli_nodes_from_lock(lockfile):
        if node.id in seen:
            continue
        record = inventory.get(node.id)
        if record is None:
            raise KeyError(f"CLI required by lockfile is not available: {node.id}")
        if record.version != node.version:
            raise ValueError(
                _cli_lockfile_mismatch_message(node.id, node.version, record.version)
            )
        records.append(record)
        seen.add(node.id)
    return records
