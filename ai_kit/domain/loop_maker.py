"""Maker executor: invokes ccw cli --mode write to generate Maker output.

Implements the Maker side of the Maker-Checker loop by spawning an
independent subprocess via `ccw cli --mode write`.
"""
from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ai_kit.domain.loop_contract import (
    ANTI_INJECTION_PREAMBLE,
    wrap_maker_output,
)

logger = logging.getLogger(__name__)

DEFAULT_MAKER_TIMEOUT = 600  # 10 minutes


@dataclass(frozen=True)
class MakerResult:
    """Result from a Maker execution."""

    success: bool
    output: str
    exit_code: int = 0
    error_message: str = ""
    duration_seconds: float = 0.0


class MakerExecutor:
    """Executes the Maker step via ccw cli subprocess.

    The Maker reads LOOP.md and produces output that will be validated
    by the Checker in the next step.
    """

    def __init__(
        self,
        *,
        loop_entry: str = "LOOP.md",
        timeout: int = DEFAULT_MAKER_TIMEOUT,
        ccw_tool: str = "gemini",
    ) -> None:
        self.loop_entry = loop_entry
        self.timeout = timeout
        self.ccw_tool = ccw_tool

    def assemble_prompt(
        self,
        loop_md_path: Path,
        prior_context: str = "",
    ) -> str:
        """Assemble the Maker prompt from LOOP.md + anti-injection preamble + prior context.

        The anti-injection preamble wraps the maker output context to
        prevent prompt injection attacks (EP-003).
        """
        loop_content = loop_md_path.read_text(encoding="utf-8")

        parts = [ANTI_INJECTION_PREAMBLE, ""]
        if prior_context:
            parts.append("--- PRIOR CONTEXT ---")
            parts.append(prior_context)
            parts.append("--- END PRIOR CONTEXT ---")
            parts.append("")
        parts.append("--- LOOP DEFINITION ---")
        parts.append(loop_content)
        parts.append("--- END LOOP DEFINITION ---")

        return "\n".join(parts)

    def execute(
        self,
        workspace_path: Path,
        prompt: str,
    ) -> MakerResult:
        """Run ccw cli --mode write in the given workspace.

        Returns a MakerResult with sanitized output.
        """
        import time

        start = time.monotonic()

        cmd = [
            "ccw", "cli",
            "-p", prompt,
            "--tool", self.ccw_tool,
            "--mode", "write",
            "--cd", str(workspace_path),
        ]

        logger.info("Maker executing: %s", " ".join(cmd[:6]))

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                encoding="utf-8",
            )
        except subprocess.TimeoutExpired:
            elapsed = time.monotonic() - start
            return MakerResult(
                success=False,
                output="",
                exit_code=-1,
                error_message=f"Maker timed out after {self.timeout}s",
                duration_seconds=elapsed,
            )
        except Exception as exc:
            elapsed = time.monotonic() - start
            return MakerResult(
                success=False,
                output="",
                exit_code=-1,
                error_message=f"Maker subprocess error: {exc}",
                duration_seconds=elapsed,
            )

        elapsed = time.monotonic() - start

        if result.returncode != 0:
            return MakerResult(
                success=False,
                output=result.stdout or "",
                exit_code=result.returncode,
                error_message=result.stderr or "Maker returned non-zero exit code",
                duration_seconds=elapsed,
            )

        # Sanitize and wrap output
        sanitized = wrap_maker_output(result.stdout or "")

        return MakerResult(
            success=True,
            output=sanitized,
            exit_code=0,
            duration_seconds=elapsed,
        )
