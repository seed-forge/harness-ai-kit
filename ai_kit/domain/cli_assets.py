from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from ai_kit.domain.identity import canonical_package_id
from ai_kit.domain.lockfile import Lockfile, LockNode
from ai_kit.domain.versions import spec_matches_version


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
    from packaging.specifiers import SpecifierSet
    from packaging.version import Version
    try:
        if Version(record.version) not in SpecifierSet(spec.version):
            raise ValueError(
                f"CLI {spec.id} requires {spec.version} but the available version is {record.version}. Publish or select a matching version first."
            )
    except Exception as exc:
        if "available version" in str(exc):
            raise
        raise ValueError(
            f"CLI {spec.id} has invalid version specifier {spec.version}: {exc}"
        ) from exc
    return record


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
                    f"CLI `{cli_id}` requires `{dependency_id}` {dependency['version']}, "
                    f"but the available version is {dependency_record.version}."
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
                f"CLI lockfile requires {node.id}@{node.version}, but the available version is {record.version}."
            )
        records.append(record)
        seen.add(node.id)
    return records
