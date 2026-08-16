"""DSL version detection by probing live Dify instances.

Detects the authoritative DSL version used by a Dify instance via:
1) Console API /console/api/version (product version -> DSL mapping)
2) Exported app's top-level "version" field (true DSL version)

Version mappings derived from yzmw123/dify-workflow-dsl-skill:
- 1.16.x = 0.7.0 (Agent App v2)
- 1.15.x = 0.6.0 (workflow features + structured output stable)
- 1.13–1.14.x ≈ 0.5.x (pre-structured-output-stable; may need adjustment)

This module prioritizes (2) — exporting an existing app reads its actual DSL version.
Fallback to (1) for rough product-version heuristics when export is unavailable.
"""

from __future__ import annotations

import re
from typing import Any

from difyctl.console_api import ConsoleApiClient
from difyctl.dsl_authoring import DEFAULT_DSL_VERSION


def detect_dsl_version(
    client: ConsoleApiClient,
    *,
    app_id: str | None = None,
    fallback_mode: str = "auto",
) -> tuple[str, str]:
    """Detect the canonical DSL version for this Dify instance.

    Strategy (preferred -> fallback):
    1) If app_id provided: export that app and read `app.version` (authoritative).
    2) Query `/console/api/version` and use product-version heuristic table.

    Returns:
        (dsl_version, source) e.g. ("0.6.0", "export:app-xxx") or ("0.6.0", "version-api").
    """
    # Priority 1: export-based detection
    if app_id:
        try:
            export_resp = client.app_export_dsl(app_id)
            if isinstance(export_resp.payload, dict) and export_resp.payload.get("data"):
                import yaml as _yaml

                exported = _yaml.safe_load(export_resp.payload["data"])
                if isinstance(exported, dict):
                    version = str(exported.get("version", ""))
                    if version:
                        return version, f"export:{app_id}"
        except Exception:  # export failed, fall through
            pass

    # Priority 2: product-version heuristic (fallback_mode="auto" only)
    if fallback_mode == "auto":
        return _detect_by_product_version(client)

    raise RuntimeError(
        f"detect_dsl_version failed: no app_id or export succeeded; fallback_mode={fallback_mode}"
    )


# Product-version → DSL version heuristic table
PRODUCT_TO_DSL_MAP = {
    "1.16": "0.7.0",  # Agent App v2 support
    "1.15": "0.6.0",  # Workflow features stable
    "1.14": "0.5.x",  # Pre-structured-output stable (approximation)
    "1.13": "0.5.x",  # Target version per SKILL.md notes (approximation)
}


def _detect_by_product_version(client: ConsoleApiClient) -> tuple[str, str]:
    """Heuristic detection from product /console/api/version endpoint."""
    resp = client.get("/console/api/version")
    if not (isinstance(resp.payload, dict)):
        return DEFAULT_DSL_VERSION, "version-api-not-available"

    product_version = str(resp.payload.get("version", "")).strip()
    if not product_version:
        return DEFAULT_DSL_VERSION, "version-api-empty"

    # Extract major.minor (e.g., "1.13.0" → "1.13")
    match = re.match(r"^(\d+\.\d+)", product_version)
    if not match:
        return DEFAULT_DSL_VERSION, "version-api-format"

    key = match.group(1)
    known = PRODUCT_TO_DSL_MAP.get(key)
    if known and not known.endswith(".x"):
        return known, f"version-api:{key}"
    if known and known.endswith(".x"):
        # Uncertain .x suffix; default safely (older DSL usually more compatible with newer apps)
        return DEFAULT_DSL_VERSION, f"version-api:{key}(approx)"

    return DEFAULT_DSL_VERSION, f"version-api:unknown-{key}"
