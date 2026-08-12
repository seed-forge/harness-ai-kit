"""LoopHarness abstract interface.

Implements F-004 (loop-harness-interface) and EP-007 (lifecycle API).
Any runtime implementing this interface is LoopHarness-compliant.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from harness_ai_kit.domain.loop_workspace import WorkspaceHandle

from harness_ai_kit.domain.loop_contract import (
    CheckerVerdict,
    ConvergenceResult,
    ExecutionMode,
    LoopStatus,
    RiskLevel,
    SelfCheckVerdict,
    validate_execution_mode,
)
from harness_ai_kit.domain.loop_manifest import LoopManifest
from harness_ai_kit.domain.loop_state import LoopState, load_state, save_state


# ---------------------------------------------------------------------------
# Supporting types
# ---------------------------------------------------------------------------

@dataclass
class CheckerContext:
    """Context provided to the Checker when spawned."""
    loop_def: LoopManifest
    maker_output: str
    iteration: int
    current_state: LoopState
    workspace_path: Path | None = None
    rubric_override: dict[str, Any] | None = None


@dataclass
class LoopProfile:
    """Minimal profile representation for harness operations."""
    profile_id: str
    loop_id: str
    loop_version: str
    execution_mode: ExecutionMode = ExecutionMode.SUB_AGENT
    stop_params: dict[str, Any] = field(default_factory=dict)
    state_path: str = ""
    workspace_isolation: str = "git_worktree"


# ---------------------------------------------------------------------------
# Abstract Harness
# ---------------------------------------------------------------------------

class LoopHarness(ABC):
    """Abstract LoopHarness interface (F-004).

    Nine core methods that any compliant runtime must implement.
    """

    @abstractmethod
    def get_execution_mode(self, profile: LoopProfile) -> ExecutionMode:
        """Return the execution mode for this profile.

        Raises ValueError if risk_level=high and mode is not sub-agent.
        """
        ...

    @abstractmethod
    def spawn_checker(
        self, loop_def: LoopManifest, checker_ctx: CheckerContext
    ) -> CheckerVerdict:
        """Spawn an independent Checker to validate Maker output.

        sub-agent mode: MUST use independent agent instance + context.
        self-check mode: MAY execute lightweight verification inline.
        MUST apply anti-injection cleansing (EP-003).
        Timeout -> escalate. Model unavailable -> RuntimeError.
        """
        ...

    @abstractmethod
    def detect_convergence(self, state: LoopState) -> ConvergenceResult:
        """Detect convergence, stagnation, or divergence.

        stagnation: primary_metric unchanged < min_improvement for N rounds.
        divergence: primary_metric decreasing for M rounds.
        oscillation: verdict alternating pass/fail for last 4 rounds.
        < 2 rounds -> UNKNOWN.
        """
        ...

    @abstractmethod
    def isolate_workspace(self, loop_id: str, profile: LoopProfile) -> WorkspaceHandle:
        """Prepare an isolated workspace.

        Implementation is free: git worktree, docker, temp dir, etc.
        Returns a WorkspaceHandle for cleanup via handle.cleanup().
        """
        ...

    @abstractmethod
    def persist_state(self, state: LoopState) -> None:
        """Persist state atomically (tmp + rename). MUST be idempotent."""
        ...

    @abstractmethod
    def escalate(
        self, loop_id: str, reason: str, state: LoopState, profile: LoopProfile
    ) -> None:
        """Trigger escalation.

        MUST persist_state first, then set status=ESCALATED.
        Escalation channel failure MUST degrade to local log, never raise.
        """
        ...

    # --- Lifecycle methods (EP-007) ---

    @abstractmethod
    def pause_loop(self, state: LoopState) -> None:
        """Pause a running loop.

        MUST complete current iteration before pausing.
        MUST persist_state and set status=PAUSED.
        """
        ...

    @abstractmethod
    def resume_loop(self, state: LoopState) -> None:
        """Resume a paused loop.

        MUST verify status==PAUSED before resuming.
        MUST verify state file has not been modified by another instance.
        """
        ...

    @abstractmethod
    def cancel_loop(self, state: LoopState) -> None:
        """Cancel a loop. Irreversible.

        Callable from any state.
        MUST persist_state and set status=CANCELLED.
        MUST clean up workspace per cleanup policy.
        """
        ...


# ---------------------------------------------------------------------------
# Compliance checklist
# ---------------------------------------------------------------------------

HARNESS_COMPLIANCE_MUST = [
    "All 9 abstract methods implemented",
    "Checker independence (sub-agent mode)",
    "State atomic write",
    "escalate never raises",
    "execution_mode validation",
]

HARNESS_COMPLIANCE_SHOULD = [
    "Convergence thresholds configurable",
]


# ---------------------------------------------------------------------------
# Concrete implementation
# ---------------------------------------------------------------------------


class LoopHarnessImpl(LoopHarness):
    """Concrete implementation of the LoopHarness interface.

    Delegates all 9 abstract methods to specialized sub-modules:
    - MakerExecutor (loop_maker)
    - CheckerSpawner (loop_checker)
    - ConvergenceDetector (loop_convergence)
    - WorkspaceManager (loop_workspace)
    - EscalationChannel (loop_escalation)
    - State persistence (loop_state save_state/load_state)
    """

    def __init__(self) -> None:
        from harness_ai_kit.domain.loop_checker import CheckerSpawner
        from harness_ai_kit.domain.loop_convergence import ConvergenceDetector
        from harness_ai_kit.domain.loop_escalation import EscalationChannel
        from harness_ai_kit.domain.loop_maker import MakerExecutor
        from harness_ai_kit.domain.loop_workspace import WorkspaceManager

        self._maker = MakerExecutor()
        self._checker = CheckerSpawner()
        self._detector = ConvergenceDetector()
        self._workspace = WorkspaceManager()
        self._escalation = EscalationChannel()

    # ------------------------------------------------------------------
    # Core abstract methods
    # ------------------------------------------------------------------

    def get_execution_mode(self, profile: LoopProfile) -> ExecutionMode:
        """Return the execution mode for this profile.

        Raises ValueError if risk_level=high and mode is not sub-agent.
        """
        # Determine risk level from profile stop_params or default to medium
        risk_level = profile.stop_params.get("risk_level", "medium")
        if isinstance(risk_level, str):
            risk_level = RiskLevel(risk_level)
        validate_execution_mode(risk_level, profile.execution_mode)
        return profile.execution_mode

    def spawn_checker(
        self, loop_def: LoopManifest, checker_ctx: CheckerContext
    ) -> CheckerVerdict:
        """Spawn an independent Checker to validate Maker output.

        sub-agent mode: uses subprocess.run ccw cli --mode analysis.
        self-check mode: executes lightweight inline verification.
        """
        mode = loop_def.loop_specific.execution_mode
        rubric = loop_def.loop_specific.checker.rubric

        if mode == ExecutionMode.SUB_AGENT:
            # Build prompt from CHECK.md + maker output + rubric
            # Workspace path from context or default
            workspace = checker_ctx.workspace_path
            if workspace is None:
                workspace = Path(".")

            check_md_path = workspace / loop_def.loop_specific.checker.entry
            prompt = self._checker.assemble_prompt(
                check_md_path=check_md_path,
                maker_output=checker_ctx.maker_output,
                rubric_dimensions=[
                    {
                        "name": d.name,
                        "description": d.description,
                        "weight": d.weight,
                        "severity": d.severity.value,
                    }
                    for d in rubric.dimensions
                ] if rubric.dimensions else None,
            )

            return self._checker.spawn_and_evaluate(
                workspace_path=workspace,
                prompt=prompt,
                iteration=checker_ctx.iteration,
            )
        else:
            # Self-check mode: inline evaluation
            from harness_ai_kit.domain.loop_contract import Rubric

            rubric_obj = None
            if rubric.dimensions:
                rubric_obj = Rubric(
                    dimensions=rubric.dimensions,
                    pass_threshold=rubric.pass_threshold,
                )

            return self._checker.evaluate_inline(
                maker_output=checker_ctx.maker_output,
                iteration=checker_ctx.iteration,
                rubric=rubric_obj,
            )

    def detect_convergence(self, state: LoopState) -> ConvergenceResult:
        """Detect convergence, stagnation, or divergence.

        Phase 1: Returns UNKNOWN trend with CONTINUE recommendation.
        """
        return self._detector.detect(state)

    def isolate_workspace(self, loop_id: str, profile: LoopProfile) -> WorkspaceHandle:
        """Prepare an isolated workspace.

        Uses git worktree or temp_dir based on profile configuration.
        Returns a WorkspaceHandle for caller-managed cleanup.
        """
        return self._workspace.isolate(loop_id)

    def persist_state(self, state: LoopState) -> None:
        """Persist state atomically (tmp + rename). MUST be idempotent."""
        state_path = state.custom_state.get("state_path", "")
        if not state_path:
            raise ValueError(
                "state.custom_state['state_path'] must be set before calling persist_state"
            )
        path = Path(state_path)
        save_state(state, path)

    def escalate(
        self, loop_id: str, reason: str, state: LoopState, profile: LoopProfile
    ) -> None:
        """Trigger escalation.

        MUST persist_state first, then set status=ESCALATED.
        Escalation channel failure MUST degrade to local log, never raise.
        """
        # Persist state first
        if state.custom_state.get("state_path"):
            try:
                self.persist_state(state)
            except Exception as exc:
                # Log but continue escalation even if persist fails
                import logging
                logging.getLogger(__name__).warning(
                    "State persist failed during escalation: %s", exc,
                )

        # Set status to ESCALATED
        state.status = LoopStatus.ESCALATED

        # Trigger escalation channel (never raises)
        self._escalation.escalate(
            loop_id=loop_id,
            reason=reason,
            state=state,
            profile_id=profile.profile_id,
        )

    # ------------------------------------------------------------------
    # Lifecycle methods (EP-007)
    # ------------------------------------------------------------------

    def pause_loop(self, state: LoopState) -> None:
        """Pause a running loop.

        MUST complete current iteration before pausing.
        MUST persist_state and set status=PAUSED.
        """
        state.status = LoopStatus.PAUSED
        if state.custom_state.get("state_path"):
            self.persist_state(state)

    def resume_loop(self, state: LoopState) -> None:
        """Resume a paused loop.

        MUST verify status==PAUSED before resuming.
        MUST verify state file has not been modified by another instance.
        """
        if state.status != LoopStatus.PAUSED:
            raise ValueError(
                f"Cannot resume loop: status is {state.status.value}, expected paused"
            )

        # Verify state file has not been modified
        state_path = state.custom_state.get("state_path", "")
        if state_path:
            saved_path = Path(state_path)
            if saved_path.exists():
                saved_state = load_state(saved_path)
                if saved_state and saved_state.updated_at != state.updated_at:
                    raise RuntimeError(
                        "State file was modified by another instance. "
                        f"Expected updated_at={state.updated_at}, "
                        f"got {saved_state.updated_at}"
                    )

        state.status = LoopStatus.RUNNING
        if state_path:
            self.persist_state(state)

    def cancel_loop(self, state: LoopState) -> None:
        """Cancel a loop. Irreversible.

        Callable from any state.
        MUST persist_state and set status=CANCELLED.
        MUST clean up workspace per cleanup policy.
        """
        state.status = LoopStatus.CANCELLED
        if state.custom_state.get("state_path"):
            self.persist_state(state)
        # Workspace cleanup is handled by the caller (LoopDriver)
        # via WorkspaceHandle.cleanup()
