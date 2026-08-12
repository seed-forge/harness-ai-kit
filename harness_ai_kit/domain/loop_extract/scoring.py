"""Loop extraction engine: value scoring, field mapping, rubric extraction.

Implements the core logic for Loop extraction (merged from session-to-loop into post-task-skill-miner):
- ValueScorer: 6-signal scoring model (REF-VALUE-SCORING)
- LoopFieldMapper: 14-field skill-to-loop mapping (REF-EXTRACTION-RUBRIC)
- RubricExtractor: 3-layer rubric dimension extraction
- StopConditionExtractor: success/failure/budget stop condition extraction
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Literal

from ._utils import (
    RISK_HIGH_KEYWORDS as _RISK_HIGH_KEYWORDS,
    RISK_MEDIUM_KEYWORDS as _RISK_MEDIUM_KEYWORDS,
    VERIFIABLE_KEYWORDS as _VERIFIABLE_KEYWORDS,
    dict_to_text as _dict_to_text,
    extract_actions_from_text as _extract_actions_from_text,
    has_verifiable_keyword as _has_verifiable_keyword,
    load_json as _load_json,
    load_plan as _load_plan,
    load_summaries as _load_summaries,
    normalize_action as _normalize_action,
)

# ---------------------------------------------------------------------------
# Value Scoring Engine (IMPL-2)
# ---------------------------------------------------------------------------

# Thresholds from REFERENCE-VALUE-SCORING.md
STRONG_THRESHOLD = 5
WEAK_THRESHOLD = 3


class Recommendation(str, Enum):
    STRONG_CANDIDATE = "strong_candidate"
    WEAK_CANDIDATE = "weak_candidate"
    NOT_RECOMMENDED = "not_recommended"


@dataclass(frozen=True)
class ValueSignal:
    """Single scoring signal."""
    name: str
    score: float  # 0 or positive integer
    evidence: str
    confidence: float  # 0.0-1.0


@dataclass(frozen=True)
class ValueScore:
    """Result of 6-signal scoring."""
    total: float
    signals: list[ValueSignal]
    recommendation: Recommendation

    @staticmethod
    def from_signals(signals: list[ValueSignal]) -> ValueScore:
        total = sum(s.score for s in signals)
        if total >= STRONG_THRESHOLD:
            rec = Recommendation.STRONG_CANDIDATE
        elif total >= WEAK_THRESHOLD:
            rec = Recommendation.WEAK_CANDIDATE
        else:
            rec = Recommendation.NOT_RECOMMENDED
        return ValueScore(total=total, signals=list(signals), recommendation=rec)


# --- Patterns for detecting situational judgment ---
_JUDGMENT_KEYWORDS = (
    "根据实际情况", "凭经验判断", "视情况而定", "酌情",
    "at discretion", "depends on context", "judge accordingly",
    "as needed", "case by case",
)

# --- Keywords indicating verifiable acceptance criteria ---


class ValueScorer:
    """Score a completed workflow session for loop extraction."""

    def score_session(self, session_dir: Path) -> ValueScore:
        """Score a completed workflow session for loop extraction.

        Reads workflow-session.json, summaries, and planning notes from
        session_dir to produce a 6-signal value score.
        """
        session_meta = _load_json(session_dir / "workflow-session.json")
        summaries = _load_summaries(session_dir / ".summaries")
        plan = _load_plan(session_dir)

        signals = [
            self._detect_repeated_patterns(summaries, session_meta),
            self._detect_clear_io(plan, summaries),
            self._detect_verifiable_criteria(summaries, plan),
            self._detect_trigger_event(plan, session_meta),
            self._detect_no_situational_judgment(summaries),
            self._detect_future_recurrence(session_meta),
        ]
        return ValueScore.from_signals(signals)

    def _detect_repeated_patterns(
        self, summaries: list[dict], session_meta: dict
    ) -> ValueSignal:
        """Signal 1 (+2): Scan summaries/session-meta for repeated operation sequences."""
        evidence_parts: list[str] = []
        repeat_count = 0

        # Strategy 1: Look for repeated skill IDs or task types in session_meta tasks
        tasks = session_meta.get("tasks", [])
        task_types: dict[str, int] = {}
        for t in tasks:
            # Normalize by extracting the action/step description
            action = t.get("action") or t.get("description") or t.get("title", "")
            key = _normalize_action(action)
            if key:
                task_types[key] = task_types.get(key, 0) + 1

        for key, count in task_types.items():
            if count >= 2:
                repeat_count += 1
                evidence_parts.append(f"'{key}' repeated {count} times")

        # Strategy 2: Scan summaries for repeated operation sequences
        action_sequences: dict[str, int] = {}
        for s in summaries:
            text = s.get("text", "")
            for action in _extract_actions_from_text(text):
                norm = _normalize_action(action)
                if norm:
                    action_sequences[norm] = action_sequences.get(norm, 0) + 1

        for seq, count in action_sequences.items():
            if count >= 2 and seq not in task_types:
                repeat_count += 1
                evidence_parts.append(f"summary action '{seq}' repeated {count} times")

        if repeat_count >= 1:
            return ValueSignal(
                name="S1_repeated_pattern",
                score=2,
                evidence="; ".join(evidence_parts) if evidence_parts else "Repeated patterns detected",
                confidence=min(1.0, 0.5 + repeat_count * 0.15),
            )
        return ValueSignal(
            name="S1_repeated_pattern",
            score=0,
            evidence="No repeated operation sequences (>=2) found",
            confidence=0.7,
        )

    def _detect_clear_io(
        self, plan: dict, summaries: list[dict]
    ) -> ValueSignal:
        """Signal 2 (+1): Check if session has clearly defined inputs and outputs."""
        has_input = False
        has_output = False
        evidence_parts: list[str] = []

        # Check plan for input/output sections
        plan_text = _dict_to_text(plan)
        if re.search(r"(input|输入|输入文件|输入参数)", plan_text, re.IGNORECASE):
            has_input = True
            evidence_parts.append("plan has input section")
        if re.search(r"(output|输出|输出文件|输出结果)", plan_text, re.IGNORECASE):
            has_output = True
            evidence_parts.append("plan has output section")

        # Check summaries for Files Modified / Content Added
        for s in summaries:
            text = s.get("text", "")
            if re.search(r"(Files Modified|files changed|修改文件)", text, re.IGNORECASE):
                has_input = True
                evidence_parts.append("summaries list modified files")
            if re.search(r"(Content Added|新增|生成文件)", text, re.IGNORECASE):
                has_output = True
                evidence_parts.append("summaries list added content")

        if has_input and has_output:
            return ValueSignal(
                name="S2_clear_io",
                score=1,
                evidence="; ".join(evidence_parts),
                confidence=0.85,
            )
        missing = []
        if not has_input:
            missing.append("input")
        if not has_output:
            missing.append("output")
        return ValueSignal(
            name="S2_clear_io",
            score=0,
            evidence=f"Missing clear {' and '.join(missing)} definition",
            confidence=0.7,
        )

    def _detect_verifiable_criteria(
        self, summaries: list[dict], plan: dict
    ) -> ValueSignal:
        """Signal 3 (+1): Check if acceptance criteria are quantifiable."""
        evidence_parts: list[str] = []

        # Check convergence.criteria in plan
        criteria = plan.get("convergence", {}).get("criteria", [])
        if criteria:
            for c in criteria:
                c_text = str(c)
                if _has_verifiable_keyword(c_text):
                    evidence_parts.append(f"criteria: {c_text[:80]}")

        # Check acceptance criteria text
        acceptance = plan.get("acceptance", "")
        if acceptance and _has_verifiable_keyword(str(acceptance)):
            evidence_parts.append(f"acceptance: {str(acceptance)[:80]}")

        # Check summaries for test/lint/verification mentions
        for s in summaries:
            text = s.get("text", "")
            for kw in _VERIFIABLE_KEYWORDS:
                if kw in text.lower():
                    evidence_parts.append(f"summary mentions '{kw}'")
                    break

        if evidence_parts:
            return ValueSignal(
                name="S3_verifiable_criteria",
                score=1,
                evidence="; ".join(evidence_parts[:3]),
                confidence=0.8,
            )
        return ValueSignal(
            name="S3_verifiable_criteria",
            score=0,
            evidence="No verifiable acceptance criteria found",
            confidence=0.7,
        )

    def _detect_trigger_event(
        self, plan: dict, session_meta: dict
    ) -> ValueSignal:
        """Signal 4 (+1): Check if there is a clear trigger event."""
        evidence_parts: list[str] = []

        # Check session_meta for trigger info
        trigger = session_meta.get("trigger", "")
        if trigger:
            evidence_parts.append(f"session trigger: {trigger}")

        # Check for trigger-related fields
        for key in ("trigger_type", "trigger_event", "trigger_condition"):
            val = session_meta.get(key, "")
            if val:
                evidence_parts.append(f"{key}: {val}")

        # Check plan for trigger description
        plan_text = _dict_to_text(plan)
        trigger_patterns = (
            r"(trigger|触发|webhook|cron|schedule|定时|CI\s*failure|on\s+push|on\s+pull)",
        )
        for pat in trigger_patterns:
            m = re.search(pat, plan_text, re.IGNORECASE)
            if m:
                evidence_parts.append(f"plan mentions trigger: {m.group(0)}")
                break

        if evidence_parts:
            return ValueSignal(
                name="S4_trigger_event",
                score=1,
                evidence="; ".join(evidence_parts),
                confidence=0.75,
            )
        return ValueSignal(
            name="S4_trigger_event",
            score=0,
            evidence="No clear trigger event identified",
            confidence=0.7,
        )

    def _detect_no_situational_judgment(
        self, summaries: list[dict]
    ) -> ValueSignal:
        """Signal 5 (+1): Check if the session does not rely on human intuition."""
        judgment_hits: list[str] = []

        for s in summaries:
            text = s.get("text", "")
            for kw in _JUDGMENT_KEYWORDS:
                if kw in text.lower():
                    judgment_hits.append(kw)

        if not judgment_hits:
            return ValueSignal(
                name="S5_no_situational_judgment",
                score=1,
                evidence="No situational judgment keywords found in session",
                confidence=0.75,
            )
        return ValueSignal(
            name="S5_no_situational_judgment",
            score=0,
            evidence=f"Situational judgment keywords found: {', '.join(set(judgment_hits))}",
            confidence=0.8,
        )

    def _detect_future_recurrence(
        self, session_meta: dict
    ) -> ValueSignal:
        """Signal 6 (+1): Estimate probability of future recurrence."""
        evidence_parts: list[str] = []

        # Check session topic for recurring themes
        topic = session_meta.get("topic", "") or session_meta.get("title", "")
        recurring_themes = (
            "ci", "cd", "deploy", "build", "test", "lint", "format",
            "migrate", "sync", "release", "fix", "refactor", "update",
        )
        topic_lower = topic.lower()
        for theme in recurring_themes:
            if theme in topic_lower:
                evidence_parts.append(f"topic contains recurring theme '{theme}'")

        # Check for repeated execution count
        exec_count = session_meta.get("execution_count", 0)
        if exec_count >= 2:
            evidence_parts.append(f"session has {exec_count} executions")

        # Check for recurring tags
        tags = session_meta.get("tags", [])
        for tag in tags:
            if any(theme in str(tag).lower() for theme in recurring_themes):
                evidence_parts.append(f"tag '{tag}' indicates recurring activity")

        if evidence_parts:
            return ValueSignal(
                name="S6_future_recurrence",
                score=1,
                evidence="; ".join(evidence_parts),
                confidence=0.7,
            )
        return ValueSignal(
            name="S6_future_recurrence",
            score=0,
            evidence="No indicators of future recurrence found",
            confidence=0.6,
        )


# ---------------------------------------------------------------------------
# Skill-to-Loop Field Mapper (IMPL-3)
# ---------------------------------------------------------------------------

# Map risk keywords to risk levels


