"""Loop enums and supporting dataclasses."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ai_kit.domain.loop_contract import (
    ConvergenceStatus,
    Verdict,
)



# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class LoopOutcome(str, Enum):
    """Final outcome of a completed loop run."""

    SUCCESS = "success"
    FAILURE = "failure"
    CANCELLED = "cancelled"
    ESCALATED = "escalated"
    BUDGET_EXHAUSTED = "budget_exhausted"
    MAX_ITERATIONS_REACHED = "max_iterations_reached"


class LoopAction(str, Enum):
    """Action to take after one iteration."""

    CONTINUE = "continue"
    SUCCESS = "success"
    FAILURE = "failure"
    ESCALATE = "escalate"
    PAUSE = "pause"


# ---------------------------------------------------------------------------
# Supporting types
# ---------------------------------------------------------------------------


@dataclass
class IterationRecord:
    """Record of a single iteration's outcome."""

    iteration: int
    verdict: Verdict
    score: float
    duration_seconds: float
    convergence_status: ConvergenceStatus
    files_changed: list[str] = field(default_factory=list)
    maker_output: str = ""

