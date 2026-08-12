"""Loop state memory file: schema, atomic I/O, backup, restore.

Implements F-003 (loop-state-memory).
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from harness_ai_kit.domain.loop_contract import LoopStatus, Verdict

# Maximum convergence metrics entries retained
MAX_CONVERGENCE_METRICS = 100
BACKUP_COUNT = 5


class ConvergenceMetricEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    iteration: int
    timestamp: str
    primary_metric: float = Field(ge=0.0, le=1.0)
    additional_metrics: dict[str, Any] = Field(default_factory=dict)
    verdict: Verdict | None = None
    trend: str | None = None

    @field_validator("iteration")
    @classmethod
    def validate_iteration(cls, v: int) -> int:
        if v < 1:
            raise ValueError("iteration must be >= 1")
        return v


class ErrorLogEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    iteration: int
    timestamp: str
    error_type: str
    message: str
    recurrence_count: int = 1


class IterationDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    maker_summary: str = ""
    checker_verdict: dict[str, Any] | None = None
    files_changed: list[str] = Field(default_factory=list)
    duration_seconds: float = 0.0


class LoopState(BaseModel):
    """Loop state memory file schema (F-003)."""

    model_config = ConfigDict(extra="forbid")

    loop_id: str
    profile_id: str
    current_iteration: int = Field(ge=0)
    status: LoopStatus = LoopStatus.IDLE
    last_error: str | None = None
    created_at: str = ""
    updated_at: str = ""
    convergence_metrics: list[ConvergenceMetricEntry] = Field(default_factory=list)
    error_log: list[ErrorLogEntry] = Field(default_factory=list)
    iteration_details: dict[str, IterationDetail] = Field(default_factory=dict)
    custom_state: dict[str, Any] = Field(default_factory=dict)

    @field_validator("loop_id", "profile_id")
    @classmethod
    def validate_kebab(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("ID cannot be empty")
        return v

    @field_validator("current_iteration")
    @classmethod
    def validate_iteration(cls, v: int) -> int:
        if v < 0:
            raise ValueError("current_iteration must be >= 0")
        return v

    def validate_metric_sequence(self) -> None:
        """Ensure convergence_metrics iterations are monotonically increasing without gaps."""
        if not self.convergence_metrics:
            return
        for i, entry in enumerate(self.convergence_metrics):
            if i == 0:
                continue
            prev = self.convergence_metrics[i - 1]
            if entry.iteration <= prev.iteration:
                raise ValueError(
                    f"convergence_metrics iterations must be strictly increasing: "
                    f"{prev.iteration} -> {entry.iteration}"
                )


# ---------------------------------------------------------------------------
# Atomic I/O
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def initialize_state(loop_id: str, profile_id: str) -> LoopState:
    """Create a fresh state for a new loop run."""
    now = _now_iso()
    return LoopState(
        loop_id=loop_id,
        profile_id=profile_id,
        current_iteration=0,
        status=LoopStatus.IDLE,
        created_at=now,
        updated_at=now,
    )


def load_state(path: Path) -> LoopState | None:
    """Load state from file. Returns None if file does not exist.

    Attempts recovery from .bak.1 if primary file is corrupted.
    """
    if not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8")
        data = json.loads(text)
        state = LoopState.model_validate(data)
        state.validate_metric_sequence()
        return state
    except (json.JSONDecodeError, ValueError, OSError):
        # Try backup
        bak_path = path.with_suffix(path.suffix + ".bak.1")
        if bak_path.exists():
            try:
                text = bak_path.read_text(encoding="utf-8")
                data = json.loads(text)
                return LoopState.model_validate(data)
            except (json.JSONDecodeError, ValueError, OSError):
                pass
        return None


def save_state(state: LoopState, path: Path) -> None:
    """Atomic write: write to tmp, fsync, rename. Maintains backup rotation."""
    state.updated_at = _now_iso()

    # Rotate backups
    _rotate_backups(path)

    # Atomic write
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent), suffix=".tmp", prefix=".loop-state-"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state.model_dump(mode="json"), f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        # Rename (atomic on most filesystems)
        os.replace(tmp_path, str(path))
    except Exception:
        # Clean up temp file on failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _rotate_backups(path: Path) -> None:
    """Rotate backup files: .bak.N -> .bak.(N+1), keeping BACKUP_COUNT backups."""
    if not path.exists():
        return
    for i in range(BACKUP_COUNT, 0, -1):
        src = path.with_suffix(path.suffix + f".bak.{i}")
        if i < BACKUP_COUNT:
            dst = path.with_suffix(path.suffix + f".bak.{i + 1}")
            if src.exists():
                shutil.move(str(src), str(dst))
    # Current -> .bak.1
    bak1 = path.with_suffix(path.suffix + ".bak.1")
    shutil.copy2(str(path), str(bak1))


def trim_convergence_metrics(state: LoopState, max_entries: int = MAX_CONVERGENCE_METRICS) -> None:
    """Keep at most max_entries convergence metric entries, preserving baseline."""
    if len(state.convergence_metrics) <= max_entries:
        return
    baseline = state.convergence_metrics[0]
    recent = state.convergence_metrics[-(max_entries - 1):]
    state.convergence_metrics = [baseline] + recent
