"""LoopFieldMapper: map skill fields to loop.json structure."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from ._utils import (
    L1_PATTERNS as _L1_PATTERNS,
    RISK_HIGH_KEYWORDS as _RISK_HIGH_KEYWORDS,
    RISK_MEDIUM_KEYWORDS as _RISK_MEDIUM_KEYWORDS,
    load_json as _load_json,
    load_plan as _load_plan,
    load_skill_meta as _load_skill_meta,
    load_summaries as _load_summaries,
)


class LoopFieldMapper:
    """Map skill fields to loop.json structure.

    Covers all 14 fields from REFERENCE-EXTRACTION-RUBRIC.md field mapping matrix.
    """

    def map_skill_to_loop(
        self,
        skill_dir: Path,
        session_dir: Path,
    ) -> dict[str, Any]:
        """Map skill fields to a loop.json-compatible dict.

        Returns a dict that can be validated as LoopManifest.
        Fields needing human review are marked with _needs_human_review=True.
        """
        skill_meta = _load_skill_meta(skill_dir)
        session_meta = _load_json(session_dir / "workflow-session.json")
        summaries = _load_summaries(session_dir / ".summaries")
        plan = _load_plan(session_dir)

        skill_name = skill_meta.get("name", session_meta.get("topic", "unnamed"))
        skill_tags = skill_meta.get("tags", [])
        skill_deps = skill_meta.get("dependencies", [])
        acceptance = plan.get("acceptance", "")

        # Detect combination mode
        combo_mode = self._detect_combination_mode(summaries, session_meta)

        result: dict[str, Any] = {
            # Field 1: loop.id (auto)
            "id": self.map_name(skill_name),
            # Field 2: loop.name (auto)
            "name": skill_name,
            # Field 3: loop.summary (semi-auto)
            "summary": self.map_summary(summaries),
            # Field 4: loop.description (semi-auto)
            "description": self._map_description(plan, summaries),
            # Field 5: loop.tags (semi-auto)
            "tags": self.map_tags(skill_tags, session_meta.get("topic", "")),
            # Field 6: loop.dependencies (auto)
            "dependencies": self.map_dependencies(skill_deps),
            # Field 7: loop.maker.entry (auto)
            "maker_entry": "LOOP.md",
            # Field 8: loop.maker.description (semi-auto)
            "maker_description": self._map_maker_description(plan, summaries),
            # Field 9: loop.checker.entry (auto)
            "checker_entry": "CHECK.md",
            # Field 10: loop.checker.description (semi-auto)
            "checker_description": self._map_checker_description(acceptance),
            # Field 11: loop.checker.rubric.dimensions (needs human)
            "rubric_dimensions": "needs_human_review",
            # Field 12: loop.stop_conditions.success (semi-auto)
            "stop_conditions_success": self._map_stop_success(acceptance),
            # Field 13: loop.stop_conditions.failure (semi-auto)
            "stop_conditions_failure": self._map_stop_failure(summaries),
            # Field 14: loop.convergence_metric (needs human)
            "convergence_metric": "needs_human_review",
            # Additional context
            "_combination_mode": combo_mode,
            "_needs_human_review": [
                "rubric_dimensions",
                "convergence_metric",
                "description",
                "stop_conditions_success",
                "stop_conditions_failure",
            ],
        }
        return result

    def map_name(self, skill_name: str) -> str:
        """Auto: Generate loop_id from skill name."""
        loop_id = skill_name.lower().strip()
        loop_id = re.sub(r"[^a-z0-9]+", "-", loop_id)
        loop_id = loop_id.strip("-")
        if not loop_id:
            loop_id = "unnamed-loop"
        return loop_id

    def map_summary(self, session_summaries: list) -> str:
        """Semi-auto: Extract summary from session summaries."""
        if not session_summaries:
            return "needs_human_review"
        # Use the first summary's first paragraph
        first = session_summaries[0]
        text = first.get("text", "")
        # Extract first paragraph (up to first blank line or 200 chars)
        paragraphs = text.split("\n\n")
        for para in paragraphs:
            clean = para.strip()
            if clean and not clean.startswith("#"):
                return clean[:200]
        return text[:200] if text else "needs_human_review"

    def map_tags(self, skill_tags: list, session_topic: str) -> list[str]:
        """Semi-auto: Aggregate tags from skill and session."""
        tags = list(skill_tags)
        # Extract keywords from topic
        if session_topic:
            words = re.split(r"[\s\-_]+", session_topic.lower())
            for w in words:
                if len(w) > 2 and w not in tags:
                    tags.append(w)
        return tags

    def map_dependencies(self, skill_deps: list) -> list[dict[str, Any]]:
        """Auto: Convert skill dependencies to loop format."""
        result = []
        for dep in skill_deps:
            if isinstance(dep, str):
                result.append({"name": dep, "version": "*"})
            elif isinstance(dep, dict):
                result.append({
                    "name": dep.get("name", ""),
                    "version": dep.get("version", "*"),
                })
        return result

    def map_trigger(self, session_meta: dict) -> dict[str, Any]:
        """Semi-auto: Infer trigger type from session metadata."""
        trigger_type = session_meta.get("trigger_type", "")
        if not trigger_type:
            # Infer from topic or description
            topic = (session_meta.get("topic", "") or "").lower()
            if "ci" in topic or "webhook" in topic:
                trigger_type = "event"
            elif "cron" in topic or "schedule" in topic:
                trigger_type = "cron"
            else:
                trigger_type = "manual"
        return {"type": trigger_type, "needs_human_review": True}

    def map_risk_level(self, operations: list[str]) -> Literal["low", "medium", "high"]:
        """Semi-auto: Infer risk_level from operation types."""
        ops_text = " ".join(operations).lower()
        for kw in _RISK_HIGH_KEYWORDS:
            if kw in ops_text:
                return "high"
        for kw in _RISK_MEDIUM_KEYWORDS:
            if kw in ops_text:
                return "medium"
        return "low"

    def _detect_combination_mode(
        self, summaries: list[dict], session_meta: dict
    ) -> Literal["pipeline", "parallel", "conditional", "unknown"]:
        """Detect multi-skill combination mode."""
        tasks = session_meta.get("tasks", [])
        if len(tasks) < 2:
            return "unknown"

        # Check for sequential dependencies
        has_sequential = False
        for t in tasks:
            deps = t.get("depends_on", [])
            if deps:
                has_sequential = True
                break

        if has_sequential:
            return "pipeline"

        # Check for parallel execution (tasks without dependencies)
        all_independent = all(not t.get("depends_on") for t in tasks)
        if all_independent and len(tasks) > 1:
            return "parallel"

        return "unknown"

    def _map_description(self, plan: dict, summaries: list[dict]) -> str:
        """Field 4: Extract description from planning notes and summaries."""
        # Try plan description first
        desc = plan.get("description", "")
        if desc:
            return desc
        # Try plan goal
        goal = plan.get("goal", "")
        if goal:
            return goal
        # Try context.goal
        ctx = plan.get("context", {})
        if isinstance(ctx, dict) and ctx.get("goal"):
            return ctx["goal"]
        return "needs_human_review"

    def _map_maker_description(
        self, plan: dict, summaries: list[dict]
    ) -> str:
        """Field 8: Extract maker description from workflow steps."""
        # Try plan tasks/steps
        tasks = plan.get("tasks", [])
        if tasks:
            steps = []
            for t in tasks:
                action = t.get("action", "")
                if action:
                    steps.append(action)
            if steps:
                return " -> ".join(steps)
        return "needs_human_review"

    def _map_checker_description(self, acceptance: str) -> str:
        """Field 10: Extract checker description from acceptance criteria."""
        if acceptance:
            return acceptance
        return "needs_human_review"

    def _map_stop_success(self, acceptance: str) -> list[dict[str, str]]:
        """Field 12: Extract success stop conditions from acceptance criteria."""
        if not acceptance:
            return [{"identifier": "rubric_pass", "predicate": "checker_score >= 0.8"}]
        conditions = []
        # Look for test-related conditions
        if re.search(r"(tests?\s*pass|通过测试|测试通过)", acceptance, re.IGNORECASE):
            conditions.append({"identifier": "tests_pass", "predicate": "tests_pass_rate == 1.0"})
        # Look for coverage conditions
        m = re.search(r"coverage\s*>=?\s*(\d+)", acceptance, re.IGNORECASE)
        if m:
            conditions.append({"identifier": "coverage", "predicate": f"coverage_pct >= {m.group(1)}"})
        # Look for lint/format conditions
        if re.search(r"(no\s*lint|无.*警告|format)", acceptance, re.IGNORECASE):
            conditions.append({"identifier": "no_lint_errors", "predicate": "error_count == 0"})
        if not conditions:
            conditions.append({"identifier": "rubric_pass", "predicate": "checker_score >= 0.8"})
        return conditions

    def _map_stop_failure(self, summaries: list[dict]) -> list[dict[str, str]]:
        """Field 13: Extract failure stop conditions from error patterns."""
        error_patterns: list[str] = []
        for s in summaries:
            text = s.get("text", "")
            if re.search(r"(error|failure|failed|exception)", text, re.IGNORECASE):
                error_patterns.append("error_detected")
                break
        return [{"identifier": "max_errors", "predicate": "error_count >= 3"}]


# ---------------------------------------------------------------------------
# Rubric Extractor (3-layer strategy)
# ---------------------------------------------------------------------------

# Layer 1 patterns are imported from ._utils


