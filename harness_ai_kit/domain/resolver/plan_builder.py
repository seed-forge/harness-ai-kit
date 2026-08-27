"""Build a resolution plan from root requirements using resolvelib."""
from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any, Callable, Iterable

from resolvelib import BaseReporter, Resolver
from resolvelib.resolvers import InconsistentCandidate, ResolutionImpossible

from harness_ai_kit.domain.artifacts import hash_skill_directory
from harness_ai_kit.domain.identity import canonical_package_id, package_key_for, split_canonical_id
from harness_ai_kit.domain.lockfile import LockNode, RootRequest
from harness_ai_kit.domain.manifest import SkillManifest
from harness_ai_kit.domain.manifest_io import load_skill_manifest
from harness_ai_kit.domain.policies import SOURCE_GIT_REPO, SOURCE_REPO, SourcePolicy
from harness_ai_kit.domain.registry import registry_artifact_url, registry_metadata_url
from harness_ai_kit.domain.resolution import DependencyRequirement, PackageCandidate, ResolutionPlan

from .git_source import GitSkillResolver, default_git_skill_resolver
from .provider import ResolutionProvider

RegistryManifestDownloader = Callable[
    [str, str, str | None],
    tuple[SkillManifest, dict[str, Any]],
]
RegistryUrlResolver = Callable[[dict[str, Any]], str]

DEFAULT_RESOLUTION_TIMEOUT = 120  # 2 分钟


class ResolutionTimeout(RuntimeError, TimeoutError):
    """Dependency resolution exceeded its time budget.

    Subclasses ``RuntimeError`` so the top-level CLI handler
    (``HANDLED_COMMAND_EXCEPTIONS``) renders it as a friendly one-line reminder
    instead of a traceback; also a ``TimeoutError`` for backward compatibility
    with any caller that catches that type.
    """


def _resolve_with_timeout(resolver: Any, requirements: list[Any], timeout: int) -> Any:
    """带超时的依赖解析，Windows 兼容（signal.alarm 不可用）。"""
    result_box: list[Any] = [None]
    error_box: list[Any] = [None]

    def _target() -> None:
        try:
            result_box[0] = resolver.resolve(requirements, max_rounds=500)
        except Exception as exc:
            error_box[0] = exc

    worker = threading.Thread(target=_target, daemon=True)
    worker.start()
    worker.join(timeout=timeout)
    if worker.is_alive():
        raise ResolutionTimeout(
            f"依赖解析超时（{timeout}s）。这通常是网络抖动或首次拉取较慢导致的临时问题，"
            f"重试一次多半即可通过。若仍失败："
            f"① harness-ai-kit sync --offline --dry-run 离线诊断（离线秒过则确认是网络）；"
            f"② 设环境变量 HARNESS_AI_KIT_RESOLUTION_TIMEOUT=<秒> 调大超时（当前 {timeout}s）。"
        )
    if error_box[0] is not None:
        raise error_box[0]
    return result_box[0]


def build_resolution_plan(
    repo_root: Path,
    registry_index_url: str,
    root_skill_ids: list[str],
    *,
    root_asset_kind: str = "skill",
    runtime: str,
    install_scope: str,
    selected_features: Iterable[str] = (),
    offline: bool = False,
    refresh_cache: bool = False,
    cli_versions: dict[str, str] | None = None,
    preferred_sources: list[str] | None = None,
    public_registry_index_url: str = "",
    cli_registry_index_url: str = "",
    root_sources: dict[str, tuple[str, str | None, str | None]] | None = None,
    root_specifiers: dict[str, str] | None = None,
    git_skill_resolver: GitSkillResolver = default_git_skill_resolver,
    registry_manifest_downloader: RegistryManifestDownloader | None = None,
    registry_artifact_url_resolver: RegistryUrlResolver = registry_artifact_url,
    registry_metadata_url_resolver: RegistryUrlResolver = registry_metadata_url,
) -> ResolutionPlan:
    if not root_skill_ids:
        raise ValueError(f"At least one root {root_asset_kind} id is required.")
    first_namespace, first_root_id = split_canonical_id(root_skill_ids[0])
    local_root_manifest = None
    local_root_parent = "skills" if root_asset_kind == "skill" else f"{root_asset_kind}s"
    local_root_dir = repo_root / local_root_parent / first_root_id
    if local_root_dir.exists():
        candidate_manifest = load_skill_manifest(local_root_dir)
        if first_namespace is None or candidate_manifest.namespace == first_namespace:
            local_root_manifest = candidate_manifest
    source_order = preferred_sources or (
        list(local_root_manifest.sources.preferred)
        if local_root_manifest
        else list(SourcePolicy().preferred)
    )
    allow_fallback = local_root_manifest.sources.allow_fallback if local_root_manifest else True
    features = sorted({feature for feature in selected_features if feature})
    provider = ResolutionProvider(
        repo_root=repo_root,
        registry_index_url=registry_index_url,
        source_order=source_order,
        allow_fallback=allow_fallback,
        selected_features=set(features),
        cli_versions=cli_versions or {},
        offline=offline,
        refresh_cache=refresh_cache,
        public_registry_index_url=public_registry_index_url,
        cli_registry_index_url=cli_registry_index_url,
        git_sources=root_sources,
        git_skill_resolver=git_skill_resolver,
        registry_manifest_downloader=registry_manifest_downloader,
        registry_artifact_url_resolver=registry_artifact_url_resolver,
        registry_metadata_url_resolver=registry_metadata_url_resolver,
    )
    reporter = BaseReporter()
    resolver = Resolver(provider, reporter)
    requirements: list[DependencyRequirement] = []
    root_requests: list[RootRequest] = []
    for skill_ref in root_skill_ids:
        namespace, skill_id = split_canonical_id(skill_ref)
        canonical_id = canonical_package_id(skill_id, namespace)
        source_ref, ref, subpath = (root_sources or {}).get(canonical_id, (None, None, None))
        root_requests.append(
            RootRequest(
                type=root_asset_kind,
                namespace=namespace,
                id=skill_id,
                source_policy=[SOURCE_GIT_REPO] if source_ref else [],
                source_ref=source_ref,
                ref=ref,
                subpath=subpath,
                version=(root_specifiers or {}).get(canonical_id),
            )
        )
        if source_ref:
            specifier = (root_specifiers or {}).get(canonical_id, ">=0")
            requirements.append(
                DependencyRequirement(
                    dep_type=root_asset_kind, namespace=namespace, package_id=skill_id,
                    specifier=specifier, source_ref=source_ref, ref=ref, subpath=subpath,
                )
            )
            continue
        root_dir = repo_root / local_root_parent / skill_id
        # Only pin to local skill.json version when the source order includes
        # repo-checkout. Consumer roles resolve registry-only; pinning to a
        # local version that may not yet be published causes resolution failure.
        use_local_version = any(s == SOURCE_REPO for s in source_order)
        if use_local_version and root_dir.exists():
            try:
                manifest = load_skill_manifest(root_dir)
            except (FileNotFoundError, OSError) as exc:
                print(f"WARNING: skill '{skill_id}' declared in harness-ai-kit.yml but skill.json not found at {root_dir}. Skipping local source; will try registry. ({exc})")
                manifest = None
            if manifest is not None:
                manifest_namespace = manifest.namespace
                if namespace is not None and manifest_namespace != namespace:
                    raise KeyError(
                        f"Requested root skill {skill_ref} resolved to local namespace "
                        f"{canonical_package_id(skill_id, manifest_namespace)}"
                    )
                requirements.append(
                    DependencyRequirement(
                        dep_type=root_asset_kind, namespace=manifest_namespace,
                        package_id=skill_id, specifier=f"=={manifest.version}",
                    )
                )
                continue
        # Fall through: directory missing or skill.json invalid → use registry source
        specifier = (root_specifiers or {}).get(canonical_id, ">=0")
        requirements.append(
            DependencyRequirement(
                dep_type=root_asset_kind, namespace=namespace, package_id=skill_id,
                specifier=specifier, source_ref=source_ref, ref=ref, subpath=subpath,
            )
        )
    resolution_timeout = int(os.environ.get("HARNESS_AI_KIT_RESOLUTION_TIMEOUT", DEFAULT_RESOLUTION_TIMEOUT))
    try:
        result = _resolve_with_timeout(resolver, requirements, timeout=resolution_timeout)
    except ResolutionImpossible as exc:
        # Format a human-readable dependency resolution error
        causes = getattr(exc, "causes", None) or getattr(exc, "backtrack_causes", None) or []
        missing_parts: list[str] = []
        for info in causes:
            req = getattr(info, "requirement", None)
            parent = getattr(info, "parent", None)
            if req is None:
                continue
            pkg_ref = canonical_package_id(
                getattr(req, "package_id", "?"),
                getattr(req, "namespace", None),
            )
            spec = getattr(req, "specifier", "") or ""
            parent_ref = (
                canonical_package_id(
                    getattr(parent, "package_id", ""),
                    getattr(parent, "namespace", None),
                )
                if parent is not None
                else "(root)"
            )
            missing_parts.append(f"  - {pkg_ref}{spec}  (required by {parent_ref})")
        detail = "\n".join(missing_parts) if missing_parts else "  (no detail available)"
        raise RuntimeError(
            f"Dependency resolution failed. Could not find matching package(s):\n{detail}\n\n"
            f"Hint: Ensure the required package is published to the registry, or install it first:\n"
            f"  harness-ai-kit install <missing-package-id>\n"
            f"Or clear the registry cache: rm -rf ~/.cache/harness-ai-kit/"
        ) from exc
    except InconsistentCandidate as exc:
        # Version conflict: candidate exists but can't satisfy all constraints
        candidate = getattr(exc, "candidate", None)
        criterion = getattr(exc, "criterion", None)
        candidate_version = getattr(candidate, "version", "?") if candidate else "?"
        candidate_id = (
            canonical_package_id(
                getattr(candidate, "package_id", "?"),
                getattr(candidate, "namespace", None),
            )
            if candidate else "?"
        )
        candidate_source = getattr(candidate, "source", "?") if candidate else "?"
        # Extract conflicting requirements
        requirements = getattr(criterion, "requirements", None) or getattr(criterion, "information", []) or []
        constraint_lines: list[str] = []
        for req_info in requirements:
            req = req_info if hasattr(req_info, "specifier") else getattr(req_info, "requirement", req_info)
            parent = getattr(req_info, "parent", None)
            pkg_ref = canonical_package_id(
                getattr(req, "package_id", "?"),
                getattr(req, "namespace", None),
            )
            spec = getattr(req, "specifier", "") or ""
            parent_ref = (
                canonical_package_id(
                    getattr(parent, "package_id", ""),
                    getattr(parent, "namespace", None),
                )
                if parent is not None
                else "(root)"
            )
            constraint_lines.append(f"  - {pkg_ref}{spec}  (required by {parent_ref})")
        constraints_detail = "\n".join(constraint_lines) if constraint_lines else "  (no detail available)"
        raise RuntimeError(
            f"Version conflict for {candidate_id}:\n"
            f"  Available: {candidate_version} (from {candidate_source})\n"
            f"  Constraints:\n{constraints_detail}\n\n"
            f"Hint: Some installed skills require conflicting CLI versions.\n"
            f"  Update or remove the skill with the outdated constraint, then retry.\n"
            f"  Or clear the lockfile: rm -f ~/.harness-ai-kit/state/harness-ai-kit.lock"
        ) from exc
    candidate_map: dict[str, PackageCandidate] = {}
    manifest_map: dict[str, SkillManifest] = {}
    edges: dict[str, list[str]] = {}
    nodes: list[LockNode] = []
    for key, candidate in result.mapping.items():
        candidate_map[key] = candidate
        dependencies = provider.get_dependencies(candidate)
        extends_deps = [dep for dep in dependencies if dep.extra_metadata and dep.extra_metadata.get("kind") == "extends"]
        regular_deps = [dep for dep in dependencies if not (dep.extra_metadata and dep.extra_metadata.get("kind") == "extends")]
        edges[key] = [package_key_for(dep.dep_type, dep.package_id, dep.namespace) for dep in regular_deps]
        for ext_dep in extends_deps:
            ext_key = package_key_for(ext_dep.dep_type, ext_dep.package_id, ext_dep.namespace)
            if ext_key not in edges[key]:
                edges[key].append(ext_key)
        if candidate.manifest:
            manifest_map[key] = candidate.manifest
        node_extends: list[dict[str, Any]] = []
        stored_extends = provider._extends_metadata_store.get(key, [])
        for ext_meta in stored_extends:
            node_extends.append({
                "base_skill_id": ext_meta.get("base_skill_id", ""),
                "base_version": ext_meta.get("base_version", ""),
                "merge_strategy": ext_meta.get("merge_strategy", "prepend"),
                "merge_sections": ext_meta.get("merge_sections", []),
            })
        nodes.append(
            LockNode(
                type=candidate.dep_type,
                namespace=candidate.namespace,
                id=candidate.package_id,
                canonical_id=canonical_package_id(candidate.package_id, candidate.namespace),
                version=candidate.version,
                source=candidate.source,
                checksum_algorithm="sha256",
                checksum=candidate.checksum or None,
                source_checksum=candidate.source_checksum or candidate.checksum or None,
                materialized_checksum=candidate.materialized_checksum or None,
                artifact_url=candidate.artifact_url,
                metadata_url=candidate.metadata_url,
                source_ref=str(candidate.path) if candidate.path else None,
                source_url=candidate.source_url,
                source_commit=candidate.source_commit,
                ref=candidate.ref,
                subpath=candidate.subpath,
                requires=list(edges.get(key, [])),
                extends=node_extends if node_extends else None,
                companion_docs=candidate.manifest.companion_docs.model_dump(mode="json") if candidate.manifest else {},
                environment=candidate.manifest.environment.model_dump(mode="json") if candidate.manifest else {},
                runtime_requirements=list(candidate.manifest.runtime_requirements) if candidate.manifest else [],
                post_install_hints=list(candidate.manifest.post_install_hints) if candidate.manifest else [],
                provenance=candidate.manifest.provenance.model_dump(mode="json") if candidate.manifest and candidate.manifest.provenance else None,
                structure_profile=candidate.manifest.structure_profile if candidate.manifest else None,
                responsibility_keys=list(candidate.manifest.responsibility_keys) if candidate.manifest else [],
                load_plan=candidate.manifest.load_plan.model_dump(mode="json") if candidate.manifest and candidate.manifest.load_plan else None,
                agents_md_inject=str(candidate.manifest.agents_md_inject).strip() if candidate.manifest else "",
                config_schema=candidate.manifest.config_schema if candidate.manifest else None,
            )
        )
    nodes.sort(key=lambda item: (item.type != "skill", item.id))
    # Patch root_requests with resolved namespaces.
    resolved_ns_lookup: dict[tuple[str, str], str | None] = {}
    for node in nodes:
        resolved_ns_lookup.setdefault((node.type, node.id), node.namespace)
    patched_requests: list[RootRequest] = []
    for req in root_requests:
        resolved_ns = resolved_ns_lookup.get((req.type, req.id))
        if resolved_ns is not None and req.namespace is None:
            patched_requests.append(req.model_copy(update={"namespace": resolved_ns}))
        else:
            patched_requests.append(req)
    root_requests = patched_requests
    return ResolutionPlan(
        roots=root_skill_ids,
        features=features,
        runtime=runtime,
        install_scope=install_scope,
        nodes=nodes,
        manifest_map=manifest_map,
        candidate_map=candidate_map,
        dependency_edges=edges,
        root_requests=root_requests,
    )
