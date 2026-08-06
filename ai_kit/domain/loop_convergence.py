"""Convergence detector: analyzes loop metrics to detect convergence patterns.

Phase 1: Returns UNKNOWN trend with CONTINUE recommendation (non-blocking).
Phase 2: Will implement full stagnation/divergence/oscillation detection.
"""
from __future__ import annotations

import logging
from typing import Any

from ai_kit.domain.loop_contract import ConvergenceResult, ConvergenceStatus
from ai_kit.domain.loop_state import LoopState

logger = logging.getLogger(__name__)


class ConvergenceDetector:
    """Detects convergence, stagnation, divergence, or oscillation.

    Phase 1 implementation: Always returns UNKNOWN trend with CONTINUE
    recommendation. This ensures the detector does not block the loop
    while the full algorithm is being developed.
    """

    def __init__(
        self,
        *,
        stagnation_rounds: int = 3,
        divergence_rounds: int = 2,
        min_improvement: float = 0.02,
        oscillation_window: int = 4,
    ) -> None:
        self.stagnation_rounds = stagnation_rounds
        self.divergence_rounds = divergence_rounds
        self.min_improvement = min_improvement
        self.oscillation_window = oscillation_window

    def detect(self, state: LoopState) -> ConvergenceResult:
        """Analyze convergence metrics and return a ConvergenceResult.

        Detects convergence, stagnation, divergence, and oscillation
        based on primary_metric trend and verdict patterns over recent
        iterations.
        """
        metrics = state.convergence_metrics

        # Need at least 2 data points for meaningful analysis
        if len(metrics) < 2:
            return ConvergenceResult(
                status=ConvergenceStatus.UNKNOWN,
                primary_metric_trend="unknown",
                stagnation_rounds=0,
                divergence_rounds=0,
                should_escalate=False,
            )

        # Run all detectors
        is_stagnating = self._detect_stagnation(metrics)
        is_diverging = self._detect_divergence(metrics)
        is_oscillating = self._detect_oscillation(metrics)

        # Determine trend from recent metrics
        trend = self._compute_trend(metrics)

        # Priority: divergence > oscillation > stagnation > converging
        if is_diverging:
            return ConvergenceResult(
                status=ConvergenceStatus.DIVERGING,
                primary_metric_trend=trend,
                stagnation_rounds=0,
                divergence_rounds=self.divergence_rounds,
                should_escalate=True,
            )

        if is_oscillating:
            return ConvergenceResult(
                status=ConvergenceStatus.STAGNATING,
                primary_metric_trend=trend,
                stagnation_rounds=0,
                divergence_rounds=0,
                should_escalate=True,
            )

        if is_stagnating:
            return ConvergenceResult(
                status=ConvergenceStatus.STAGNATING,
                primary_metric_trend=trend,
                stagnation_rounds=self.stagnation_rounds,
                divergence_rounds=0,
                should_escalate=False,
            )

        return ConvergenceResult(
            status=ConvergenceStatus.CONVERGING,
            primary_metric_trend=trend,
            stagnation_rounds=0,
            divergence_rounds=0,
            should_escalate=False,
        )

    def _compute_trend(self, metrics: list[Any]) -> str:
        """Compute overall trend from recent metrics."""
        if len(metrics) < 2:
            return "unknown"
        recent = metrics[-3:]  # Last 3 rounds
        first = recent[0].primary_metric
        last = recent[-1].primary_metric
        diff = last - first
        if abs(diff) < self.min_improvement:
            return "stable"
        return "improving" if diff > 0 else "declining"

    def _detect_stagnation(self, metrics: list[Any]) -> bool:
        """Check if primary_metric changes < min_improvement for N consecutive rounds."""
        if len(metrics) < self.stagnation_rounds + 1:
            return False

        recent = metrics[-(self.stagnation_rounds + 1):]
        for i in range(1, len(recent)):
            diff = abs(recent[i].primary_metric - recent[i - 1].primary_metric)
            if diff >= self.min_improvement:
                return False
        return True

    def _detect_divergence(self, metrics: list[Any]) -> bool:
        """Check if primary_metric decreasing for M consecutive rounds."""
        if len(metrics) < self.divergence_rounds + 1:
            return False

        recent = metrics[-(self.divergence_rounds + 1):]
        for i in range(1, len(recent)):
            if recent[i].primary_metric >= recent[i - 1].primary_metric:
                return False
        return True

    def _detect_oscillation(self, metrics: list[Any]) -> bool:
        """Check if verdicts alternating pass/fail for last N rounds."""
        if len(metrics) < self.oscillation_window:
            return False

        recent = metrics[-self.oscillation_window:]
        verdicts = [m.verdict for m in recent if m.verdict is not None]
        if len(verdicts) < 2:
            return False

        # Check for alternation pattern
        alternating = True
        for i in range(1, len(verdicts)):
            if verdicts[i] == verdicts[i - 1]:
                alternating = False
                break
        return alternating
