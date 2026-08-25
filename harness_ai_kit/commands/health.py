from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class HealthCommandContext:
    runtime_profiles: Mapping[str, Any]
    format_table: Callable[[tuple[str, ...], list[tuple[str, ...]]], str]
    report_presentation: Any
    load_config: Callable[[Path], Any]
    effective_config: Callable[[Any], Any]
    resolve_repo_root: Callable[[str | None, Any], Path]
    installed_skill_locations: Callable[[Path | None, str], list[tuple[str, Path]]]
    installed_skill_ids: Callable[[Path, str], list[str]]
    manual_invocation_hint: Callable[[str, str], str]
    skill_install_state: Callable[[Any, Path | None], Any]
    skill_record_factory: Callable[..., Any]
    doctor_versions_results: Callable[[Path], list[dict[str, str]]]
    doctor_drift_results: Callable[[Path, Any], list[dict[str, str]]]
    doctor_sources_payload: Callable[[Any, str | None, str | None], dict[str, Any]]
    doctor_env_results: Callable[[Path], list[dict[str, str]]]
    doctor_assets_results: Callable[[Path], list[dict[str, str]]]
    load_managed_asset_inventory: Callable[[Path, str], dict[str, Any]]
    managed_asset_install_state: Callable[[Any, Path | None], Any]
    managed_asset_types: tuple[str, ...]
    current_cli_versions: Callable[[Path | None, Any | None], dict[str, str]]
    pm: Any
    git_available: Callable[[], bool]
    python_module_available: Callable[[str], bool]
    run_repo_validation: Callable[[Path], list[tuple[str, str, str]]]
    doctor_extends_results: Callable[[Path, Any, Path | None], list[dict[str, str]]]


def build_health_handlers(context: HealthCommandContext) -> Mapping[str, Callable[[argparse.Namespace, Path], int]]:
    return {
        "doctor": lambda args, config_path: command_doctor(args, config_path, context),
        "validate": lambda args, config_path: command_validate(args, config_path, context),
    }


def _check_skill_registry_index(config: Any) -> dict[str, str]:
    """Validate skill registry index URL is reachable and returns skills."""
    url = getattr(config, "skill_registry_index_url", "") or ""
    if not url:
        return {"check": "skill-registry-index", "status": "warning", "message": "No skill_registry_index_url configured"}
    try:
        import httpx
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            resp = client.get(url)
        if resp.status_code != 200:
            return {"check": "skill-registry-index", "status": "error", "message": f"HTTP {resp.status_code} from {url}"}
        data = resp.json()
        count = len(data.get("skills", []))
        if count == 0:
            return {
                "check": "skill-registry-index",
                "status": "error",
                "message": f"Registry returned 0 skills — URL may be wrong. Current: {url} | Expected: .../raw-hosted-skill/index.json",
            }
        return {"check": "skill-registry-index", "status": "success", "message": f"Registry index OK ({count} skills)"}
    except Exception as exc:
        return {"check": "skill-registry-index", "status": "error", "message": f"Cannot reach registry: {exc}"}


def command_doctor(args: argparse.Namespace, config_path: Path, context: HealthCommandContext) -> int:
    # Handle --check-bindings flag
    if getattr(args, "check_bindings", False):
        from harness_ai_kit.domain.doctor_checks import check_bindings
        from pathlib import Path
        results = check_bindings(Path.cwd())
        has_error = any(item["status"] == "error" for item in results)
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            rows = [(item["subject"], item["status"], item["message"]) for item in results]
            print(context.format_table(("SUBJECT", "STATUS", "MESSAGE"), rows))
            if has_error:
                print("❌ 绑定检查发现错误")
            else:
                print("✅ 所有绑定检查通过")
        return 1 if has_error else 0

    if getattr(args, "subject", "") == "dsh":
        from harness_ai_kit.domain.doctor_checks import DSH_BASELINE_VERSION, doctor_dsh_results

        results = doctor_dsh_results()
        has_error = any(item["status"] == "error" for item in results)
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            rows = [(item["subject"], item["status"], item["message"]) for item in results]
            print(context.format_table(("SUBJECT", "STATUS", "MESSAGE"), rows))
            print(f"Baseline: dsh {DSH_BASELINE_VERSION} / pnpm >=10 (see docs/dsh-integration.md)")
            print("[ERROR] dsh 环境检查发现错误" if has_error else "[OK] dsh 环境检查完成")
        return 1 if has_error else 0

    if getattr(args, "subject", "") == "pi":
        from harness_ai_kit.domain.doctor_checks import doctor_pi_results

        config = context.load_config(config_path)
        effective = context.effective_config(config) if hasattr(context, "effective_config") else config
        results = doctor_pi_results(config=effective)
        has_error = any(item["status"] == "error" for item in results)
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            rows = [(item["subject"], item["status"], item["message"]) for item in results]
            print(context.format_table(("SUBJECT", "STATUS", "MESSAGE"), rows))
            print("Baseline: pi (no pinned version) + configured npm registry (see docs/pi-integration.md)")
            print("[ERROR] pi 环境检查发现错误" if has_error else "[OK] pi 环境检查完成")
        return 1 if has_error else 0

    if getattr(args, "subject", "") == "runtimes":
        profiles = list(context.runtime_profiles.values())
        if args.json:
            payload = [
                {
                    "runtime": profile.runtime_id,
                    "name": profile.display_name,
                    "status": profile.status,
                    "project_target": profile.project_target or "",
                    "global_target": profile.global_target or "",
                    "notes": profile.notes,
                }
                for profile in profiles
            ]
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            rows = [
                (
                    profile.runtime_id,
                    profile.status,
                    profile.project_target or "-",
                    profile.global_target or "-",
                    profile.notes,
                )
                for profile in profiles
            ]
            print(context.format_table(("RUNTIME", "STATUS", "PROJECT TARGET", "GLOBAL TARGET", "NOTES"), rows))
            print(context.report_presentation.doctor_runtimes_next_line())
        return 0

    if getattr(args, "subject", "") == "skills":
        config = context.load_config(config_path)
        try:
            repo_root = context.resolve_repo_root(getattr(args, "repo_root", None), config)
        except FileNotFoundError:
            repo_root = None
        runtime_id = getattr(args, "runtime", "codex")
        locations = context.installed_skill_locations(repo_root, runtime_id)
        payload = []
        for scope_name, path in locations:
            skills = context.installed_skill_ids(path, runtime_id)
            payload.append(
                {
                    "scope": scope_name,
                    "path": str(path),
                    "exists": path.exists(),
                    "skills": skills,
                    "invocation_hint": context.manual_invocation_hint(runtime_id, skills[0]) if skills else "",
                }
            )
        discovered_rows: list[tuple[str, str, str, str, str]] = []
        discovered_payload: list[dict[str, str]] = []
        for skill_id in sorted({skill_id for item in payload for skill_id in item["skills"]}):
            state = context.skill_install_state(
                context.skill_record_factory(
                    skill_id=skill_id,
                    path=None,
                    name=skill_id,
                    status="unknown",
                    owner="",
                    version="",
                    summary="",
                    asset_type="skill",
                    source="installed",
                ),
                repo_root,
            )
            for item in state.installed_locations:
                if item.runtime != runtime_id:
                    continue
                discovered_rows.append((skill_id, item.scope, item.version or "-", item.drift_status, item.path.as_posix()))
                discovered_payload.append(
                    {
                        "id": skill_id,
                        "scope": item.scope,
                        "version": item.version,
                        "drift_status": item.drift_status,
                        "drift_message": item.drift_message,
                        "path": str(item.path),
                    }
                )
        if args.json:
            print(json.dumps({"runtime": runtime_id, "locations": payload, "skills": discovered_payload}, ensure_ascii=False, indent=2))
        else:
            rows = [(item["scope"], "yes" if item["exists"] else "no", str(len(item["skills"])), item["path"]) for item in payload]
            print(context.format_table(("SCOPE", "EXISTS", "SKILL COUNT", "PATH"), rows))
            installed = sorted({skill_id for item in payload for skill_id in item["skills"]})
            if installed:
                print(context.report_presentation.doctor_skills_discovered_line(skill_ids=installed))
                print("")
                print(context.format_table(("SKILL", "SCOPE", "VERSION", "DRIFT", "PATH"), discovered_rows))
                print(context.report_presentation.doctor_skills_hint_line(invocation_hint=context.manual_invocation_hint(runtime_id, installed[0])))
            else:
                print(context.report_presentation.doctor_skills_empty_line())
            if runtime_id == "codex":
                for line in context.report_presentation.doctor_skills_codex_note_lines():
                    print(line)
        return 0

    if getattr(args, "subject", "") == "versions":
        config = context.effective_config(context.load_config(config_path))
        repo_root = context.resolve_repo_root(getattr(args, "repo_root", None), config)
        results = context.doctor_versions_results(repo_root)
        has_error = any(item["status"] == "error" for item in results)
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            rows = [(item["subject"], item["status"], item["message"]) for item in results]
            print(context.format_table(("SUBJECT", "STATUS", "MESSAGE"), rows))
            print(context.report_presentation.doctor_versions_summary_line(has_error=has_error))
        return 1 if has_error else 0

    if getattr(args, "subject", "") == "drift":
        config = context.effective_config(context.load_config(config_path))
        repo_root = context.resolve_repo_root(getattr(args, "repo_root", None), config)
        results = context.doctor_drift_results(repo_root, config)
        has_error = any(item["status"] == "error" for item in results)
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            rows = [(item["subject"], item["status"], item["message"]) for item in results]
            print(context.format_table(("SUBJECT", "STATUS", "MESSAGE"), rows))
            print(context.report_presentation.doctor_drift_summary_line(has_error=has_error))
        return 1 if has_error else 0

    if getattr(args, "subject", "") == "sources":
        config = context.effective_config(context.load_config(config_path))
        payload = context.doctor_sources_payload(config, getattr(args, "repo_root", None), getattr(args, "target_dir", None))
        has_error = bool(payload["errors"])
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"Manifest: {'yes' if payload['manifest_found'] else 'no'}")
            if payload["manifest_path"]:
                print(f"Manifest path: {payload['manifest_path']}")
            print(f"Lockfile: {'yes' if payload['lock_found'] else 'no'}")
            if payload["lock_path"]:
                print(f"Lock path: {payload['lock_path']}")
            print(f"Runtime: {payload['runtime']}")
            print(f"Scope: {payload['scope']}")
            print(f"Features: {', '.join(payload['features']) if payload['features'] else '-'}")
            roots = payload["roots"]
            if roots:
                rows = context.report_presentation.doctor_sources_root_rows(roots)
                print(context.format_table(("ROOT", "REPO", "REGISTRY", "SELECTED SOURCE", "SELECTED VERSION", "REASON"), rows))
            else:
                print(context.report_presentation.doctor_sources_empty_roots_line())
            for warning in payload["warnings"]:
                print(context.report_presentation.doctor_sources_warning_line(warning=warning))
            for error in payload["errors"]:
                print(context.report_presentation.doctor_sources_error_line(error=error))
            if not payload["errors"]:
                print(context.report_presentation.doctor_sources_success_hint_line())
        return 1 if has_error else 0

    if getattr(args, "subject", "") == "env":
        config = context.effective_config(context.load_config(config_path))
        repo_root = context.resolve_repo_root(getattr(args, "repo_root", None), config)
        results = context.doctor_env_results(repo_root)
        has_error = any(item["status"] == "error" for item in results)
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            print(context.format_table(("SUBJECT", "STATUS", "MESSAGE"), context.report_presentation.result_rows(results)))
        return 1 if has_error else 0

    if getattr(args, "subject", "") == "assets":
        config = context.effective_config(context.load_config(config_path))
        repo_root = context.resolve_repo_root(getattr(args, "repo_root", None), config)
        results = context.doctor_assets_results(repo_root)
        for asset_type in ("plugin", "hook", "subagent", "mcp", "loop"):
            inventory = context.load_managed_asset_inventory(repo_root, asset_type)
            for record in inventory.values():
                state = context.managed_asset_install_state(record, repo_root)
                results.append(
                    {
                        "subject": f"{asset_type}:{record.skill_id}:drift",
                        "status": "success" if state.drift_status == "up-to-date" else ("warning" if state.drift_status != "not-installed" else "success"),
                        "message": state.drift_status,
                    }
                )
        has_error = any(item["status"] == "error" for item in results)
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            print(context.format_table(("ASSET", "STATUS", "MESSAGE"), context.report_presentation.result_rows(results)))
        return 1 if has_error else 0

    if getattr(args, "subject", "") == "deps":
        config = context.effective_config(context.load_config(config_path))
        repo_root = context.resolve_repo_root(getattr(args, "repo_root", None), config)
        inventories = {asset_type: context.load_managed_asset_inventory(repo_root, asset_type) for asset_type in context.managed_asset_types}
        rows: list[tuple[str, str, str]] = []
        cli_versions = context.current_cli_versions(repo_root, config)
        for asset_type, inventory in inventories.items():
            for record in inventory.values():
                manifest = context.pm.load_skill_manifest(record.path)
                summary = context.pm.dependency_summary(manifest)
                missing_managed: list[str] = []
                optional_managed: list[str] = []
                for dep_type, summary_key in (("skill", "skills"), ("plugin", "plugins"), ("hook", "hooks"), ("subagent", "subagents"), ("loop", "loops")):
                    available_ids = inventories[dep_type]
                    missing_managed.extend(
                        f"{dep_type}:{item['id']}" for item in summary[summary_key]["required"] if item["id"] not in available_ids
                    )
                    optional_managed.extend(f"{dep_type}:{item['id']}" for item in summary[summary_key]["optional"])
                missing_clis = [item["id"] for item in summary["clis"]["required"] if item["id"] not in cli_versions]
                missing_mcps = [item["id"] for item in summary["mcps"]["required"]]
                optional_clis = [item["id"] for item in summary["clis"]["optional"]]
                optional_mcps = [item["id"] for item in summary["mcps"]["optional"]]
                optional_deps = optional_managed + [f"cli:{item}" for item in optional_clis] + [f"mcp:{item}" for item in optional_mcps]
                status, message = context.report_presentation.doctor_dependency_status_and_message(
                    missing_managed=missing_managed,
                    missing_clis=missing_clis,
                    missing_mcps=missing_mcps,
                    optional_deps=optional_deps,
                )
                rows.append(context.report_presentation.doctor_dependency_row(asset_type=asset_type, asset_id=record.skill_id, status=status, message=message))
        if args.json:
            print(json.dumps(context.report_presentation.doctor_dependency_payload(rows), ensure_ascii=False, indent=2))
        else:
            print(context.format_table(("ASSET", "STATUS", "MESSAGE"), rows))
        return 0

    if getattr(args, "subject", "") == "extends":
        config = context.effective_config(context.load_config(config_path))
        try:
            repo_root = context.resolve_repo_root(getattr(args, "repo_root", None), config)
        except FileNotFoundError:
            repo_root = None
        target_dir = Path(getattr(args, "target_dir", ".")) if getattr(args, "target_dir", None) else None
        results = context.doctor_extends_results(repo_root, config, target_dir)
        has_error = any(item["status"] == "error" for item in results)
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            rows = [(item["subject"], item["status"], item["message"]) for item in results]
            print(context.format_table(("EXTENDS EDGE", "STATUS", "MESSAGE"), rows))
            if has_error:
                print(context.report_presentation.doctor_drift_summary_line(has_error=True))
            else:
                print(context.report_presentation.doctor_drift_summary_line(has_error=False))
        return 1 if has_error else 0

    config = context.load_config(config_path)
    # YAML duplicate skill check
    try:
        repo_root = context.resolve_repo_root(getattr(args, "repo_root", None), config)
        from harness_ai_kit.domain.doctor_checks import check_yaml_duplicate_skills
        from harness_ai_kit.domain.manifest_ops import find_project_manifest
        manifest_path = find_project_manifest(repo_root)
        if manifest_path:
            dup_results = check_yaml_duplicate_skills(manifest_path)
            if dup_results:
                for item in dup_results:
                    print(f"[{item['status'].upper()}] {item['subject']}: {item['message']}")
    except Exception:
        pass  # Non-fatal: skip duplicate check if manifest not found

    # namespace 治理检查（2026-08-16 统一 team/ 后生效）
    try:
        repo_root = context.resolve_repo_root(getattr(args, "repo_root", None), config)
        from harness_ai_kit.domain.doctor_checks import check_namespace_conventions
        ns_results = check_namespace_conventions(repo_root)
        for item in ns_results:
            print(f"[{item['status'].upper()}] {item['subject']}: {item['message']}")
    except Exception:
        pass  # Non-fatal: skip namespace check if repo not available

    checks: list[dict[str, str]] = [
        {
            "check": "git",
            "status": "success" if context.git_available() else "error",
            "message": "git is available on PATH" if context.git_available() else "git is not available on PATH",
        },
        {
            "check": "config",
            "status": "success" if config_path.exists() else "warning",
            "message": f"Config path: {config_path}",
        },
        {
            "check": "build",
            "status": "success" if context.python_module_available("build") else "warning",
            "message": "python -m build is available" if context.python_module_available("build") else "python -m build is not installed",
        },
        {
            "check": "twine",
            "status": "success" if context.python_module_available("twine") else "warning",
            "message": "python -m twine is available" if context.python_module_available("twine") else "python -m twine is not installed",
        },
        {
            "check": "registry",
            "status": "success" if config.registry_upload_url else "warning",
            "message": f"Registry upload URL: {config.registry_upload_url}" if config.registry_upload_url else "No registry upload URL configured",
        },
        {
            "check": "skill-registry",
            "status": "success" if config.skill_registry_upload_url else "warning",
            "message": f"Skill registry upload URL: {config.skill_registry_upload_url}" if config.skill_registry_upload_url else "No skill registry upload URL configured",
        },
        _check_skill_registry_index(config),
        {
            "check": "cli-registry",
            "status": "success" if config.cli_registry_upload_url else "warning",
            "message": f"CLI registry upload URL: {config.cli_registry_upload_url}" if config.cli_registry_upload_url else "No CLI registry upload URL configured",
        },
    ]
    try:
        repo_root = context.resolve_repo_root(getattr(args, "repo_root", None), config)
        checks.append({"check": "repo", "status": "success", "message": f"Repo root: {repo_root}"})
    except FileNotFoundError as exc:
        checks.append({"check": "repo", "status": "warning", "message": str(exc)})
        repo_root = None
    status_rank = {"success": 0, "warning": 1, "error": 2}
    overall_status = max((status_rank[item["status"]] for item in checks), default=0)
    if args.json:
        print(json.dumps({"checks": checks, "ok": overall_status < 2}, ensure_ascii=False, indent=2))
    else:
        rows = [(item["check"], item["status"], item["message"]) for item in checks]
        print(context.format_table(("CHECK", "STATUS", "MESSAGE"), rows))
        print(context.report_presentation.doctor_summary_line(overall_status=overall_status))
        print(context.report_presentation.doctor_next_line(repo_available=repo_root is not None))
    return 0 if overall_status < 2 else 1


def command_validate(args: argparse.Namespace, config_path: Path, context: HealthCommandContext) -> int:
    config = context.load_config(config_path)
    repo_root = context.resolve_repo_root(getattr(args, "repo_root", None), config)
    repo_results = context.run_repo_validation(repo_root)
    version_results = context.doctor_versions_results(repo_root)
    results = repo_results + [(item["subject"], item["status"], item["message"]) for item in version_results]
    has_error = any(status == "error" for _, status, _ in results)
    if args.json:
        print(json.dumps(context.report_presentation.validation_payload(results), ensure_ascii=False, indent=2))
    else:
        print(context.format_table(("SUBJECT", "STATUS", "MESSAGE"), results))
        for line in context.report_presentation.validation_summary_lines(has_error=has_error):
            print(line)
    return 1 if has_error else 0
