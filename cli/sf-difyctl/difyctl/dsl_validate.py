"""Dify DSL validator (in-house implementation).

Check dimensions are informed by yzmw123/dify-workflow-dsl-skill's public
validation checklist; the implementation here is original. Validates
import-readiness for DSL 0.6.0 / 0.7.0 documents.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

KNOWN_VERSIONS = ("0.6.0", "0.7.0")
GRAPH_MODES = ("workflow", "advanced-chat")
VALID_MODES = ("workflow", "advanced-chat", "chat", "completion", "agent-chat", "agent")

ENTRY_NODE_TYPES = ("start",)
TERMINAL_TYPES_BY_MODE = {"workflow": "end", "advanced-chat": "answer"}
NON_EXECUTABLE_TYPES = frozenset({"custom-note", ""})
RESERVED_CODE_OUTPUTS = frozenset({"error"})

# {{#node_id.field#}} — runtime restricts node id part to 1-50 word chars
VARIABLE_REF_RE = re.compile(r"\{\{#([^.#{}]+)\.([^#{}]+)#\}\}")
NODE_ID_PART_RE = re.compile(r"^[A-Za-z0-9_]{1,50}$|^sys$|^env$|^conversation$")


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "errors": self.errors, "warnings": self.warnings}


def _err(report: ValidationReport, message: str) -> None:
    report.errors.append(message)


def _warn(report: ValidationReport, message: str) -> None:
    report.warnings.append(message)


def _check_top_level(payload: dict[str, Any], report: ValidationReport, target_version: str | None) -> str:
    version = payload.get("version")
    if not isinstance(version, str):
        _err(report, "`version` must be a quoted string (e.g. \"0.6.0\")")
    elif not re.match(r"^\d+\.\d+\.\d+$", version):
        _err(report, f"`version` `{version}` is not semver-shaped (expected like 0.6.0)")
    elif target_version and version != target_version:
        _err(report, f"DSL version {version} does not match required target {target_version}")
    elif version not in KNOWN_VERSIONS:
        # Unknown-but-valid version: warn (instance may run a version we haven't cataloged)
        _warn(report, f"DSL version {version} is outside the cataloged set ({', '.join(KNOWN_VERSIONS)}); detected via difyctl dsl detect-version is authoritative")

    if payload.get("kind") != "app":
        _err(report, "`kind` must be `app`")

    app = payload.get("app")
    mode = ""
    if not isinstance(app, dict):
        _err(report, "missing top-level `app` mapping")
    else:
        if not str(app.get("name", "")).strip():
            _err(report, "app.name is required")
        mode = str(app.get("mode", "")).strip()
        if mode not in VALID_MODES:
            _err(report, f"app.mode `{mode}` is not a valid mode ({', '.join(VALID_MODES)})")
        if mode == "agent" and isinstance(payload.get("version"), str) and payload["version"] == "0.6.0":
            _err(report, "app.mode `agent` requires DSL version \"0.7.0\"")
    return mode


def _node_map(nodes: list[dict[str, Any]], report: ValidationReport) -> dict[str, dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    for index, node in enumerate(nodes):
        node_id = str(node.get("id", "")).strip()
        if not node_id:
            _err(report, f"graph.nodes[{index}] is missing `id`")
            continue
        if node_id in seen:
            _err(report, f"duplicate node id: {node_id}")
            continue
        if not isinstance(node.get("data"), dict):
            _err(report, f"node {node_id} is missing `data` mapping")
            continue
        seen[node_id] = node
    return seen


def _node_type(node: dict[str, Any]) -> str:
    return str(node.get("data", {}).get("type", "")).strip()


def _check_llm_node(node_id: str, data: dict[str, Any], report: ValidationReport) -> None:
    for required in ("model", "prompt_template"):
        if required not in data:
            _err(report, f"llm node {node_id} is missing `{required}`")
    context = data.get("context")
    if not isinstance(context, dict) or "enabled" not in context:
        _err(report, f"llm node {node_id} must include `context` object even when disabled")
    # Warn if LLM node lacks retry_config (difyctl scaffold adds this by default;
    # hand-written or exported DSLs may be missing it).
    if "retry_config" not in data:
        _warn(report, f"llm node {node_id} lacks `retry_config` — transient failures (429/5xx) will abort the workflow; difyctl scaffold defaults to 3 retries")
    elif not data.get("retry_config", {}).get("retry_enabled", False):
        _warn(report, f"llm node {node_id} has `retry_config.retry_enabled=false` — consider enabling auto-retry for production resilience")
    # Warn if LLM node lacks error_strategy (fallback value or fail-branch).
    if "error_strategy" not in data:
        _warn(report, f"llm node {node_id} lacks `error_strategy` — when all retries are exhausted the workflow will crash; consider adding a default_value fallback")


def _check_code_node(node_id: str, data: dict[str, Any], report: ValidationReport) -> None:
    outputs = data.get("outputs")
    if not isinstance(outputs, dict) or not outputs:
        _err(report, f"code node {node_id} must declare every returned field in `outputs`")
        return
    for name in outputs:
        if name in RESERVED_CODE_OUTPUTS:
            _err(report, f"code node {node_id} uses reserved output variable name `{name}`")


def _check_variable_refs(node_id: str, data: dict[str, Any], node_ids: set[str], report: ValidationReport) -> None:
    def scan(value: Any) -> None:
        if isinstance(value, str):
            for match in VARIABLE_REF_RE.finditer(value):
                ref_node = match.group(1)
                if not NODE_ID_PART_RE.match(ref_node):
                    _err(report, f"node {node_id}: variable ref `{match.group(0)}` node-id part is not runtime-safe (1-50 word chars)")
                elif ref_node not in node_ids and ref_node not in {"sys", "env", "conversation"}:
                    _err(report, f"node {node_id}: variable ref `{match.group(0)}` targets unknown node `{ref_node}`")
            # Common malformed patterns: single-# or missing #
            if re.search(r"\{\{(?!#)[^{}]+\.[^{}]+\}\}", value):
                _warn(report, f"node {node_id}: found `{{{{...}}}}` reference without `#` markers — Dify requires {{{{#node.field#}}}}")
        elif isinstance(value, dict):
            for item in value.values():
                scan(item)
        elif isinstance(value, list):
            for item in value:
                scan(item)

    scan(data)


def _check_edges(
    edges: list[dict[str, Any]],
    nodes_by_id: dict[str, dict[str, Any]],
    report: ValidationReport,
) -> dict[str, list[str]]:
    adjacency: dict[str, list[str]] = {node_id: [] for node_id in nodes_by_id}
    for index, edge in enumerate(edges):
        source = str(edge.get("source", "")).strip()
        target = str(edge.get("target", "")).strip()
        if source not in nodes_by_id:
            _err(report, f"graph.edges[{index}] source `{source}` does not exist")
            continue
        if target not in nodes_by_id:
            _err(report, f"graph.edges[{index}] target `{target}` does not exist")
            continue
        adjacency[source].append(target)
        source_node = nodes_by_id[source]
        if _node_type(source_node) == "if-else":
            handle = str(edge.get("sourceHandle", "")).strip()
            cases = source_node.get("data", {}).get("cases", [])
            valid_handles = {str(case.get("case_id", case.get("id", ""))) for case in cases if isinstance(case, dict)}
            valid_handles.add("false")
            valid_handles.add("true")
            if handle not in valid_handles:
                _err(report, f"if-else node {source} edge handle `{handle}` is not a declared case id or `false`")
    return adjacency


def _check_reachability(
    mode: str,
    nodes_by_id: dict[str, dict[str, Any]],
    adjacency: dict[str, list[str]],
    report: ValidationReport,
) -> None:
    entries = [node_id for node_id, node in nodes_by_id.items() if _node_type(node) in ENTRY_NODE_TYPES]
    if not entries:
        _err(report, "graph has no `start` entry node")
        return
    if mode == "advanced-chat" and len(entries) > 1:
        _err(report, "advanced-chat graph must have exactly one `start` node")

    visited: set[str] = set()
    stack = list(entries)
    while stack:
        current = stack.pop()
        if current in visited:
            continue
        visited.add(current)
        stack.extend(adjacency.get(current, []))

    for node_id, node in nodes_by_id.items():
        if _node_type(node) in NON_EXECUTABLE_TYPES:
            continue
        if node_id not in visited:
            _err(report, f"node {node_id} ({_node_type(node)}) is unreachable from start")

    terminal_type = TERMINAL_TYPES_BY_MODE.get(mode, "end")
    terminal_reached = any(
        _node_type(nodes_by_id[node_id]) == terminal_type for node_id in visited if node_id in nodes_by_id
    )
    if not terminal_reached:
        _warn(report, f"no reachable `{terminal_type}` node — acceptable only for triggered side-effect workflows")


def _check_cycles(adjacency: dict[str, list[str]], report: ValidationReport) -> None:
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {node_id: WHITE for node_id in adjacency}

    def dfs(node_id: str) -> bool:
        color[node_id] = GRAY
        for neighbor in adjacency.get(node_id, []):
            if color.get(neighbor, WHITE) == GRAY:
                return True
            if color.get(neighbor, WHITE) == WHITE and dfs(neighbor):
                return True
        color[node_id] = BLACK
        return False

    for node_id in adjacency:
        if color[node_id] == WHITE and dfs(node_id):
            _err(report, f"graph contains a cycle involving node {node_id}")
            return


def validate_dsl(payload: dict[str, Any], *, target_version: str | None = None) -> ValidationReport:
    """Validate an import-ready Dify DSL document. Returns a ValidationReport."""
    report = ValidationReport()
    if not isinstance(payload, dict):
        _err(report, "DSL document must be a YAML mapping")
        return report

    mode = _check_top_level(payload, report, target_version)

    if mode not in GRAPH_MODES:
        # Non-graph app kinds (chat/completion/agent) skip graph checks.
        return report

    workflow = payload.get("workflow")
    if not isinstance(workflow, dict):
        _err(report, "graph modes require a top-level `workflow` mapping")
        return report
    graph = workflow.get("graph")
    if not isinstance(graph, dict):
        _err(report, "workflow.graph is required")
        return report
    nodes = graph.get("nodes")
    edges = graph.get("edges")
    if not isinstance(nodes, list) or not nodes:
        _err(report, "workflow.graph.nodes must be a non-empty list")
        return report
    if not isinstance(edges, list):
        _err(report, "workflow.graph.edges must be a list")
        return report

    nodes_by_id = _node_map(nodes, report)
    node_ids = set(nodes_by_id)

    for node_id, node in nodes_by_id.items():
        data = node.get("data", {})
        node_type = _node_type(node)
        if node_type == "llm":
            _check_llm_node(node_id, data, report)
        elif node_type == "code":
            _check_code_node(node_id, data, report)
        _check_variable_refs(node_id, data, node_ids, report)

    adjacency = _check_edges(edges, nodes_by_id, report)
    _check_reachability(mode, nodes_by_id, adjacency, report)
    _check_cycles(adjacency, report)
    return report
