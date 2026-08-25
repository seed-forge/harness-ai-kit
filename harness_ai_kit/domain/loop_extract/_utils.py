"""Shared helper functions and constants for loop_extract sub-modules.

This module centralizes utilities that are used across multiple sub-modules
to avoid circular import issues.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Keywords indicating verifiable acceptance criteria
VERIFIABLE_KEYWORDS = (
    "tests_pass", "pass_rate", "coverage", "error_count",
    "lint", "format", "compile", "build", "assert",
    "must pass", "should pass", "no regression", "no error",
    "通过", "覆盖率", "无错误", "无回归",
)

RISK_HIGH_KEYWORDS = frozenset({"delete", "remove", "deploy", "destroy", "drop", "migrate", "publish"})
RISK_MEDIUM_KEYWORDS = frozenset({"write", "create", "modify", "update", "edit", "add", "install", "commit", "push"})

# Template paths relative to repo root
TEMPLATE_DIR_PARTS = ("skills", "base-session-ai-kit-miner", "templates")
LOOP_MD_TEMPLATE = "loop.md.template"
CHECK_MD_TEMPLATE = "check.md.template"
USAGE_MD_TEMPLATE = "usage.md.template"

# Convergence thresholds by risk level
CONVERGENCE_BY_RISK: dict[str, dict[str, int]] = {
    "low": {"stagnation_threshold": 3, "divergence_threshold": 2},
    "medium": {"stagnation_threshold": 3, "divergence_threshold": 2},
    "high": {"stagnation_threshold": 2, "divergence_threshold": 1},
}

# Layer 1: high-confidence pattern mappings for rubric extraction
L1_PATTERNS: list[tuple[str, str, str, str, float]] = [
    (r"tests?\s*\w*\s*pass", "tests_pass", "All tests must pass", "must_pass", 0.5),
    (r"tests_pass_rate", "tests_pass", "All tests must pass", "must_pass", 0.5),
    (r"no\s*regression", "no_regression", "No regression introduced", "must_pass", 0.3),
    (r"coverage", "coverage", "Test coverage requirement", "should_pass", 0.2),
    (r"lint", "lint_clean", "No lint errors", "should_pass", 0.2),
    (r"format", "format_compliance", "Code formatting compliance", "should_pass", 0.1),
    (r"security|安全", "security", "No security issues", "must_pass", 0.3),
    (r"performance|性能", "performance", "No performance regression", "should_pass", 0.2),
    (r"通过测试", "tests_pass", "All tests must pass", "must_pass", 0.5),
    (r"无错误", "no_errors", "No errors", "must_pass", 0.3),
    (r"覆盖率", "coverage", "Test coverage requirement", "should_pass", 0.2),
    (r"无回归", "no_regression", "No regression introduced", "must_pass", 0.3),
]

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def load_json(path: Path) -> dict:
    """Load a JSON file, return empty dict on failure."""
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def load_summaries(summaries_dir: Path) -> list[dict]:
    """Load all summary files from a directory."""
    results: list[dict] = []
    if not summaries_dir.exists():
        return results
    for p in sorted(summaries_dir.glob("*.md")):
        try:
            text = p.read_text(encoding="utf-8")
            results.append({"path": str(p), "text": text, "name": p.stem})
        except OSError:
            continue
    return results


def load_plan(session_dir: Path) -> dict:
    """Load planning notes from session directory."""
    for name in ("IMPL_PLAN.md", "planning-notes.md"):
        p = session_dir / name
        if p.exists():
            try:
                text = p.read_text(encoding="utf-8")
                return {"_raw_text": text, "_source": name}
            except OSError:
                continue
    return {}


def load_skill_meta(skill_dir: Path) -> dict:
    """Load skill metadata from SKILL.md frontmatter and skill.json."""
    meta: dict[str, Any] = {}

    sj = skill_dir / "skill.json"
    if sj.exists():
        try:
            meta = json.loads(sj.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    sk = skill_dir / "SKILL.md"
    if sk.exists():
        try:
            text = sk.read_text(encoding="utf-8")
            m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
            if m:
                for line in m.group(1).split("\n"):
                    if ":" in line:
                        key, val = line.split(":", 1)
                        key = key.strip()
                        val = val.strip()
                        if key and val and key not in meta:
                            meta[key] = val
        except OSError:
            pass

    return meta


def normalize_action(action: str) -> str:
    """Normalize an action string for pattern comparison."""
    if not action:
        return ""
    normalized = re.sub(r"[A-Z]:\\[^\s]+", "<path>", action)
    normalized = re.sub(r"/[^\s/]+\.(ts|py|js|md|json)", "/<file>", normalized)
    normalized = re.sub(r"\b(IMPL-\d+[\.\d]*)", "<task>", normalized)
    return normalized.strip().lower()


def extract_actions_from_text(text: str) -> list[str]:
    """Extract action verbs from summary text."""
    actions: list[str] = []
    for m in re.finditer(
        r"(?:^|\n)\s*(?:\d+[\.\)]\s*|[-*]\s*)(Create|Read|Write|Edit|Update|Delete|Implement|Add|Fix|Modify|Generate|Build|Test|Verify|Run)\s+[^\n]+",
        text,
        re.IGNORECASE,
    ):
        actions.append(m.group(0).strip())
    return actions


def has_verifiable_keyword(text: str) -> bool:
    """Check if text contains verifiable acceptance keywords."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in VERIFIABLE_KEYWORDS)


def dict_to_text(d: dict) -> str:
    """Convert a dict to searchable text."""
    parts: list[str] = []
    for k, v in d.items():
        if isinstance(v, str):
            parts.append(f"{k}: {v}")
        elif isinstance(v, dict):
            parts.append(dict_to_text(v))
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    parts.append(dict_to_text(item))
    return " ".join(parts)


def normalize_weights(dimensions: list[dict[str, Any]]) -> None:
    """Normalize dimension weights to sum to 1.0 (in-place)."""
    total = sum(d["weight"] for d in dimensions)
    if total > 0:
        for d in dimensions:
            d["weight"] = round(d["weight"] / total, 3)
