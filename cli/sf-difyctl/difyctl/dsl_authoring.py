"""Import-ready Dify DSL builder.

Produces complete, importable Dify App DSL YAML documents targeting DSL
version "0.6.0" (Dify 1.13.x-1.15.x). Structure facts follow the official
Dify DSL import/export service (``api/services/app_dsl_service.py``).

Node templates and the auto-layout algorithm are adapted from two
MIT-licensed references:

- yoloyolo8/dify-workflow-writer (node schemas, gotchas)
- LingyiChen-AI/workflow-skill (layout constants, edge id format)
"""

from __future__ import annotations

import time
from copy import deepcopy
from typing import Any

# Default DSL version (authoritative via --dsl-version / config / runtime detect)
DEFAULT_DSL_VERSION = "0.6.0"

# Layout constants (adapted from LingyiChen-AI/workflow-skill, MIT)
LAYOUT_START_X = 80
LAYOUT_START_Y = 282
LAYOUT_X_STEP = 300  # node width 244 + gap
LAYOUT_Y_STEP = 200  # parallel branch spacing
NODE_WIDTH = 244
NODE_HEIGHT = 118

DEFAULT_LLM_MODEL = {
    "provider": "langgenius/deepseek/deepseek",
    "name": "deepseek-v4-flash",
    "mode": "chat",
    "completion_params": {
        "temperature": 0.1,
    },
}

# Reserved output variable names that break Dify runtime (writer gotcha #3)
RESERVED_OUTPUT_NAMES = frozenset({"error"})

# Default LLM retry config: auto-retry on transient failures (429/5xx/timeout).
# newapi already retries at the proxy layer; this is a second safety net inside
# Dify for cases where the error originates in the model response itself.
DEFAULT_LLM_RETRY_CONFIG = {
    "retry_enabled": True,
    "max_retries": 3,
    "retry_interval": 1000,  # milliseconds between retries
}

# Default LLM error strategy: when all retries are exhausted, output a
# fallback value so downstream nodes don't crash the entire workflow.
# Set to None to disable error handling (not recommended for production).
DEFAULT_LLM_ERROR_STRATEGY = {
    "type": "default_value",
    "default_value": "",
}


def _now_ms() -> int:
    return int(time.time() * 1000)


def allocate_node_ids(count: int, *, base_ms: int | None = None) -> list[str]:
    """Allocate unique 13-digit millisecond-timestamp node ids (quoted strings)."""
    base = base_ms if base_ms is not None else _now_ms()
    return [str(base + offset) for offset in range(count)]


def default_features() -> dict[str, Any]:
    return {
        "file_upload": {
            "enabled": False,
            "image": {"enabled": False, "number_limits": 3, "transfer_methods": ["local_file", "remote_url"]},
            "allowed_file_extensions": [],
            "allowed_file_types": [],
            "allowed_file_upload_methods": ["local_file", "remote_url"],
            "number_limits": 3,
        },
        "opening_statement": "",
        "retriever_resource": {"enabled": False},
        "sensitive_word_avoidance": {"enabled": False},
        "speech_to_text": {"enabled": False},
        "suggested_questions": [],
        "suggested_questions_after_answer": {"enabled": False},
        "text_to_speech": {"enabled": False, "language": "", "voice": ""},
    }


def _wrap_node(node_id: str, data: dict[str, Any], *, col: int, row: int = 0, height: int = NODE_HEIGHT) -> dict[str, Any]:
    return {
        "id": node_id,
        "type": "custom",
        "position": {"x": LAYOUT_START_X + col * LAYOUT_X_STEP, "y": LAYOUT_START_Y + row * LAYOUT_Y_STEP},
        "positionAbsolute": {"x": LAYOUT_START_X + col * LAYOUT_X_STEP, "y": LAYOUT_START_Y + row * LAYOUT_Y_STEP},
        "width": NODE_WIDTH,
        "height": height,
        "selected": False,
        "sourcePosition": "right",
        "targetPosition": "left",
        "data": data,
    }


def build_start_node(node_id: str, variables: list[dict[str, Any]], *, col: int = 0) -> dict[str, Any]:
    normalized = []
    for item in variables:
        entry = {
            "variable": str(item.get("variable") or item.get("name", "")),
            "label": str(item.get("label") or item.get("name", "")),
            "type": str(item.get("type", "text-input")),
            "required": bool(item.get("required", True)),
            "max_length": int(item.get("max_length", 4000)),
            "options": list(item.get("options", [])),
        }
        normalized.append(entry)
    data = {"type": "start", "title": "Start", "desc": "", "variables": normalized}
    return _wrap_node(node_id, data, col=col)


def build_llm_node(
    node_id: str,
    *,
    title: str,
    system_prompt: str,
    user_prompt: str = "",
    model: dict[str, Any] | None = None,
    structured_output: dict[str, Any] | None = None,
    retry_config: dict[str, Any] | None = DEFAULT_LLM_RETRY_CONFIG,
    error_strategy: dict[str, Any] | None = DEFAULT_LLM_ERROR_STRATEGY,
    col: int = 1,
    row: int = 0,
) -> dict[str, Any]:
    """Build an LLM node with default retry (3x) and error handling.

    Pass ``retry_config=None`` to disable auto-retry, or
    ``error_strategy=None`` to disable fallback (workflow will abort on error).
    """
    prompt_template: list[dict[str, Any]] = [
        {"id": f"{node_id}-system", "role": "system", "text": system_prompt},
    ]
    if user_prompt:
        prompt_template.append({"id": f"{node_id}-user", "role": "user", "text": user_prompt})
    data: dict[str, Any] = {
        "type": "llm",
        "title": title,
        "desc": "",
        "model": deepcopy(model) if model else deepcopy(DEFAULT_LLM_MODEL),
        "prompt_template": prompt_template,
        # Dify requires the context object even when disabled.
        "context": {"enabled": False, "variable_selector": []},
        "vision": {"enabled": False},
        "variables": [],
    }
    # Default: retry 3 times on transient failures (429/5xx/timeout),
    # then fall back to a default value so the workflow doesn't crash.
    if retry_config is not None:
        data["retry_config"] = deepcopy(retry_config)
    if error_strategy is not None:
        data["error_strategy"] = deepcopy(error_strategy)
    if structured_output:
        data["structured_output_enabled"] = True
        data["structured_output"] = deepcopy(structured_output)
    return _wrap_node(node_id, data, col=col, row=row)


def build_code_node(
    node_id: str,
    *,
    title: str,
    code: str,
    variables: list[dict[str, Any]],
    outputs: dict[str, Any],
    code_language: str = "python3",
    col: int = 1,
    row: int = 0,
) -> dict[str, Any]:
    for name in outputs:
        if name in RESERVED_OUTPUT_NAMES:
            raise ValueError(f"Reserved output variable name not allowed in code node: {name!r}")
    data = {
        "type": "code",
        "title": title,
        "desc": "",
        "code_language": code_language,
        "code": code,
        "variables": deepcopy(variables),
        "outputs": deepcopy(outputs),
    }
    return _wrap_node(node_id, data, col=col, row=row)


def build_http_request_node(
    node_id: str,
    *,
    title: str,
    method: str = "get",
    url: str = "",
    headers: str = "",
    params: str = "",
    body_type: str = "none",
    body_data: list[dict[str, Any]] | None = None,
    col: int = 1,
    row: int = 0,
) -> dict[str, Any]:
    data = {
        "type": "http-request",
        "title": title,
        "desc": "",
        "method": method,
        "url": url,
        "headers": headers,
        "params": params,
        "body": {"type": body_type, "data": list(body_data or [])},
        "authorization": {"type": "no-auth", "config": None},
        "timeout": {"max_connect_timeout": 0, "max_read_timeout": 0, "max_write_timeout": 0},
        "retry_config": {"retry_enabled": True, "max_retries": 3, "retry_interval": 100},
    }
    return _wrap_node(node_id, data, col=col, row=row)


def build_template_transform_node(
    node_id: str,
    *,
    title: str,
    template: str,
    variables: list[dict[str, Any]],
    col: int = 1,
    row: int = 0,
) -> dict[str, Any]:
    data = {
        "type": "template-transform",
        "title": title,
        "desc": "",
        "template": template,
        "variables": deepcopy(variables),
    }
    return _wrap_node(node_id, data, col=col, row=row)


def build_tool_node(
    node_id: str,
    *,
    title: str,
    provider_id: str,
    tool_name: str,
    tool_parameters: dict[str, Any],
    tool_configurations: dict[str, Any] | None = None,
    tool_label: str | None = None,
    provider_type: str = "builtin",
    retry: bool = True,
    col: int = 1,
    row: int = 0,
) -> dict[str, Any]:
    """Build a builtin-tool node (e.g. SearXNG/Firecrawl/Tavily web search).

    Runtime inputs go in ``tool_parameters`` wrapped as ``{type, value}`` (type
    ``mixed`` for ``{{#node.field#}}`` refs, ``constant`` for literals). Static
    config knobs go in ``tool_configurations`` as raw values (Dify validates the
    raw value against the param's options). See infra-dify-ops SKILL for the
    per-tool output-var gotcha (SearXNG -> json, Firecrawl -> text).
    """
    data: dict[str, Any] = {
        "type": "tool",
        "title": title,
        "desc": "",
        "provider_id": provider_id,
        "provider_name": provider_id,
        "provider_type": provider_type,
        "tool_name": tool_name,
        "tool_label": tool_label or tool_name,
        "tool_configurations": deepcopy(tool_configurations or {}),
        "tool_parameters": deepcopy(tool_parameters or {}),
    }
    if retry:
        data["retry_config"] = {"retry_enabled": True, "max_retries": 2, "retry_interval": 1000}
    return _wrap_node(node_id, data, col=col, row=row)


def build_if_else_node(
    node_id: str,
    *,
    title: str,
    cases: list[dict[str, Any]],
    col: int = 1,
    row: int = 0,
) -> dict[str, Any]:
    data = {
        "type": "if-else",
        "title": title,
        "desc": "",
        "cases": deepcopy(cases),
    }
    return _wrap_node(node_id, data, col=col, row=row)


def build_end_node(node_id: str, outputs: list[dict[str, Any]], *, col: int, row: int = 0) -> dict[str, Any]:
    data = {"type": "end", "title": "End", "desc": "", "outputs": deepcopy(outputs)}
    return _wrap_node(node_id, data, col=col, row=row)


def build_edge(
    source_id: str,
    target_id: str,
    *,
    source_type: str,
    target_type: str,
    source_handle: str = "source",
    z_index: int = 0,
) -> dict[str, Any]:
    """Edge with the ``{src}-{handle}-{tgt}-target`` id format."""
    return {
        "id": f"{source_id}-{source_handle}-{target_id}-target",
        "source": source_id,
        "sourceHandle": source_handle,
        "target": target_id,
        "targetHandle": "target",
        "type": "custom",
        "zIndex": z_index,
        "data": {"sourceType": source_type, "targetType": target_type, "isInIteration": False},
    }


def build_app_dsl(
    *,
    name: str,
    mode: str,
    description: str,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    dsl_version: str = DEFAULT_DSL_VERSION,
    icon: str = "🤖",
    icon_background: str = "#FFEAD5",
    environment_variables: list[dict[str, Any]] | None = None,
    conversation_variables: list[dict[str, Any]] | None = None,
    dependencies: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Assemble the complete top-level import-ready DSL document.

    dsl_version is validated by dsl_validate.validate_dsl (semver-shaped, e.g. 0.6.0),
    not restricted to a hard-coded set — instances can run any version detected at runtime.
    """
    import re as _re

    if not _re.match(r"^\d+\.\d+\.\d+$", str(dsl_version)):
        raise ValueError(f"Invalid DSL version format: {dsl_version!r} (expected semver like 0.6.0)")
    return {
        "app": {
            "name": name,
            "mode": mode,
            "icon": icon,
            "icon_type": "emoji",
            "icon_background": icon_background,
            "description": description,
            "use_icon_as_answer_icon": False,
        },
        "kind": "app",
        "version": dsl_version,
        "dependencies": list(dependencies or []),
        "workflow": {
            "environment_variables": list(environment_variables or []),
            "conversation_variables": list(conversation_variables or []),
            "features": default_features(),
            "graph": {
                "nodes": nodes,
                "edges": edges,
                "viewport": {"x": 0, "y": 0, "zoom": 1},
            },
        },
    }
