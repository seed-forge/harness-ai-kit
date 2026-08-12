"""Predicate evaluator for stop conditions."""
from __future__ import annotations

import re
from typing import Any

_PREDICATE_PATTERN = re.compile(
    r"^([a-z_][a-z0-9_]*)\s*(==|!=|>=|<=|<|>|contains|matches)\s*(.+)$",
    re.IGNORECASE,
)


def _eval_predicate(predicate: str, metrics: dict[str, Any]) -> bool:
    """Evaluate a simple predicate against a metrics dict.

    Supports: metric >= value, metric <= value, metric == value,
              metric != value, metric > value, metric < value.

    Returns False if metric is not found or predicate is malformed.
    """
    predicate = predicate.strip()
    m = _PREDICATE_PATTERN.match(predicate)
    if not m:
        return False

    metric_name = m.group(1).strip()
    operator = m.group(2).strip()
    try:
        threshold = float(m.group(3).strip())
    except (ValueError, TypeError):
        return False

    value = metrics.get(metric_name)
    if value is None:
        return False

    try:
        value = float(value)
    except (ValueError, TypeError):
        return False

    ops = {
        ">=": lambda a, b: a >= b,
        "<=": lambda a, b: a <= b,
        "==": lambda a, b: a == b,
        "!=": lambda a, b: a != b,
        ">": lambda a, b: a > b,
        "<": lambda a, b: a < b,
    }
    cmp_fn = ops.get(operator)
    if cmp_fn is None:
        return False

    return cmp_fn(value, threshold)
