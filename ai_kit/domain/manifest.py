from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ai_kit.domain.dependencies import DependencySpec, ExtendsSpec, IntegrationSpec, _PrivateFieldsAllowed
from ai_kit.domain.policies import InstallationPolicy, SourcePolicy
from ai_kit.domain.versions import ensure_version

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
    skill_type: str = "operational"
    domain_tags: list[str] = Field(default_factory=list)
    agents_md_inject: str = ""
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
