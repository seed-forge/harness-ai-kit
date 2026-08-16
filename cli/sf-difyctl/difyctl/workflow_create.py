from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import yaml

from difyctl.dsl_authoring import (
    DEFAULT_DSL_VERSION,
    DEFAULT_LLM_MODEL,
    allocate_node_ids,
    build_app_dsl,
    build_code_node,
    build_edge,
    build_end_node,
    build_http_request_node,
    build_if_else_node,
    build_llm_node,
    build_start_node,
    build_template_transform_node,
    build_tool_node,
)

SUPPORTED_SPEC_VERSIONS = (1, 2)
SUPPORTED_STEP_TYPES = ("llm", "code", "http-request", "if-else", "template-transform", "tool")


def default_spec_payload(
    *,
    name: str,
    mode: str,
    goal: str,
    inputs: list[str],
    outputs: list[str],
    steps: list[str],
) -> dict[str, object]:
    """Build a v2 spec skeleton from flat CLI arguments."""
    return {
        "version": 2,
        "workflow": {
            "name": name,
            "mode": mode,
            "goal": goal,
            "inputs": [{"name": item, "type": "text-input", "required": True} for item in inputs],
            "outputs": [{"name": item, "type": "text"} for item in outputs],
            "steps": [
                {"id": f"step_{index + 1}", "name": step, "type": "llm"}
                for index, step in enumerate(steps)
            ],
        },
    }


def write_spec(path: Path, payload: dict[str, object], *, force: bool = False) -> Path:
    if path.exists() and not force:
        raise FileExistsError(f"Spec file already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


def load_spec(path: Path) -> dict[str, object]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError("workflow spec must be a mapping document")
    return payload


def validate_spec_payload(payload: dict[str, object]) -> list[str]:
    errors: list[str] = []
    version = payload.get("version", 1)
    if version not in SUPPORTED_SPEC_VERSIONS:
        errors.append(f"spec version {version!r} is not supported (supported: {SUPPORTED_SPEC_VERSIONS})")
    workflow = payload.get("workflow")
    if not isinstance(workflow, dict):
        return ["missing mapping field `workflow`"]
    if not str(workflow.get("name", "")).strip():
        errors.append("workflow.name is required")
    if not str(workflow.get("mode", "")).strip():
        errors.append("workflow.mode is required")
    steps = workflow.get("steps", [])
    if not isinstance(steps, list) or not steps:
        errors.append("workflow.steps must be a non-empty list")
    else:
        for index, step in enumerate(steps):
            if not isinstance(step, dict):
                errors.append(f"workflow.steps[{index}] must be a mapping")
                continue
            if not str(step.get("id", "")).strip():
                errors.append(f"workflow.steps[{index}].id is required")
            if not str(step.get("name", "")).strip():
                errors.append(f"workflow.steps[{index}].name is required")
            step_type = str(step.get("type", "llm")).strip() or "llm"
            if step_type not in SUPPORTED_STEP_TYPES:
                errors.append(
                    f"workflow.steps[{index}].type `{step_type}` unsupported (supported: {', '.join(SUPPORTED_STEP_TYPES)})"
                )
            if step_type == "code":
                if not isinstance(step.get("outputs"), dict) or not step.get("outputs"):
                    errors.append(f"workflow.steps[{index}] (code) must declare `outputs` mapping")
                if "error" in (step.get("outputs") or {}):
                    errors.append(f"workflow.steps[{index}] (code) uses reserved output name `error`")
            if step_type == "tool":
                if not str(step.get("provider_id", "")).strip():
                    errors.append(f"workflow.steps[{index}] (tool) must set `provider_id` (e.g. langgenius/searxng/searxng)")
                if not str(step.get("tool_name", "")).strip():
                    errors.append(f"workflow.steps[{index}] (tool) must set `tool_name` (e.g. searxng_search)")
    return errors


def _normalize_inputs(raw_inputs: list) -> list[dict[str, object]]:
    normalized = []
    for item in raw_inputs:
        if not isinstance(item, dict):
            continue
        input_type = str(item.get("type", "text-input"))
        if input_type == "text":
            input_type = "text-input"
        normalized.append(
            {
                "variable": str(item.get("variable") or item.get("name", "")),
                "label": str(item.get("label") or item.get("name", "")),
                "type": input_type,
                "required": bool(item.get("required", True)),
                "max_length": int(item.get("max_length", 4000)),
                "options": list(item.get("options", [])),
            }
        )
    return normalized


def _build_step_node(step: dict, node_id: str, *, col: int, workflow_name: str, prior_ids: dict[str, str]) -> dict:
    """Build one graph node from a spec step definition."""
    step_type = str(step.get("type", "llm")).strip() or "llm"
    title = str(step.get("name", "")).strip() or step_type
    instruction = str(step.get("instruction", "")).strip()

    if step_type == "llm":
        model = step.get("model") if isinstance(step.get("model"), dict) else deepcopy(DEFAULT_LLM_MODEL)
        structured = step.get("structured_output") if isinstance(step.get("structured_output"), dict) else None
        return build_llm_node(
            node_id,
            title=title,
            system_prompt=instruction or f"Handle step `{step.get('id')}` for workflow `{workflow_name}`.",
            user_prompt=str(step.get("user_prompt", "")).strip(),
            model=model,
            structured_output=structured,
            col=col,
        )
    if step_type == "code":
        return build_code_node(
            node_id,
            title=title,
            code=str(step.get("code", "def main():\n    return {}\n")),
            variables=list(step.get("variables", [])),
            outputs=dict(step.get("outputs", {})),
            code_language=str(step.get("code_language", "python3")),
            col=col,
        )
    if step_type == "http-request":
        return build_http_request_node(
            node_id,
            title=title,
            method=str(step.get("method", "get")),
            url=str(step.get("url", "")),
            headers=str(step.get("headers", "")),
            params=str(step.get("params", "")),
            col=col,
        )
    if step_type == "template-transform":
        return build_template_transform_node(
            node_id,
            title=title,
            template=str(step.get("template", "")),
            variables=list(step.get("variables", [])),
            col=col,
        )
    if step_type == "if-else":
        return build_if_else_node(
            node_id,
            title=title,
            cases=list(step.get("cases", [])),
            col=col,
        )
    if step_type == "tool":
        return build_tool_node(
            node_id,
            title=title,
            provider_id=str(step.get("provider_id", "")),
            tool_name=str(step.get("tool_name", "")),
            tool_parameters=dict(step.get("tool_parameters", {})),
            tool_configurations=dict(step.get("tool_configurations", {})),
            tool_label=step.get("tool_label"),
            provider_type=str(step.get("provider_type", "builtin")),
            col=col,
        )
    raise ValueError(f"Unsupported step type: {step_type}")


def _remap_references(obj, remap: dict[str, str]):
    """Recursively remap stable spec step-ids to generated node-ids.

    Rewrites both mixed-string refs (``{{#step_id.field#}}``) and
    ``value_selector``/``variable_selector`` list heads so cross-node data flow
    (e.g. tool -> template -> tool -> llm) wires to the real node ids.
    """
    if isinstance(obj, str):
        s = obj
        for k, v in remap.items():
            if k != v:
                s = s.replace(f"#{k}.", f"#{v}.")
        return s
    if isinstance(obj, list):
        return [_remap_references(x, remap) for x in obj]
    if isinstance(obj, dict):
        out: dict = {}
        for key, val in obj.items():
            if key in ("value_selector", "variable_selector") and isinstance(val, list) and val:
                head = val[0]
                new_head = remap.get(head, head) if isinstance(head, str) else head
                out[key] = [new_head, *[_remap_references(x, remap) for x in val[1:]]]
            else:
                out[key] = _remap_references(val, remap)
        return out
    return obj


def scaffold_dsl_from_spec(
    payload: dict[str, object],
    *,
    dsl_version: str | None = None,
) -> dict[str, object]:
    """Scaffold a complete import-ready Dify DSL document from a spec (v1 or v2).

    If dsl_version is None or 'auto', uses DEFAULT_DSL_VERSION (0.6.0) or reads
    from config if available. For full auto-detect from live instance, use
    detect_and_scaffold() in cli.py instead.
    """
    workflow = payload.get("workflow")
    if not isinstance(workflow, dict):
        raise ValueError("payload['workflow'] must be a mapping")

    name = str(workflow.get("name", "")).strip()
    mode = str(workflow.get("mode", "")).strip()
    description = str(workflow.get("goal", "")).strip()
    inputs = _normalize_inputs(list(workflow.get("inputs", [])))
    outputs = list(workflow.get("outputs", []))
    steps = list(workflow.get("steps", []))

    # Resolve effective version
    effective_version = dsl_version if dsl_version else None
    if not effective_version:
        effective_version = payload.get("dsl_version", DEFAULT_DSL_VERSION)
    effective_version = str(effective_version)

    node_ids = allocate_node_ids(len(steps) + 2)
    start_id, step_node_ids, end_id = node_ids[0], node_ids[1:-1], node_ids[-1]
    id_by_step: dict[str, str] = {
        str(step.get("id", f"step_{idx + 1}")): step_node_ids[idx] for idx, step in enumerate(steps)
    }

    nodes: list[dict] = [build_start_node(start_id, inputs, col=0)]
    edges: list[dict] = []
    previous_id, previous_type = start_id, "start"

    # Stable spec-id -> generated-node-id map (incl. the start node under "start").
    remap: dict[str, str] = {"start": start_id, **id_by_step}

    for index, step in enumerate(steps):
        node_id = step_node_ids[index]
        node = _build_step_node(step, node_id, col=index + 1, workflow_name=name, prior_ids=id_by_step)
        node["data"] = _remap_references(node["data"], remap)
        step_type = str(step.get("type", "llm")).strip() or "llm"
        nodes.append(node)
        edges.append(build_edge(previous_id, node_id, source_type=previous_type, target_type=step_type))
        previous_id, previous_type = node_id, step_type

    end_outputs = []
    last_step_id = previous_id
    for item in outputs:
        if not isinstance(item, dict):
            continue
        selector = item.get("value_selector")
        if not isinstance(selector, list) or not selector:
            selector = [last_step_id, str(item.get("source_field", "text"))]
        else:
            # Re-map spec step ids (and "start") to generated node ids where applicable.
            head = str(selector[0])
            selector = [remap.get(head, head), *[str(part) for part in selector[1:]]]
        end_outputs.append({"variable": str(item.get("name", "output")), "value_selector": selector})

    nodes.append(build_end_node(end_id, end_outputs, col=len(steps) + 1))
    edges.append(build_edge(previous_id, end_id, source_type=previous_type, target_type="end"))

    return build_app_dsl(
        name=name,
        mode=mode,
        description=description,
        nodes=nodes,
        edges=edges,
        dsl_version=effective_version,
    )


def write_dsl(path: Path, payload: dict[str, object], *, force: bool = False) -> Path:
    if path.exists() and not force:
        raise FileExistsError(f"DSL file already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path
