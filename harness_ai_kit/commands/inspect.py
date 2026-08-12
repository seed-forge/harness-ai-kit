from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..domain import report_presentation

EXCLUSIVE_LIST_SUBJECTS = {
    "cli",
    "clis",
    "loop",
    "loops",
    "plugin",
    "plugins",
    "hook",
    "hooks",
    "subagent",
    "subagents",
    "mcp",
    "mcps",
}


@dataclass(frozen=True)
class InspectCommandContext:
    load_effective_config: Callable[[Path], Any]
    resolve_repo_root_if_available: Callable[[str | None, Any], Path | None]
    maybe_sync_repo: Callable[[argparse.Namespace, Path], None]
    load_combined_skill_inventory: Callable[[Path | None, Any], dict[str, Any]]
    load_combined_cli_inventory: Callable[[Path | None, Any], dict[str, Any]]
    load_managed_asset_inventory: Callable[[Path | None, str], dict[str, Any]]
    load_skill_inventory_for_source: Callable[[Path | None, Any, str | None], dict[str, Any]]
    load_managed_asset_inventory_for_source: Callable[[Path | None, str], dict[str, Any]]
    select_records: Callable[[dict[str, Any], list[str], bool], list[Any]]
    skill_install_state: Callable[[Any, Path | None], Any]
    cli_install_state: Callable[[Any], Any]
    managed_asset_install_state: Callable[[Any, Path | None], Any]
    load_skill_metadata_for_record: Callable[[Any, Any], dict[str, Any]]
    skill_dependency_payload: Callable[[dict[str, Any]], list[dict[str, Any]]]
    list_has_upgrade_available: Callable[[dict[str, Any], dict[str, Any], str], bool]
    format_skill_table: Callable[[list[Any], dict[str, Any]], str]
    format_cli_table: Callable[[list[Any], dict[str, Any]], str]
    format_managed_asset_table: Callable[[list[Any], dict[str, Any]], str]
    load_skill_document_for_record: Callable[..., str]


def build_inspect_handlers(context: InspectCommandContext) -> Mapping[str, Callable[[argparse.Namespace, Path], int]]:
    return {
        "list": lambda args, config_path: command_list(args, config_path, context),
        "show": lambda args, config_path: command_show(args, config_path, context),
        "cat": lambda args, config_path: command_cat(args, config_path, context),
    }


def command_list(args: argparse.Namespace, config_path: Path, context: InspectCommandContext) -> int:
    config = context.load_effective_config(config_path)
    repo_root = context.resolve_repo_root_if_available(getattr(args, "repo_root", None), config)
    subject = (args.subject or "assets").lower()
    if repo_root is not None:
        context.maybe_sync_repo(args, repo_root)
    skill_excluded = subject in EXCLUSIVE_LIST_SUBJECTS
    cli_excluded = subject in {"skill", "skills", "loop", "loops", "plugin", "plugins", "hook", "hooks", "subagent", "subagents", "mcp", "mcps"}
    inventory = context.load_combined_skill_inventory(repo_root, config) if not skill_excluded else {}
    cli_inventory = context.load_combined_cli_inventory(repo_root, config) if not cli_excluded else {}
    loop_inventory = context.load_managed_asset_inventory(repo_root, "loop") if repo_root is not None and subject in {"loop", "loops", "assets"} else {}
    plugin_inventory = context.load_managed_asset_inventory(repo_root, "plugin") if repo_root is not None and subject in {"plugin", "plugins", "assets"} else {}
    hook_inventory = context.load_managed_asset_inventory(repo_root, "hook") if repo_root is not None and subject in {"hook", "hooks", "assets"} else {}
    subagent_inventory = context.load_managed_asset_inventory(repo_root, "subagent") if repo_root is not None and subject in {"subagent", "subagents", "assets"} else {}
    mcp_inventory = context.load_managed_asset_inventory(repo_root, "mcp") if repo_root is not None and subject in {"mcp", "mcps", "assets"} else {}
    skill_records = list(inventory.values())
    cli_records = list(cli_inventory.values())
    loop_records = list(loop_inventory.values())
    plugin_records = list(plugin_inventory.values())
    hook_records = list(hook_inventory.values())
    subagent_records = list(subagent_inventory.values())
    mcp_records = list(mcp_inventory.values())
    skill_states = {record.skill_id: context.skill_install_state(record, repo_root) for record in skill_records}
    cli_states = {record.cli_id: context.cli_install_state(record) for record in cli_records}
    loop_states = {record.skill_id: context.managed_asset_install_state(record, repo_root) for record in loop_records}
    plugin_states = {record.skill_id: context.managed_asset_install_state(record, repo_root) for record in plugin_records}
    hook_states = {record.skill_id: context.managed_asset_install_state(record, repo_root) for record in hook_records}
    subagent_states = {record.skill_id: context.managed_asset_install_state(record, repo_root) for record in subagent_records}
    mcp_states = {record.skill_id: context.managed_asset_install_state(record, repo_root) for record in mcp_records}
    if args.json:
        skill_dependencies = {
            record.skill_id: context.skill_dependency_payload(context.load_skill_metadata_for_record(record, config))
            for record in skill_records
        }
        payload = report_presentation.list_payload(
            skill_records=skill_records,
            skill_states=skill_states,
            skill_dependencies=skill_dependencies,
            cli_records=cli_records,
            cli_states=cli_states,
            loop_records=loop_records,
            loop_states=loop_states,
            plugin_records=plugin_records,
            plugin_states=plugin_states,
            hook_records=hook_records,
            hook_states=hook_states,
            subagent_records=subagent_records,
            subagent_states=subagent_states,
            mcp_records=mcp_records,
            mcp_states=mcp_states,
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if subject in {"skill", "skills"}:
        if not skill_records:
            _print_empty_list(subject, repo_root)
            return 0
        print(context.format_skill_table(skill_records, skill_states))
        if context.list_has_upgrade_available(skill_states, cli_states, subject):
            print(report_presentation.list_update_available_line())
        return 0

    if subject in {"cli", "clis"}:
        if not cli_records:
            _print_empty_list(subject, repo_root)
            return 0
        print(context.format_cli_table(cli_records, cli_states))
        if context.list_has_upgrade_available(skill_states, cli_states, subject):
            print(report_presentation.list_update_available_line())
        return 0

    managed_subjects = {
        "loop": (loop_records, loop_states),
        "loops": (loop_records, loop_states),
        "plugin": (plugin_records, plugin_states),
        "plugins": (plugin_records, plugin_states),
        "hook": (hook_records, hook_states),
        "hooks": (hook_records, hook_states),
        "subagent": (subagent_records, subagent_states),
        "subagents": (subagent_records, subagent_states),
        "mcp": (mcp_records, mcp_states),
        "mcps": (mcp_records, mcp_states),
    }
    if subject in managed_subjects:
        records, states = managed_subjects[subject]
        print(context.format_managed_asset_table(records, states))
        return 0

    _print_asset_sections(
        context,
        subject=subject,
        repo_root=repo_root,
        skill_records=skill_records,
        skill_states=skill_states,
        cli_records=cli_records,
        cli_states=cli_states,
        loop_records=loop_records,
        loop_states=loop_states,
        plugin_records=plugin_records,
        plugin_states=plugin_states,
        hook_records=hook_records,
        hook_states=hook_states,
        subagent_records=subagent_records,
        subagent_states=subagent_states,
        mcp_records=mcp_records,
        mcp_states=mcp_states,
    )
    return 0


def command_show(args: argparse.Namespace, config_path: Path, context: InspectCommandContext) -> int:
    config = context.load_effective_config(config_path)
    repo_root = context.resolve_repo_root_if_available(getattr(args, "repo_root", None), config)
    if args.asset_kind == "skill":
        inventory = context.load_skill_inventory_for_source(repo_root, config, args.source)
    else:
        inventory = context.load_managed_asset_inventory_for_source(repo_root, args.asset_kind)
    record = context.select_records(inventory, [args.asset_id], install_all=False)[0]
    metadata = context.load_skill_metadata_for_record(record, config)
    install_state = (
        context.skill_install_state(record, repo_root)
        if record.asset_type == "skill"
        else context.managed_asset_install_state(record, repo_root)
    )
    payload = report_presentation.show_payload(
        record=record,
        metadata=metadata,
        dependencies=context.skill_dependency_payload(metadata),
        install_state=install_state,
    )
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    for line in report_presentation.show_lines(payload):
        print(line)
    return 0


def command_cat(args: argparse.Namespace, config_path: Path, context: InspectCommandContext) -> int:
    config = context.load_effective_config(config_path)
    repo_root = context.resolve_repo_root_if_available(getattr(args, "repo_root", None), config)
    if args.asset_kind == "skill":
        inventory = context.load_skill_inventory_for_source(repo_root, config, args.source)
    else:
        inventory = context.load_managed_asset_inventory_for_source(repo_root, args.asset_kind)
    record = context.select_records(inventory, [args.asset_id], install_all=False)[0]
    document = "CHANGELOG.md" if getattr(args, "changelog", False) else None
    if document is None:
        metadata = context.load_skill_metadata_for_record(record, config)
        companion_docs = dict(metadata.get("companion_docs", {}))
        if getattr(args, "usage", False):
            document = str(companion_docs.get("usage", "USAGE.md")).strip() or "USAGE.md"
        elif getattr(args, "example", False):
            document = str(companion_docs.get("example", "EXAMPLE.md")).strip() or "EXAMPLE.md"
        else:
            document = str(metadata.get("entry", "SKILL.md")).strip() or "SKILL.md"
    print(context.load_skill_document_for_record(record, config, document=document, offline=getattr(args, "offline", False)))
    return 0


def _print_empty_list(subject: str, repo_root: Path | None) -> None:
    for line in report_presentation.list_empty_lines(subject=subject, repo_available=repo_root is not None):
        print(line)


def _print_asset_sections(
    context: InspectCommandContext,
    *,
    subject: str,
    repo_root: Path | None,
    skill_records: list[Any],
    skill_states: dict[str, Any],
    cli_records: list[Any],
    cli_states: dict[str, Any],
    loop_records: list[Any],
    loop_states: dict[str, Any],
    plugin_records: list[Any],
    plugin_states: dict[str, Any],
    hook_records: list[Any],
    hook_states: dict[str, Any],
    subagent_records: list[Any],
    subagent_states: dict[str, Any],
    mcp_records: list[Any],
    mcp_states: dict[str, Any],
) -> None:
    if skill_records:
        print(report_presentation.list_section_title(title="Skills"))
        print(context.format_skill_table(skill_records, skill_states))
        print("")
    if cli_records:
        print(report_presentation.list_section_title(title="CLIs"))
        print(context.format_cli_table(cli_records, cli_states))
    if loop_records:
        print("")
        print(report_presentation.list_section_title(title="Loops"))
        print(context.format_managed_asset_table(loop_records, loop_states))
    if plugin_records:
        print("")
        print(report_presentation.list_section_title(title="Plugins"))
        print(context.format_managed_asset_table(plugin_records, plugin_states))
    if hook_records:
        print("")
        print(report_presentation.list_section_title(title="Hooks"))
        print(context.format_managed_asset_table(hook_records, hook_states))
    if subagent_records:
        print("")
        print(report_presentation.list_section_title(title="Subagents"))
        print(context.format_managed_asset_table(subagent_records, subagent_states))
    if mcp_records:
        print("")
        print(report_presentation.list_section_title(title="MCPs"))
        print(context.format_managed_asset_table(mcp_records, mcp_states))
    if not skill_records and not cli_records and not loop_records and not plugin_records and not hook_records and not subagent_records and not mcp_records:
        _print_empty_list(subject, repo_root)
    elif context.list_has_upgrade_available(skill_states, cli_states, subject):
        print(report_presentation.list_update_available_line())
