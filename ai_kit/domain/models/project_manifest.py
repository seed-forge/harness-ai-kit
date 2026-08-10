"""Project manifest Pydantic models."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ai_kit import package_manager as pm
from ai_kit.domain.runtime_install import RUNTIME_PROFILES
from ai_kit.domain.versions import is_latest_specifier

from .constants import LEGACY_PROJECT_MANIFEST_SCHEMA_VERSION, PROJECT_MANIFEST_SCHEMA_VERSION


class ProjectRootSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    namespace: str | None = None
    id: str
    features: list[str] = Field(default_factory=list)
    sources: list[
        Literal[
            "repo-checkout",
            "skill-registry",
            "public-registry",
            "git-repo",
            "local-cache",
            "lockfile",
        ]
    ] = Field(default_factory=list)
    source_ref: str | None = None
    ref: str | None = None
    subpath: str | None = None
    version: str | None = None
    extends: list[dict] | None = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def normalize_shorthand_payload(cls, value: Any) -> Any:
        if isinstance(value, str):
            text = value.strip()
            if pm.is_git_source_selector(text):
                source = pm.parse_git_source_ref(text)
                fallback_id = Path(source.subpath).name if source.subpath else pm.git_source_repo_name(text)
                return {
                    "id": fallback_id,
                    "sources": [pm.SOURCE_GIT_REPO],
                    "source_ref": text,
                    "ref": source.ref,
                    "subpath": source.subpath,
                }
            namespace, root_id = pm.split_canonical_id(text)
            payload: dict[str, object] = {"id": root_id}
            if namespace:
                payload["namespace"] = namespace
            return payload
        if isinstance(value, dict):
            payload = dict(value)
            raw_id = payload.get("id")
            if isinstance(raw_id, str) and "/" in raw_id and not payload.get("namespace"):
                namespace, root_id = pm.split_canonical_id(raw_id)
                payload["id"] = root_id
                if namespace:
                    payload["namespace"] = namespace
            source_ref = str(payload.get("source_ref") or "").strip()
            if source_ref:
                source = pm.parse_git_source_ref(source_ref)
                payload.setdefault("sources", [pm.SOURCE_GIT_REPO])
                payload.setdefault("ref", source.ref)
                payload.setdefault("subpath", source.subpath)
                if not str(payload.get("id") or "").strip():
                    payload["id"] = Path(source.subpath).name if source.subpath else pm.git_source_repo_name(source_ref)
            return payload
        return value

    @field_validator("namespace")
    @classmethod
    def validate_namespace(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        if "/" in value:
            raise ValueError("Project root namespace must be a single segment.")
        return value

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Project root id cannot be empty.")
        if "/" in value:
            raise ValueError("Project root id must not contain '/'. Use the namespace field instead.")
        return value

    @field_validator("features")
    @classmethod
    def validate_features(cls, value: list[str]) -> list[str]:
        deduped: list[str] = []
        for item in value:
            feature = str(item).strip()
            if feature and feature not in deduped:
                deduped.append(feature)
        return deduped

    @field_validator("source_ref", "ref", "subpath")
    @classmethod
    def validate_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        return text or None

    @field_validator("version")
    @classmethod
    def validate_version(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = str(value).strip()
        if not value:
            return None
        from packaging.specifiers import InvalidSpecifier, SpecifierSet
        try:
            SpecifierSet(value)
        except InvalidSpecifier as exc:
            raise ValueError(f"Invalid version specifier: {value}") from exc
        return value


class ProjectVersionedAssetSpec(BaseModel):
    model_config = ConfigDict(extra="ignore")

    namespace: str | None = None
    id: str
    version: str = "latest"

    @field_validator("namespace")
    @classmethod
    def validate_namespace(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        if "/" in value:
            raise ValueError("Project asset namespace must be a single segment.")
        return value

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Project asset id cannot be empty.")
        if "/" in value:
            raise ValueError("Project asset id must not contain '/'. Use the namespace field instead.")
        return value

    @field_validator("version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        value = str(value).strip()
        if is_latest_specifier(value):
            return value
        from packaging.specifiers import InvalidSpecifier, SpecifierSet
        try:
            SpecifierSet(value)
        except InvalidSpecifier as exc:
            raise ValueError(f"Invalid version specifier: {value}") from exc
        return value


class ProjectManifestAssets(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skills: list[ProjectRootSpec] = Field(default_factory=list)
    clis: list[ProjectVersionedAssetSpec] = Field(default_factory=list)
    plugins: list[ProjectVersionedAssetSpec] = Field(default_factory=list)
    hooks: list[ProjectVersionedAssetSpec] = Field(default_factory=list)
    subagents: list[ProjectVersionedAssetSpec] = Field(default_factory=list)
    mcps: list[ProjectVersionedAssetSpec] = Field(default_factory=list)
    loops: list[ProjectVersionedAssetSpec] = Field(default_factory=list)


class ProjectManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = PROJECT_MANIFEST_SCHEMA_VERSION
    runtime: str = "codex"
    scope: str = "project"
    runtime_priority: list[str] = Field(default_factory=list)
    roots: list[ProjectRootSpec] = Field(default_factory=list)
    features: list[str] = Field(default_factory=list)
    assets: ProjectManifestAssets = Field(default_factory=ProjectManifestAssets)
    sync_targets: list[str] = Field(default_factory=list)

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, value: str) -> str:
        value = str(value)
        if value not in {LEGACY_PROJECT_MANIFEST_SCHEMA_VERSION, PROJECT_MANIFEST_SCHEMA_VERSION}:
            raise ValueError(f"Unsupported project manifest schema_version: {value}")
        return value

    @field_validator("runtime")
    @classmethod
    def validate_runtime(cls, value: str) -> str:
        value = value.strip()
        if value not in RUNTIME_PROFILES:
            available = ", ".join(sorted(RUNTIME_PROFILES))
            raise ValueError(f"Unsupported runtime: {value}. Available runtimes: {available}")
        return value

    @field_validator("scope")
    @classmethod
    def validate_scope(cls, value: str) -> str:
        value = value.strip()
        if value not in {"project", "global"}:
            raise ValueError("Project manifest scope must be project or global.")
        return value

    @field_validator("features")
    @classmethod
    def validate_features(cls, value: list[str]) -> list[str]:
        deduped: list[str] = []
        for item in value:
            item = str(item).strip()
            if item and item not in deduped:
                deduped.append(item)
        return deduped

    @field_validator("runtime_priority")
    @classmethod
    def validate_runtime_priority(cls, value: list[str]) -> list[str]:
        validated: list[str] = []
        for item in value:
            item = str(item).strip()
            if not item:
                continue
            if item not in RUNTIME_PROFILES:
                available = ", ".join(sorted(RUNTIME_PROFILES))
                raise ValueError(
                    f"Unknown runtime '{item}' in runtime_priority. Available: {available}"
                )
            if item not in validated:
                validated.append(item)
        return validated

    @field_validator("sync_targets")
    @classmethod
    def validate_sync_targets(cls, value: list[str]) -> list[str]:
        validated: list[str] = []
        for item in value:
            item = str(item).strip()
            if item and item not in validated:
                if item != "all" and item not in RUNTIME_PROFILES:
                    raise ValueError(f"Invalid sync target runtime: {item}")
                validated.append(item)
        return validated

    @model_validator(mode="after")
    def normalize_legacy_roots(self) -> "ProjectManifest":
        if self.roots and not self.assets.skills:
            self.assets.skills = [
                ProjectRootSpec(
                    namespace=item.namespace,
                    id=item.id,
                    features=list(item.features),
                    sources=list(item.sources),
                )
                for item in self.roots
            ]
        if self.schema_version == LEGACY_PROJECT_MANIFEST_SCHEMA_VERSION and not self.roots:
            self.roots = [
                ProjectRootSpec(
                    namespace=item.namespace,
                    id=item.id,
                    features=list(item.features),
                    sources=list(item.sources),
                )
                for item in self.assets.skills
            ]
        return self
