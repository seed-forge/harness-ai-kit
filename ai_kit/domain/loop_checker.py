"""Checker spawner: invokes ccw cli --mode analysis to validate Maker output.

Implements the Checker side of the Maker-Checker loop. The Checker runs
in a separate subprocess to ensure context isolation from the Maker (EP-003).
"""
from __future__ import annotations

import json
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_kit.domain.loop_contract import (
    ANTI_INJECTION_PREAMBLE,
    CheckerVerdict,
    ConvergenceSignal,
    EvidenceItem,
    Rubric,
    RubricResult,
    RubricSeverity,
    Verdict,
    wrap_maker_output,
)

logger = logging.getLogger(__name__)

DEFAULT_CHECKER_TIMEOUT = 300  # 5 minutes


class CheckerSpawner:
    """Spawns an independent Checker via ccw cli --mode analysis.

    Sub-agent mode: MUST use independent agent instance + context isolation.
    Self-check mode: MAY execute lightweight verification inline.
    """

    def __init__(
        self,
        *,
        check_entry: str = "CHECK.md",
        timeout: int = DEFAULT_CHECKER_TIMEOUT,
        ccw_tool: str = "gemini",
        pass_threshold: float = 0.8,
    ) -> None:
        self.check_entry = check_entry
        self.timeout = timeout
        self.ccw_tool = ccw_tool
        self.pass_threshold = pass_threshold

    def assemble_prompt(
        self,
        check_md_path: Path,
        maker_output: str,
        rubric_dimensions: list[dict[str, Any]] | None = None,
    ) -> str:
        """Assemble the Checker prompt.

        Combines CHECK.md + sanitized_maker_output + rubric into a single
        prompt for the Checker agent.
        """
        check_content = check_md_path.read_text(encoding="utf-8") if check_md_path.exists() else ""

        # Wrap maker output with boundary markers (EP-003)
        wrapped_maker = wrap_maker_output(maker_output)

        parts = [
            ANTI_INJECTION_PREAMBLE,
            "",
            "--- CHECK RUBRIC ---",
            check_content,
            "--- END CHECK RUBRIC ---",
            "",
            wrapped_maker,
        ]

        if rubric_dimensions:
            parts.append("")
            parts.append("--- RUBRIC DIMENSIONS ---")
            for dim in rubric_dimensions:
                parts.append(
                    f"- {dim.get('name', 'unnamed')}: {dim.get('description', '')} "
                    f"(weight={dim.get('weight', 0)}, severity={dim.get('severity', 'should_pass')})"
                )
            parts.append("--- END RUBRIC DIMENSIONS ---")

        return "\n".join(parts)

    def spawn_and_evaluate(
        self,
        workspace_path: Path,
        prompt: str,
        iteration: int,
    ) -> CheckerVerdict:
        """Run ccw cli --mode analysis and parse the Verdict JSON.

        The Checker MUST return a JSON verdict object. If parsing fails,
        a default FAIL verdict is returned.
        """
        import time

        start = time.monotonic()

        cmd = [
            "ccw", "cli",
            "-p", prompt,
            "--tool", self.ccw_tool,
            "--mode", "analysis",
            "--cd", str(workspace_path),
        ]

        logger.info("Checker spawning: %s", " ".join(cmd[:6]))

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
            logger.warning("Checker timed out after %ds", self.timeout)
            return CheckerVerdict(
                verdict=Verdict.RETRY,
                score=0.0,
                iteration=iteration,
                timestamp=datetime.now(timezone.utc).isoformat(),
                evidence=[EvidenceItem(
                    type="observation",
                    description="Checker timed out",
                    severity="medium",
                )],
                recommendation="Retry with shorter scope",
            )
        except Exception as exc:
            elapsed = time.monotonic() - start
            logger.warning("Checker subprocess error: %s", exc)
            return CheckerVerdict(
                verdict=Verdict.FAIL,
                score=0.0,
                iteration=iteration,
                timestamp=datetime.now(timezone.utc).isoformat(),
                evidence=[EvidenceItem(
                    type="observation",
                    description=f"Checker subprocess error: {exc}",
                    severity="high",
                )],
                recommendation="Investigate checker infrastructure",
            )

        elapsed = time.monotonic() - start

        # Parse verdict from output
        verdict = self._parse_verdict(
            output=result.stdout or "",
            stderr=result.stderr or "",
            iteration=iteration,
        )

        return verdict

    def evaluate_inline(
        self,
        maker_output: str,
        iteration: int,
        rubric: Rubric | None = None,
    ) -> CheckerVerdict:
        """Lightweight inline evaluation for self-check mode.

        Phase 1: raises NotImplementedError — self-check mode requires
        a proper LLM-based evaluation that is not yet implemented.
        Phase 2 will implement a real inline evaluator.
        """
        raise NotImplementedError(
            "Self-check mode (evaluate_inline) is not yet implemented. "
            "Use execution_mode='sub-agent' until Phase 2. "
            f"Iteration {iteration}: maker output length={len(maker_output)}"
        )

    def _parse_verdict(
        self,
        output: str,
        stderr: str,
        iteration: int,
    ) -> CheckerVerdict:
        """Parse Checker output into a CheckerVerdict.

        Attempts to find a JSON object in the output. Falls back to a
        default verdict if parsing fails.
        """
        # Try to extract JSON from output
        verdict_data = self._extract_json(output)
        if verdict_data is None:
            # Also try stderr
            verdict_data = self._extract_json(stderr)

        if verdict_data is None:
            logger.warning("Checker did not return parseable JSON output")
            return CheckerVerdict(
                verdict=Verdict.RETRY,
                score=0.5,
                iteration=iteration,
                timestamp=datetime.now(timezone.utc).isoformat(),
                evidence=[EvidenceItem(
                    type="observation",
                    description="Checker output not parseable as JSON",
                    severity="low",
                )],
                recommendation="Retry checker",
            )

        return self._build_verdict_from_data(verdict_data, iteration)

    def _extract_json(self, text: str) -> dict[str, Any] | None:
        """Try to extract a JSON dict from text."""
        # Try parsing the whole text as JSON
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

        # Try to find a JSON block within the text
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                data = json.loads(text[start:end + 1])
                if isinstance(data, dict):
                    return data
            except json.JSONDecodeError:
                pass

        return None

    def _build_verdict_from_data(
        self,
        data: dict[str, Any],
        iteration: int,
    ) -> CheckerVerdict:
        """Build a CheckerVerdict from parsed JSON data."""
        score = float(data.get("score", 0.5))
        score = max(0.0, min(1.0, score))

        raw_verdict = data.get("verdict", "retry")
        try:
            verdict = Verdict(raw_verdict)
        except ValueError:
            verdict = Verdict.RETRY

        evidence_items = []
        for ev in data.get("evidence", []):
            try:
                evidence_items.append(EvidenceItem(
                    type=ev.get("type", "custom"),
                    description=ev.get("description", ""),
                    severity=ev.get("severity", "info"),
                    file_ref=ev.get("file_ref"),
                    line_ref=ev.get("line_ref"),
                ))
            except (ValueError, TypeError):
                pass

        rubric_results = []
        for rr in data.get("rubric_results", []):
            try:
                sev = RubricSeverity(rr.get("severity", "should_pass"))
                rubric_results.append(RubricResult(
                    dimension=rr.get("dimension", ""),
                    severity=sev,
                    score=float(rr.get("score", 0.0)),
                    passed=bool(rr.get("passed", False)),
                    evidence_refs=rr.get("evidence_refs", []),
                ))
            except (ValueError, TypeError):
                pass

        convergence_signal = None
        sig = data.get("convergence_signal")
        if sig:
            try:
                convergence_signal = ConvergenceSignal(
                    trend=sig.get("trend", "indeterminate"),
                    confidence=float(sig.get("confidence", 0.0)),
                    key_factors=sig.get("key_factors", []),
                    previous_score=sig.get("previous_score"),
                )
            except (ValueError, TypeError):
                pass

        return CheckerVerdict(
            verdict=verdict,
            score=score,
            iteration=iteration,
            timestamp=datetime.now(timezone.utc).isoformat(),
            evidence=evidence_items,
            recommendation=data.get("recommendation", ""),
            convergence_signal=convergence_signal,
            rubric_results=rubric_results,
        )
