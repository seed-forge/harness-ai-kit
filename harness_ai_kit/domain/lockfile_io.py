from __future__ import annotations

import json
import os
from pathlib import Path

from harness_ai_kit.product import active_product_profile
from harness_ai_kit.domain.identity import canonical_package_id, normalize_namespace, package_key_for, split_canonical_id
from harness_ai_kit.domain.lockfile import LockNode, Lockfile
from harness_ai_kit.domain.manifest_io import find_lock_node
from harness_ai_kit.domain.resolution import ResolutionPlan


LOCKFILE_NAME = "harness-ai-kit.lock"


def active_lockfile_name() -> str:
    return active_product_profile().lockfile_name


def state_dir() -> Path:
    return Path.home() / active_product_profile().config_dirname / "state"


def lockfile_path(base_dir: Path | None = None) -> Path:
    return (base_dir or Path.cwd()).resolve() / active_lockfile_name()


def _write_lockfile_payload(payload: dict[str, object], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    temp_path = output_path.parent / f".{output_path.name}.tmp"
    try:
        if temp_path.exists():
            temp_path.unlink()
        temp_path.write_text(text, encoding="utf-8", newline="")
        os.replace(temp_path, output_path)
    finally:
        if temp_path.exists():
            temp_path.unlink()
    return output_path


def write_lockfile(plan: ResolutionPlan, output_path: Path) -> Path:
    return _write_lockfile_payload(plan.to_lockfile().model_dump(mode="json"), output_path)


def write_lockfile_model(lockfile: Lockfile, output_path: Path) -> Path:
    return _write_lockfile_payload(lockfile.model_dump(mode="json"), output_path)


def read_lockfile(path: Path) -> Lockfile:
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["schema_version"] = str(payload.get("schema_version") or "2")
    if "root_requests" not in payload:
        payload["root_requests"] = [{"type": "skill", "id": root_id} for root_id in payload.get("roots", [])]
    for node in payload.get("nodes", []):
        namespace = normalize_namespace(node.get("namespace"))
        node["namespace"] = namespace
        if not node.get("canonical_id") and node.get("id"):
            node["canonical_id"] = canonical_package_id(str(node["id"]), namespace)
    return Lockfile.model_validate(payload)


def topological_skill_nodes(plan: ResolutionPlan) -> list[LockNode]:
    nodes_by_key = {package_key_for(node.type, node.id, node.namespace): node for node in plan.nodes}
    visited: set[str] = set()
    ordered: list[LockNode] = []

    def visit(key: str) -> None:
        if key in visited:
            return
        visited.add(key)
        for child in plan.dependency_edges.get(key, []):
            if child in nodes_by_key:
                visit(child)
        if key in nodes_by_key and nodes_by_key[key].type == "skill":
            ordered.append(nodes_by_key[key])

    if plan.root_requests:
        for request in plan.root_requests:
            root_key = package_key_for(request.type, request.id, request.namespace)
            if root_key in nodes_by_key:
                visit(root_key)
        # Defensive fallback: when root_requests exist but namespace mismatch
        # caused zero matches, retry via roots[].
        if not ordered and plan.roots:
            visited.clear()
            for root_id in plan.roots:
                root_node = find_lock_node(plan.nodes, "skill", root_id)
                if root_node is not None:
                    visit(package_key_for("skill", root_id, root_node.namespace))
        return ordered
    for root_id in plan.roots:
        root_node = find_lock_node(plan.nodes, "skill", root_id)
        root_namespace = root_node.namespace if root_node else None
        visit(package_key_for("skill", root_id, root_namespace))
    return ordered


def topological_skill_nodes_from_lock(lockfile: Lockfile) -> list[LockNode]:
    nodes_by_key = {package_key_for(node.type, node.id, node.namespace): node for node in lockfile.nodes}
    visited: set[str] = set()
    ordered: list[LockNode] = []

    def visit(key: str) -> None:
        if key in visited:
            return
        visited.add(key)
        node = nodes_by_key[key]

        # Visit requires dependencies first
        for child in node.requires:
            if child in nodes_by_key:
                visit(child)

        # Visit extends edges so base skills install before extending skills.
        # node.extends entries use canonical_id format (e.g. "team/infra-ops").
        # Convert to package_key_for("skill", ...) for lookup.
        for ext_edge in (node.extends or []):
            base_canonical_id = str(ext_edge.get("base_skill_id", ""))
            if not base_canonical_id:
                continue
            namespace, skill_id = split_canonical_id(base_canonical_id)
            base_key = package_key_for("skill", skill_id, namespace)
            if base_key in nodes_by_key and base_key not in visited:
                visit(base_key)

        if node.type == "skill":
            ordered.append(node)

    if lockfile.root_requests:
        for request in lockfile.root_requests:
            root_key = package_key_for(request.type, request.id, request.namespace)
            if root_key in nodes_by_key:
                visit(root_key)
        # Defensive fallback: when root_requests exist but namespace mismatch
        # caused zero matches (e.g. old lockfiles with namespace=None
        # root_requests but namespace="team" nodes), retry via roots[].
        if not ordered and lockfile.roots:
            visited.clear()
            for root_id in lockfile.roots:
                root_node = find_lock_node(lockfile.nodes, "skill", root_id)
                if root_node is not None:
                    visit(package_key_for("skill", root_id, root_node.namespace))
        return ordered
    for root_id in lockfile.roots:
        root_node = find_lock_node(lockfile.nodes, "skill", root_id)
        visit(package_key_for("skill", root_id, root_node.namespace if root_node else None))
    return ordered


def tree_lines(plan: ResolutionPlan) -> list[str]:
    nodes_by_key = {package_key_for(node.type, node.id, node.namespace): node for node in plan.nodes}
    lines: list[str] = []

    def visit(key: str, ancestors: list[bool]) -> None:
        node = nodes_by_key[key]
        display_id = node.canonical_id or canonical_package_id(node.id, node.namespace)
        if not ancestors:
            lines.append(f"{node.type}:{display_id}@{node.version} [{node.source}]")
        else:
            prefix = "".join("   " if ancestor_last else "|  " for ancestor_last in ancestors[:-1])
            connector = "\\- " if ancestors[-1] else "+- "
            lines.append(f"{prefix}{connector}{node.type}:{display_id}@{node.version} [{node.source}]")
        children = plan.dependency_edges.get(key, [])
        for index, child in enumerate(children):
            visit(child, [*ancestors, index == len(children) - 1])

    if plan.root_requests:
        for request in plan.root_requests:
            root_key = package_key_for(request.type, request.id, request.namespace)
            if root_key in nodes_by_key:
                visit(root_key, [])
        return lines
    for root in plan.roots:
        root_node = find_lock_node(plan.nodes, "skill", root)
        root_namespace = root_node.namespace if root_node else None
        visit(package_key_for("skill", root, root_namespace), [])
    return lines


def reverse_dependencies(plan: ResolutionPlan, dependency_key: str) -> list[str]:
    owners: list[str] = []
    for owner, children in plan.dependency_edges.items():
        if dependency_key in children:
            owners.append(owner)
    return owners
