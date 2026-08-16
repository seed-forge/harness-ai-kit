from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import yaml


RESOURCE_ROOT_NAME = "resources"
RESOURCE_METADATA_NAME = "resource.json"


@dataclass(frozen=True)
class ResourceRecord:
    resource_id: str
    mode: str
    title: str
    path: Path
    app_id: str
    app_name: str
    tags: tuple[str, ...]
    updated_at: str


# Authoritative resource_id format (see fleet-platform/resources/dify/README.md
# "资源命名规范"). kebab-case, lowercase-alpha start, 3-50 chars.
RESOURCE_ID_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
RESOURCE_ID_MIN = 3
RESOURCE_ID_MAX = 50


def validate_resource_id(resource_id: str) -> str:
    """Validate a resource_id against the naming spec; return it unchanged or raise.

    Rule: `^[a-z][a-z0-9]*(-[a-z0-9]+)*$`, length 3-50. See the authoritative
    naming spec in fleet-platform/resources/dify/README.md (资源命名规范).
    """
    rid = (resource_id or "").strip()
    hint = (
        "resource_id must be kebab-case matching ^[a-z][a-z0-9]*(-[a-z0-9]+)*$ "
        f"(len {RESOURCE_ID_MIN}-{RESOURCE_ID_MAX}); domain/type goes in tags, not a prefix. "
        "See fleet-platform/resources/dify/README.md 资源命名规范."
    )
    if not rid:
        raise ValueError(f"resource_id is required. {hint}")
    if not (RESOURCE_ID_MIN <= len(rid) <= RESOURCE_ID_MAX):
        raise ValueError(f"resource_id '{rid}' length must be {RESOURCE_ID_MIN}-{RESOURCE_ID_MAX}. {hint}")
    if not RESOURCE_ID_RE.match(rid):
        raise ValueError(f"resource_id '{rid}' is invalid. {hint}")
    return rid


def derive_resource_id(name: str) -> str:
    """Best-effort derive a spec-compliant resource_id from a display name.

    Lowercases, replaces non-alnum runs with '-', trims, collapses. The result
    is NOT guaranteed valid (e.g. too short / leading digit) — callers must run
    validate_resource_id and fall back to an explicit --resource-id on failure.
    """
    lowered = (name or "").strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return slug


def slugify_label(label: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-z._-]+", "-", label.strip())
    cleaned = cleaned.strip("-")
    return cleaned or "snapshot"


def load_structured_file(path: Path) -> dict[str, object]:
    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8")
    if suffix == ".json":
        payload = json.loads(text)
    else:
        payload = yaml.safe_load(text)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a mapping document in {path}")
    return payload


def summarize_dsl(path: Path) -> dict[str, object]:
    payload = load_structured_file(path)
    app_section = payload.get("app", {}) if isinstance(payload.get("app"), dict) else {}
    workflow_section = payload.get("workflow", {}) if isinstance(payload.get("workflow"), dict) else {}
    graph_section = workflow_section.get("graph", {}) if isinstance(workflow_section.get("graph"), dict) else {}
    if not graph_section and isinstance(payload.get("graph"), dict):
        graph_section = payload.get("graph", {})

    nodes = graph_section.get("nodes", []) if isinstance(graph_section.get("nodes"), list) else []
    edges = graph_section.get("edges", []) if isinstance(graph_section.get("edges"), list) else []
    return {
        "path": str(path),
        "mode": payload.get("kind") or app_section.get("mode") or payload.get("mode") or "",
        "name": app_section.get("name") or payload.get("name") or path.stem,
        "description": app_section.get("description") or payload.get("description") or "",
        "node_count": len(nodes),
        "edge_count": len(edges),
        "top_level_keys": sorted(payload.keys()),
    }


def workspace_root(workspace_dir: str) -> Path:
    if not workspace_dir:
        raise ValueError("workspace_dir is empty")
    return Path(workspace_dir).expanduser().resolve()


def resource_dir(root: Path, resource_id: str) -> Path:
    return root / RESOURCE_ROOT_NAME / resource_id


def metadata_path(resource_root: Path) -> Path:
    return resource_root / RESOURCE_METADATA_NAME


def read_resource(resource_root: Path) -> ResourceRecord:
    payload = json.loads(metadata_path(resource_root).read_text(encoding="utf-8"))
    return ResourceRecord(
        resource_id=payload["resource_id"],
        mode=payload.get("mode", ""),
        title=payload.get("title", ""),
        path=resource_root,
        app_id=payload.get("app_id", ""),
        app_name=payload.get("app_name", ""),
        tags=tuple(payload.get("tags", [])),
        updated_at=payload.get("updated_at", ""),
    )


def write_resource_metadata(
    resource_root: Path,
    *,
    resource_id: str,
    mode: str,
    title: str,
    app_id: str,
    app_name: str,
    tags: list[str],
) -> ResourceRecord:
    now = datetime.now().isoformat(timespec="seconds")
    payload = {
        "resource_id": resource_id,
        "mode": mode,
        "title": title,
        "app_id": app_id,
        "app_name": app_name,
        "tags": tags,
        "updated_at": now,
    }
    metadata_path(resource_root).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return read_resource(resource_root)


def ensure_resource(
    root: Path,
    *,
    resource_id: str,
    mode: str,
    title: str,
    app_id: str,
    app_name: str,
    tags: list[str],
) -> ResourceRecord:
    target = resource_dir(root, resource_id)
    dsl_dir = target / "dsl"
    snapshot_dir = dsl_dir / "snapshots"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    readme_path = target / "README.md"
    if not readme_path.exists():
        readme_path.write_text(
            "\n".join(
                [
                    f"# {title or resource_id}",
                    "",
                    f"- resource_id: `{resource_id}`",
                    f"- mode: `{mode}`",
                    f"- app_id: `{app_id}`",
                    f"- app_name: `{app_name}`",
                    "",
                    "## Notes",
                    "",
                    "- Capture exported Dify DSL snapshots under `dsl/snapshots/`.",
                    "- Keep the promoted current DSL at `dsl/current.*`.",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
    return write_resource_metadata(
        target,
        resource_id=resource_id,
        mode=mode,
        title=title or resource_id,
        app_id=app_id,
        app_name=app_name,
        tags=tags,
    )


def capture_dsl(root: Path, resource_id: str, dsl_path: Path, *, label: str = "", promote: bool = True) -> dict[str, str]:
    if not dsl_path.exists():
        raise FileNotFoundError(f"DSL file not found: {dsl_path}")
    target = resource_dir(root, resource_id)
    if not target.exists():
        raise FileNotFoundError(f"Resource not found: {resource_id}")
    dsl_dir = target / "dsl"
    snapshots_dir = dsl_dir / "snapshots"
    snapshots_dir.mkdir(parents=True, exist_ok=True)

    ext = dsl_path.suffix or ".yml"
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    label_part = f"-{slugify_label(label)}" if label else ""
    snapshot_path = snapshots_dir / f"{stamp}{label_part}{ext}"
    snapshot_path.write_text(dsl_path.read_text(encoding="utf-8"), encoding="utf-8")

    current_path = dsl_dir / f"current{ext}"
    if promote:
        current_path.write_text(dsl_path.read_text(encoding="utf-8"), encoding="utf-8")

    return {
        "snapshot_path": str(snapshot_path),
        "current_path": str(current_path) if promote else "",
    }


def scan_resources(root: Path) -> list[ResourceRecord]:
    resources_root = root / RESOURCE_ROOT_NAME
    if not resources_root.exists():
        return []
    records: list[ResourceRecord] = []
    for child in sorted(resources_root.iterdir()):
        if not child.is_dir():
            continue
        meta = metadata_path(child)
        if not meta.exists():
            continue
        records.append(read_resource(child))
    return records

