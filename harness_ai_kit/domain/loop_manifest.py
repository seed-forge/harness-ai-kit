"""Loop asset manifest (loop.json) Pydantic model.

Implements F-001 (loop-asset-schema) and F-002 (loop-specific fields).
"""
from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from harness_ai_kit.domain.dependencies import DependencySpec
from harness_ai_kit.domain.loop_contract import (
    ExecutionMode,
    RiskLevel,
    RubricDimension,
    RubricSeverity,
    StopCondition,
    StopConditions,
    validate_execution_mode,
    validate_predicate,
)
from harness_ai_kit.domain.manifest import ExecutionContext
from harness_ai_kit.domain.policies import InstallationPolicy, SourcePolicy
from harness_ai_kit.domain.versions import ensure_version

_LOOP_ID_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


# ---------------------------------------------------------------------------
# Maker / Checker definitions
# ---------------------------------------------------------------------------

class MakerConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entry: str = "LOOP.md"
    agent_type: Literal["subagent", "self-check-context"] = "subagent"
    description: str = ""


class CheckerRubric(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dimensions: list[RubricDimension] = Field(default_factory=list)
    pass_threshold: float = Field(default=0.8, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_weights_sum(self) -> "CheckerRubric":
        if self.dimensions:
            total = sum(d.weight for d in self.dimensions)
            if total < 0.95 or total > 1.05:
                raise ValueError(
                    f"Rubric dimension weights must sum to 0.95-1.05, got {total:.3f}"
                )
        return self


class CheckerConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entry: str = "CHECK.md"
    agent_type: Literal["subagent", "self-check-context"] = "subagent"
    description: str = ""
    rubric: CheckerRubric = Field(default_factory=CheckerRubric)


class ConvergenceMetricConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    primary: str = "checker_score"
    direction: Literal["increase", "decrease"] = "increase"
    stagnation_threshold: int = Field(default=3, ge=1)
    divergence_threshold: int = Field(default=2, ge=1)


class LoopSpecific(BaseModel):
    """Loop-specific configuration embedded in loop.json."""

    model_config = ConfigDict(extra="forbid")

    maker: MakerConfig = Field(default_factory=MakerConfig)
    checker: CheckerConfig = Field(default_factory=CheckerConfig)
    stop_conditions: StopConditions
    convergence_metric: ConvergenceMetricConfig = Field(default_factory=ConvergenceMetricConfig)
    risk_level: RiskLevel = RiskLevel.MEDIUM
    execution_mode: ExecutionMode = ExecutionMode.SUB_AGENT

    # Domain extension blocks already in use across team loops (F-002 extension).
    # Keep them optional so extra="forbid" still rejects truly unknown keys.
    target_repo: dict | list | str | None = None
    report_output: dict | list | str | None = None
    human_decisions: dict | list | str | None = None
    audit_delegate: dict | list | str | None = None
    audit_scope: dict | list | str | None = None
    audit_dimensions: dict | list | str | None = None
    handling_tiers: dict | list | str | None = None
    newapi: dict | list | str | None = None
    draft_source: dict | list | str | None = None
    boundaries: dict | list | str | None = None
    target_scope: dict | list | str | None = None
    ledger: dict | list | str | None = None
    target_workspaces: dict | list | str | None = None
    publish_targets: dict | list | str | None = None

    @model_validator(mode="after")
    def validate_execution_mode_constraint(self) -> "LoopSpecific":
        try:
            validate_execution_mode(self.risk_level, self.execution_mode)
        except ValueError:
            # For manifest validation, coerce to sub-agent if invalid
            object.__setattr__(self, "execution_mode", ExecutionMode.SUB_AGENT)
        return self


# ---------------------------------------------------------------------------
# Companion docs
# ---------------------------------------------------------------------------

class LoopCompanionDocs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    usage: str = "USAGE.md"
    example: str = "EXAMPLE.md"
    example_required: bool = False


class TriggerContract(BaseModel):
    """Machine-readable contract for a scheduler's thin loop invocation."""

    model_config = ConfigDict(extra="forbid")

    entry: str = "LOOP.md"
    profile: str | None = None
    mode: str = "maker"
    output: str = "standard"
    mutation_policy: str = "controlled"
    scheduler_ownership: str = "external"
    prompt: str = ""


# ---------------------------------------------------------------------------
# Main loop manifest
# ---------------------------------------------------------------------------

class LoopManifest(BaseModel):
    """The loop.json asset manifest (F-001)."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1"
    namespace: str | None = None
    id: str
    name: str
    owner: str
    version: str
    status: str = "draft"
    package_type: Literal["loop"] = "loop"
    tags: list[str] = Field(default_factory=list)
    summary: str = ""
    description: str = ""
    execution_context: ExecutionContext = Field(default_factory=ExecutionContext)
    installation: InstallationPolicy = Field(
        default_factory=lambda: InstallationPolicy(default_scope="project", install_mode="skill_dir")
    )
    entry: str = "LOOP.md"
    dependencies: list[DependencySpec] = Field(default_factory=list)
    sources: SourcePolicy = Field(default_factory=SourcePolicy)
    companion_docs: LoopCompanionDocs = Field(default_factory=LoopCompanionDocs)
    trigger_contract: TriggerContract | None = None
    environment: dict = Field(default_factory=dict)
    runtime_requirements: list[str] = Field(default_factory=list)
    post_install_hints: list[str] = Field(default_factory=list)
    loop_specific: LoopSpecific
    updated_at: str | None = None

    # --- Validators ---

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("id cannot be empty")
        if not _LOOP_ID_PATTERN.match(v):
            raise ValueError(
                f"Loop id must be kebab-case (^[a-z0-9]+(-[a-z0-9]+)*$), got '{v}'"
            )
        return v

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        return ensure_version(v)

    @field_validator("name", "owner", "status")
    @classmethod
    def validate_required_text(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Required text fields cannot be empty.")
        return v

    @field_validator("namespace")
    @classmethod
    def validate_namespace(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if "/" in v:
            raise ValueError("Namespace must be a single segment.")
        return v

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("schema_version cannot be empty")
        return v

    @model_validator(mode="after")
    def reject_runtime_specific_execution_context(self) -> "LoopManifest":
        """Keep the portable Loop contract separate from its runner."""
        if self.execution_context.server_runtime is not None:
            raise ValueError(
                "Loop manifests must not bind to a server_runtime; "
                "configure the execution environment outside the Loop asset."
            )
        return self


def load_loop_manifest(data: dict) -> LoopManifest:
    """Parse and validate a loop.json dict into a LoopManifest."""
    return LoopManifest.model_validate(data)


def load_loop_manifest_file(path) -> LoopManifest:
    """Load and validate a loop.json file."""
    import json
    from pathlib import Path

    p = Path(path)
    text = p.read_text(encoding="utf-8")
    data = json.loads(text)
    return load_loop_manifest(data)
