from __future__ import annotations

from pathlib import Path

from harness_ai_kit import package_manager as pm
from harness_ai_kit.domain.policies import SOURCE_GIT_REPO, SOURCE_REGISTRY, SOURCE_REPO

MAINTAINER_DOC = "docs/MAINTAINER-SKILL-LOCK-REGISTRY.md"


def is_ai_kit_repo_root(path: Path) -> bool:
    return (path / "cli" / "harness_ai_kit").is_dir() and (path / "skills").is_dir()


def embedded_ai_kit_skill_checkouts(project_root: Path, root_ids: list[str]) -> dict[str, Path]:
    """Find nested harness-ai-kit skill checkouts inside a consumer workspace."""
    if not project_root.is_dir():
        return {}

    found: dict[str, Path] = {}
    for root_id in root_ids:
        _, base_id = pm.split_canonical_id(root_id)
        candidates = [
            project_root / "工程规范" / "harness-ai-kit" / "skills" / base_id,
            project_root / "harness-ai-kit" / "skills" / base_id,
        ]
        for candidate in candidates:
            if (candidate / "SKILL.md").is_file() or (candidate / "skill.json").is_file():
                kit_root = candidate.parent.parent
                if kit_root.is_dir() and is_ai_kit_repo_root(kit_root):
                    found[root_id] = candidate
                    break
        if root_id in found:
            continue
        for skill_md in project_root.glob(f"**/harness-ai-kit/skills/{base_id}/SKILL.md"):
            kit_root = skill_md.parent.parent.parent
            if kit_root.name == "harness-ai-kit" and is_ai_kit_repo_root(kit_root):
                if kit_root.resolve() == project_root.resolve():
                    continue
                found[root_id] = skill_md.parent
                break
    return found


def collect_registry_lock_guardrails(
    *,
    project_root: Path | None,
    manifest_root_ids: list[str],
    manifest_skill_ids: list[str],
    lockfile: pm.Lockfile | None,
    registry_available: bool,
    repo_root: Path | None,
) -> tuple[list[str], list[str]]:
    warnings: list[str] = []
    errors: list[str] = []

    if project_root is None or not manifest_skill_ids:
        return warnings, errors

    embedded = embedded_ai_kit_skill_checkouts(project_root, manifest_skill_ids)
    in_repo_maintainer_context = repo_root is not None and repo_root.resolve() == project_root.resolve()

    if lockfile is not None and manifest_skill_ids:
        if len(lockfile.roots) > max(len(manifest_skill_ids), 1) + 2:
            warnings.append(
                f"ai-kit.lock lists {len(lockfile.roots)} roots but manifest declares {len(manifest_skill_ids)} skill(s); "
                f"avoid `install --all --refresh-lock`. See {MAINTAINER_DOC}."
            )

    for root_id in manifest_skill_ids:
        _, base_id = pm.split_canonical_id(root_id)
        checkout_path = embedded.get(root_id)
        lock_node = None
        if lockfile is not None:
            lock_node = _find_lock_skill_node(lockfile, root_id)

        if lock_node is not None and lock_node.source == SOURCE_REGISTRY:
            if not (lock_node.artifact_url and lock_node.metadata_url):
                errors.append(
                    f"{root_id}: lock node uses skill-registry but artifact_url/metadata_url is missing; "
                    f"re-run refresh-lock. See {MAINTAINER_DOC}."
                )

        if lock_node is not None and lock_node.source == SOURCE_GIT_REPO:
            if not lock_node.source_url:
                errors.append(f"{root_id}: git-repo lock node is missing source_url; re-run refresh-lock.")
            if not lock_node.source_commit:
                errors.append(f"{root_id}: git-repo lock node is missing source_commit; re-run refresh-lock.")
            if not lock_node.metadata_url:
                warnings.append(
                    f"{root_id}: git-repo lock node has no metadata_url; this is expected only for metadata-free skills."
                )

        if checkout_path is not None and not in_repo_maintainer_context:
            hint = (
                f"Move `{checkout_path.relative_to(project_root)}` aside (e.g. `_skills-repo-bak/{base_id}`) "
                f"before `harness-ai-kit install --runtime codex --scope project --refresh-lock`."
            )
            if lock_node is not None and lock_node.source == SOURCE_REPO:
                errors.append(
                    f"{root_id}: embedded harness-ai-kit checkout conflicts with registry lock refresh "
                    f"(lock source=repo-checkout). {hint} See {MAINTAINER_DOC}."
                )
            else:
                warnings.append(
                    f"{root_id}: embedded harness-ai-kit checkout detected at `{checkout_path.relative_to(project_root)}`. "
                    f"{hint} See {MAINTAINER_DOC}."
                )

    return warnings, errors


def _find_lock_skill_node(lockfile: pm.Lockfile, root_id: str) -> pm.LockNode | None:
    namespace, base_id = pm.split_canonical_id(root_id)
    for node in lockfile.nodes:
        if node.type != "skill" or node.id != base_id:
            continue
        if namespace is not None and node.namespace != namespace:
            continue
        return node
    return None
