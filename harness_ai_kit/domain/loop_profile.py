"""Loop Profile configuration parsing and validation.

Implements F-005 (loop-profile-config).
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from harness_ai_kit.domain.loop_contract import ExecutionMode, RiskLevel, TriggerType


class TriggerConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: TriggerType
    event_source: str | None = None
    event_filter: dict[str, Any] = Field(default_factory=dict)
    cron_expression: str | None = None
    timezone: str = "UTC"

    @model_validator(mode="after")
    def validate_trigger_shape(self) -> "TriggerConfig":
        if self.type == TriggerType.CRON and not self.cron_expression:
            raise ValueError("cron trigger requires cron_expression")
        if self.type == TriggerType.EVENT and not self.event_source:
            raise ValueError("event trigger requires event_source")
        if self.type != TriggerType.CRON and self.cron_expression:
            raise ValueError("cron_expression is only valid for cron triggers")
        return self


class EscalationTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["notification", "issue", "webhook"] = "notification"
    target: str = ""
    assignee: str | None = None
    labels: list[str] = Field(default_factory=list)


class EscalationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    on_stagnation: EscalationTarget | None = None
    on_divergence: EscalationTarget | None = None
    on_unrecoverable: EscalationTarget | None = None


class WorkspaceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    isolation: Literal["git_worktree", "docker", "temp_dir"] = "git_worktree"
    base_branch: str = "main"
    branch_prefix: str = "loop/"
    cleanup: str = "keep_last_3"


class ConvergenceParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stagnation_rounds: int = Field(default=3, ge=1)
    divergence_rounds: int = Field(default=2, ge=1)


class StateConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = ""
    strategy: Literal["single", "rotation"] = "single"


class LoopRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    version: str


class LoopProfileConfig(BaseModel):
    """A Loop Profile instance configuration (F-005)."""

    model_config = ConfigDict(extra="forbid")

    profile_id: str
    description: str = ""
    loop: LoopRef
    trigger: TriggerConfig
    stop_params: dict[str, Any] = Field(default_factory=dict)
    execution_mode: ExecutionMode = ExecutionMode.SUB_AGENT
    convergence: ConvergenceParams = Field(default_factory=ConvergenceParams)
    state: StateConfig = Field(default_factory=StateConfig)
    escalation: EscalationConfig = Field(default_factory=EscalationConfig)
    workspace: WorkspaceConfig = Field(default_factory=WorkspaceConfig)

    @field_validator("profile_id")
    @classmethod
    def validate_profile_id(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("profile_id cannot be empty")
        return v

    def validate_execution_mode_against_risk(self, risk_level: RiskLevel) -> None:
        """Enforce execution mode constraints from F-002/F-005."""
        if risk_level == RiskLevel.HIGH and self.execution_mode != ExecutionMode.SUB_AGENT:
            raise ValueError(
                f"Loop risk_level=high forces sub-agent mode, "
                f"but profile specifies {self.execution_mode.value}"
            )
        if risk_level == RiskLevel.MEDIUM and self.execution_mode == ExecutionMode.SELF_CHECK:
            raise ValueError(
                f"Loop risk_level=medium prohibits self-check mode"
            )


def load_profile_config(data: dict) -> LoopProfileConfig:
    """Parse and validate a profile dict."""
    return LoopProfileConfig.model_validate(data)


def load_profile_config_file(path) -> LoopProfileConfig:
    """Load and validate a profile YAML/JSON file."""
    import json
    from pathlib import Path

    p = Path(path)
    text = p.read_text(encoding="utf-8")
    # Try YAML first, fall back to JSON
    try:
        import yaml
        data = yaml.safe_load(text)
    except ImportError:
        data = json.loads(text)
    return load_profile_config(data)
