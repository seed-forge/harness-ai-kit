from __future__ import annotations

from pathlib import Path


def build_create_plan(*, base_url: str, name: str, mode: str, description: str = "", dsl_path: str = "") -> dict[str, object]:
    steps = [
        "Open Dify Studio.",
        "Choose create app.",
        f"Select mode `{mode}`.",
        f"Fill name `{name}`.",
    ]
    if description:
        steps.append("Fill the description field.")
    if dsl_path:
        steps = [
            "Open Dify Studio.",
            "Choose import DSL file.",
            f"Upload `{dsl_path}`.",
            "Finish version compatibility confirmation if prompted.",
        ]
    return {
        "base_url": base_url,
        "operation": "create" if not dsl_path else "import-dsl",
        "name": name,
        "mode": mode,
        "description": description,
        "dsl_path": dsl_path,
        "steps": steps,
    }


def build_export_plan(*, base_url: str, resource_id: str, app_name: str = "", app_id: str = "") -> dict[str, object]:
    return {
        "base_url": base_url,
        "operation": "export-dsl",
        "resource_id": resource_id,
        "app_name": app_name,
        "app_id": app_id,
        "steps": [
            "Open Dify Studio.",
            "Locate the target application on the Studio page.",
            "Open the application menu or orchestration page.",
            "Click Export DSL.",
            "Save the exported YML file into the local resource workspace.",
        ],
    }


def build_duplicate_plan(*, base_url: str, resource_id: str, app_name: str = "", app_id: str = "") -> dict[str, object]:
    return {
        "base_url": base_url,
        "operation": "duplicate",
        "resource_id": resource_id,
        "app_name": app_name,
        "app_id": app_id,
        "steps": [
            "Open Dify Studio.",
            "Locate the target application.",
            "Open the application page.",
            "Click Duplicate.",
            "Rename the duplicated application if needed.",
        ],
    }
