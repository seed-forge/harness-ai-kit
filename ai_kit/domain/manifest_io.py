from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

from pydantic import ValidationError

from ai_kit.domain.identity import canonical_package_id, split_canonical_id
from ai_kit.domain.lockfile import LockNode
from ai_kit.domain.manifest import ASSET_METADATA_FILENAMES, SkillManifest
from ai_kit.domain.loop_manifest import LoopManifest


def manifest_metadata_filename(package_type: str) -> str:
    return ASSET_METADATA_FILENAMES.get(package_type, "skill.json")


def manifest_metadata_path(asset_dir: Path, package_type: str | None = None) -> Path:
    if package_type is not None:
        return asset_dir / manifest_metadata_filename(package_type)
    for filename in ("loop.json", "skill.json", "asset.json", "mcp.json"):
        candidate = asset_dir / filename
        if candidate.exists():
            return candidate
    return asset_dir / "skill.json"


def load_loop_manifest(loop_dir: Path) -> LoopManifest:
    """Load and validate a loop.json from a loop asset directory."""
    payload = json.loads((loop_dir / "loop.json").read_text(encoding="utf-8"))
    return LoopManifest.model_validate(payload)


def load_skill_manifest(skill_dir: Path) -> SkillManifest:
    payload = json.loads(manifest_metadata_path(skill_dir).read_text(encoding="utf-8"))
    return SkillManifest.model_validate(payload)


def dependency_summary(manifest: SkillManifest) -> dict[str, object]:
    payload: dict[str, list[dict[str, str]]] = {
        "required": [],
        "optional": [],
    }
    by_type: dict[str, dict[str, list[dict[str, str]]]] = {
        "skill": {"required": [], "optional": []},
        "plugin": {"required": [], "optional": []},
        "hook": {"required": [], "optional": []},
        "subagent": {"required": [], "optional": []},
        "cli": {"required": [], "optional": []},
        "mcp": {"required": [], "optional": []},
        "loop": {"required": [], "optional": []},
    }
    for dependency in manifest.dependencies:
        item = {
            "id": dependency.id,
            "version": dependency.version,
        }
        if dependency.namespace:
            item["namespace"] = dependency.namespace
            item["canonical_id"] = canonical_package_id(dependency.id, dependency.namespace)
        if dependency.feature:
            item["feature"] = dependency.feature
        by_type[dependency.type][dependency.scope].append(item)
        payload[dependency.scope].append({"type": dependency.type, **item})
    return {
        "all": payload,
        "skills": by_type["skill"],
        "plugins": by_type["plugin"],
        "hooks": by_type["hook"],
        "subagents": by_type["subagent"],
        "clis": by_type["cli"],
        "mcps": by_type["mcp"],
        "loops": by_type["loop"],
        "companion_docs": manifest.companion_docs.model_dump(mode="json"),
        "environment": manifest.environment.model_dump(mode="json"),
        "runtime_requirements": list(manifest.runtime_requirements),
        "post_install_hints": list(manifest.post_install_hints),
        "recommended_tools": list(manifest.recommended_tools),
        "contributors": list(manifest.contributors),
        "skill_type": manifest.skill_type,
        "agents_md_inject": manifest.agents_md_inject,
        "config_schema": manifest.config_schema,
    }


def find_lock_node(nodes: Sequence[LockNode], dep_type: str, package_id: str) -> LockNode | None:
    namespace, base_id = split_canonical_id(package_id)
    for node in nodes:
        if node.type != dep_type or node.id != base_id:
            continue
        if namespace is not None and node.namespace != namespace:
            continue
        return node
    return None


def manifest_canonical_id(manifest: SkillManifest) -> str:
    return canonical_package_id(manifest.id, manifest.namespace)


def manifest_validation_error(exc: ValidationError) -> str:
    return "; ".join(f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}" for error in exc.errors())
