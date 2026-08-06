from __future__ import annotations

from typing import Any, Sequence

from ai_kit.domain.policies import display_source_name

from .versions import highest_version


def result_rows(results: Sequence[dict[str, Any]], *, subject_key: str = "subject") -> list[tuple[str, str, str]]:
    return [(str(item[subject_key]), str(item["status"]), str(item["message"])) for item in results]


def validation_payload(results: Sequence[tuple[str, str, str]]) -> list[dict[str, str]]:
    return [{"subject": subject, "status": status, "message": message} for subject, status, message in results]


def validation_summary_lines(*, has_error: bool) -> list[str]:
    if has_error:
        return [
            "Error: validation failed.",
            "Next: fix the reported metadata, version drift, or entry-file issues, then rerun `ai-kit validate`.",
        ]
    return [
        "Success: repository validation passed.",
        "Next: run `ai-kit publish ...` when you are ready to release changes.",
    ]


def sync_repo_success_lines(*, message: str) -> list[str]:
    return [
        f"Success: {message}",
        "Next: run `ai-kit list` or `ai-kit install ...`.",
    ]


def list_empty_lines(*, subject: str, repo_available: bool) -> list[str]:
    if subject in {"skill", "skills"}:
        next_hint = (
            "Add a skill under `skills/` and rerun `ai-kit validate`."
            if repo_available
            else "Bootstrap the team repo or pass --repo-root to inspect local skills."
        )
        return ["Warning: no installable skills found.", f"Next: {next_hint}"]
    if subject in {"cli", "clis"}:
        next_hint = (
            "Add `cli/<name>/cli.json` and rerun `ai-kit list clis`."
            if repo_available
            else "Configure cli_registry_index_url or bootstrap the team repo before listing CLIs."
        )
        return ["Warning: no installable CLIs found.", f"Next: {next_hint}"]
    next_hint = (
        "Create one with `ai-kit create skill <id>` or `ai-kit create cli <id>`."
        if repo_available
        else "Bootstrap the team repo or configure the remote registries before retrying."
    )
    return ["Warning: no installable skills or CLIs found.", f"Next: {next_hint}"]


def list_update_available_line() -> str:
    return "Next: run `ai-kit update` to refresh outdated installed assets."


def list_section_title(*, title: str) -> str:
    return f"[{title}]"


def list_payload(
    *,
    skill_records: Sequence[Any],
    skill_states: dict[str, Any],
    skill_dependencies: dict[str, Any],
    cli_records: Sequence[Any],
    cli_states: dict[str, Any],
    loop_records: Sequence[Any],
    loop_states: dict[str, Any],
    plugin_records: Sequence[Any],
    plugin_states: dict[str, Any],
    hook_records: Sequence[Any],
    hook_states: dict[str, Any],
    subagent_records: Sequence[Any],
    subagent_states: dict[str, Any],
    mcp_records: Sequence[Any],
    mcp_states: dict[str, Any],
) -> dict[str, Any]:
    return {
        "skills": [_skill_payload(record, skill_states[record.skill_id], skill_dependencies[record.skill_id]) for record in skill_records],
        "clis": [_cli_payload(record, cli_states[record.cli_id]) for record in cli_records],
        "loops": [_managed_asset_payload(record, loop_states[record.skill_id]) for record in loop_records],
        "plugins": [_managed_asset_payload(record, plugin_states[record.skill_id]) for record in plugin_records],
        "hooks": [_managed_asset_payload(record, hook_states[record.skill_id]) for record in hook_records],
        "subagents": [_managed_asset_payload(record, subagent_states[record.skill_id]) for record in subagent_records],
        "mcps": [_managed_asset_payload(record, mcp_states[record.skill_id]) for record in mcp_records],
    }


def show_payload(*, record: Any, metadata: dict[str, Any], dependencies: dict[str, Any], install_state: Any) -> dict[str, Any]:
    return {
        "asset_type": record.asset_type,
        "id": record.skill_id,
        "name": record.name,
        "status": record.status,
        "owner": record.owner,
        "version": record.version,
        "summary": record.summary,
        "source": record.source,
        "path": str(record.path) if record.path else "",
        "metadata_url": record.metadata_url,
        "compatible_clients": list(metadata.get("compatible_clients", [])),
        "installation": dict(metadata.get("installation", {})),
        "dependencies": dependencies,
        "companion_docs": dict(metadata.get("companion_docs", {})),
        "environment": dict(metadata.get("environment", {})),
        "runtime_requirements": list(metadata.get("runtime_requirements", [])),
        "post_install_hints": list(metadata.get("post_install_hints", [])),
        "agents_md_inject": str(metadata.get("agents_md_inject", "")).strip(),
        "config_schema": metadata.get("config_schema"),
        "installed": install_state.installed,
        "installed_versions": list(install_state.installed_versions),
        "drift_status": install_state.drift_status,
        "installed_locations": [_installed_location_payload(item) for item in install_state.installed_locations],
    }


def show_lines(payload: dict[str, Any]) -> list[str]:
    lines = [
        f"{str(payload['asset_type']).title()}: {payload['id']}@{payload['version']} [{payload['source']}]",
        f"Name: {payload['name']}",
        f"Owner: {payload['owner']}",
        f"Status: {payload['status']}",
        f"Summary: {payload['summary']}",
    ]
    if payload["compatible_clients"]:
        lines.append(f"Clients: {', '.join(payload['compatible_clients'])}")
    default_scope = str(payload["installation"].get("default_scope", "")).strip()
    if default_scope:
        lines.append(f"Default scope: {default_scope}")
    if payload["path"]:
        lines.append(f"Path: {payload['path']}")
    if payload["metadata_url"]:
        lines.append(f"Metadata: {payload['metadata_url']}")
    lines.append(f"Installed: {'yes' if payload['installed'] else 'no'}")
    if payload["installed_versions"]:
        lines.append(f"Installed versions: {', '.join(payload['installed_versions'])}")
    lines.append(f"Drift: {payload['drift_status']}")
    if payload["companion_docs"]:
        lines.append("Companion docs: " + ", ".join(f"{key}={value}" for key, value in payload["companion_docs"].items()))
    if payload["installed_locations"]:
        lines.append("Installed locations:")
        for item in payload["installed_locations"]:
            lines.append(f"- {item['runtime']}/{item['scope']} {item['version'] or '-'} {item['drift_status']} {item['path']}")
    dependencies = payload["dependencies"]
    required = dependencies["all"]["required"]
    optional = dependencies["all"]["optional"]
    if required:
        lines.append("Required dependencies:")
        for item in required:
            dep_ref = item.get("canonical_id") or item["id"]
            lines.append(f"- {item['type']} {dep_ref} {item['version']}")
    if optional:
        lines.append("Optional dependencies:")
        for item in optional:
            dep_ref = item.get("canonical_id") or item["id"]
            suffix = f" feature={item['feature']}" if item.get("feature") else ""
            lines.append(f"- {item['type']} {dep_ref} {item['version']}{suffix}")
    for note in payload["runtime_requirements"]:
        lines.append(f"Runtime requirement: {note}")
    environment = payload["environment"]
    dependency_groups = [str(item).strip() for item in environment.get("dependency_groups", []) if str(item).strip()]
    if dependency_groups:
        lines.append("Dependency groups: " + ", ".join(dependency_groups))
    for executable in environment.get("system", []):
        install_suffix = " (installable)" if executable.get("install_commands") else ""
        lines.append(f"System dependency: {executable.get('name') or executable.get('command')} -> {executable.get('command')}{install_suffix}")
    python_packages = [str(pkg).strip() for pkg in environment.get("python_packages", []) if str(pkg).strip()]
    if python_packages:
        lines.append(f"Python dependencies [{environment.get('python_strategy', 'none')}]: " + ", ".join(python_packages))
    for command in payload["environment"].get("verify_commands", []):
        lines.append(f"Verify command: {command}")
    for hint in payload["post_install_hints"]:
        lines.append(f"Post-install hint: {hint}")
    return lines


def skill_table_headers() -> tuple[str, ...]:
    return ("ASSET ID", "NAME", "LIFECYCLE", "INSTALLED", "INSTALLED VERSION", "AVAILABLE", "UPGRADE", "DRIFT", "SUMMARY")


def skill_table_rows(records: Sequence[Any], states: dict[str, Any] | None = None) -> list[tuple[str, str, str, str, str, str, str, str, str]]:
    state_map = states or {}
    rows = []
    for record in records:
        state = state_map.get(record.skill_id)
        rows.append(
            (
                record.skill_id,
                record.name,
                record.status,
                "yes" if state is not None and state.installed else "no",
                _highest_version(getattr(state, "installed_versions", ())) or "-",
                record.version,
                getattr(state, "upgrade_status", "not-installed"),
                getattr(state, "drift_status", "not-installed"),
                record.summary,
            )
        )
    return rows


def managed_asset_table_headers() -> tuple[str, ...]:
    return ("ASSET TYPE", "ASSET ID", "NAME", "LIFECYCLE", "INSTALLED", "AVAILABLE", "DRIFT", "SUMMARY")


def managed_asset_table_rows(records: Sequence[Any], states: dict[str, Any] | None = None) -> list[tuple[str, str, str, str, str, str, str, str]]:
    state_map = states or {}
    rows = []
    for record in records:
        state = state_map.get(record.skill_id)
        rows.append(
            (
                record.asset_type,
                record.skill_id,
                record.name,
                record.status,
                "yes" if state is not None and state.installed else "no",
                record.version,
                getattr(state, "drift_status", "not-installed"),
                record.summary,
            )
        )
    return rows


def cli_table_headers() -> tuple[str, ...]:
    return ("CLI ID", "NAME", "LIFECYCLE", "INSTALLED", "INSTALLED VERSION", "AVAILABLE", "UPGRADE", "PACKAGE", "SUMMARY")


def cli_table_rows(records: Sequence[Any], states: dict[str, Any] | None = None) -> list[tuple[str, str, str, str, str, str, str, str, str]]:
    state_map = states or {}
    rows = []
    for record in records:
        state = state_map.get(record.cli_id)
        rows.append(
            (
                record.cli_id,
                record.name,
                record.status,
                "yes" if state is not None and state.installed else "no",
                getattr(state, "installed_version", "") or "-",
                record.version,
                getattr(state, "upgrade_status", "not-installed"),
                record.package_name,
                record.summary,
            )
        )
    return rows


def _skill_payload(record: Any, state: Any, dependencies: Any) -> dict[str, Any]:
    return {
        "id": record.skill_id,
        "name": record.name,
        "status": record.status,
        "owner": record.owner,
        "version": record.version,
        "summary": record.summary,
        "path": str(record.path) if record.path else "",
        "source": record.source,
        "dependencies": dependencies,
        "installed": state.installed,
        "installed_versions": list(state.installed_versions),
        "installed_locations": [_installed_location_payload(item) for item in state.installed_locations],
        "upgrade_status": state.upgrade_status,
        "drift_status": state.drift_status,
    }


def _cli_payload(record: Any, state: Any) -> dict[str, Any]:
    return {
        "id": record.cli_id,
        "name": record.name,
        "status": record.status,
        "owner": record.owner,
        "version": record.version,
        "summary": record.summary,
        "package_name": record.package_name,
        "path": str(record.path) if record.path else "",
        "source": record.source,
        "installed": state.installed,
        "installed_version": state.installed_version,
        "upgrade_status": state.upgrade_status,
    }


def _managed_asset_payload(record: Any, state: Any) -> dict[str, Any]:
    return {
        "id": record.skill_id,
        "name": record.name,
        "status": record.status,
        "version": record.version,
        "summary": record.summary,
        "installed": state.installed,
        "installed_versions": list(state.installed_versions),
        "drift_status": state.drift_status,
    }


def _installed_location_payload(item: Any) -> dict[str, Any]:
    return {
        "runtime": item.runtime,
        "scope": item.scope,
        "path": str(item.path),
        "version": item.version,
        "drift_status": item.drift_status,
        "drift_message": item.drift_message,
    }


def _highest_version(values: Sequence[str]) -> str | None:
    return highest_version(values)


def doctor_runtimes_next_line() -> str:
    return "Next: use `ai-kit install skill <id> --runtime codex --scope project` or add a runtime adapter."


def doctor_skills_discovered_line(*, skill_ids: list[str]) -> str:
    return f"Discovered skills: {', '.join(skill_ids)}"


def doctor_skills_empty_line() -> str:
    return "Warning: no installed skills were discovered for this runtime."


def doctor_skills_hint_line(*, invocation_hint: str) -> str:
    return f"Hint: {invocation_hint}"


def doctor_skills_codex_note_lines() -> list[str]:
    return [
        "Note: project skills are only visible when Codex opens the matching workspace root.",
        "Note: after installing a skill, start a fresh Codex thread before testing discovery.",
    ]


def doctor_versions_summary_line(*, has_error: bool) -> str:
    return "Error: version audit found mismatches." if has_error else "Success: version audit passed."


def doctor_drift_summary_line(*, has_error: bool) -> str:
    if has_error:
        return "Error: drift audit found registry mismatches."
    return "Success: drift audit passed or only found follow-up warnings."


def doctor_sources_empty_roots_line() -> str:
    return "Warning: no roots are currently declared or locked for this project."


def doctor_sources_warning_line(*, warning: str) -> str:
    return f"Warning: {warning}"


def doctor_sources_error_line(*, error: str) -> str:
    return f"Error: {error}"


def doctor_sources_success_hint_line() -> str:
    return "Hint: run `ai-kit sync-repo` or `ai-kit upgrade --all` if the selected source looks stale."


def doctor_sources_root_rows(roots: Sequence[dict[str, Any]]) -> list[tuple[str, str, str, str, str, str]]:
    return [
        (
            str(item["canonical_id"]),
            str(item["repo_version"] or "-"),
            str(item["registry_version"] or "-"),
            display_source_name(item["selected_source"]),
            str(item["selected_version"] or "-"),
            str(item["reason"]),
        )
        for item in roots
    ]


def doctor_dependency_status_and_message(
    *,
    missing_managed: Sequence[str],
    missing_clis: Sequence[str],
    missing_mcps: Sequence[str],
    optional_deps: Sequence[str],
) -> tuple[str, str]:
    status = "success" if not missing_managed and not missing_clis and not missing_mcps else "warning"
    message_parts: list[str] = []
    if missing_managed:
        message_parts.append("missing managed deps: " + ", ".join(missing_managed))
    if missing_clis:
        message_parts.append("missing CLI deps: " + ", ".join(missing_clis))
    if missing_mcps:
        message_parts.append("manual MCP deps: " + ", ".join(missing_mcps))
    if optional_deps:
        message_parts.append("optional deps: " + ", ".join(optional_deps))
    if not message_parts:
        message_parts.append("dependency requirements look satisfied")
    return status, "; ".join(message_parts)


def doctor_dependency_row(*, asset_type: str, asset_id: str, status: str, message: str) -> tuple[str, str, str]:
    return (f"{asset_type}:{asset_id}", status, message)


def doctor_dependency_payload(rows: Sequence[tuple[str, str, str]]) -> list[dict[str, str]]:
    return [{"asset": asset_ref, "status": status, "message": message} for asset_ref, status, message in rows]


def doctor_summary_line(*, overall_status: int) -> str:
    if overall_status == 0:
        return "Success: doctor checks passed."
    if overall_status == 1:
        return "Warning: doctor checks found follow-up items."
    return "Error: doctor checks found blocking issues."


def doctor_next_line(*, repo_available: bool) -> str:
    next_hint = "ai-kit list" if repo_available else "ai-kit bootstrap --repo-url <git-url>"
    return f"Next: run `{next_hint}`."


def format_table(headers: Sequence[str], rows: list[Sequence[str]]) -> str:
    widths = [len(header) for header in headers]
    for row in rows:
        for idx, value in enumerate(row):
            widths[idx] = max(widths[idx], len(value))

    lines = [
        "  ".join(header.ljust(widths[idx]) for idx, header in enumerate(headers)),
        "  ".join("-" * widths[idx] for idx in range(len(headers))),
    ]
    for row in rows:
        lines.append("  ".join(value.ljust(widths[idx]) for idx, value in enumerate(row)))
    return "\n".join(lines)


def format_skill_table(records: list[Any], states: dict[str, Any] | None = None) -> str:
    return format_table(skill_table_headers(), skill_table_rows(records, states))


def format_managed_asset_table(records: list[Any], states: dict[str, Any] | None = None) -> str:
    return format_table(managed_asset_table_headers(), managed_asset_table_rows(records, states))


def format_cli_table(records: list[Any], states: dict[str, Any] | None = None) -> str:
    return format_table(cli_table_headers(), cli_table_rows(records, states))
