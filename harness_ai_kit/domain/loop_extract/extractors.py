"""RubricExtractor and StopConditionExtractor."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ._utils import (
    CONVERGENCE_BY_RISK as _CONVERGENCE_BY_RISK,
    L1_PATTERNS as _L1_PATTERNS,
    LOOP_MD_TEMPLATE as _LOOP_MD_TEMPLATE,
    CHECK_MD_TEMPLATE as _CHECK_MD_TEMPLATE,
    USAGE_MD_TEMPLATE as _USAGE_MD_TEMPLATE,
    TEMPLATE_DIR_PARTS as _TEMPLATE_DIR_PARTS,
    normalize_weights as _normalize_weights,
)


class RubricExtractor:
    """Extract rubric dimensions from acceptance criteria text.

    Uses a 3-layer strategy:
    - Layer 1: High-confidence pattern matching
    - Layer 2: Medium-confidence semantic classification
    - Layer 3: Low-confidence default fallback
    """

    def extract_dimensions(self, acceptance_text: str) -> list[dict[str, Any]]:
        """Extract rubric dimensions from acceptance criteria text.

        Returns a list of dimension dicts, each with confidence and
        needs_human_review flag.
        """
        if not acceptance_text:
            return self._layer3_default_fallback()

        l1 = self._layer1_pattern_match(acceptance_text)
        l2 = self._layer2_semantic_classify(acceptance_text)

        # Merge: Layer 1 takes priority, Layer 2 fills gaps
        seen_names = {d["name"] for d in l1}
        merged = list(l1)
        for d in l2:
            if d["name"] not in seen_names:
                merged.append(d)

        if not merged:
            return self._layer3_default_fallback()

        # Normalize weights to sum to 1.0
        _normalize_weights(merged)
        return merged

    def _layer1_pattern_match(self, text: str) -> list[dict[str, Any]]:
        """Layer 1: High-confidence pattern matching."""
        dimensions: list[dict[str, Any]] = []
        seen: set[str] = set()
        text_lower = text.lower()

        for pattern, name, desc, severity, weight in _L1_PATTERNS:
            if name in seen:
                continue
            if re.search(pattern, text_lower):
                seen.add(name)
                dimensions.append({
                    "name": name,
                    "description": desc,
                    "severity": severity,
                    "weight": weight,
                    "confidence": 0.9,
                    "needs_human_review": False,
                    "layer": 1,
                })
        return dimensions

    def _layer2_semantic_classify(self, text: str) -> list[dict[str, Any]]:
        """Layer 2: Medium-confidence semantic classification."""
        dimensions: list[dict[str, Any]] = []
        text_lower = text.lower()
        seen: set[str] = set()

        # Look for verification step patterns
        step_patterns = [
            (r"(检查|verify|check|validate)\s*(.*?)(?:[,;.]|$)", "verification_step"),
            (r"(确保|ensure|confirm)\s*(.*?)(?:[,;.]|$)", "ensurance_step"),
            (r"(输出|output)\s*(.*?)(?:符合|matches|correct)", "output_quality"),
        ]
        for pattern, category in step_patterns:
            if category in seen:
                continue
            m = re.search(pattern, text_lower)
            if m:
                seen.add(category)
                dimensions.append({
                    "name": f"{category}_{len(dimensions)}",
                    "description": f"Semantic match: {m.group(0)[:80]}",
                    "severity": "should_pass",
                    "weight": 0.15,
                    "confidence": 0.6,
                    "needs_human_review": True,
                    "layer": 2,
                })

        return dimensions

    def _layer3_default_fallback(self) -> list[dict[str, Any]]:
        """Layer 3: Low-confidence default fallback."""
        return [
            {
                "name": "output_quality",
                "description": "Overall output quality",
                "severity": "must_pass",
                "weight": 1.0,
                "confidence": 0.3,
                "needs_human_review": True,
                "layer": 3,
            },
        ]


# ---------------------------------------------------------------------------
# Stop Condition Extractor
# ---------------------------------------------------------------------------

_DEFAULT_BUDGET = [
    {"identifier": "max_iterations", "predicate": "iteration_count >= 10"},
    {"identifier": "max_tokens", "predicate": "token_usage >= 500000"},
]


class StopConditionExtractor:
    """Extract success/failure/budget stop conditions."""

    def extract(
        self, acceptance_text: str, error_patterns: list[str] | None = None
    ) -> dict[str, list[dict[str, str]]]:
        """Extract success/failure/budget stop conditions.

        Returns dict with keys 'success', 'failure', 'budget'.
        """
        return {
            "success": self._extract_success(acceptance_text),
            "failure": self._extract_failure(error_patterns or []),
            "budget": self._extract_budget(acceptance_text),
        }

    def _extract_success(self, acceptance_text: str) -> list[dict[str, str]]:
        """Extract success stop conditions from acceptance criteria."""
        if not acceptance_text:
            return [{"identifier": "rubric_pass", "predicate": "checker_score >= 0.8"}]

        conditions: list[dict[str, str]] = []
        text_lower = acceptance_text.lower()

        if re.search(r"(tests?[\s_]*pass|通过测试|测试通过)", text_lower):
            conditions.append({"identifier": "tests_pass", "predicate": "tests_pass_rate == 1.0"})
        m = re.search(r"coverage\s*>=?\s*(\d+)", text_lower)
        if m:
            conditions.append({"identifier": "coverage", "predicate": f"coverage_pct >= {m.group(1)}"})
        if re.search(r"(no\s*lint|无.*警告)", text_lower):
            conditions.append({"identifier": "no_lint_errors", "predicate": "error_count == 0"})
        if re.search(r"(no\s*error|无错误)", text_lower):
            conditions.append({"identifier": "no_errors", "predicate": "error_count == 0"})

        if not conditions:
            conditions.append({"identifier": "rubric_pass", "predicate": "checker_score >= 0.8"})
        return conditions

    def _extract_failure(
        self, error_patterns: list[str]
    ) -> list[dict[str, str]]:
        """Extract failure stop conditions from error patterns."""
        conditions: list[dict[str, str]] = [
            {"identifier": "max_errors", "predicate": "error_count >= 3"},
        ]
        for pat in error_patterns:
            if "timeout" in pat.lower():
                conditions.append({
                    "identifier": "timeout",
                    "predicate": "duration_seconds >= 3600",
                })
            if "memory" in pat.lower() or "oom" in pat.lower():
                conditions.append({
                    "identifier": "memory_exceeded",
                    "predicate": "memory_usage_mb >= 4096",
                })
        return conditions

    def _extract_budget(self, acceptance_text: str) -> list[dict[str, str]]:
        """Extract budget stop conditions (default values + text overrides)."""
        conditions = list(_DEFAULT_BUDGET)

        # Check acceptance text for iteration count hints
        if acceptance_text:
            m = re.search(r"(?:iteration|迭代)\s*>=?\s*(\d+)", acceptance_text, re.IGNORECASE)
            if m:
                count = int(m.group(1))
                conditions[0] = {
                    "identifier": "max_iterations",
                    "predicate": f"iteration_count >= {count}",
                }
        return conditions


# ---------------------------------------------------------------------------
# Loop Asset Generator (IMPL-4)
# ---------------------------------------------------------------------------

# Template paths and convergence thresholds are imported from ._utils


