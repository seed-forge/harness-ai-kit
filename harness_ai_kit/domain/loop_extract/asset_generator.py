"""LoopAssetGenerator: generate loop assets from session analysis."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .scoring import ValueScore, ValueScorer
from .field_mapper import LoopFieldMapper
from .extractors import RubricExtractor, StopConditionExtractor
from ._utils import (
    CONVERGENCE_BY_RISK as _CONVERGENCE_BY_RISK,
    LOOP_MD_TEMPLATE as _LOOP_MD_TEMPLATE,
    CHECK_MD_TEMPLATE as _CHECK_MD_TEMPLATE,
    USAGE_MD_TEMPLATE as _USAGE_MD_TEMPLATE,
    TEMPLATE_DIR_PARTS as _TEMPLATE_DIR_PARTS,
    VERIFIABLE_KEYWORDS as _VERIFIABLE_KEYWORDS,
)


class LoopAssetGenerator:
    """Generate loop assets from session analysis.

    Combines ValueScorer, LoopFieldMapper, RubricExtractor, and
    StopConditionExtractor to produce a complete loop draft:
    loop.json + LOOP.md + CHECK.md + USAGE.md.
    """

    def __init__(self) -> None:
        self._scorer = ValueScorer()
        self._mapper = LoopFieldMapper()
        self._rubric_extractor = RubricExtractor()
        self._stop_extractor = StopConditionExtractor()

    def generate(
        self,
        session_dir: Path,
        output_dir: Path,
        loop_id: str | None = None,
        skill_dir: Path | None = None,
    ) -> Path:
        """Generate loop.json + LOOP.md + CHECK.md + USAGE.md to output_dir.

        Returns the output directory path.
        """
        session_dir = Path(session_dir)
        output_dir = Path(output_dir)

        # 1. Score session
        score = self._scorer.score_session(session_dir)

        # 2. Map fields
        if skill_dir is None:
            # Use session dir as fallback skill dir (no SKILL.md = minimal meta)
            skill_dir = session_dir
        mapped = self._mapper.map_skill_to_loop(Path(skill_dir), session_dir)

        # Override loop_id if provided
        if loop_id:
            mapped["id"] = loop_id

        # 3. Extract rubric dimensions
        session_meta = _load_json(session_dir / "workflow-session.json")
        plan = _load_plan(session_dir)
        acceptance = plan.get("acceptance", "")
        if not acceptance:
            acceptance = plan.get("context", {}).get("goal", "") if isinstance(plan.get("context"), dict) else ""
        summaries = _load_summaries(session_dir / ".summaries")
        rubric_dims = self._rubric_extractor.extract_dimensions(acceptance)

        # 4. Extract stop conditions
        stop_conditions = self._stop_extractor.extract(acceptance)

        # 5. Determine risk level and convergence metric
        operations = _extract_operations_from_summaries(summaries)
        risk_level = self._mapper.map_risk_level(operations)
        convergence = _CONVERGENCE_BY_RISK.get(risk_level, _CONVERGENCE_BY_RISK["medium"])

        # 6. Build loop.json
        loop_json = self._generate_loop_json(
            mapped, rubric_dims, stop_conditions, risk_level, convergence, score
        )

        # 7. Generate markdown files
        loop_md = self._generate_loop_md(mapped["id"], mapped.get("maker_description", ""))
        check_md = self._generate_check_md(mapped["id"], rubric_dims)
        trigger = self._mapper.map_trigger(session_meta)
        usage_md = self._generate_usage_md(mapped["id"], trigger)

        # 8. Write files to output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        import json as _json
        (output_dir / "loop.json").write_text(
            _json.dumps(loop_json, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        (output_dir / "LOOP.md").write_text(loop_md, encoding="utf-8")
        (output_dir / "CHECK.md").write_text(check_md, encoding="utf-8")
        (output_dir / "USAGE.md").write_text(usage_md, encoding="utf-8")

        return output_dir

    def _generate_loop_json(
        self,
        mapped: dict,
        rubric_dims: list[dict],
        stop_conditions: dict,
        risk_level: str,
        convergence: dict,
        score: "ValueScore",
    ) -> dict:
        """Assemble loop.json from mapped fields, rubric, and stop conditions."""
        # Convert rubric dimensions to schema format
        rubric_dimensions = []
        for dim in rubric_dims:
            rubric_dimensions.append({
                "name": dim["name"],
                "description": dim["description"],
                "weight": dim["weight"],
                "severity": dim["severity"],
                "verification": "automated check" if not dim.get("needs_human_review") else "manual review",
            })

        # Convert stop conditions to schema format
        def _to_stop_conds(conds: list[dict]) -> list[dict]:
            return [
                {"identifier": c["identifier"], "predicate": c["predicate"], "description": ""}
                for c in conds
            ]

        loop_json = {
            "schema_version": "1",
            "id": mapped["id"],
            "name": mapped["name"],
            "owner": "team",
            "version": "0.1.0",
            "status": "draft",
            "package_type": "loop",
            "tags": mapped.get("tags", []),
            "summary": mapped.get("summary", ""),
            "description": mapped.get("description", ""),
            "installation": {
                "default_scope": "project",
                "install_mode": "skill_dir",
            },
            "entry": "LOOP.md",
            "dependencies": mapped.get("dependencies", []),
            "sources": {
                "preferred": ["repo-checkout", "public-registry"],
                "allow_fallback": True,
            },
            "companion_docs": {
                "usage": "USAGE.md",
                "example": "EXAMPLE.md",
                "example_required": False,
            },
            "loop_specific": {
                "maker": {
                    "entry": mapped.get("maker_entry", "LOOP.md"),
                    "agent_type": "subagent",
                    "description": mapped.get("maker_description", ""),
                },
                "checker": {
                    "entry": mapped.get("checker_entry", "CHECK.md"),
                    "agent_type": "subagent",
                    "description": mapped.get("checker_description", ""),
                    "rubric": {
                        "dimensions": rubric_dimensions,
                        "pass_threshold": 0.8,
                    },
                },
                "stop_conditions": {
                    "success": _to_stop_conds(stop_conditions.get("success", [])),
                    "failure": _to_stop_conds(stop_conditions.get("failure", [])),
                    "budget": _to_stop_conds(stop_conditions.get("budget", [])),
                },
                "convergence_metric": {
                    "primary": "checker_score",
                    "direction": "increase",
                    "stagnation_threshold": convergence["stagnation_threshold"],
                    "divergence_threshold": convergence["divergence_threshold"],
                },
                "risk_level": risk_level,
                "execution_mode": "sub-agent",
            },
        }
        return loop_json

    def _generate_loop_md(self, loop_id: str, maker_steps: str) -> str:
        """Generate LOOP.md content from template and maker steps."""
        template = _load_template(_LOOP_MD_TEMPLATE)
        if not template:
            # Fallback minimal content
            return f"# {loop_id}\n\n{maker_steps}\n"

        # Format maker steps as workflow steps
        steps_text = maker_steps if maker_steps else "Execute the maker workflow."
        # Split on ' -> ' to create numbered steps
        step_parts = [s.strip() for s in steps_text.split(" -> ") if s.strip()]
        workflow_steps = ""
        constraints = "- Do not modify files outside the target scope.\n- Follow existing code conventions."
        success_criteria = "- Output meets quality bar.\n- No regressions introduced."

        if len(step_parts) > 1:
            for i, step in enumerate(step_parts, 1):
                workflow_steps += f"### Step {i}\n\n{step}\n\n"
        else:
            workflow_steps = steps_text

        result = template
        result = result.replace("{{loop_name}}", loop_id)
        result = result.replace("{{loop_description}}", maker_steps or "Auto-generated loop.")
        result = result.replace("{{source_session_id}}", "N/A")
        result = result.replace("{{source_summaries}}", "auto-extracted")
        result = result.replace("{{loop_tags}}", "auto-extracted")
        result = result.replace("{{maker_input_1}}", "Session artifacts")
        result = result.replace("{{maker_input_2}}", "Planning notes")
        # Fill step placeholders
        for i in range(1, 4):
            result = result.replace(f"{{{{step_{i}_title}}}}", f"Step {i}")
            result = result.replace(f"{{{{step_{i}_description}}}}", "Execute step.")
        result = result.replace("{{maker_steps}}", workflow_steps)
        result = result.replace("{{constraint_1}}", "Do not modify files outside target scope")
        result = result.replace("{{constraint_2}}", "Follow existing code conventions")
        result = result.replace("{{success_criterion_1}}", "Output meets quality bar")
        result = result.replace("{{success_criterion_2}}", "No regressions introduced")
        result = result.replace("{{dependency_1}}", "None")
        result = result.replace("{{dependency_2}}", "None")
        return result

    def _generate_check_md(self, loop_id: str, rubric_dims: list[dict]) -> str:
        """Generate CHECK.md content from template and rubric dimensions."""
        template = _load_template(_CHECK_MD_TEMPLATE)
        if not template:
            return f"# Checker -- {loop_id}\n\nRubric dimensions: {len(rubric_dims)}\n"

        # Format rubric dimensions as markdown table
        rubric_table = "| Dimension | Weight | Severity | Description |\n"
        rubric_table += "|-----------|--------|----------|-------------|\n"
        for dim in rubric_dims:
            rubric_table += (
                f"| {dim['name']} | {dim['weight']:.3f} | {dim['severity']} "
                f"| {dim['description']} |\n"
            )

        result = template
        result = result.replace("{{loop_name}}", loop_id)
        result = result.replace("{{maker_input_summary}}", "Maker output")
        result = result.replace("{{rubric_dimensions}}", rubric_table)
        result = result.replace("{{pass_threshold}}", "0.8")
        result = result.replace("{{failure_condition_1}}", "must_pass dimension score < 0.5")
        result = result.replace("{{failure_condition_2}}", "weighted total < pass_threshold")
        # Fill dimension placeholders for report format
        if rubric_dims:
            result = result.replace("{{rubric_dim_1}}", rubric_dims[0]["name"])
            result = result.replace("{{weight_1}}", f"{rubric_dims[0]['weight']:.3f}")
        else:
            result = result.replace("{{rubric_dim_1}}", "output_quality")
            result = result.replace("{{weight_1}}", "1.000")
        result = result.replace("{{rubric_dim_2}}", "N/A")
        result = result.replace("{{weight_2}}", "N/A")
        result = result.replace("{{score_1}}", "0.0")
        result = result.replace("{{score_2}}", "0.0")
        result = result.replace("{{verdict_1}}", "pending")
        result = result.replace("{{verdict_2}}", "pending")
        result = result.replace("{{total_score}}", "0.0")
        result = result.replace("{{issue_1}}", "N/A")
        result = result.replace("{{issue_2}}", "N/A")
        result = result.replace("{{recommendation}}", "Run maker first")
        return result

    def _generate_usage_md(self, loop_id: str, trigger: dict) -> str:
        """Generate USAGE.md content from template and trigger config."""
        template = _load_template(_USAGE_MD_TEMPLATE)
        if not template:
            return f"# {loop_id} -- Usage\n\nTrigger: {trigger.get('type', 'manual')}\n"

        trigger_type = trigger.get("type", "manual")
        result = template
        result = result.replace("{{loop_name}}", loop_id)
        result = result.replace("{{loop_id}}", loop_id)
        result = result.replace("{{trigger_condition_1}}", f"Trigger type: {trigger_type}")
        result = result.replace("{{trigger_condition_2}}", "Manual invocation via loopctl")
        result = result.replace("{{auto_trigger_1}}", f"{trigger_type} event")
        result = result.replace("{{auto_trigger_2}}", "Manual invocation")
        result = result.replace("{{use_case_1}}", "Repeated automation tasks")
        result = result.replace("{{use_case_2}}", "Quality gate enforcement")
        result = result.replace("{{not_applicable_1}}", "One-off exploratory tasks")
        result = result.replace("{{not_applicable_2}}", "Tasks requiring situational judgment")
        result = result.replace("{{expected_output_1}}", "Validated deliverable")
        result = result.replace("{{expected_output_2}}", "Quality report")
        result = result.replace("{{risk_level}}", trigger_type)
        result = result.replace("{{risk_description}}", "Auto-extracted loop")
        result = result.replace("{{escalation_target}}", "human operator")
        return result


def _load_template(name: str) -> str | None:
    """Load a template file from the skills directory."""
    # Walk up from this file to find repo root
    current = Path(__file__).resolve()
    for parent in [current, *current.parents]:
        template_path = parent / Path(*_TEMPLATE_DIR_PARTS) / name
        if template_path.exists():
            try:
                return template_path.read_text(encoding="utf-8")
            except OSError:
                return None
        # Also try repo-style lookup
        template_path = parent / "skills" / "base-session-ai-kit-miner" / "templates" / name
        if template_path.exists():
            try:
                return template_path.read_text(encoding="utf-8")
            except OSError:
                return None
    return None


def _extract_operations_from_summaries(summaries: list[dict]) -> list[str]:
    """Extract operation keywords from summaries for risk level detection."""
    operations: list[str] = []
    for s in summaries:
        text = s.get("text", "")
        # Look for action verbs in summary text
        for m in re.finditer(
            r"(Create|Write|Edit|Update|Delete|Deploy|Remove|Migrate|Install|Publish|Push|Commit)\s+\S+",
            text,
            re.IGNORECASE,
        ):
            operations.append(m.group(1))
    return operations


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> dict:
    """Load a JSON file, return empty dict on failure."""
    import json
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _load_summaries(summaries_dir: Path) -> list[dict]:
    """Load all summary files from a directory."""
    import re as _re
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


def _load_plan(session_dir: Path) -> dict:
    """Load planning notes from session directory."""
    for name in ("IMPL_PLAN.md", "planning-notes.md"):
        p = session_dir / name
        if p.exists():
            try:
                text = p.read_text(encoding="utf-8")
                # Parse as simple key-value sections
                return {"_raw_text": text, "_source": name}
            except OSError:
                continue
    return {}


def _load_skill_meta(skill_dir: Path) -> dict:
    """Load skill metadata from SKILL.md frontmatter and skill.json."""
    import json
    meta: dict[str, Any] = {}

    # Try skill.json first
    sj = skill_dir / "skill.json"
    if sj.exists():
        try:
            meta = json.loads(sj.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    # Try SKILL.md frontmatter
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


def _normalize_action(action: str) -> str:
    """Normalize an action string for pattern comparison."""
    if not action:
        return ""
    # Remove file paths and variable parts
    normalized = re.sub(r"[A-Z]:\\[^\s]+", "<path>", action)
    normalized = re.sub(r"/[^\s/]+\.(ts|py|js|md|json)", "/<file>", normalized)
    normalized = re.sub(r"\b(IMPL-\d+[\.\d]*)", "<task>", normalized)
    return normalized.strip().lower()


def _extract_actions_from_text(text: str) -> list[str]:
    """Extract action verbs from summary text."""
    actions: list[str] = []
    # Look for step descriptions like "1. Create file...", "Step 1: ..."
    for m in re.finditer(
        r"(?:^|\n)\s*(?:\d+[\.\)]\s*|[-*]\s*)(Create|Read|Write|Edit|Update|Delete|Implement|Add|Fix|Modify|Generate|Build|Test|Verify|Run)\s+[^\n]+",
        text,
        re.IGNORECASE,
    ):
        actions.append(m.group(0).strip())
    return actions


def _has_verifiable_keyword(text: str) -> bool:
    """Check if text contains verifiable acceptance keywords."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in _VERIFIABLE_KEYWORDS)


def _dict_to_text(d: dict) -> str:
    """Convert a dict to searchable text."""
    parts: list[str] = []
    for k, v in d.items():
        if isinstance(v, str):
            parts.append(f"{k}: {v}")
        elif isinstance(v, dict):
            parts.append(_dict_to_text(v))
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    parts.append(_dict_to_text(item))
    return " ".join(parts)


def _normalize_weights(dimensions: list[dict[str, Any]]) -> None:
    """Normalize dimension weights to sum to 1.0 (in-place)."""
    total = sum(d["weight"] for d in dimensions)
    if total > 0:
        for d in dimensions:
            d["weight"] = round(d["weight"] / total, 3)
