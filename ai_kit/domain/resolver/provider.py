"""ResolutionProvider: resolvelib AbstractProvider implementation for skill/CLI dependency resolution."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Iterator, Sequence

from packaging.specifiers import SpecifierSet
from packaging.version import Version
from resolvelib import AbstractProvider

from ai_kit.domain.artifacts import hash_skill_directory
from ai_kit.domain.dependencies import DependencySpec
from ai_kit.domain.identity import canonical_package_id, package_key_for, split_canonical_id
from ai_kit.domain.manifest import SkillManifest
from ai_kit.domain.manifest_io import load_skill_manifest, manifest_metadata_path
from ai_kit.domain.versions import is_latest_specifier
from ai_kit.domain.policies import (
    SOURCE_GIT_REPO,
    SOURCE_MANUAL,
    SOURCE_PUBLIC_REGISTRY,
    SOURCE_REGISTRY,
    SOURCE_REPO,
)
from ai_kit.domain.registry import registry_artifact_url, registry_metadata_url, RegistryUnavailableError
from ai_kit.domain.resolution import DependencyRequirement, PackageCandidate

from .git_source import (
    DiscoveredGitSkill,
    GitSkillResolver,
    default_git_skill_resolver,
    git_skill_checkout_root,
    git_source_commit,
    github_raw_metadata_url,
    load_git_skill_manifest,
    parse_git_source_ref,
    skill_dirs_under,
)

RegistryManifestDownloader = Callable[
    [str, str, str | None],
    tuple[SkillManifest, dict[str, Any]],
]
RegistryUrlResolver = Callable[[dict[str, Any]], str]


class CircularExtendsError(Exception):
    """Raised when a circular extends chain is detected during resolution."""

    def __init__(self, cycle_path: list[str]) -> None:
        self.cycle_path = cycle_path
        chain = " -> ".join(cycle_path)
        super().__init__(f"Circular extends chain detected: {chain}")


class ResolutionProvider(AbstractProvider[DependencyRequirement, PackageCandidate, str]):
    def __init__(
        self,
        repo_root: Path,
        registry_index_url: str,
        source_order: list[str],
        allow_fallback: bool,
        selected_features: set[str],
        cli_versions: dict[str, str],
        offline: bool,
        *,
        public_registry_index_url: str = "",
        cli_registry_index_url: str = "",
        git_sources: dict[str, tuple[str, str | None, str | None]] | None = None,
        git_skill_resolver: GitSkillResolver = default_git_skill_resolver,
        registry_manifest_downloader: RegistryManifestDownloader | None = None,
        registry_artifact_url_resolver: RegistryUrlResolver = registry_artifact_url,
        registry_metadata_url_resolver: RegistryUrlResolver = registry_metadata_url,
    ) -> None:
        self.repo_root = repo_root
        self.registry_index_url = registry_index_url
        self.public_registry_index_url = public_registry_index_url
        self.git_sources = git_sources or {}
        self.git_skill_resolver = git_skill_resolver
        self.source_order = source_order
        self.allow_fallback = allow_fallback
        self.selected_features = selected_features
        self.cli_versions = cli_versions
        self.offline = offline
        self.cli_registry_index_url = cli_registry_index_url
        self.registry_manifest_downloader = registry_manifest_downloader or self._download_registry_manifest
        self.registry_artifact_url_resolver = registry_artifact_url_resolver
        self.registry_metadata_url_resolver = registry_metadata_url_resolver
        self._manifest_cache: dict[str, SkillManifest] = {}
        self._registry_entry_cache: dict[str, dict[str, Any]] = {}
        self._extends_chain_stack: list[str] = []
        self._extends_metadata_store: dict[str, list[dict[str, Any]]] = {}
        self._candidate_matches_cache: dict[tuple[str, str, str | None], list[PackageCandidate]] = {}
        self._skill_candidates_cache: dict[tuple[str, str | None], list[PackageCandidate]] = {}
        self._registry_exact_cache: dict[tuple[str, str | None, str], list[PackageCandidate]] = {}

    def _download_registry_manifest(self, index_url: str, skill_id: str, version: str | None) -> tuple[SkillManifest, dict[str, Any]]:
        from ai_kit.domain.registry import download_registry_manifest
        return download_registry_manifest(index_url, skill_id, version, offline=self.offline)

    def identify(self, requirement_or_candidate: DependencyRequirement | PackageCandidate) -> str:
        return package_key_for(
            requirement_or_candidate.dep_type,
            requirement_or_candidate.package_id,
            requirement_or_candidate.namespace,
        )

    def get_preference(self, identifier: str, resolutions: dict[str, PackageCandidate], candidates: dict[str, Iterator[PackageCandidate]], information: dict[str, Iterator[DependencyRequirement]], backtrack_causes: Sequence[Any]) -> int:
        base = hash(identifier) % 1000
        if identifier in backtrack_causes:
            return base + 10000
        return base

    def find_matches(self, identifier: str, requirements: dict[str, Iterator[DependencyRequirement]], incompatibilities: dict[str, Iterator[PackageCandidate]]) -> list[PackageCandidate]:
        dep_type, canonical_id = identifier.split(":", 1)
        namespace, package_id = split_canonical_id(canonical_id)
        requirement_list = list(requirements[identifier])
        specifiers = [
            SpecifierSet(requirement.specifier) if not is_latest_specifier(requirement.specifier) else None
            for requirement in requirement_list
        ]
        matches = self._candidate_matches(dep_type, package_id, namespace)
        incompatible = {
            (candidate.dep_type, candidate.namespace, candidate.package_id, candidate.version, candidate.source)
            for candidate in incompatibilities.get(identifier, [])
        }
        if dep_type == "skill":
            has_satisfying_candidate = any(
                self._candidate_satisfies_specifiers(candidate, specifiers)
                and (candidate.dep_type, candidate.namespace, candidate.package_id, candidate.version, candidate.source) not in incompatible
                for candidate in matches
            )
            if not has_satisfying_candidate:
                matches = matches + self._exact_registry_candidates_for_requirements(package_id, namespace, requirement_list)
        git_requirements = [requirement for requirement in requirement_list if requirement.source_ref]
        if git_requirements:
            matches = self._git_candidates_for_requirements(package_id, namespace, git_requirements) + matches
        source_url_requirements = [requirement for requirement in requirement_list if requirement.source_url]
        if source_url_requirements:
            matches = self._source_url_candidates(package_id, namespace, source_url_requirements) + matches
        filtered: list[PackageCandidate] = []
        for candidate in matches:
            if not self._candidate_satisfies_specifiers(candidate, specifiers):
                continue
            signature = (candidate.dep_type, candidate.namespace, candidate.package_id, candidate.version, candidate.source)
            if signature in incompatible:
                continue
            filtered.append(candidate)
        if filtered or dep_type not in {"cli", "mcp"}:
            return filtered
        synthesized: list[PackageCandidate] = []
        seen_versions: set[str] = set()
        for requirement in requirement_list:
            if not requirement.specifier.startswith("=="):
                continue
            version = requirement.specifier[2:].strip()
            if not version or version in seen_versions:
                continue
            seen_versions.add(version)
            synthesized.append(
                PackageCandidate(
                    dep_type=dep_type,
                    namespace=requirement.namespace,
                    package_id=requirement.package_id,
                    version=version,
                    source=SOURCE_MANUAL,
                )
            )
        return synthesized

    def _candidate_satisfies_specifiers(self, candidate: PackageCandidate, specifiers: list[SpecifierSet | None]) -> bool:
        if not specifiers:
            return True
        spec = specifiers[0]
        if spec is None:
            return True  # None means "latest" — matches any version
        return Version(candidate.version) in spec

    def is_satisfied_by(self, requirement: DependencyRequirement, candidate: PackageCandidate) -> bool:
        if is_latest_specifier(requirement.specifier):
            return True
        return Version(candidate.version) in SpecifierSet(requirement.specifier)

    def get_dependencies(self, candidate: PackageCandidate) -> list[DependencyRequirement]:
        if not candidate.manifest:
            return []
        requirements: list[DependencyRequirement] = []
        for dependency in candidate.manifest.dependencies:
            if dependency.scope == "optional" and dependency.feature not in self.selected_features:
                continue
            requirements.append(
                DependencyRequirement(
                    dep_type=dependency.type,
                    namespace=dependency.namespace,
                    package_id=dependency.id,
                    specifier=dependency.version,
                    scope=dependency.scope,
                    feature=dependency.feature,
                    source_url=getattr(dependency, "source_url", None),
                    source_ref=getattr(dependency, "source_ref", None),
                    subpath=getattr(dependency, "subpath", None),
                )
            )

        extends_list = candidate.manifest.extends or []
        if extends_list:
            pkg_key = package_key_for("skill", candidate.package_id, candidate.namespace)
            if pkg_key in self._extends_chain_stack:
                cycle = list(self._extends_chain_stack) + [pkg_key]
                raise CircularExtendsError(cycle)
            self._detect_extends_circular(candidate.manifest)
            self._extends_chain_stack.append(pkg_key)
            try:
                pkg_extends: list[dict[str, Any]] = []
                for extends_spec in extends_list:
                    ext_canonical_id = canonical_package_id(extends_spec.id, extends_spec.namespace)
                    extend_metadata: dict[str, Any] = {
                        "kind": "extends",
                        "merge_strategy": extends_spec.merge_strategy,
                        "merge_sections": extends_spec.merge_sections or [],
                        "auto_install": extends_spec.auto_install,
                        "visible": extends_spec.visible,
                        "base_skill_id": ext_canonical_id,
                        "base_version": extends_spec.version,
                    }
                    pkg_extends.append(extend_metadata)
                    if extends_spec.auto_install:
                        requirements.append(
                            DependencyRequirement(
                                dep_type="skill",
                                namespace=extends_spec.namespace,
                                package_id=extends_spec.id,
                                specifier=extends_spec.version,
                                scope="required",
                                extra_metadata=extend_metadata,
                            )
                        )
                self._extends_metadata_store[pkg_key] = pkg_extends
            finally:
                self._extends_chain_stack.pop()
        return requirements

    def _detect_extends_circular(self, manifest: SkillManifest) -> None:
        extends_list = manifest.extends or []
        if not extends_list:
            return
        manifest_key = package_key_for("skill", manifest.id, manifest.namespace)
        adjacency: dict[str, list[str]] = {}
        for extends_spec in extends_list:
            base_key = package_key_for("skill", extends_spec.id, extends_spec.namespace)
            adjacency.setdefault(manifest_key, []).append(base_key)
            if base_key == manifest_key:
                raise CircularExtendsError([manifest_key, manifest_key])
        visited_global: set[str] = set()
        for node in list(adjacency.keys()):
            if node in visited_global:
                continue
            self._dfs_cycle_detect(node, adjacency, visited_global, [])

    @staticmethod
    def _dfs_cycle_detect(node: str, adjacency: dict[str, list[str]], visited_global: set[str], path: list[str]) -> None:
        if node in path:
            cycle_start = path.index(node)
            raise CircularExtendsError(path[cycle_start:] + [node])
        if node in visited_global:
            return
        visited_global.add(node)
        path.append(node)
        for neighbor in adjacency.get(node, []):
            ResolutionProvider._dfs_cycle_detect(neighbor, adjacency, visited_global, path)
        path.pop()

    def _resolve_extends_chain(self, base_skill_id: str, base_namespace: str | None, base_version: str, depth: int = 0, visited: set[str] | None = None) -> list[SkillManifest]:
        MAX_EXTENDS_DEPTH = 3
        if depth > MAX_EXTENDS_DEPTH:
            raise ValueError(f"Extends chain exceeds maximum depth of {MAX_EXTENDS_DEPTH}. Current depth: {depth}")
        if visited is None:
            visited = set()
        chain_key = package_key_for("skill", base_skill_id, base_namespace)
        if chain_key in visited:
            raise CircularExtendsError(list(visited) + [chain_key])
        visited.add(chain_key)
        candidates = self._skill_candidates(base_skill_id, base_namespace)
        if not candidates:
            raise KeyError(f"Extended base skill '{canonical_package_id(base_skill_id, base_namespace)}' not found in any available source.")
        base_manifest = candidates[0].manifest
        if base_manifest is None:
            raise KeyError(f"Extended base skill '{canonical_package_id(base_skill_id, base_namespace)}' has no loadable manifest.")
        chain: list[SkillManifest] = [base_manifest]
        base_extends_list = base_manifest.extends or []
        if base_extends_list:
            sub_chains: list[list[SkillManifest]] = []
            for base_extends in base_extends_list:
                sub_chain = self._resolve_extends_chain(base_extends.id, base_extends.namespace, base_extends.version, depth=depth + 1, visited=visited.copy())
                sub_chains.append(sub_chain)
            chain = ResolutionProvider._c3_linearize([chain] + sub_chains)
        return chain

    @staticmethod
    def _c3_linearize(chains: list[list[SkillManifest]]) -> list[SkillManifest]:
        if not chains:
            return []
        if len(chains) == 1:
            return list(chains[0])
        chains = [list(c) for c in chains]
        result: list[SkillManifest] = []
        seen_ids: set[str] = set()
        while any(chains):
            chosen: SkillManifest | None = None
            for chain in chains:
                if not chain:
                    continue
                head = chain[0]
                if head.id in seen_ids:
                    continue
                appears_in_tail = False
                for other in chains:
                    if other is chain:
                        continue
                    if any(head.id == item.id for item in other[1:]):
                        appears_in_tail = True
                        break
                if not appears_in_tail:
                    chosen = head
                    break
            if chosen is None:
                remaining = [c[0].id for c in chains if c]
                raise ValueError(f"Cannot linearize extends chains due to ordering conflict. Remaining heads: {remaining}")
            result.append(chosen)
            seen_ids.add(chosen.id)
            for chain in chains:
                if chain and chain[0].id == chosen.id:
                    chain.pop(0)
        return result

    def _candidate_matches(self, dep_type: str, package_id: str, namespace: str | None = None, *, _dep_context: str | None = None) -> list[PackageCandidate]:
        cache_key = (dep_type, package_id, namespace)
        cached = self._candidate_matches_cache.get(cache_key)
        if cached is not None:
            return cached
        if dep_type == "mcp":
            managed_candidates = self._managed_asset_candidates(dep_type, package_id, namespace)
            if managed_candidates:
                self._candidate_matches_cache[cache_key] = managed_candidates
                return managed_candidates
            result = [
                PackageCandidate(
                    dep_type="mcp", namespace=namespace, package_id=package_id, version="1.0.0", source=SOURCE_MANUAL,
                    dependency_spec=DependencySpec(type="mcp", namespace=namespace, id=package_id, version="==1.0.0"),
                )
            ]
            self._candidate_matches_cache[cache_key] = result
            return result
        if dep_type == "cli":
            version = self.cli_versions.get(package_id)
            if not version and not self.offline:
                # Fallback to CLI registry index
                try:
                    import urllib.request
                    import json
                    index_url = self.cli_registry_index_url or ""
                    if index_url:
                        with urllib.request.urlopen(index_url, timeout=10) as response:
                            index_data = json.loads(response.read().decode("utf-8"))
                            for cli_entry in index_data.get("clis", []):
                                if cli_entry.get("id") == package_id:
                                    version = cli_entry.get("latest_version")
                                    break
                except Exception:
                    pass  # Registry lookup failed, fall through to return empty
            if not version:
                self._candidate_matches_cache[cache_key] = []
                return []
            result = [PackageCandidate(dep_type="cli", namespace=namespace, package_id=package_id, version=version, source=SOURCE_REPO)]
            self._candidate_matches_cache[cache_key] = result
            return result
        if dep_type in {"plugin", "hook", "subagent", "mcp", "loop"}:
            result = self._managed_asset_candidates(dep_type, package_id, namespace)
            self._candidate_matches_cache[cache_key] = result
            return result
        result = self._skill_candidates(package_id, namespace, _dep_context=_dep_context)
        self._candidate_matches_cache[cache_key] = result
        return result

    def _managed_asset_candidates(self, dep_type: str, package_id: str, namespace: str | None = None) -> list[PackageCandidate]:
        asset_dir = self.repo_root / f"{dep_type}s" / package_id
        if not asset_dir.exists():
            return []
        try:
            manifest = load_skill_manifest(asset_dir)
        except (FileNotFoundError, OSError) as exc:
            print(f"WARNING: {dep_type} '{package_id}' directory exists at {asset_dir} but metadata file is missing or invalid. Skipping. ({exc})")
            return []
        candidate_namespace = manifest.namespace or namespace
        if namespace is not None and candidate_namespace != namespace:
            return []
        return [
            PackageCandidate(
                dep_type=dep_type, namespace=candidate_namespace, package_id=package_id,
                version=manifest.version, source=SOURCE_REPO, manifest=manifest, path=asset_dir,
                checksum=hash_skill_directory(asset_dir), source_checksum=hash_skill_directory(asset_dir),
            )
        ]

    def _skill_candidates(self, skill_id: str, namespace: str | None = None, *, _dep_context: str | None = None) -> list[PackageCandidate]:
        cache_key = (skill_id, namespace)
        cached = self._skill_candidates_cache.get(cache_key)
        if cached is not None:
            return cached
        candidates: list[PackageCandidate] = []
        sources_tried: list[str] = []
        for source in self.source_order:
            if source == SOURCE_REPO:
                skill_dir = self.repo_root / "skills" / skill_id
                if skill_dir.exists():
                    try:
                        manifest = load_skill_manifest(skill_dir)
                    except (FileNotFoundError, OSError) as exc:
                        print(f"WARNING: skill directory '{skill_id}' exists at {skill_dir} but skill.json is missing or invalid. Skipping repo-checkout source. ({exc})")
                        manifest = None
                    if manifest is not None:
                        candidate_namespace = manifest.namespace or namespace
                        if namespace is not None and candidate_namespace != namespace:
                            continue
                        candidates.append(PackageCandidate(
                            dep_type="skill", namespace=candidate_namespace, package_id=skill_id,
                            version=manifest.version, source=SOURCE_REPO, manifest=manifest, path=skill_dir,
                            checksum=hash_skill_directory(skill_dir), source_checksum=hash_skill_directory(skill_dir),
                        ))
                sources_tried.append(f"repo-checkout ({skill_dir})")
            elif source in {SOURCE_REGISTRY, SOURCE_PUBLIC_REGISTRY}:
                registry_index_url = self.public_registry_index_url if source == SOURCE_PUBLIC_REGISTRY else self.registry_index_url
                if not registry_index_url:
                    sources_tried.append(f"{source} (no index URL configured)")
                    continue
                try:
                    manifest, entry = self.registry_manifest_downloader(registry_index_url, canonical_package_id(skill_id, namespace), None)
                except KeyError as exc:
                    sources_tried.append(f"{source} (not found: {exc})")
                    continue
                except RegistryUnavailableError:
                    # Network/transport failure: do NOT silently degrade to
                    # "not found". Propagate so consumers (registry-only) get a
                    # clear "registry unreachable" error instead of a misleading
                    # dependency-resolution failure.
                    raise
                except Exception as exc:
                    sources_tried.append(f"{source} (error: {exc})")
                    continue
                candidate_namespace = manifest.namespace or namespace
                if namespace is not None and candidate_namespace != namespace:
                    sources_tried.append(f"{source} (namespace mismatch: {candidate_namespace} != {namespace})")
                    continue
                candidates.append(PackageCandidate(
                    dep_type="skill", namespace=candidate_namespace, package_id=skill_id,
                    version=manifest.version, source=source, manifest=manifest,
                    artifact_url=self.registry_artifact_url_resolver(entry),
                    metadata_url=self.registry_metadata_url_resolver(entry),
                    checksum=str(entry.get("checksum") or ""), source_checksum=str(entry.get("checksum") or ""),
                ))
            elif source == SOURCE_GIT_REPO:
                git_source = self.git_sources.get(canonical_package_id(skill_id, namespace))
                if not git_source:
                    sources_tried.append(f"git-repo (no git source configured)")
                    continue
                source_ref, ref, subpath = git_source
                candidate = self._git_candidate(skill_id, namespace, source_ref, ref, subpath)
                if candidate:
                    return [candidate]
                sources_tried.append(f"git-repo (checkout failed)")
        if not candidates and _dep_context:
            source_details = "; ".join(sources_tried) if sources_tried else "no sources configured"
            print(f"ERROR: Cannot resolve dependency '{skill_id}' required by {_dep_context}. Sources tried: {source_details}")
        self._skill_candidates_cache[cache_key] = candidates
        return candidates

    def _exact_registry_candidates_for_requirements(self, skill_id: str, namespace: str | None, requirements: list[DependencyRequirement]) -> list[PackageCandidate]:
        versions: list[str] = []
        seen: set[str] = set()
        for requirement in requirements:
            text = requirement.specifier.strip()
            if not text.startswith("=="):
                continue
            version = text[2:].strip()
            if not version or any(token in version for token in ",!*<>~= "):
                continue
            if version in seen:
                continue
            seen.add(version)
            versions.append(version)
        if not versions:
            return []
        cache_key = (skill_id, namespace, ",".join(versions))
        cached = self._registry_exact_cache.get(cache_key)
        if cached is not None:
            return cached
        candidates: list[PackageCandidate] = []
        seen_sigs: set[tuple[str | None, str, str, str]] = set()
        for source in self.source_order:
            if source not in {SOURCE_REGISTRY, SOURCE_PUBLIC_REGISTRY}:
                continue
            registry_index_url = self.public_registry_index_url if source == SOURCE_PUBLIC_REGISTRY else self.registry_index_url
            if not registry_index_url:
                continue
            for version in versions:
                try:
                    manifest, entry = self.registry_manifest_downloader(registry_index_url, canonical_package_id(skill_id, namespace), version)
                except KeyError:
                    continue
                candidate_namespace = manifest.namespace or namespace
                if namespace is not None and candidate_namespace != namespace:
                    continue
                signature = (candidate_namespace, skill_id, manifest.version, source)
                if signature in seen_sigs:
                    continue
                seen_sigs.add(signature)
                candidates.append(PackageCandidate(
                    dep_type="skill", namespace=candidate_namespace, package_id=skill_id,
                    version=manifest.version, source=source, manifest=manifest,
                    artifact_url=self.registry_artifact_url_resolver(entry),
                    metadata_url=self.registry_metadata_url_resolver(entry),
                    checksum=str(entry.get("checksum") or ""), source_checksum=str(entry.get("checksum") or ""),
                ))
        self._registry_exact_cache[cache_key] = candidates
        return candidates

    def _git_candidates_for_requirements(self, skill_id: str, namespace: str | None, requirements: list[DependencyRequirement]) -> list[PackageCandidate]:
        candidates: list[PackageCandidate] = []
        seen: set[tuple[str, str | None, str | None]] = set()
        for requirement in requirements:
            if not requirement.source_ref:
                continue
            signature = (requirement.source_ref, requirement.ref, requirement.subpath)
            if signature in seen:
                continue
            seen.add(signature)
            candidate = self._git_candidate(skill_id, namespace, requirement.source_ref, requirement.ref, requirement.subpath)
            if candidate:
                candidates.append(candidate)
        return candidates

    def _source_url_candidates(self, skill_id: str, namespace: str | None, requirements: list[DependencyRequirement]) -> list[PackageCandidate]:
        """Resolve candidates from ``source_url`` declarations (community skills).

        Each requirement carries a ``source_url`` that points to a git repository
        or other remote source.  We reuse the existing ``_git_candidate`` machinery
        so that checkout, manifest loading, and checksum computation are handled
        uniformly.
        """
        candidates: list[PackageCandidate] = []
        seen: set[tuple[str, str | None, str | None]] = set()
        for requirement in requirements:
            if not requirement.source_url:
                continue
            source_url = requirement.source_url
            ref = requirement.ref or requirement.source_ref
            subpath = requirement.subpath
            signature = (source_url, ref, subpath)
            if signature in seen:
                continue
            seen.add(signature)
            candidate = self._git_candidate(skill_id, namespace, source_url, ref, subpath)
            if candidate:
                candidates.append(candidate)
        return candidates

    def _git_candidate(self, skill_id: str, namespace: str | None, source_ref: str, ref: str | None, subpath: str | None) -> PackageCandidate | None:
        source = parse_git_source_ref(source_ref)
        effective_ref = ref or source.ref
        effective_subpath = subpath or source.subpath
        try:
            skill_dir = self.git_skill_resolver(source_ref, effective_ref, effective_subpath, skill_id)
        except KeyError:
            return None
        manifest = load_git_skill_manifest(skill_dir, fallback_id=skill_id)
        candidate_namespace = manifest.namespace or namespace
        if namespace is not None and candidate_namespace != namespace:
            return None
        if manifest.id != skill_id:
            return None
        checkout_dir = git_skill_checkout_root(skill_dir, source_ref, effective_ref)
        source_commit = git_source_commit(checkout_dir)
        metadata_url = github_raw_metadata_url(source_ref, source_commit, effective_subpath) if manifest_metadata_path(skill_dir).exists() else None
        return PackageCandidate(
            dep_type="skill", namespace=candidate_namespace, package_id=skill_id,
            version=manifest.version, source=SOURCE_GIT_REPO, manifest=manifest, path=skill_dir,
            metadata_url=metadata_url, source_ref=source_ref, source_url=source.clone_url,
            source_commit=source_commit, ref=effective_ref, subpath=effective_subpath,
            checksum=hash_skill_directory(skill_dir), source_checksum=hash_skill_directory(skill_dir),
        )
