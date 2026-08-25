"""``harness-ai-kit`` → ``harness-ai-kit`` asset-id remapping used by ``migrate``.

The rename shipped the CLI package and every ``harness-ai-kit-*`` asset to the
``harness-ai-kit-*`` namespace, and superseded a few ``devlab`` assets. The
``migrate`` command moved the manifest *file* but left the asset **ids** inside
it untouched, so already-migrated consumers kept resolving retired/old-named
assets. These helpers rewrite those stale ids in place.

Scope is deliberately manifest-only: the lockfile is a derived snapshot and is
regenerated from the (now corrected) manifest on the next ``sync`` / ``upgrade``
/ ``install``, so no fragile lock surgery is attempted here.
"""
from __future__ import annotations

from typing import Any

# Explicit 1:1 renames the prefix rule below cannot infer (same lineage).
EXPLICIT_ASSET_RENAMES: dict[str, str] = {
    "harness-ai-kit": "harness-ai-kit",     # old CLI pip package id
    "harness-ai-kit-cli": "harness-ai-kit",  # transitional duplicate alias
}

# Retire-with-replacement: old asset removed, superseded by a different asset.
ASSET_RETIREMENTS: dict[str, str] = {
    "devlab-ai-kit-ops": "devlab-harness-ops",
}

_LEGACY_PREFIX = "harness-ai-kit-"
_CANONICAL_PREFIX = "harness-ai-kit-"


def canonical_asset_id(asset_id: str) -> str:
    """Map a possibly-legacy asset id to its canonical ``harness-ai-kit`` id.

    Resolution order: retirements → explicit renames → ``harness-ai-kit-*`` prefix
    rule. Ids already canonical (or unrelated) are returned unchanged.
    """
    if asset_id in ASSET_RETIREMENTS:
        return ASSET_RETIREMENTS[asset_id]
    if asset_id in EXPLICIT_ASSET_RENAMES:
        return EXPLICIT_ASSET_RENAMES[asset_id]
    if asset_id.startswith(_LEGACY_PREFIX):
        return _CANONICAL_PREFIX + asset_id[len(_LEGACY_PREFIX):]
    return asset_id


def _remap_specs(specs: list[Any], label: str, changes: list[str]) -> list[Any]:
    """Rewrite ids in a spec list, dropping duplicates that collide post-remap."""
    seen: set[tuple[str | None, str]] = set()
    result: list[Any] = []
    for spec in specs:
        new_id = canonical_asset_id(spec.id)
        if new_id != spec.id:
            retired = spec.id in ASSET_RETIREMENTS
            suffix = " (retired)" if retired else ""
            changes.append(f"{label}: {spec.id} -> {new_id}{suffix}")
            spec = spec.model_copy(update={"id": new_id})
        key = (spec.namespace, spec.id)
        if key in seen:
            changes.append(f"{label}: dropped duplicate {spec.id}")
            continue
        seen.add(key)
        result.append(spec)
    return result


def rewrite_manifest_asset_ids(manifest: Any) -> list[str]:
    """Rewrite stale ``harness-ai-kit`` asset ids in ``manifest`` in place.

    Returns an ordered list of human-readable change descriptions (empty when
    the manifest is already canonical).
    """
    changes: list[str] = []
    manifest.roots = _remap_specs(manifest.roots, "roots", changes)
    assets = manifest.assets
    assets.skills = _remap_specs(assets.skills, "skills", changes)
    assets.clis = _remap_specs(assets.clis, "clis", changes)
    assets.plugins = _remap_specs(assets.plugins, "plugins", changes)
    assets.hooks = _remap_specs(assets.hooks, "hooks", changes)
    assets.subagents = _remap_specs(assets.subagents, "subagents", changes)
    assets.mcps = _remap_specs(assets.mcps, "mcps", changes)
    assets.loops = _remap_specs(assets.loops, "loops", changes)
    return changes
