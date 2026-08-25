from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "7"


class LockNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["skill", "plugin", "hook", "subagent", "cli", "mcp", "loop"]
    namespace: str | None = None
    id: str
    canonical_id: str | None = None
    version: str
    source: str
    checksum_algorithm: str = "sha256"
    checksum: str | None = None
    source_checksum: str | None = None
    materialized_checksum: str | None = None
    artifact_url: str | None = None
    metadata_url: str | None = None
    source_ref: str | None = None
    source_url: str | None = None
    source_commit: str | None = None
    ref: str | None = None
    subpath: str | None = None
    scope: Literal["required", "optional"] = "required"
    feature: str | None = None
    requires: list[str] = Field(default_factory=list)
    extends: list[dict] | None = Field(default_factory=list)
    companion_docs: dict[str, str | bool] = Field(default_factory=dict)
    environment: dict[str, Any] = Field(default_factory=dict)
    runtime_requirements: list[str] = Field(default_factory=list)
    post_install_hints: list[str] = Field(default_factory=list)
    recommended_tools: list[str] = Field(default_factory=list)
    contributors: list[dict[str, str]] = Field(default_factory=list)
    provenance: dict[str, Any] | None = None
    structure_profile: str | None = None
    responsibility_keys: list[str] = Field(default_factory=list)
    load_plan: dict[str, Any] | None = None
    skill_type: str = "operational"
    agents_md_inject: str = ""
    config_schema: str | None = None


class RootRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["skill", "plugin", "hook", "subagent", "cli", "mcp", "loop"]
    namespace: str | None = None
    id: str
    version: str | None = None
    feature_refs: list[str] = Field(default_factory=list)
    source_policy: list[
        Literal[
            "repo-checkout",
            "public-registry",
            "public-registry",
            "git-repo",
            "local-cache",
            "lockfile",
        ]
    ] = Field(default_factory=list)
    source_ref: str | None = None
    ref: str | None = None
    subpath: str | None = None
    extends: list[dict] | None = Field(default_factory=list)


class Lockfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    generated_at: str
    runtime: str
    install_scope: str
    roots: list[str]
    features: list[str] = Field(default_factory=list)
    root_requests: list[RootRequest] = Field(default_factory=list)
    nodes: list[LockNode]
