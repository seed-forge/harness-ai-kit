"""Validate command handler and repo validation logic."""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from harness_ai_kit import package_manager as pm
from harness_ai_kit.domain import report_presentation
from harness_ai_kit.domain.models.constants import ASSET_DIRECTORY_NAMES, MANAGED_ASSET_TYPES
from harness_ai_kit.domain.models.constants import LOOP_ID_RE
from harness_ai_kit.domain.inventory import (
    iter_cli_dirs,
    iter_managed_asset_dirs,
    load_cli_record,
)
from harness_ai_kit.domain.loop_manifest import load_loop_manifest_file
from harness_ai_kit.domain.loop_profile import load_profile_config_file
from harness_ai_kit.domain.validation import (
    validate_cli_companion_docs,
    validate_cli_portability,
    validate_companion_docs,
    validate_asset_portability,
)
from harness_ai_kit.domain.doctor_checks import (
    check_namespace_conventions,
    doctor_versions_results,
)
from harness_ai_kit.domain.report_presentation import format_table
from harness_ai_kit.domain.versions import spec_matches_version
from harness_ai_kit.infrastructure.config_io import (
    load_config,
    repo_looks_valid,
    resolve_repo_root,
)


# These identify concrete scheduler runners, rather than generic scheduling
# concepts such as cron expressions or external profile registration.
_RUNTIME_BOUND_SCHEDULER_PATTERNS = (
    re.compile(r"\bqoder-(?:agent|scheduled-agent|schedule-mcp)\b", re.IGNORECASE),
    re.compile(r"\bqoder\s+(?:schedule|scheduler)(?:\s+mcp)?\b", re.IGNORECASE),
    re.compile(r"\bqoder[^\n]{0,80}\b(?:scheduled-task|scheduler|schedule)\b", re.IGNORECASE),
    re.compile(r"\bschedule[-_]mcp\b", re.IGNORECASE),
    re.compile(r"\bmanage_scheduled_task\b", re.IGNORECASE),
    re.compile(r"\btasks\.v2\.json\b", re.IGNORECASE),
    re.compile(r"\bagentTurn\b", re.IGNORECASE),
    re.compile(r"\bharness-ai-kit\s+scheduler\b", re.IGNORECASE),
    re.compile(r"\bhermes[^\n]{0,80}\bcron\b", re.IGNORECASE),
    re.compile(r"\bcron[^\n]{0,80}\bhermes\b", re.IGNORECASE),
)


def _local_asset_versions(repo_root: Path) -> dict[tuple[str, str | None, str], str]:
    """Build the offline version index used for deterministic dependency checks."""
    versions: dict[tuple[str, str | None, str], str] = {}
    for asset_type in MANAGED_ASSET_TYPES:
        asset_root = repo_root / ASSET_DIRECTORY_NAMES[asset_type]
        for asset_dir in iter_managed_asset_dirs(asset_root):
            try:
                manifest = _load_asset_manifest(asset_type, asset_dir)
            except Exception:
                continue
            versions[(asset_type, manifest.namespace, manifest.id)] = manifest.version
    for cli_dir in iter_cli_dirs(repo_root / "cli"):
        try:
            record = load_cli_record(cli_dir)
        except Exception:
            continue
        versions[("cli", None, record.cli_id)] = record.version
    return versions


def _load_asset_manifest(asset_type: str, asset_dir: Path) -> Any:
    """Use the strict LoopManifest model for loop.json assets."""
    if asset_type == "loop":
        return load_loop_manifest_file(asset_dir / "loop.json")
    return pm.load_skill_manifest(asset_dir)


def _validate_local_dependency_versions(
    manifest: Any,
    local_versions: dict[tuple[str, str | None, str], str],
) -> list[str]:
    """Reject local dependency declarations that cannot resolve offline.

    Registry-only and git dependencies are intentionally skipped here; their
    source/registry checks belong to the resolver and doctor commands.
    """
    errors: list[str] = []
    for dependency in manifest.dependencies:
        if getattr(dependency, "source_url", None):
            continue
        dependency_type = str(dependency.type)
        dependency_id = str(dependency.id)
        namespace = getattr(dependency, "namespace", None)
        actual = local_versions.get((dependency_type, namespace, dependency_id))
        if actual is None and namespace is not None:
            actual = local_versions.get((dependency_type, None, dependency_id))
        if actual is None:
            continue
        specifier = str(dependency.version)
        if not spec_matches_version(specifier, actual):
            errors.append(
                f"{manifest.id}: local dependency {dependency_type}:{dependency_id} "
                f"declares {specifier}, but checkout provides {actual}"
            )
    return errors


def run_repo_validation(repo_root: Path) -> list[tuple[str, str, str]]:
    checks: list[tuple[str, str, str]] = []
    if not repo_looks_valid(repo_root):
        return [("repo", "error", f"Repository root is invalid: {repo_root}")]

    checks.append(("repo", "success", f"Repository root detected: {repo_root}"))
    local_versions = _local_asset_versions(repo_root)
    for asset_type in MANAGED_ASSET_TYPES:
        asset_root = repo_root / ASSET_DIRECTORY_NAMES[asset_type]
        for asset_dir in iter_managed_asset_dirs(asset_root):
            metadata_path = pm.manifest_metadata_path(asset_dir, asset_type)
            if not metadata_path.exists():
                checks.append((f"{asset_type}:{asset_dir.name}", "error", f"Missing {metadata_path.name}"))
                continue
            try:
                manifest = _load_asset_manifest(asset_type, asset_dir)
            except ValidationError as exc:
                checks.append((f"{asset_type}:{asset_dir.name}", "error", pm.manifest_validation_error(exc)))
                continue
            doc_errors = validate_companion_docs(asset_dir, manifest)
            portability_errors = validate_asset_portability(asset_dir)
            doc_errors.extend(portability_errors)
            doc_errors.extend(_validate_local_dependency_versions(manifest, local_versions))
            if doc_errors:
                for message in doc_errors:
                    checks.append((f"{asset_type}:{asset_dir.name}", "error", message))
                continue
            # plugin 资产专项门禁：plugin.json schema（package_type/hosts/dsh.bundle）
            if asset_type == "plugin":
                from harness_ai_kit.domain.plugin_assets import validate_plugin_metadata

                plugin_errors = validate_plugin_metadata(asset_dir)
                if plugin_errors:
                    for message in plugin_errors:
                        checks.append((f"plugin:{asset_dir.name}", "error", message))
                    continue
            # SKILL.md 正文 changelog 混入门禁（2026-08-15 文档分层规范）
            if asset_type == "skill":
                changelog_errors = _validate_skill_changelog_in_body(asset_dir, manifest)
                if changelog_errors:
                    for message in changelog_errors:
                        checks.append((f"skill:{asset_dir.name}", "error", message))
                    continue
            # loop 专属治理门禁（命名规范 + 定时台账必选）
            if asset_type == "loop":
                loop_errors = _validate_loop_governance(asset_dir)
                if loop_errors:
                    for message in loop_errors:
                        checks.append((f"loop:{asset_dir.name}", "error", message))
                    continue
            # config_schema 校验（Warning 级别，不阻塞）
            config_schema = getattr(manifest, "config_schema", None)
            if config_schema:
                config_file = asset_dir / config_schema
                if not config_file.exists():
                    checks.append((f"{asset_type}:{asset_dir.name}", "error", f"config_schema references '{config_schema}' but file not found"))
                else:
                    try:
                        import yaml
                        config_data = yaml.safe_load(config_file.read_text(encoding="utf-8"))
                        if isinstance(config_data, dict) and config_data.get("$schema") != "harness-ai-kit-config/v1":
                            checks.append((f"{asset_type}:{asset_dir.name}", "error", f"config_schema file has invalid $schema: expected 'harness-ai-kit-config/v1'"))
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
        doc_errors.extend(validate_cli_portability(cli_dir))
        if doc_errors:
            for message in doc_errors:
                checks.append((f"cli:{cli_dir.name}", "error", message))
            continue
        checks.append((f"cli:{cli_dir.name}", "success", "Metadata and companion docs look valid"))
    # namespace 治理门禁（2026-08-16 统一 team/ 后生效）：内部资产必须归入 team/，对外用 public/
    for item in check_namespace_conventions(repo_root):
        checks.append((item["subject"], item["status"], item["message"]))
    return checks


def _validate_skill_changelog_in_body(asset_dir: Path, manifest: Any) -> list[str]:
    """SKILL.md 正文 changelog 混入门禁：正文禁止 changelog 章节（文档分层规范）。"""
    errors: list[str] = []
    entry = asset_dir / str(getattr(manifest, "entry", "SKILL.md"))
    if not entry.exists():
        return errors
    text = entry.read_text(encoding="utf-8", errors="replace")
    # strip YAML frontmatter
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            text = parts[2]
    changelog_heading = re.search(
        r"(?m)^##\s*(?:变更记录|更新历史|版本历史|Changelog|CHANGELOG|演进记录)\s*$",
        text,
    )
    if changelog_heading:
        errors.append(
            f"{asset_dir.name}: SKILL.md 正文禁止 changelog 章节（文档分层规范），"
            "变更史应收敛到 CHANGELOG.md（例外：tombstone 横幅 / 一行改名声明）"
        )
    return errors


def _validate_loop_governance(asset_dir: Path) -> list[str]:
    """Enforce portable Loop manifests and external scheduler profiles."""
    errors: list[str] = []
    try:
        manifest_path = asset_dir / "loop.json"
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return errors
    loop_id = str(data.get("id", ""))
    if not LOOP_ID_RE.fullmatch(loop_id):
        errors.append(
            f"{asset_dir.name}: loop id `{loop_id}` 不符合命名规范 "
            "`<domain>-<scenario>-loop`（域白名单: homelab/infra/devlab/cnt/fin/base/harness-ai-kit）"
        )
    try:
        load_loop_manifest_file(manifest_path)
    except Exception as exc:
        errors.append(f"{asset_dir.name}: loop.json schema invalid: {exc}")

    if (asset_dir / "schedule-ledger.yaml").exists():
        errors.append(
            f"{asset_dir.name}: schedule-ledger.yaml is retired; use execution-ledger.yaml "
            "for execution history and profiles/*.yaml for scheduling."
        )

    for path in asset_dir.rglob("*"):
        if not path.is_file() or path.name in {"CHANGELOG.md", "execution-ledger.yaml", ".publish-lag.json"}:
            continue
        if path.suffix.lower() not in {".json", ".md", ".yaml", ".yml", ".py", ".ps1", ".sh"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if any(pattern.search(text) for pattern in _RUNTIME_BOUND_SCHEDULER_PATTERNS):
            errors.append(
                f"{asset_dir.name}: runtime-specific scheduler/agent reference in "
                f"{path.relative_to(asset_dir).as_posix()}"
            )

    profile_paths = sorted(
        path
        for pattern in ("profiles/*.yaml", "profiles/*.yml", "profiles/*.json")
        for path in asset_dir.glob(pattern)
    )
    loop_version = str(data.get("version", ""))
    for profile_path in profile_paths:
        try:
            profile = load_profile_config_file(profile_path)
        except Exception as exc:
            errors.append(
                f"{asset_dir.name}: invalid scheduler profile "
                f"{profile_path.relative_to(asset_dir).as_posix()}: {exc}"
            )
            continue
        if profile.loop.id != loop_id:
            errors.append(
                f"{asset_dir.name}: profile {profile_path.name} targets "
                f"{profile.loop.id}, expected {loop_id}"
            )
        if profile.loop.version != loop_version:
            errors.append(
                f"{asset_dir.name}: profile {profile_path.name} pins loop version "
                f"{profile.loop.version}, expected {loop_version}"
            )
    return errors




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
