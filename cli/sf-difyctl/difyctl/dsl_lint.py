"""Local DSL static analysis (lint) and model retargeting for Dify DSL documents.

Pure functions over a parsed DSL dict (no network). Used by `dsl lint` and
`dsl retarget`. Lint focuses on issues detectable from the DSL alone:
- hardcoded secrets in credentials (security; reported as errors)
- dangling variable references ({{#node_id.field#}} to a non-existent node)
- empty/missing model references on LLM-type nodes
Retarget rewrites model provider+name across LLM/agent nodes and model_config.
"""
from __future__ import annotations

import re

# Keys whose non-empty, non-variable string value looks like a real secret.
_SECRET_KEY_RE = re.compile(r"(api[_-]?key|secret|token|password|access[_-]?key)", re.IGNORECASE)
# A Dify variable reference like {{#1712345678901.query#}} or {{#start.text#}}
_VAR_REF_RE = re.compile(r"\{\{#([^.}]+)\.[^}]+#\}\}")
# Placeholders that are NOT real secrets
_PLACEHOLDER_VALUES = {"", "***", "****", "your-api-key", "sk-xxx", "changeme", "placeholder"}


def _looks_like_secret(value: str) -> bool:
    v = str(value or "").strip()
    if v in _PLACEHOLDER_VALUES or len(v) < 8:
        return False
    if v.startswith("{{") or v.startswith("$") or v.startswith("{"):  # variable / env ref
        return False
    return True


def _walk(obj, path=""):
    """Yield (path, key, value) for every dict key in a nested structure."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            here = f"{path}.{k}" if path else str(k)
            yield here, k, v
            yield from _walk(v, here)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            yield from _walk(item, f"{path}[{i}]")


def _graph_nodes(document: dict) -> list[dict]:
    wf = document.get("workflow", {}) if isinstance(document, dict) else {}
    graph = wf.get("graph", {}) if isinstance(wf, dict) else {}
    nodes = graph.get("nodes", []) if isinstance(graph, dict) else []
    return [n for n in nodes if isinstance(n, dict)]


def lint_dsl(document: dict) -> dict:
    """Static-analyze a DSL document. Returns {ok, errors, warnings, findings}."""
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(document, dict):
        return {"ok": False, "errors": ["DSL root is not a mapping"], "warnings": [], "findings": {}}

    # 1) hardcoded secrets (security -> error)
    secrets: list[str] = []
    for path, key, value in _walk(document):
        if isinstance(value, str) and _SECRET_KEY_RE.search(str(key)) and _looks_like_secret(value):
            secrets.append(path)
    if secrets:
        errors.append(f"hardcoded secret(s) at: {secrets}")

    # 2) node ids + dangling variable references (warning)
    nodes = _graph_nodes(document)
    node_ids = {str(n.get("id", "")) for n in nodes if n.get("id")}
    dangling: set[str] = set()
    if node_ids:
        for _path, _key, value in _walk(document):
            if isinstance(value, str):
                for ref in _VAR_REF_RE.findall(value):
                    # sys / env / conversation scopes are always valid pseudo-nodes
                    if ref in ("sys", "env", "conversation"):
                        continue
                    if ref not in node_ids:
                        dangling.add(ref)
    if dangling:
        warnings.append(f"variable reference to unknown node id(s): {sorted(dangling)}")

    # 3) empty model refs on LLM/agent nodes (warning)
    empty_models: list[str] = []
    for n in nodes:
        data = n.get("data", {}) if isinstance(n.get("data"), dict) else {}
        ntype = str(data.get("type", ""))
        if ntype in ("llm", "agent", "parameter-extractor", "question-classifier"):
            model = data.get("model", {}) if isinstance(data.get("model"), dict) else {}
            if not str(model.get("name", "") or "").strip():
                empty_models.append(str(n.get("id", "")))
    if empty_models:
        warnings.append(f"LLM-type node(s) with empty model name: {empty_models}")

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "findings": {"secrets": secrets, "dangling_refs": sorted(dangling), "empty_models": empty_models,
                     "node_count": len(nodes)},
    }


def retarget_dsl(document: dict, provider: str, model_name: str, mode: str = "") -> tuple[dict, int]:
    """Rewrite model provider+name across LLM/agent nodes and model_config.

    Returns (document, changed_count). Only touches nodes that already carry a
    ``data.model`` mapping (LLM-type nodes) plus a top-level ``model_config.model``
    (chat/completion apps). Does not invent model blocks where none exist.
    """
    changed = 0
    if not isinstance(document, dict):
        return document, 0

    def _apply(model_obj: dict) -> None:
        nonlocal changed
        if not isinstance(model_obj, dict):
            return
        model_obj["provider"] = provider
        model_obj["name"] = model_name
        if mode:
            model_obj["mode"] = mode
        changed += 1

    for n in _graph_nodes(document):
        data = n.get("data", {})
        if isinstance(data, dict) and isinstance(data.get("model"), dict):
            _apply(data["model"])

    # chat/completion apps store model under model_config.model
    mc = document.get("model_config", {})
    if isinstance(mc, dict) and isinstance(mc.get("model"), dict):
        _apply(mc["model"])

    return document, changed
