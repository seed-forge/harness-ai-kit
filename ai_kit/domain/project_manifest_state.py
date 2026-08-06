from __future__ import annotations

from typing import Any, Callable

from ai_kit.domain.identity import canonical_package_id, package_key_for, split_canonical_id
from ai_kit.domain.lockfile import Lockfile, RootRequest


VERSIONED_ASSET_KINDS = ("cli", "plugin", "hook", "subagent", "mcp", "loop")
ManifestFactory = Callable[[str, str, list[str]], Any]
RootSpecFactory = Callable[
    [str | None, str, list[str], list[str], str | None, str | None, str | None, str | None],
    Any,
]
VersionedSpecFactory = Callable[[str | None, str, str], Any]


def declared_skill_specs(manifest: Any) -> list[Any]:
    if manifest.assets.skills:
        return list(manifest.assets.skills)
    return list(manifest.roots)


def declared_versioned_specs(manifest: Any, asset_kind: str) -> list[Any]:
    if asset_kind == "cli":
        return list(manifest.assets.clis)
    if asset_kind == "plugin":
        return list(manifest.assets.plugins)
    if asset_kind == "hook":
        return list(manifest.assets.hooks)
    if asset_kind == "subagent":
        return list(manifest.assets.subagents)
    if asset_kind == "mcp":
        return list(manifest.assets.mcps)
    if asset_kind == "loop":
        return list(manifest.assets.loops)
    raise ValueError(f"Unsupported versioned asset kind: {asset_kind}")


def manifest_has_declared_assets(manifest: Any) -> bool:
    return bool(
        declared_skill_specs(manifest)
        or any(declared_versioned_specs(manifest, asset_kind) for asset_kind in VERSIONED_ASSET_KINDS)
    )


def project_root_ids(manifest: Any) -> list[str]:
    return [canonical_package_id(item.id, item.namespace) for item in declared_skill_specs(manifest)]


def manifest_declared_features(manifest: Any) -> list[str]:
    features = list(manifest.features)
    for item in declared_skill_specs(manifest):
        features.extend(item.features)
    deduped: list[str] = []
    for item in features:
        feature = str(item).strip()
        if feature and feature not in deduped:
            deduped.append(feature)
    return deduped


def project_manifest_root_requests(manifest: Any) -> list[RootRequest]:
    requests: list[RootRequest] = []
    for item in declared_skill_specs(manifest):
        requests.append(
            RootRequest(
                type="skill",
                namespace=item.namespace,
                id=item.id,
                feature_refs=list(item.features),
                source_policy=list(item.sources),
                source_ref=item.source_ref,
                ref=item.ref,
                subpath=item.subpath,
                version=item.version,
                extends=item.extends if hasattr(item, "extends") and item.extends else [],  # type: ignore[union-attr]
            )
        )
    for item in declared_versioned_specs(manifest, "cli"):
        requests.append(RootRequest(type="cli", namespace=item.namespace, id=item.id, version=item.version))
    for item in declared_versioned_specs(manifest, "plugin"):
        requests.append(RootRequest(type="plugin", namespace=item.namespace, id=item.id, version=item.version))
    for item in declared_versioned_specs(manifest, "hook"):
        requests.append(RootRequest(type="hook", namespace=item.namespace, id=item.id, version=item.version))
    for item in declared_versioned_specs(manifest, "subagent"):
        requests.append(RootRequest(type="subagent", namespace=item.namespace, id=item.id, version=item.version))
    for item in declared_versioned_specs(manifest, "mcp"):
        requests.append(RootRequest(type="mcp", namespace=item.namespace, id=item.id, version=item.version))
    for item in declared_versioned_specs(manifest, "loop"):
        requests.append(RootRequest(type="loop", namespace=item.namespace, id=item.id, version=item.version))
    return requests


def add_skill_to_manifest(manifest: Any, spec: Any) -> bool:
    existing = {canonical_package_id(item.id, item.namespace): item for item in declared_skill_specs(manifest)}
    key = canonical_package_id(spec.id, spec.namespace)
    if key in existing:
        return False
    manifest.assets.skills.append(spec)
    manifest.roots = list(manifest.assets.skills)
    return True


def add_versioned_asset_to_manifest(items: list[Any], spec: Any) -> bool:
    key = canonical_package_id(spec.id, spec.namespace)
    for item in items:
        if canonical_package_id(item.id, item.namespace) == key:
            return False
    items.append(spec)
    return True


def manifest_bucket_for_asset(manifest: Any, asset_kind: str) -> list[Any]:
    if asset_kind == "skill":
        return manifest.assets.skills
    if asset_kind == "cli":
        return manifest.assets.clis
    if asset_kind == "plugin":
        return manifest.assets.plugins
    if asset_kind == "hook":
        return manifest.assets.hooks
    if asset_kind == "subagent":
        return manifest.assets.subagents
    if asset_kind == "mcp":
        return manifest.assets.mcps
    if asset_kind == "loop":
        return manifest.assets.loops
    raise ValueError(f"Unsupported asset kind for manifest mutation: {asset_kind}")


def remove_asset_from_manifest(manifest: Any, asset_kind: str, asset_id: str) -> bool:
    namespace, base_id = split_canonical_id(asset_id)
    if asset_kind == "skill":
        original = len(manifest.assets.skills)
        manifest.assets.skills = [
            item for item in manifest.assets.skills if not (item.id == base_id and item.namespace == namespace)
        ]
        manifest.roots = list(manifest.assets.skills)
        return len(manifest.assets.skills) != original
    items = manifest_bucket_for_asset(manifest, asset_kind)
    original = len(items)
    filtered = [item for item in items if not (item.id == base_id and item.namespace == namespace)]
    if asset_kind == "cli":
        manifest.assets.clis = filtered
    elif asset_kind == "plugin":
        manifest.assets.plugins = filtered
    elif asset_kind == "hook":
        manifest.assets.hooks = filtered
    elif asset_kind == "subagent":
        manifest.assets.subagents = filtered
    elif asset_kind == "mcp":
        manifest.assets.mcps = filtered
    elif asset_kind == "loop":
        manifest.assets.loops = filtered
    else:
        raise ValueError(f"Unsupported asset kind for manifest mutation: {asset_kind}")
    return len(filtered) != original


def project_manifest_from_lockfile(
    lockfile: Lockfile,
    *,
    create_manifest: ManifestFactory,
    create_root_spec: RootSpecFactory,
    create_versioned_spec: VersionedSpecFactory,
) -> Any:
    manifest = create_manifest(lockfile.runtime, lockfile.install_scope, list(lockfile.features))
    nodes_by_key = {package_key_for(node.type, node.id, node.namespace): node for node in lockfile.nodes}
    if lockfile.root_requests:
        for request in lockfile.root_requests:
            if request.type == "skill":
                manifest.assets.skills.append(
                    create_root_spec(
                        request.namespace,
                        request.id,
                        list(request.feature_refs),
                        list(request.source_policy),
                        request.source_ref,
                        request.ref,
                        request.subpath,
                        request.version,
                    )
                )
                continue
            node = nodes_by_key.get(package_key_for(request.type, request.id, request.namespace))
            version = request.version or (f"=={node.version}" if node is not None else None)
            if version is None:
                continue
            spec = create_versioned_spec(request.namespace, request.id, version)
            if request.type == "cli":
                manifest.assets.clis.append(spec)
            elif request.type == "plugin":
                manifest.assets.plugins.append(spec)
            elif request.type == "hook":
                manifest.assets.hooks.append(spec)
            elif request.type == "subagent":
                manifest.assets.subagents.append(spec)
            elif request.type == "mcp":
                manifest.assets.mcps.append(spec)
            elif request.type == "loop":
                manifest.assets.loops.append(spec)
    else:
        for root_id in lockfile.roots:
            namespace, skill_id = split_canonical_id(root_id)
            manifest.assets.skills.append(create_root_spec(namespace, skill_id, [], [], None, None, None, None))
    manifest.roots = list(manifest.assets.skills)
    return manifest
