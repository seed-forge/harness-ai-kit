from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from harness_ai_kit.domain.identity import canonical_package_id, package_key_for
from harness_ai_kit.domain.lockfile import Lockfile, LockNode, RootRequest
from harness_ai_kit.domain.policies import SOURCE_REGISTRY, SOURCE_REPO


@dataclass(frozen=True)
class CliLockEntry:
    spec: Any
    record: Any


@dataclass(frozen=True)
class ManagedAssetLockEntry:
    asset_type: str
    spec: Any
    record: Any
    companion_docs: Mapping[str, str | bool]
    environment: Mapping[str, Any]
    runtime_requirements: Sequence[str]
    post_install_hints: Sequence[str]
    recommended_tools: Sequence[str]
    contributors: Sequence[dict[str, str]]
    skill_type: str
    agents_md_inject: str = ""
    config_schema: str | None = None


def cli_lock_source_for_record(record: Any) -> tuple[str, str | None]:
    if record.source == "registry":
        return SOURCE_REGISTRY, None
    if record.path is not None:
        return SOURCE_REPO, str(record.path)
    return str(record.source), None


def cli_lock_node_from_entry(entry: CliLockEntry) -> LockNode:
    spec = entry.spec
    record = entry.record
    source, source_ref = cli_lock_source_for_record(record)
    metadata_url = str(getattr(record, "metadata_url", "") or "").strip() or None
    return LockNode(
        type="cli",
        namespace=spec.namespace,
        id=record.cli_id,
        canonical_id=canonical_package_id(record.cli_id, spec.namespace),
        version=record.version,
        source=source,
        source_ref=source_ref,
        metadata_url=metadata_url,
    )


def replace_declared_cli_lock_nodes(
    nodes: Sequence[LockNode],
    entries: Sequence[CliLockEntry],
    *,
    declared_cli_ids: set[str],
) -> list[LockNode]:
    if not declared_cli_ids:
        return list(nodes)
    preserved = [node for node in nodes if not (node.type == "cli" and node.id in declared_cli_ids)]
    merged = list(preserved)
    nodes_by_key = {package_key_for(node.type, node.id, node.namespace): node for node in merged}
    for entry in entries:
        spec = entry.spec
        record = entry.record
        if record.cli_id not in declared_cli_ids:
            continue
        key = package_key_for("cli", record.cli_id, spec.namespace)
        existing = nodes_by_key.get(key)
        new_node = cli_lock_node_from_entry(entry)
        if existing is not None and existing.version != new_node.version:
            raise ValueError(
                f"CLI {record.cli_id} is already required via skill dependencies at {existing.version}, "
                f"which conflicts with the project pin {spec.version}."
            )
        if existing is not None:
            merged = [node for node in merged if package_key_for(node.type, node.id, node.namespace) != key]
            nodes_by_key.pop(key, None)
        merged.append(new_node)
        nodes_by_key[key] = new_node
    return merged


def append_cli_lock_nodes(nodes: Sequence[LockNode], entries: Sequence[CliLockEntry]) -> list[LockNode]:
    merged = list(nodes)
    nodes_by_key = {package_key_for(node.type, node.id, node.namespace): node for node in merged}
    for entry in entries:
        spec = entry.spec
        record = entry.record
        key = package_key_for("cli", record.cli_id, spec.namespace)
        existing = nodes_by_key.get(key)
        if existing is not None:
            if existing.version != record.version:
                raise ValueError(
                    f"CLI {record.cli_id} is already required via skill dependencies at {existing.version}, which conflicts with the project pin {spec.version}."
                )
            continue
        node = LockNode(
            type="cli",
            namespace=spec.namespace,
            id=record.cli_id,
            canonical_id=canonical_package_id(record.cli_id, spec.namespace),
            version=record.version,
            source=record.source,
            source_ref=str(record.path) if record.path is not None else None,
        )
        merged.append(node)
        nodes_by_key[key] = node
    return merged


def append_managed_asset_lock_nodes(nodes: Sequence[LockNode], entries: Sequence[ManagedAssetLockEntry]) -> list[LockNode]:
    merged = list(nodes)
    nodes_by_key = {package_key_for(node.type, node.id, node.namespace): node for node in merged}
    for entry in entries:
        spec = entry.spec
        record = entry.record
        key = package_key_for(entry.asset_type, record.skill_id, spec.namespace)
        existing = nodes_by_key.get(key)
        if existing is not None:
            if existing.version != record.version:
                raise ValueError(
                    f"{entry.asset_type.title()} {record.skill_id} is already required via skill dependencies at {existing.version}, which conflicts with the project pin {spec.version}."
                )
            continue
        node = LockNode(
            type=entry.asset_type,
            namespace=spec.namespace,
            id=record.skill_id,
            canonical_id=canonical_package_id(record.skill_id, spec.namespace),
            version=record.version,
            source=SOURCE_REPO if record.source == "local" else record.source,
            source_ref=str(record.path) if record.path is not None else None,
            companion_docs=dict(entry.companion_docs),
            environment=dict(entry.environment),
            runtime_requirements=list(entry.runtime_requirements),
            post_install_hints=list(entry.post_install_hints),
            recommended_tools=list(entry.recommended_tools),
            contributors=list(entry.contributors),
            skill_type=entry.skill_type,
            agents_md_inject=entry.agents_md_inject,
            config_schema=entry.config_schema,
        )
        merged.append(node)
        nodes_by_key[key] = node
    return merged


def assemble_project_lockfile(
    *,
    generated_at: str,
    runtime: str,
    install_scope: str,
    roots: Sequence[str],
    features: Sequence[str],
    root_requests: Sequence[RootRequest],
    base_nodes: Sequence[LockNode],
    cli_entries: Sequence[CliLockEntry] = (),
    managed_entries: Sequence[ManagedAssetLockEntry] = (),
) -> Lockfile:
    nodes = append_cli_lock_nodes(base_nodes, cli_entries)
    nodes = append_managed_asset_lock_nodes(nodes, managed_entries)
    return Lockfile(
        generated_at=generated_at,
        runtime=runtime,
        install_scope=install_scope,
        roots=list(roots),
        features=list(features),
        root_requests=list(root_requests),
        nodes=nodes,
    )
