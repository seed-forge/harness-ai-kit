"""Validate command handler and repo validation logic."""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from ai_kit import package_manager as pm
from ai_kit.domain import report_presentation
from ai_kit.domain.models.constants import ASSET_DIRECTORY_NAMES, MANAGED_ASSET_TYPES
from ai_kit.domain.inventory import (
    iter_cli_dirs,
    iter_managed_asset_dirs,
    load_cli_record,
)
from ai_kit.domain.validation import (
    validate_cli_companion_docs,
    validate_companion_docs,
)
from ai_kit.domain.doctor_checks import doctor_versions_results
from ai_kit.domain.report_presentation import format_table
from ai_kit.infrastructure.config_io import (
    load_config,
    repo_looks_valid,
    resolve_repo_root,
)


def run_repo_validation(repo_root: Path) -> list[tuple[str, str, str]]:
    checks: list[tuple[str, str, str]] = []
    if not repo_looks_valid(repo_root):
        return [("repo", "error", f"Repository root is invalid: {repo_root}")]

    checks.append(("repo", "success", f"Repository root detected: {repo_root}"))
    for asset_type in MANAGED_ASSET_TYPES:
        asset_root = repo_root / ASSET_DIRECTORY_NAMES[asset_type]
        for asset_dir in iter_managed_asset_dirs(asset_root):
            metadata_path = pm.manifest_metadata_path(asset_dir, asset_type)
            if not metadata_path.exists():
                checks.append((f"{asset_type}:{asset_dir.name}", "error", f"Missing {metadata_path.name}"))
                continue
            try:
                manifest = pm.load_skill_manifest(asset_dir)
            except ValidationError as exc:
                checks.append((f"{asset_type}:{asset_dir.name}", "error", pm.manifest_validation_error(exc)))
                continue
            doc_errors = validate_companion_docs(asset_dir, manifest)
            if doc_errors:
                for message in doc_errors:
                    checks.append((f"{asset_type}:{asset_dir.name}", "error", message))
                continue
            # config_schema 校验（Warning 级别，不阻塞）
            if manifest.config_schema:
                config_file = asset_dir / manifest.config_schema
                if not config_file.exists():
                    checks.append((f"{asset_type}:{asset_dir.name}", "error", f"config_schema references '{manifest.config_schema}' but file not found"))
                else:
                    try:
                        import yaml
                        config_data = yaml.safe_load(config_file.read_text(encoding="utf-8"))
                        if isinstance(config_data, dict) and config_data.get("$schema") != "ai-kit-config/v1":
                            checks.append((f"{asset_type}:{asset_dir.name}", "error", f"config_schema file has invalid $schema: expected 'ai-kit-config/v1'"))
                    except Exception:
                        pass  # YAML parse errors are non-blocking for now
            checks.append((f"{asset_type}:{asset_dir.name}", "success", "Metadata and companion docs look valid"))
    for cli_dir in iter_cli_dirs(repo_root / "cli"):
        try:
            load_cli_record(cli_dir)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            checks.append((f"cli:{cli_dir.name}", "error", f"Invalid cli.json: {exc}"))
            continue
        doc_errors = validate_cli_companion_docs(cli_dir)
        if doc_errors:
            for message in doc_errors:
                checks.append((f"cli:{cli_dir.name}", "error", message))
            continue
        checks.append((f"cli:{cli_dir.name}", "success", "Metadata and companion docs look valid"))
    return checks




def command_validate(args: argparse.Namespace, config_path: Path) -> int:
    config = load_config(config_path)
    repo_root = resolve_repo_root(getattr(args, "repo_root", None), config)
    repo_results = run_repo_validation(repo_root)
    version_results = doctor_versions_results(repo_root)
    results = repo_results + [
        (item["subject"], item["status"], item["message"])
        for item in version_results
    ]
    has_error = any(status == "error" for _, status, _ in results)

    if args.json:
        payload = report_presentation.validation_payload(results)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_table(("SUBJECT", "STATUS", "MESSAGE"), results))
        for line in report_presentation.validation_summary_lines(has_error=has_error):
            print(line)
    return 1 if has_error else 0


