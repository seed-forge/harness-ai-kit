from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from harness_ai_kit.domain.dependencies import DependencySpec, ExtendsSpec, IntegrationSpec, _PrivateFieldsAllowed
from harness_ai_kit.domain.policies import InstallationPolicy, SourcePolicy
from harness_ai_kit.domain.versions import ensure_version

MANAGED_ASSET_TYPES = ("skill", "plugin", "hook", "subagent", "mcp", "loop")
DEPENDENCY_TYPES = (*MANAGED_ASSET_TYPES, "cli", "mcp")
ASSET_METADATA_FILENAMES = {
    "skill": "skill.json",
    "plugin": "asset.json",
    "hook": "asset.json",
    "subagent": "asset.json",
    "mcp": "mcp.json",
    "loop": "loop.json",
}


class ExecutionContext(_PrivateFieldsAllowed):
    """Declares where a skill/loop can execute (ide vs headless server)."""

    model_config = ConfigDict(extra="forbid")

    ide: bool = True
    """IDE agent available (Qoder/Codex/Cursor, has codebase access)."""
    server: bool = False
    """Headless server/worker container available."""
    requires_codebase: bool = False
    """Needs full codebase/workspace files."""
    requires_browser: bool = False
    """Needs a browser (Playwright/social-auto-upload etc.)."""
    requires_interactive: bool = False
    """Needs user interaction (confirmation dialogs, scan-login)."""
    server_runtime: Literal["cli-direct", "codebase-sandbox", "data-params"] | None = None
    """Server-mode runtime type. Only meaningful when server=True.
    - cli-direct: direct CLI invocation, no codebase needed
    - codebase-sandbox: git clone -> execute -> push -> PR -> approval
    - data-params: Temporal-native, activity receives data as parameters
    """


class CompanionDocs(_PrivateFieldsAllowed):
    model_config = ConfigDict(extra="forbid")

    usage: str = "USAGE.md"
    example: str = "EXAMPLE.md"
    example_required: bool = False


class ExecutableRequirement(_PrivateFieldsAllowed):
    model_config = ConfigDict(extra="forbid")

    name: str
    command: str
    platforms: list[str] = Field(default_factory=list)
    optional: bool = False
    install_commands: list[str] = Field(default_factory=list)

    @field_validator("name", "command")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Executable requirement fields cannot be empty.")
        return value

    @field_validator("platforms", "install_commands")
    @classmethod
    def validate_string_list(cls, value: list[str]) -> list[str]:
        deduped: list[str] = []
        for item in value:
            text = str(item).strip()
            if text and text not in deduped:
                deduped.append(text)
        return deduped


class EnvironmentRequirements(_PrivateFieldsAllowed):
    model_config = ConfigDict(extra="forbid")

    dependency_groups: list[str] = Field(default_factory=list)
    system: list[ExecutableRequirement] = Field(default_factory=list)
    python_strategy: Literal["none", "project-venv", "global-python"] = "none"
    python_packages: list[str] = Field(default_factory=list)
    fonts: list[str] = Field(default_factory=list)
    verify_commands: list[str] = Field(default_factory=list)

    @field_validator("dependency_groups", "python_packages", "fonts", "verify_commands")
    @classmethod
    def validate_string_list(cls, value: list[str]) -> list[str]:
        deduped: list[str] = []
        for item in value:
            text = str(item).strip()
            if text and text not in deduped:
                deduped.append(text)
        return deduped


class AgentsInjectEntry(_PrivateFieldsAllowed):
    """A single AGENTS.md injection declared by a skill."""

    model_config = ConfigDict(extra="forbid")

    path: str = "AGENTS.md"
    scope: Literal["project"] = "project"
    when: Literal["on_install"] = "on_install"
    content: str = ""

    @field_validator("path", "content")
    @classmethod
    def validate_text(cls, value: str) -> str:
        return value.strip()


def _normalize_relative_document_path(value: str) -> str:
    """Keep metadata-owned document references inside one asset directory."""
    text = value.strip().replace("\\", "/")
    path = PurePosixPath(text)
    if not text or path.is_absolute() or ".." in path.parts:
        raise ValueError("Document paths must be non-empty, asset-relative paths.")
    return path.as_posix()


class UpstreamProvenance(_PrivateFieldsAllowed):
    """Pinned, attributable upstream used to adapt an asset."""

    model_config = ConfigDict(extra="forbid")

    url: str
    revision: str
    license: str
    retrieved_at: str | None = None
    adaptation: str = ""

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        value = value.strip()
        if not re.match(r"^https?://", value, re.IGNORECASE):
            raise ValueError("Upstream provenance URLs must use http or https.")
        return value

    @field_validator("revision", "license", "adaptation")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Upstream provenance fields cannot be empty.")
        return value

    @field_validator("retrieved_at")
    @classmethod
    def validate_retrieved_at(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError("retrieved_at must use YYYY-MM-DD.")
        return value


class AssetProvenance(_PrivateFieldsAllowed):
    """Lineage metadata separate from installation source policy."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["original", "public-remix", "internal-remix"] = "original"
    upstreams: list[UpstreamProvenance] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_upstream_for_remix(self) -> "AssetProvenance":
        if self.kind != "original" and not self.upstreams:
            raise ValueError("Remixed assets must declare at least one pinned upstream.")
        return self


class LoadRoute(_PrivateFieldsAllowed):
    """One conditional documentation route for a folder-light or routed Skill."""

    model_config = ConfigDict(extra="forbid")

    id: str
    triggers: list[str] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        value = value.strip()
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", value):
            raise ValueError("Load route ids must use lowercase letters, numbers, and hyphens.")
        return value

    @field_validator("triggers")
    @classmethod
    def validate_triggers(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        for value in values:
            text = str(value).strip()
            if text and text not in cleaned:
                cleaned.append(text)
        if not cleaned:
            raise ValueError("Load routes must declare at least one trigger.")
        return cleaned

    @field_validator("references")
    @classmethod
    def validate_references(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        for value in values:
            path = _normalize_relative_document_path(str(value))
            if path not in cleaned:
                cleaned.append(path)
        return cleaned


class LoadPlan(_PrivateFieldsAllowed):
    """Progressive loading contract. It documents selection, not dependencies."""

    model_config = ConfigDict(extra="forbid")

    always_read: list[str] = Field(default_factory=list)
    routes: list[LoadRoute] = Field(default_factory=list)

    @field_validator("always_read")
    @classmethod
    def validate_always_read(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        for value in values:
            path = _normalize_relative_document_path(str(value))
            if path not in cleaned:
                cleaned.append(path)
        return cleaned

    @model_validator(mode="after")
    def validate_route_ids(self) -> "LoadPlan":
        route_ids = [route.id for route in self.routes]
        if len(route_ids) != len(set(route_ids)):
            raise ValueError("Load route ids must be unique.")
        overlap = set(self.always_read)
        for route in self.routes:
            duplicate = overlap.intersection(route.references)
            if duplicate:
                raise ValueError(
                    f"References cannot be both always_read and route-specific: {', '.join(sorted(duplicate))}."
                )
        return self


class SkillManifest(_PrivateFieldsAllowed):
    model_config = ConfigDict(extra="forbid")

    schema_version: str | None = None
    namespace: str | None = None
    id: str
    name: str
    owner: str
    version: str
    status: str
    visibility: Literal["internal", "public", "private", "unlisted"] | None = None
    entry: str = "SKILL.md"
    package_type: Literal["skill", "plugin", "hook", "subagent", "mcp", "loop"] = "skill"
    tags: list[str] = Field(default_factory=list)
    summary: str = ""
    description: str = ""
    owners: list[str] = Field(default_factory=list)
    license: str = ""
    homepage: str = ""
    repository: str = ""
    compatible_clients: list[str] = Field(default_factory=list)
    execution_context: ExecutionContext = Field(default_factory=ExecutionContext)
    installation: InstallationPolicy = Field(default_factory=InstallationPolicy)
    dependencies: list[DependencySpec] = Field(default_factory=list)
    integrations: list[IntegrationSpec] = Field(default_factory=list)
    extends: list[ExtendsSpec] | None = Field(default_factory=list)
    sources: SourcePolicy = Field(default_factory=SourcePolicy)
    companion_docs: CompanionDocs = Field(default_factory=CompanionDocs)
    companion_cli: str | None = None
    environment: EnvironmentRequirements = Field(default_factory=EnvironmentRequirements)
    runtime_requirements: list[str] = Field(default_factory=list)
    post_install_hints: list[str] = Field(default_factory=list)
    recommended_tools: list[str] = Field(default_factory=list)
    contributors: list[dict[str, str]] = Field(default_factory=list)
    provenance: AssetProvenance | None = None
    structure_profile: Literal["direct", "folder-light", "routed"] | None = None
    responsibility_keys: list[str] = Field(default_factory=list)
    load_plan: LoadPlan | None = None
    skill_type: str = "operational"
    domain_tags: list[str] = Field(default_factory=list)
    agents_md_inject: str = ""
    agents_inject: list[AgentsInjectEntry] = Field(default_factory=list)
    config_schema: str | None = None
    loop_specific: dict[str, Any] | None = None
    updated_at: str | None = None

    @field_validator("namespace")
    @classmethod
    def validate_namespace(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        if "/" in value:
            raise ValueError("Namespace must be a single segment.")
        return value

    @field_validator("name", "owner", "status", "entry")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Required text fields cannot be empty.")
        return value

    @field_validator("description", "license", "homepage", "repository")
    @classmethod
    def validate_optional_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Required text fields cannot be empty.")
        if "/" in value:
            raise ValueError("Skill id must not contain '/'. Use the namespace field instead.")
        return value

    @field_validator("version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        return ensure_version(value)

    @field_validator("owners")
    @classmethod
    def validate_owners(cls, value: list[str]) -> list[str]:
        deduped: list[str] = []
        for item in value:
            text = str(item).strip()
            if text and text not in deduped:
                deduped.append(text)
        return deduped

    @field_validator("responsibility_keys")
    @classmethod
    def validate_responsibility_keys(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        for value in values:
            text = str(value).strip()
            if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", text):
                raise ValueError("responsibility_keys must use lowercase letters, numbers, and hyphens.")
            if text in cleaned:
                raise ValueError("responsibility_keys must be unique within an asset.")
            cleaned.append(text)
        return cleaned

    @model_validator(mode="after")
    def validate_structure_contract(self) -> "SkillManifest":
        if self.structure_profile == "direct" and self.load_plan is not None:
            raise ValueError("direct Skills cannot declare a load_plan; keep their procedure in SKILL.md.")
        if self.structure_profile == "routed" and (self.load_plan is None or not self.load_plan.routes):
            raise ValueError("routed Skills must declare at least one load_plan route.")
        if self.structure_profile is not None and not self.responsibility_keys:
            raise ValueError("Skills with a structure_profile must declare responsibility_keys.")
        return self
