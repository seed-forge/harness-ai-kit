"""Escalation channel: routes loop failures to appropriate handlers.

Phase 1: Writes escalation artifacts to disk + emits log entries.
Phase 2: Will implement notification/issue/webhook delivery.

Key invariant: escalate() NEVER raises exceptions.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from harness_ai_kit.domain.loop_state import LoopState

logger = logging.getLogger(__name__)


class EscalationChannel:
    """Routes escalation events to appropriate channels.

    Phase 1 implementation: Persists escalation artifacts to
    .workflow/loops/{profile_id}/escalations/ and emits log entries.

    Invariant: All methods NEVER raise exceptions.
    """

    def __init__(
        self,
        *,
        escalation_dir: Path | None = None,
    ) -> None:
        self.escalation_dir = escalation_dir

    def escalate(
        self,
        loop_id: str,
        reason: str,
        state: LoopState,
        profile_id: str = "",
        **extra_context: Any,
    ) -> None:
        """Trigger escalation.

        Writes an escalation artifact and emits a log entry.
        This method NEVER raises exceptions.
        """
        try:
            self._write_escalation_artifact(
                loop_id=loop_id,
                reason=reason,
                state=state,
                profile_id=profile_id,
                extra_context=extra_context,
            )
            logger.warning(
                "Escalation triggered for loop=%s reason=%s",
                loop_id, reason,
            )
        except Exception as exc:
            # escalate must never raise - log and swallow
            logger.error("Escalation failed silently: %s", exc)

    def route(
        self,
        reason: str,
        context: dict[str, Any],
        loop_id: str = "",
        profile_id: str = "",
    ) -> None:
        """Route an escalation to the appropriate channel.

        Phase 1: writes to disk. Phase 2: notification/issue/webhook.
        """
        try:
            state_snapshot = context.get("state")
            state_obj = None
            if isinstance(state_snapshot, LoopState):
                state_obj = state_snapshot

            self._write_escalation_artifact(
                loop_id=loop_id,
                reason=reason,
                state=state_obj,
                profile_id=profile_id,
                extra_context=context,
            )
        except Exception as exc:
            logger.error("Escalation routing failed: %s", exc)

    def _write_escalation_artifact(
        self,
        *,
        loop_id: str,
        reason: str,
        state: LoopState | None,
        profile_id: str,
        extra_context: dict[str, Any],
    ) -> None:
        """Persist an escalation artifact to disk."""
        esc_dir = self._get_escalation_dir(profile_id)
        esc_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).isoformat()
        filename = f"{loop_id}_{timestamp.replace(':', '-')}.json"
        artifact_path = esc_dir / filename

        # Build state snapshot
        state_data = {}
        if state:
            try:
                state_data = state.model_dump(mode="json")
            except Exception:
                state_data = {"error": "Could not serialize state"}

        artifact = {
            "loop_id": loop_id,
            "profile_id": profile_id,
            "reason": reason,
            "timestamp": timestamp,
            "iteration": state.current_iteration if state else 0,
            "state": state_data,
            "extra_context": _safe_serialize(extra_context),
        }

        artifact_path.write_text(
            json.dumps(artifact, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

    def _get_escalation_dir(self, profile_id: str) -> Path:
        """Get or create the escalation directory."""
        if self.escalation_dir:
            return self.escalation_dir / profile_id / "escalations"

        # Default: .workflow/loops/{profile_id}/escalations/
        base = Path.cwd() / ".workflow" / "loops"
        return base / profile_id / "escalations"


def _safe_serialize(obj: dict[str, Any]) -> dict[str, Any]:
    """Create a JSON-safe copy of a dict."""
    result = {}
    for key, value in obj.items():
        try:
            json.dumps(value, default=str)
            result[key] = value
        except (TypeError, ValueError):
            result[key] = f"<unserializable: {type(value).__name__}>"
    return result
