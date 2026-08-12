from __future__ import annotations

import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from resolvelib.resolvers import ResolutionImpossible

from .project_manifest_dto import (
    InitProjectRequest,
    InitProjectResult,
    ManifestMigrateRequest,
    ManifestMigrateResult,
    ProjectAddRequest,
    ProjectAddResult,
    ProjectRemoveRequest,
    ProjectRemoveResult,
)
from harness_ai_kit.domain.lockfile_io import state_dir


MANAGED_ASSET_KINDS = {"plugin", "hook", "subagent", "mcp", "loop"}


__all__ = [
    "ProjectManifestPorts",
    "ProjectManifestService",
    "MANAGED_ASSET_KINDS",
    "InitProjectRequest",
    "InitProjectResult",
    "ManifestMigrateRequest",
    "ManifestMigrateResult",
    "ProjectAddRequest",
    "ProjectAddResult",
    "ProjectRemoveRequest",
    "ProjectRemoveResult",
]


@dataclass(frozen=True)
class ProjectManifestPorts:
    project_manifest_path: Callable[[Path], Path]
    parse_project_root_ref: Callable[[str], Any]
    create_manifest: Callable[..., Any]
    create_manifest_assets: Callable[..., Any]
    save_project_manifest: Callable[[Path, Any], None]
    load_contextual_project_manifest: Callable[[str | Path | None], tuple[Path | None, Any | None]]
    load_project_manifest_if_present: Callable[[], tuple[Path | None, Any | None]]
    ensure_project_manifest: Callable[[Path | None, Any | None], tuple[Path, Any]]
    find_project_lockfile: Callable[[Path], Path | None]
    infer_project_root_from_target_dir: Callable[[str | Path | None], Path | None]
    read_lockfile: Callable[[Path], Any]
    project_manifest_from_lockfile: Callable[[Any], Any]
    project_manifest_payload_text: Callable[[Any], str]
    backup_file_once: Callable[[Path], Path]
    load_effective_config: Callable[[Path], Any]
    resolve_repo_root_if_available: Callable[..., Path | None]
    load_combined_cli_inventory: Callable[[Path | None, Any], dict[str, Any]]
    load_managed_asset_inventory: Callable[[Path, str], dict[str, Any]]
    is_git_source_selector: Callable[[str], bool]
    discover_git_skills: Callable[..., list[Any]]
    version_to_pinned: Callable[[str], str]
    version_to_compatible_range: Callable[[str], str]
    create_project_root_spec: Callable[..., Any]
    create_versioned_asset_spec: Callable[..., Any]
    add_skill_to_manifest: Callable[[Any, Any], bool]
    add_versioned_asset_to_manifest: Callable[[list[Any], Any], bool]
    manifest_bucket_for_asset: Callable[[Any, str], list[Any]]
    remove_asset_from_manifest: Callable[[Any, str, str], bool]
    run_project_sync: Callable[..., dict[str, Any]]
    input_is_interactive: Callable[[], bool] = lambda: False
    choose_git_skill: Callable[[Sequence[Any]], Any | None] = lambda _discovered: None




class ProjectManifestService:
    def __init__(self, ports: ProjectManifestPorts) -> None:
        self._ports = ports

    def _global_manifest_path(self) -> Path:
        """Return the manifest path for global scope."""
        return self._ports.project_manifest_path(state_dir())

    def _load_manifest_for_scope(
        self,
        scope: str | None,
        target_dir: str | Path | None = None,
    ) -> tuple[Path | None, Any | None]:
        """Load manifest from the correct location based on scope.

        For global scope: always use global state directory, ignoring project yml.
        For project scope: use contextual project manifest.
        """
        if scope == "global":
            global_path = self._global_manifest_path()
            if global_path.exists():
                from harness_ai_kit.domain.manifest_ops import load_project_manifest
                return global_path, load_project_manifest(global_path)
            return None, None
        return self._ports.load_contextual_project_manifest(target_dir)

    def _ensure_manifest_for_scope(
        self,
        scope: str | None,
        manifest_path: Path | None,
        manifest: Any | None,
        runtime: str = "codex",
    ) -> tuple[Path, Any]:
        """Ensure manifest exists for the given scope, creating if needed."""
        if scope == "global" and (manifest_path is None or manifest is None):
            global_path = self._global_manifest_path()
            global_path.parent.mkdir(parents=True, exist_ok=True)
            manifest = self._ports.create_manifest(
                runtime=runtime,
                scope="global",
                roots=[],
                assets=self._ports.create_manifest_assets(skills=[]),
                features=[],
            )
            self._ports.save_project_manifest(global_path, manifest)
            return global_path, manifest
        return self._ports.ensure_project_manifest(
            manifest_path, manifest,
            runtime=runtime,
            scope=scope or "project",
        )

    def init_project(self, request: InitProjectRequest) -> InitProjectResult:
        manifest_path = self._ports.project_manifest_path(request.cwd)
        if manifest_path.exists() and not request.force:
            raise FileExistsError(f"Project manifest already exists: {manifest_path}")
        roots = [self._ports.parse_project_root_ref(item) for item in request.root_refs]
        manifest = self._ports.create_manifest(
            runtime=request.runtime,
            scope=request.scope,
            roots=roots,
            assets=self._ports.create_manifest_assets(skills=roots),
            features=list(request.features),
        )
        self._ports.save_project_manifest(manifest_path, manifest)
        return InitProjectResult(manifest_path=manifest_path)

    def migrate_manifest(self, request: ManifestMigrateRequest) -> ManifestMigrateResult:
        manifest_path, manifest = self._ports.load_contextual_project_manifest(request.target_dir)
        if manifest_path is None or manifest is None:
            root = self._ports.infer_project_root_from_target_dir(request.target_dir) or Path.cwd()
            lock_path = self._ports.find_project_lockfile(root)
            if lock_path is None:
                raise FileNotFoundError("No ai-kit.yml or ai-kit.lock found in the current project.")
            lockfile = self._ports.read_lockfile(lock_path)
            manifest_path = self._ports.project_manifest_path(lock_path.parent)
            manifest = self._ports.project_manifest_from_lockfile(lockfile)
            if request.dry_run:
                return ManifestMigrateResult(
                    manifest_path=manifest_path,
                    payload_text=self._ports.project_manifest_payload_text(manifest),
                    lock_path=lock_path,
                )
            self._ports.save_project_manifest(manifest_path, manifest)
            return ManifestMigrateResult(manifest_path=manifest_path, lock_path=lock_path)
        if request.dry_run:
            return ManifestMigrateResult(
                manifest_path=manifest_path,
                payload_text=self._ports.project_manifest_payload_text(manifest),
            )
        backup_path = self._ports.backup_file_once(manifest_path)
        self._ports.save_project_manifest(manifest_path, manifest)
        return ManifestMigrateResult(manifest_path=manifest_path, backup_path=backup_path)

    def add_asset(self, request: ProjectAddRequest) -> ProjectAddResult:
        config = self._ports.load_effective_config(request.config_path)
        scope = request.scope or "project"
        manifest_path, manifest = self._load_manifest_for_scope(scope, request.target_dir)
        manifest_path, manifest = self._ensure_manifest_for_scope(
            scope,
            manifest_path,
            manifest,
            runtime=request.runtime or "codex",
        )
        changed = self._add_asset_to_manifest(request, config, manifest_path, manifest)
        if not changed or request.no_install:
            # No sync will run — persist manifest change immediately
            self._ports.save_project_manifest(manifest_path, manifest)
            return ProjectAddResult(
                manifest_path=manifest_path,
                asset_kind=request.asset_kind,
                asset_id=request.asset_id,
                changed=changed,
                no_install=request.no_install,
            )
        # Defer manifest persistence until sync succeeds to avoid pollution on failure
        try:
            summary = self._ports.run_project_sync(
                config,
                manifest_path,
                manifest,
                repo_root_arg=request.repo_root,
                target_dir_override=request.target_dir,
                runtime_override=request.runtime,
                scope_override=request.scope,
                sync_repo=request.sync_repo,
                offline=request.offline,
                dry_run=False,
                cli_upgrade=True,
            )
        except ResolutionImpossible as exc:
            if request.asset_kind == "skill":
                raise ValueError(
                    f"Unknown skill ID: {request.asset_id}. "
                    "Use --source-ref <git-url> or add a known harness-ai-kit skill."
                ) from exc
            raise
        self._ports.save_project_manifest(manifest_path, manifest)
        return ProjectAddResult(
            manifest_path=manifest_path,
            asset_kind=request.asset_kind,
            asset_id=request.asset_id,
            changed=True,
            no_install=False,
            lock_path=summary["lock_path"],
        )

    def remove_asset(self, request: ProjectRemoveRequest) -> ProjectRemoveResult:
        config = self._ports.load_effective_config(request.config_path)
        scope = request.scope or "project"
        manifest_path, manifest = self._load_manifest_for_scope(scope, request.target_dir)
        if manifest_path is None or manifest is None:
            if scope == "global":
                raise FileNotFoundError(f"No global ai-kit.yml found at {self._global_manifest_path()}.")
            raise FileNotFoundError("No ai-kit.yml found in the current project.")
        if not self._ports.remove_asset_from_manifest(manifest, request.asset_kind, request.asset_id):
            raise KeyError(f"{request.asset_kind} {request.asset_id} is not declared in {manifest_path}.")
        self._ports.save_project_manifest(manifest_path, manifest)
        if request.no_install:
            return ProjectRemoveResult(
                manifest_path=manifest_path,
                asset_kind=request.asset_kind,
                asset_id=request.asset_id,
                no_install=True,
            )
        summary = self._ports.run_project_sync(
            config,
            manifest_path,
            manifest,
            repo_root_arg=request.repo_root,
            target_dir_override=request.target_dir,
            runtime_override=request.runtime,
            scope_override=request.scope,
            sync_repo=request.sync_repo,
            offline=request.offline,
            dry_run=False,
            cli_upgrade=True,
        )
        return ProjectRemoveResult(
            manifest_path=manifest_path,
            asset_kind=request.asset_kind,
            asset_id=request.asset_id,
            no_install=False,
            lock_path=summary["lock_path"],
            removed_skills=summary.get("removed_skills", []),
            removed_assets=summary.get("removed_assets", []),
        )

    def _add_asset_to_manifest(
        self,
        request: ProjectAddRequest,
        config: Any,
        manifest_path: Path,
        manifest: Any,
    ) -> bool:
        if request.asset_kind == "skill":
            return self._add_skill_asset_to_manifest(request, manifest)
        if request.source_ref or request.ref or request.subpath or request.override_id:
            raise ValueError("Git source options are only supported for `add skill`.")
        if request.asset_kind == "cli":
            repo_root = self._ports.resolve_repo_root_if_available(request.repo_root, config, cwd=manifest_path.parent)
            inventory = self._ports.load_combined_cli_inventory(repo_root, config)
            record = inventory.get(request.asset_id)
            if record is None:
                available = ", ".join(sorted(inventory))
                raise KeyError(f"Unknown CLI ID: {request.asset_id}. Available CLIs: {available}")
            version = request.version or self._ports.version_to_compatible_range(record.version)
            spec = self._ports.create_versioned_asset_spec(id=request.asset_id, version=version)
            return self._ports.add_versioned_asset_to_manifest(manifest.assets.clis, spec)
        if request.asset_kind in MANAGED_ASSET_KINDS:
            repo_root = self._ports.resolve_repo_root_if_available(request.repo_root, config, cwd=manifest_path.parent)
            if repo_root is None:
                raise FileNotFoundError("A local harness-ai-kit repository is required to add managed assets.")
            inventory = self._ports.load_managed_asset_inventory(repo_root, request.asset_kind)
            record = inventory.get(request.asset_id)
            if record is None:
                available = ", ".join(sorted(inventory))
                raise KeyError(f"Unknown {request.asset_kind} ID: {request.asset_id}. Available {request.asset_kind}s: {available}")
            version = request.version or self._ports.version_to_compatible_range(record.version)
            spec = self._ports.create_versioned_asset_spec(id=request.asset_id, version=version)
            return self._ports.add_versioned_asset_to_manifest(
                self._ports.manifest_bucket_for_asset(manifest, request.asset_kind),
                spec,
            )
        raise ValueError(f"Unsupported add asset kind: {request.asset_kind}")

    def _add_skill_asset_to_manifest(self, request: ProjectAddRequest, manifest: Any) -> bool:
        asset_is_git_source = self._ports.is_git_source_selector(request.asset_id)
        has_git_options = bool(request.source_ref or request.ref or request.subpath or request.override_id)
        extends_data = self._build_extends_payload(request)
        if not asset_is_git_source and not has_git_options:
            spec = self._ports.parse_project_root_ref(request.asset_id)
            if extends_data:
                spec = self._ports.create_project_root_spec(
                    namespace=spec.namespace,
                    id=spec.id,
                    sources=spec.sources if spec.sources else [],
                    source_ref=spec.source_ref,
                    ref=spec.ref,
                    subpath=spec.subpath,
                    version=spec.version,
                    extends=extends_data,
                )
            return self._ports.add_skill_to_manifest(manifest, spec)
        if asset_is_git_source and request.source_ref:
            raise ValueError("Use either `add skill <git-url>` or `add skill <id> --source-ref <git-url>`, not both.")
        if request.override_id and not asset_is_git_source:
            raise ValueError("`--id` is only supported when `asset_id` is a Git source URL.")
        source_ref = request.source_ref or request.asset_id
        desired_ref = request.ref
        desired_subpath = request.subpath
        desired_spec = (
            self._ports.parse_project_root_ref(request.override_id)
            if request.override_id
            else None
        )
        if not asset_is_git_source:
            desired_spec = self._ports.parse_project_root_ref(request.asset_id)
        selected = self._select_git_skill(
            source_ref=source_ref,
            ref=desired_ref,
            subpath=desired_subpath,
            desired_spec=desired_spec,
            no_input=request.no_input,
        )
        spec_namespace = desired_spec.namespace if desired_spec is not None else getattr(selected, "namespace", None)
        spec_id = desired_spec.id if desired_spec is not None else getattr(selected, "id")
        spec = self._ports.create_project_root_spec(
            namespace=spec_namespace,
            id=spec_id,
            sources=["git-repo"],
            source_ref=getattr(selected, "source_ref", source_ref),
            ref=getattr(selected, "ref", desired_ref),
            subpath=getattr(selected, "subpath", desired_subpath),
            extends=extends_data,
        )
        return self._ports.add_skill_to_manifest(manifest, spec)

    @staticmethod
    def _build_extends_payload(request: Any) -> list[dict] | None:
        """Build extends payload list from request flags.

        Validates that --extends-version is present when --extends is specified,
        and that --extends-strategy is only meaningful with --extends.
        Returns None if no extends flags are specified.
        """
        extends_base_ids = getattr(request, "extends", None) or []
        if not extends_base_ids:
            if getattr(request, "extends_version", None):
                raise ValueError("--extends-version requires --extends.")
            if getattr(request, "extends_strategy", None) and getattr(request, "extends_strategy", None) != "prepend":
                raise ValueError("--extends-strategy requires --extends.")
            return None
        extends_version = getattr(request, "extends_version", None)
        if not extends_version:
            raise ValueError("--extends-version is required when --extends is specified.")
        extends_strategy = getattr(request, "extends_strategy", "prepend") or "prepend"
        payload: list[dict] = []
        for base_id in extends_base_ids:
            base_id = str(base_id).strip()
            if not base_id:
                continue
            namespace: str | None = None
            skill_id = base_id
            if "/" in base_id:
                parts = base_id.split("/", 1)
                namespace = parts[0]
                skill_id = parts[1]
            payload.append({
                "namespace": namespace,
                "id": skill_id,
                "version": extends_version,
                "merge_strategy": extends_strategy,
            })
        return payload if payload else None

    def _select_git_skill(
        self,
        *,
        source_ref: str,
        ref: str | None,
        subpath: str | None,
        desired_spec: Any | None,
        no_input: bool,
    ) -> Any:
        try:
            discovered = self._ports.discover_git_skills(source_ref, ref=ref, subpath=subpath)
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or str(exc)).strip()
            raise ValueError(f"Failed to fetch Git skill source {source_ref}: {detail}") from exc
        except KeyError as exc:
            raise ValueError(str(exc)) from exc
        if not discovered:
            raise ValueError(f"No valid skill found in Git source {source_ref}. Expected a directory containing SKILL.md.")
        if desired_spec is not None:
            matches = [
                skill
                for skill in discovered
                if getattr(skill, "id", None) == desired_spec.id
                and getattr(skill, "namespace", None) == desired_spec.namespace
            ]
            if not matches:
                if len(discovered) == 1 and not self._has_explicit_metadata(discovered[0]):
                    return discovered[0]
                candidates = self._format_git_skill_candidates(discovered)
                requested = f"{desired_spec.namespace}/{desired_spec.id}" if desired_spec.namespace else desired_spec.id
                raise ValueError(f"Skill {requested} was not found in Git source {source_ref}. Available skills: {candidates}")
            if len(matches) > 1:
                candidates = self._format_git_skill_candidates(matches)
                raise ValueError(f"Git source {source_ref} contains multiple matches. Use --subpath to choose one: {candidates}")
            return matches[0]
        if len(discovered) != 1:
            if not no_input and self._ports.input_is_interactive():
                selected = self._ports.choose_git_skill(discovered)
                if selected is not None:
                    return selected
            candidates = self._format_git_skill_candidates(discovered)
            raise ValueError(
                f"Git source {source_ref} contains multiple skills. "
                f"Use --id <id> or --subpath <path> to choose one: {candidates}"
            )
        return discovered[0]

    @staticmethod
    def _has_explicit_metadata(skill: Any) -> bool:
        path = getattr(skill, "path", None)
        if path is None:
            return True
        skill_dir = Path(path)
        return any((skill_dir / filename).exists() for filename in ("skill.json", "asset.json", "mcp.json"))

    @staticmethod
    def _format_git_skill_candidates(discovered: Sequence[Any]) -> str:
        parts: list[str] = []
        for skill in discovered:
            skill_id = getattr(skill, "id", "")
            namespace = getattr(skill, "namespace", None)
            canonical = f"{namespace}/{skill_id}" if namespace else skill_id
            subpath = getattr(skill, "subpath", None)
            parts.append(f"{canonical} ({subpath or '.'})")
        return ", ".join(parts)
