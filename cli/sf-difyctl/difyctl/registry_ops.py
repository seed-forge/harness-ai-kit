from __future__ import annotations

from datetime import datetime
from pathlib import Path

import yaml


# ledger.yaml is the single source of truth (see fleet-platform/resources/dify/README.md).
# resources.yml is a read-only legacy fallback: if only it exists, its data is read and
# migrated to ledger.yaml on the next write.
LEDGER_FILENAME = "ledger.yaml"
LEGACY_REGISTRY_FILENAME = "resources.yml"

# v2 entry defaults (per naming spec). tags handled separately (mutable).
_V2_SCALAR_DEFAULTS = {
    "mode": "",
    "title": "",
    "app_id": "",
    "app_name": "",
    "dsl_path": "",
    "dsl_version": "",
    "status": "development",
    "updated_at": "",
}


def registry_path(workspace_root: Path) -> Path:
    """Write target is always the ledger.yaml (single source of truth)."""
    return workspace_root / LEDGER_FILENAME


def legacy_registry_path(workspace_root: Path) -> Path:
    return workspace_root / LEGACY_REGISTRY_FILENAME


def _source_path(workspace_root: Path) -> tuple[Path, bool]:
    """Resolve read source: ledger.yaml preferred; resources.yml legacy fallback.

    Returns (path, is_legacy). When neither exists, returns the ledger path.
    """
    ledger = registry_path(workspace_root)
    if ledger.exists():
        return ledger, False
    legacy = legacy_registry_path(workspace_root)
    if legacy.exists():
        return legacy, True
    return ledger, False


def registry_is_legacy_only(workspace_root: Path) -> bool:
    """True when ledger.yaml is absent but a legacy resources.yml exists."""
    return not registry_path(workspace_root).exists() and legacy_registry_path(workspace_root).exists()


def canonical_dsl_path(resource_id: str) -> str:
    """Canonical (file-form) dsl_path for a resource (O2)."""
    return f"resources/{resource_id}/dsl/current.yml"


def default_ledger_payload() -> dict[str, object]:
    return {
        "version": 2,
        "ledger_type": "dify-resource",
        "runtime_system": "",
        "maintainer": "",
        "resources": [],
    }


def _ensure_top_level(payload: dict[str, object]) -> dict[str, object]:
    """Ensure v2 top-level metadata keys exist without clobbering present values."""
    payload.setdefault("version", 2)
    payload.setdefault("ledger_type", "dify-resource")
    payload.setdefault("runtime_system", "")
    payload.setdefault("maintainer", "")
    payload.setdefault("resources", [])
    if not isinstance(payload["resources"], list):
        raise ValueError(f"{LEDGER_FILENAME} field `resources` must be a list")
    return payload


def load_registry(workspace_root: Path) -> dict[str, object]:
    path, _is_legacy = _source_path(workspace_root)
    if not path.exists():
        return default_ledger_payload()
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name} must be a mapping document")
    return _ensure_top_level(payload)


def save_registry(workspace_root: Path, payload: dict[str, object]) -> Path:
    # Always write ledger.yaml, merge-preserving whatever top-level metadata the
    # caller's payload carries (governance: never drop version/ledger_type/... ).
    path = registry_path(workspace_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(_ensure_top_level(payload), allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


def init_registry(workspace_root: Path, *, force: bool = False) -> Path:
    """Idempotent: if ledger.yaml exists, only ensure top-level metadata (no clobber).

    force=True rewrites a fresh empty v2 ledger.
    """
    path = registry_path(workspace_root)
    if path.exists() and not force:
        return save_registry(workspace_root, load_registry(workspace_root))
    return save_registry(workspace_root, default_ledger_payload())


def list_registry_resources(workspace_root: Path) -> list[dict[str, object]]:
    payload = load_registry(workspace_root)
    return [item for item in payload.get("resources", []) if isinstance(item, dict)]


def get_registry_resource(workspace_root: Path, resource_id: str) -> dict[str, object] | None:
    for item in list_registry_resources(workspace_root):
        if str(item.get("resource_id", "")).strip() == resource_id:
            return item
    return None


def _normalize_entry(entry: dict[str, object], existing: dict[str, object] | None = None) -> dict[str, object]:
    """Merge `entry` over `existing` (entry wins for provided keys), then fill v2 defaults.

    Merge-on-upsert preserves fields the caller did not supply (e.g. dsl_version,
    status) instead of wholesale-replacing the entry.
    """
    merged: dict[str, object] = dict(existing or {})
    for key, value in entry.items():
        merged[key] = value
    for key, default in _V2_SCALAR_DEFAULTS.items():
        merged.setdefault(key, default)
    if "tags" not in merged or merged.get("tags") is None:
        merged["tags"] = []
    if not str(merged.get("updated_at") or "").strip():
        merged["updated_at"] = datetime.now().strftime("%Y-%m-%d")
    return merged


def upsert_registry_resource(workspace_root: Path, entry: dict[str, object]) -> Path:
    payload = load_registry(workspace_root)
    resources = [item for item in payload.get("resources", []) if isinstance(item, dict)]
    target_id = str(entry.get("resource_id", "")).strip()
    if not target_id:
        raise ValueError("registry entry requires resource_id")
    replaced = False
    for index, item in enumerate(resources):
        if str(item.get("resource_id", "")).strip() == target_id:
            resources[index] = _normalize_entry(entry, existing=item)
            replaced = True
            break
    if not replaced:
        resources.append(_normalize_entry(entry))
    payload["resources"] = resources
    return save_registry(workspace_root, payload)


def audit_against_live(ledger_entries: list[dict[str, object]], live_apps: list[dict[str, object]]) -> dict[str, object]:
    """Compare ledger entries against live apps. Pure function (no I/O) for testability.

    - zombies: ledger entries whose app_id is absent from live apps.
    - unregistered: live apps whose id is not tracked in the ledger.
    - drift: app_id present in both but display name differs.
    """
    live_by_id = {str(a.get("id", "")): a for a in live_apps if isinstance(a, dict) and a.get("id")}
    tracked_ids: set[str] = set()
    zombies: list[dict[str, object]] = []
    drift: list[dict[str, object]] = []
    for entry in ledger_entries:
        app_id = str(entry.get("app_id", "") or "")
        if not app_id:
            continue
        tracked_ids.add(app_id)
        if app_id not in live_by_id:
            zombies.append({"resource_id": entry.get("resource_id"), "app_id": app_id})
            continue
        live_name = str(live_by_id[app_id].get("name", "") or "")
        ledger_name = str(entry.get("app_name", "") or entry.get("title", "") or "")
        if live_name and ledger_name and live_name != ledger_name:
            drift.append({"resource_id": entry.get("resource_id"), "app_id": app_id, "ledger_name": ledger_name, "live_name": live_name})
    unregistered = [
        {"app_id": app_id, "name": str(app.get("name", "") or "")}
        for app_id, app in live_by_id.items()
        if app_id not in tracked_ids
    ]
    # Duplicate live app names (same display name across >1 live app) — the
    # symptom of missing import dedup. Grouped {name: [app_id, ...]}.
    _by_name: dict[str, list[str]] = {}
    for app_id, app in live_by_id.items():
        nm = str(app.get("name", "") or "")
        if nm:
            _by_name.setdefault(nm, []).append(app_id)
    duplicate_names = [{"name": nm, "count": len(ids), "app_ids": ids} for nm, ids in _by_name.items() if len(ids) > 1]
    duplicate_names.sort(key=lambda d: -d["count"])
    return {
        "zombies": zombies,
        "unregistered": unregistered,
        "drift": drift,
        "duplicate_names": duplicate_names,
        "counts": {
            "ledger": len([e for e in ledger_entries if str(e.get("app_id", "") or "")]),
            "live": len(live_by_id),
            "zombies": len(zombies),
            "unregistered": len(unregistered),
            "drift": len(drift),
            "duplicate_names": len(duplicate_names),
        },
    }


def find_live_apps_by_name(live_apps: list[dict[str, object]], name: str) -> list[str]:
    """Return app_ids of live apps whose display name equals ``name`` (exact)."""
    target = str(name or "").strip()
    if not target:
        return []
    return [str(a.get("id", "")) for a in live_apps if isinstance(a, dict) and str(a.get("name", "") or "").strip() == target and a.get("id")]


def batch_filter(
    entries: list[dict[str, object]],
    *,
    mode: str = "",
    tag: str = "",
    selector: str = "",
) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for item in entries:
        item_mode = str(item.get("mode", "")).strip()
        item_id = str(item.get("resource_id", "")).strip()
        item_title = str(item.get("title", "")).strip()
        tags = item.get("tags", [])
        normalized_tags = [str(tag_item).strip() for tag_item in tags] if isinstance(tags, list) else []
        if mode and item_mode != mode:
            continue
        if tag and tag not in normalized_tags:
            continue
        if selector and selector not in item_id and selector not in item_title:
            continue
        results.append(item)
    return results
