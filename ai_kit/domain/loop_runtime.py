"""Loop runtime data model.

Combines LoopProfile + LoopManifest + LoopState into a single runtime
context object used by LoopHarnessImpl during loop execution.
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_kit.domain.loop_harness import LoopProfile
from ai_kit.domain.loop_manifest import LoopManifest
from ai_kit.domain.loop_state import LoopState

logger = logging.getLogger(__name__)


@dataclass(frozen=False)
class LoopRuntime:
    """Runtime context for a single loop execution session.

    Combines static configuration (profile + manifest) with mutable
    execution state and lifecycle signal events.
    """

    profile: LoopProfile
    manifest: LoopManifest
    state: LoopState

    # Lifecycle signal events
    cancel_event: threading.Event = field(default_factory=threading.Event)
    pause_event: threading.Event = field(default_factory=threading.Event)

    # Runtime tracking
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    workspace_path: Path | None = None
    current_iteration_output: str = ""

    @property
    def is_cancelled(self) -> bool:
        return self.cancel_event.is_set()

    @property
    def is_paused(self) -> bool:
        return self.pause_event.is_set()

    def request_cancel(self) -> None:
        """Signal the loop to cancel."""
        self.cancel_event.set()
        logger.info("Loop runtime cancel requested for %s", self.profile.profile_id)

    def request_pause(self) -> None:
        """Signal the loop to pause at end of current iteration."""
        self.pause_event.set()
        logger.info("Loop runtime pause requested for %s", self.profile.profile_id)

    def clear_pause(self) -> None:
        """Clear the pause signal (used when resuming)."""
        self.pause_event.clear()

    @classmethod
    def from_manifest_and_state(
        cls,
        manifest: LoopManifest,
        state: LoopState,
        profile: LoopProfile | None = None,
    ) -> "LoopRuntime":
        """Construct a LoopRuntime from manifest + state.

        If no profile is provided, a minimal one is derived from the manifest.
        """
        if profile is None:
            profile = LoopProfile(
                profile_id=manifest.id,
                loop_id=manifest.id,
                loop_version=manifest.version,
                execution_mode=manifest.loop_specific.execution_mode,
                stop_params={},
                workspace_isolation="git_worktree",
            )
        return cls(profile=profile, manifest=manifest, state=state)
