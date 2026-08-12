"""LoopDriver: main loop execution engine."""
from __future__ import annotations

import logging
import re
import time
from pathlib import Path
from typing import Any

from harness_ai_kit.domain.loop_contract import (
    ConvergenceResult,
    ConvergenceStatus,
    LoopStatus,
    Verdict,
)
from harness_ai_kit.domain.loop_harness import LoopHarness, LoopHarnessImpl, LoopProfile
from harness_ai_kit.domain.loop_lock import LoopLockManager
from harness_ai_kit.domain.loop_manifest import LoopManifest
from harness_ai_kit.domain.loop_runtime import LoopRuntime
from harness_ai_kit.domain.loop_state import (
    ConvergenceMetricEntry,
    IterationDetail,
    LoopState,
    _now_iso,
    save_state,
)
from harness_ai_kit.domain.loop_workspace import WorkspaceHandle

from .models import LoopAction, LoopOutcome, IterationRecord
from .evaluator import _eval_predicate

logger = logging.getLogger(__name__)


class LoopDriver:
    """Main loop execution engine.

    Lifecycle:
        1. acquire_lock
        2. isolate_workspace
        3. clear_pause (ready to run)
        4. while True:
            a. check cancel/pause/budget/max_iterations
            b. _one_iteration
            c. _evaluate_action
            d. handle action (continue/success/failure/escalate/pause)
        5. finally: release_lock, cleanup workspace

    Usage::

        driver = LoopDriver(harness, runtime, manifest, lock_manager)
        outcome = driver.run()
        # outcome is a LoopOutcome
    """

    def __init__(
        self,
        harness: LoopHarness | None = None,
        runtime: LoopRuntime | None = None,
        manifest: LoopManifest | None = None,
        profile: LoopProfile | None = None,
        state: LoopState | None = None,
        lock_manager: LoopLockManager | None = None,
        root_dir: Path | None = None,
    ) -> None:
        self._harness = harness or LoopHarnessImpl()
        self._runtime = runtime
        self._manifest = manifest
        self._profile = profile
        self._state = state
        self._lock_manager = lock_manager
        self._root_dir = root_dir

        # Internal tracking
        self._consecutive_fails = 0
        self._consecutive_successes = 0
        self._iteration_records: list[IterationRecord] = []
        self._workspace_handle: WorkspaceHandle | None = None
        self._current_maker_output: str = ""

    @property
    def harness(self) -> LoopHarness:
        return self._harness

    @property
    def runtime(self) -> LoopRuntime:
        if self._runtime is None:
            raise RuntimeError(
                "LoopRuntime not set. Provide via constructor or call setup()."
            )
        return self._runtime

    @property
    def manifest(self) -> LoopManifest:
        if self._manifest is None:
            raise RuntimeError(
                "LoopManifest not set. Provide via constructor or call setup()."
            )
        return self._manifest

    @property
    def state(self) -> LoopState:
        if self._state is None:
            raise RuntimeError(
                "LoopState not set. Provide via constructor or call setup()."
            )
        return self._state

    @property
    def profile(self) -> LoopProfile:
        if self._profile is None:
            raise RuntimeError(
                "LoopProfile not set. Provide via constructor or call setup()."
            )
        return self._profile

    @property
    def workspace_path(self) -> Path | None:
        if self._workspace_handle:
            return self._workspace_handle.workspace_path
        return None

    # ------------------------------------------------------------------
    # Setup helpers
    # ------------------------------------------------------------------

    def setup(
        self,
        runtime: LoopRuntime,
        manifest: LoopManifest,
        profile: LoopProfile,
        state: LoopState,
        lock_manager: LoopLockManager | None = None,
    ) -> None:
        """Bind runtime context for execution."""
        self._runtime = runtime
        self._manifest = manifest
        self._profile = profile
        self._state = state
        self._lock_manager = lock_manager

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> LoopOutcome:
        """Execute the main loop.

        Returns a LoopOutcome indicating how the loop terminated.
        """
        runtime = self.runtime
        manifest = self.manifest
        state = self.state
        profile = self.profile

        # Ensure state_path is set
        if not state.custom_state.get("state_path"):
            state_dir = (self._root_dir or Path(".")).resolve()
            state_path = state_dir / ".loop-state" / f"{profile.profile_id}.json"
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state.custom_state["state_path"] = str(state_path)

        # Acquire lock if lock_manager provided
        lock_held = False
        if self._lock_manager and not self._lock_manager.acquired:
            self._lock_manager.acquire(holder=f"loop-driver-{profile.profile_id}")
            lock_held = True

        try:
            # Isolate workspace via public harness interface
            self._workspace_handle = self._harness.isolate_workspace(profile.profile_id, profile)
            ws_path = self._workspace_handle.workspace_path
            runtime.workspace_path = ws_path

            # Clear pause signal (ready to run)
            runtime.clear_pause()

            # Set state to running
            state.status = LoopStatus.RUNNING
            self._persist_state(state)
            logger.info(
                "Loop started: profile=%s, mode=%s",
                profile.profile_id,
                manifest.loop_specific.execution_mode.value,
            )

            outcome = None
            try:
                outcome = self._main_loop(runtime, manifest, state, profile)
            except Exception as exc:
                logger.error(
                    "Loop error: profile=%s, error=%s, iterations=%d",
                    profile.profile_id,
                    exc,
                    state.current_iteration,
                )
                raise
            finally:
                # Persist final state
                self._persist_state(state)
                logger.info(
                    "Loop finished: profile=%s, outcome=%s, iterations=%d",
                    profile.profile_id,
                    outcome.value if outcome else state.status.value,
                    state.current_iteration,
                )
                # Cleanup workspace via handle
                if self._workspace_handle:
                    try:
                        self._workspace_handle.cleanup()
                    except Exception as exc:
                        logger.warning("Workspace cleanup failed: %s", exc)

            return outcome

        finally:
            # Release lock
            if lock_held and self._lock_manager:
                self._lock_manager.release()

    def _main_loop(
        self,
        runtime: LoopRuntime,
        manifest: LoopManifest,
        state: LoopState,
        profile: LoopProfile,
    ) -> LoopOutcome:
        """Inner loop: check signals, iterate, evaluate, act."""
        while True:
            # Check lifecycle signals (cancel/pause)
            signal_outcome = self._check_signals(runtime, state)
            if signal_outcome:
                return signal_outcome

            # Check budget stop conditions
            budget_outcome = self._check_budget(manifest, state)
            if budget_outcome:
                return budget_outcome

            # Execute one iteration
            action = self._one_iteration(runtime, manifest, state, profile)

            # Handle iteration result
            iteration_outcome = self._handle_action(
                action, manifest, state, runtime, profile,
            )
            if iteration_outcome:
                return iteration_outcome

        # Should not reach here
        state.status = LoopStatus.FAILED
        return LoopOutcome.FAILURE

    def _check_signals(
        self, runtime: LoopRuntime, state: LoopState,
    ) -> LoopOutcome | None:
        """Check cancel/pause signals. Returns outcome if terminal, None to continue."""
        if runtime.is_cancelled:
            state.status = LoopStatus.CANCELLED
            return LoopOutcome.CANCELLED

        if runtime.is_paused:
            state.status = LoopStatus.PAUSED
            self._persist_state(state)
            # 带超时的等待，防止暂停后永不恢复导致永久阻塞
            while runtime.is_paused and not runtime.is_cancelled:
                runtime.pause_event.wait(timeout=1.0)
            runtime.clear_pause()
            state.status = LoopStatus.RUNNING
            self._persist_state(state)
            if runtime.is_cancelled:
                state.status = LoopStatus.CANCELLED
                return LoopOutcome.CANCELLED

        return None

    def _check_budget(
        self, manifest: LoopManifest, state: LoopState,
    ) -> LoopOutcome | None:
        """Check budget/iteration limits. Returns outcome if exhausted, None to continue."""
        stop_conditions = manifest.loop_specific.stop_conditions
        budget_metrics = self._budget_metrics(state)

        for cond in stop_conditions.budget:
            if _eval_predicate(cond.predicate, budget_metrics):
                state.status = LoopStatus.FAILED
                state.last_error = f"Budget exhausted: {cond.identifier}"
                return LoopOutcome.BUDGET_EXHAUSTED

        max_iter = budget_metrics.get("max_iterations", 100)
        if state.current_iteration >= max_iter:
            state.status = LoopStatus.FAILED
            state.last_error = f"Max iterations reached ({max_iter})"
            return LoopOutcome.MAX_ITERATIONS_REACHED

        return None

    def _handle_action(
        self,
        action: LoopAction,
        manifest: LoopManifest,
        state: LoopState,
        runtime: LoopRuntime,
        profile: LoopProfile,
    ) -> LoopOutcome | None:
        """Handle iteration action. Returns outcome if terminal, None to continue."""
        if action == LoopAction.CONTINUE:
            return None
        if action == LoopAction.SUCCESS:
            state.status = LoopStatus.COMPLETED
            return LoopOutcome.SUCCESS
        if action == LoopAction.FAILURE:
            state.status = LoopStatus.FAILED
            return LoopOutcome.FAILURE
        if action == LoopAction.ESCALATE:
            self._harness.escalate(
                manifest.id,
                reason="Loop evaluation triggered escalation",
                state=state,
                profile=profile,
            )
            return LoopOutcome.ESCALATED
        if action == LoopAction.PAUSE:
            runtime.request_pause()
            return None
        return None

    # ------------------------------------------------------------------
    # One iteration
    # ------------------------------------------------------------------

    def _one_iteration(
        self,
        runtime: LoopRuntime,
        manifest: LoopManifest,
        state: LoopState,
        profile: LoopProfile,
    ) -> LoopAction:
        """Execute a single Maker -> Checker -> Convergence -> Action cycle.

        Returns the LoopAction to take based on the verdict.
        """
        loop_specific = manifest.loop_specific

        # Begin iteration
        self._begin_iteration(state)

        # Maker execute
        start_time = time.monotonic()
        from harness_ai_kit.domain.loop_maker import MakerExecutor

        ws_path = self.workspace_path or Path(".")
        maker = MakerExecutor(
            loop_entry=loop_specific.maker.entry,
        )
        loop_md_path = ws_path / loop_specific.maker.entry
        prompt = ""
        if loop_md_path.exists():
            prompt = maker.assemble_prompt(loop_md_path)
        maker_result = maker.execute(ws_path, prompt)
        maker_duration = time.monotonic() - start_time

        self._current_maker_output = maker_result.output

        # Checker spawn
        from harness_ai_kit.domain.loop_harness import CheckerContext

        checker_ctx = CheckerContext(
            loop_def=manifest,
            maker_output=self._current_maker_output,
            iteration=state.current_iteration,
            current_state=state,
            workspace_path=self.workspace_path,
        )
        verdict = self._harness.spawn_checker(manifest, checker_ctx)

        # Convergence detect
        convergence = self._harness.detect_convergence(state)

        # Record iteration
        self._record_iteration(
            state, verdict, convergence, maker_duration, maker_result.output
        )

        # Budget record (tokens, duration)
        self._budget_record(state, maker_duration)

        # Persist state
        self._persist_state(state)

        # Log iteration result
        logger.debug(
            "Iteration %d: verdict=%s, score=%.2f, convergence=%s",
            state.current_iteration,
            verdict.verdict.value if verdict else "none",
            verdict.score if verdict else 0.0,
            convergence.status.value if convergence else "unknown",
        )

        # Evaluate action
        return self._evaluate_action(state, verdict, convergence, manifest)

    def _begin_iteration(self, state: LoopState) -> None:
        """Mark the start of a new iteration."""
        state.current_iteration += 1

    def _record_iteration(
        self,
        state: LoopState,
        verdict,
        convergence: ConvergenceResult,
        duration: float,
        maker_output: str = "",
    ) -> None:
        """Record iteration results in state and update counters."""
        from harness_ai_kit.domain.loop_state import ConvergenceMetricEntry

        entry = ConvergenceMetricEntry(
            iteration=state.current_iteration,
            timestamp=_now_iso(),
            primary_metric=verdict.score,
            verdict=verdict.verdict,
        )
        state.convergence_metrics.append(entry)

        # Update consecutive counters
        if verdict.verdict == Verdict.PASS:
            self._consecutive_successes += 1
            self._consecutive_fails = 0
        else:
            self._consecutive_fails += 1
            self._consecutive_successes = 0

        # Store iteration detail
        state.iteration_details[str(state.current_iteration)] = IterationDetail(
            maker_summary=maker_output[:200] if maker_output else "",
            checker_verdict={
                "verdict": verdict.verdict.value,
                "score": verdict.score,
            },
            duration_seconds=duration,
        )

        # Store iteration record for driver-internal use
        self._iteration_records.append(
            IterationRecord(
                iteration=state.current_iteration,
                verdict=verdict.verdict,
                score=verdict.score,
                duration_seconds=duration,
                convergence_status=convergence.status,
                maker_output=maker_output,
            )
        )

    def _budget_record(self, state: LoopState, duration: float) -> None:
        """Record budget consumption (duration, estimated tokens)."""
        accumulated = state.custom_state.get("total_duration", 0.0)
        state.custom_state["total_duration"] = accumulated + duration

        # Rough token estimate based on maker output length
        if self._current_maker_output:
            token_estimate = len(self._current_maker_output) // 4
            accumulated_tokens = state.custom_state.get("total_tokens", 0)
            state.custom_state["total_tokens"] = accumulated_tokens + token_estimate

    # ------------------------------------------------------------------
    # Action evaluation
    # ------------------------------------------------------------------

    def _evaluate_action(
        self,
        state: LoopState,
        verdict,
        convergence: ConvergenceResult,
        manifest: LoopManifest,
    ) -> LoopAction:
        """Decision matrix: verdict + convergence + stop_conditions -> LoopAction.

        Priority order:
        1. Success check (stop_conditions.success predicates met)
        2. Failure check (consecutive fails >= configured threshold)
        3. Convergence check (divergence detected)
        4. Budget check (budget stop conditions met)

        Anti-flapping: single fail -> CONTINUE (give maker another chance).
        """
        stop_conditions = manifest.loop_specific.stop_conditions

        # 1. Success check
        success_metrics = self._success_metrics(state, verdict)
        for cond in stop_conditions.success:
            if _eval_predicate(cond.predicate, success_metrics):
                return LoopAction.SUCCESS

        # 2. Failure check — evaluate failure predicates FIRST
        failure_metrics = self._failure_metrics(state, verdict)
        for cond in stop_conditions.failure:
            if _eval_predicate(cond.predicate, failure_metrics):
                return LoopAction.FAILURE

        # 2b. Consecutive fails (secondary fallback)
        max_fails = self._get_max_consecutive_fails(manifest)
        if self._consecutive_fails >= max_fails:
            return LoopAction.FAILURE
        # Anti-flapping: single fail -> CONTINUE
        if self._consecutive_fails > 0:
            return LoopAction.CONTINUE

        # 3. Convergence check
        if convergence.status == ConvergenceStatus.DIVERGING:
            if convergence.divergence_rounds >= 2:
                return LoopAction.ESCALATE

        # 4. Budget check
        budget_metrics = self._budget_metrics(state)
        for cond in stop_conditions.budget:
            if _eval_predicate(cond.predicate, budget_metrics):
                return LoopAction.FAILURE

        # Default: continue
        return LoopAction.CONTINUE

    # ------------------------------------------------------------------
    # Metric builders
    # ------------------------------------------------------------------

    def _success_metrics(self, state: LoopState, verdict) -> dict[str, Any]:
        """Build metrics dict for success predicate evaluation."""
        return {
            "tests_pass_rate": state.custom_state.get("tests_pass_rate", 1.0),
            "error_count": state.custom_state.get("error_count", 0),
            "coverage_pct": state.custom_state.get("coverage_pct", 0.0),
            "checker_score": verdict.score,
            "iteration_count": state.current_iteration,
            "token_usage": state.custom_state.get("total_tokens", 0),
            "duration_seconds": state.custom_state.get("total_duration", 0.0),
        }

    def _budget_metrics(self, state: LoopState) -> dict[str, Any]:
        """Build metrics dict for budget predicate evaluation."""
        return {
            "iteration_count": state.current_iteration,
            "token_usage": state.custom_state.get("total_tokens", 0),
            "duration_seconds": state.custom_state.get("total_duration", 0.0),
            "error_count": state.custom_state.get("error_count", 0),
            "max_iterations": state.custom_state.get("max_iterations", 100),
        }

    def _failure_metrics(self, state: LoopState, verdict) -> dict[str, Any]:
        """Build metrics dict for failure predicate evaluation.

        Includes error count, checker score, and error-related metrics
        from stop_conditions.failure predicates (e.g. 'error_count >= 3',
        'checker_score < 0.3').
        """
        return {
            "error_count": state.custom_state.get("error_count", 0),
            "checker_score": verdict.score,
            "iteration_count": state.current_iteration,
            "tests_pass_rate": state.custom_state.get("tests_pass_rate", 1.0),
        }

    def _get_max_consecutive_fails(self, manifest: LoopManifest) -> int:
        """Extract max consecutive failures from manifest stop conditions.

        Looks for predicates like 'error_count >= N' in failure conditions.
        Falls back to 3 if no explicit threshold is found.
        """
        pattern = re.compile(r"error_count\s*>=\s*(\d+)")
        for cond in manifest.loop_specific.stop_conditions.failure:
            m = pattern.search(cond.predicate)
            if m:
                return int(m.group(1))

        # Check for iteration_count based conditions as fallback
        pattern2 = re.compile(r"iteration_count\s*>=\s*(\d+)")
        for cond in manifest.loop_specific.stop_conditions.failure:
            m = pattern2.search(cond.predicate)
            if m:
                return int(m.group(1))

        # Default: allow 3 consecutive failures before giving up
        return 3

    # ------------------------------------------------------------------
    # State persistence
    # ------------------------------------------------------------------

    def _persist_state(self, state: LoopState) -> None:
        """Persist state to file atomically."""
        state_path = state.custom_state.get("state_path", "")
        if state_path:
            try:
                save_state(state, Path(state_path))
            except Exception as exc:
                logger.warning("State persist failed: %s", exc)
