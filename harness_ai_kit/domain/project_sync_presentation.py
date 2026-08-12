from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

from harness_ai_kit.domain.policies import display_source_name


def project_sync_dry_run_lines(
    *,
    skill_items: Sequence[tuple[Any, Path, str, str]],
    cli_records: Sequence[Any],
    managed_items: Sequence[tuple[Any, Path]],
    removed_skills: Sequence[str],
    removed_assets: Sequence[str],
    external_dependency_lines: Sequence[str] = (),
    extends_summary: str | None = None,
    extends_merge_lines: Sequence[str] = (),
) -> list[str]:
    lines: list[str] = []
    for node, destination, runtime, scope in skill_items:
        line = (
            f"Preview: would sync skill {node.id}@{node.version} -> {destination} "
            f"({runtime}/{scope}, source={node.source})"
        )
        if getattr(node, "extends", None):
            extends_ids = [ext.get("base_skill_id", "?") for ext in (node.extends or [])]
            if extends_ids:
                line += f" [extends: {', '.join(extends_ids)}]"
        lines.append(line)
    for record in cli_records:
        lines.append(f"Preview: would sync CLI {record.cli_id}@{record.version}")
    for node, destination in managed_items:
        lines.append(f"Preview: would sync {node.type} {node.id}@{node.version} -> {destination}")
    if removed_skills:
        lines.append("Preview: would prune orphaned project skills -> " + ", ".join(removed_skills))
    if removed_assets:
        lines.append("Preview: would prune orphaned project assets -> " + ", ".join(removed_assets))
    for line in external_dependency_lines:
        lines.append(f"Preview: would install external dependency -> {line}")
    for line in extends_merge_lines:
        lines.append(line)
    if extends_summary:
        lines.append(extends_summary)
    return lines


def project_sync_applied_lines(
    *,
    skill_items: Sequence[tuple[Any, Path, str]],
    cli_items: Sequence[tuple[Any, str]],
    managed_items: Sequence[tuple[Any, Path]],
    removed_skills: Sequence[str],
    removed_assets: Sequence[str],
    action: str = "synced",
    external_dependency_lines: Sequence[str] = (),
    extends_summary: str | None = None,
    extends_merge_lines: Sequence[str] = (),
) -> list[str]:
    lines: list[str] = []
    for node, destination, hint in skill_items:
        lines.append(f"Success: {action} skill {node.id}@{node.version} -> {destination}")
        if hint:
            lines.append(f"Hint: {hint}")
    for record, output in cli_items:
        lines.append(f"Success: {action} CLI {record.cli_id}@{record.version}")
        if output:
            lines.append(output)
    for node, destination in managed_items:
        lines.append(f"Success: {action} {node.type} {node.id}@{node.version} -> {destination}")
    for line in external_dependency_lines:
        lines.append(f"Success: installed external dependency -> {line}")
    for line in extends_merge_lines:
        lines.append(line)
    if extends_summary:
        lines.append(extends_summary)
    if removed_skills:
        lines.append("Success: pruned project skills -> " + ", ".join(removed_skills))
    if removed_assets:
        lines.append("Success: pruned project assets -> " + ", ".join(removed_assets))
    return lines


def project_sync_lockfile_line(lock_path: Path, *, dry_run: bool) -> str:
    prefix = "Preview: would write lockfile" if dry_run else "Success: lockfile ready"
    return f"{prefix} -> {lock_path}"


def lockfile_written_line(lock_path: Path) -> str:
    return f"Success: wrote lockfile -> {lock_path}"


def cache_empty_line() -> str:
    return "Warning: cache is empty."


def cache_clean_success_line(*, removed_count: int) -> str:
    return f"Success: removed {removed_count} cached file(s)."


def project_add_no_change_line(*, asset_kind: str, asset_id: str, manifest_path: Path) -> str:
    return f"No change: {asset_kind} {asset_id} is already declared in {manifest_path}."


def project_add_success_lines(*, asset_kind: str, asset_id: str, manifest_path: Path, no_install: bool) -> list[str]:
    lines = [f"Success: added {asset_kind} {asset_id} to {manifest_path}"]
    if no_install:
        lines.append("Next: run `harness-ai-kit sync` to apply the updated project declaration.")
    return lines


def project_remove_success_lines(*, asset_kind: str, asset_id: str, manifest_path: Path, no_install: bool) -> list[str]:
    lines = [f"Success: removed {asset_kind} {asset_id} from {manifest_path}"]
    if no_install:
        lines.append("Next: run `harness-ai-kit sync` to reconcile the updated project declaration.")
    return lines


def project_remove_followup_lines(*, asset_kind: str, asset_id: str, removed_skills: Sequence[str], removed_assets: Sequence[str]) -> list[str]:
    lines: list[str] = []
    if removed_skills:
        lines.append("Pruned project skills: " + ", ".join(removed_skills))
    if removed_assets:
        lines.append("Pruned project assets: " + ", ".join(removed_assets))
    if asset_kind == "cli":
        lines.append(f"Note: project remove does not uninstall the environment-level CLI package `{asset_id}`. Use `harness-ai-kit uninstall cli {asset_id}` if needed.")
    if asset_kind == "mcp":
        lines.append(f"Note: MCP declarations are manual requirements. Remove any local MCP wiring separately for `{asset_id}`.")
    return lines


def manifest_bootstrapped_from_lock_lines(*, manifest_path: Path, lock_path: Path) -> list[str]:
    return [
        f"Success: bootstrapped project manifest from lockfile -> {manifest_path}",
        f"Source lockfile: {lock_path}",
    ]


def manifest_migrate_success_lines(*, manifest_path: Path, backup_path: Path) -> list[str]:
    return [
        f"Success: migrated project manifest -> {manifest_path}",
        f"Backup: {backup_path}",
    ]


def project_lockfile_synced_line(lock_path: Path | str) -> str:
    return f"Success: synced project lockfile -> {lock_path}"


def prune_result_lines(*, removed_skills: Sequence[str], removed_assets: Sequence[str]) -> list[str]:
    lines: list[str] = []
    if removed_skills:
        lines.append("Success: pruned orphaned project skills -> " + ", ".join(removed_skills))
    if removed_assets:
        lines.append("Success: pruned orphaned project assets -> " + ", ".join(removed_assets))
    if not removed_skills and not removed_assets:
        lines.append("Success: no orphaned project skills or assets were found.")
    return lines


def missing_external_dependency_warning_lines(items: Sequence[dict[str, str]]) -> list[str]:
    return [
        f"Warning: missing external dependency -> {item['asset']} {item['kind']} {item['subject']} ({item['detail']})"
        for item in items
    ]


def no_skills_matched_line() -> str:
    return "Warning: no skills matched the requested selection."


def git_tag_created_line(*, tag_name: str) -> str:
    return f"Success: created git tag {tag_name}"


def standalone_install_dry_run_lines(
    *,
    skill_items: Sequence[tuple[Any, Path, str, str]],
    managed_items: Sequence[tuple[Any, Path]],
    external_dependency_lines: Sequence[str] = (),
    lock_path: Path,
    manifest_path: Path | None = None,
    extends_summary: str | None = None,
    extends_merge_lines: Sequence[str] = (),
) -> list[str]:
    lines: list[str] = []
    for node, destination, runtime, scope in skill_items:
        line = (
            f"Preview: would install skill {node.id}@{node.version} -> {destination} "
            f"({runtime}/{scope}, source={display_source_name(node.source)})"
        )
        if getattr(node, "extends", None):
            extends_ids = [ext.get("base_skill_id", "?") for ext in (node.extends or [])]
            if extends_ids:
                line += f" [extends: {', '.join(extends_ids)}]"
        lines.append(line)
    for node, destination in managed_items:
        lines.append(f"Preview: would install {node.type} {node.id}@{node.version} -> {destination}")
    for line in external_dependency_lines:
        lines.append(f"Preview: would install external dependency -> {line}")
    for line in extends_merge_lines:
        lines.append(line)
    if extends_summary:
        lines.append(extends_summary)
    lines.append(project_sync_lockfile_line(lock_path, dry_run=True))
    if manifest_path is not None:
        lines.append(f"Preview: would initialize project manifest -> {manifest_path}")
    lines.append("Next: rerun without `--dry-run` to install the selected skills.")
    return lines


def standalone_install_applied_lines(
    *,
    skill_items: Sequence[tuple[Any, Path, str]],
    managed_items: Sequence[tuple[Any, Path]],
    action: str,
    external_dependency_lines: Sequence[str] = (),
    initialized_manifest_path: Path | None = None,
    lock_path: Path,
    runtime: str,
    extends_summary: str | None = None,
    extends_merge_lines: Sequence[str] = (),
) -> list[str]:
    lines: list[str] = []
    for node, destination, hint in skill_items:
        lines.append(f"Success: {action} {node.id}@{node.version} -> {destination}")
        if hint:
            lines.append(f"Hint: {hint}")
    for node, destination in managed_items:
        lines.append(f"Success: {action} {node.type} {node.id}@{node.version} -> {destination}")
    for line in external_dependency_lines:
        lines.append(f"Success: installed external dependency -> {line}")
    for line in extends_merge_lines:
        lines.append(line)
    if extends_summary:
        lines.append(extends_summary)
    if initialized_manifest_path is not None:
        lines.append(f"Success: initialized project manifest -> {initialized_manifest_path}")
    lines.append(project_sync_lockfile_line(lock_path, dry_run=False))
    lines.append(f"Next: open the target skill directory for runtime `{runtime}` or run your agent workflow.")
    if runtime == "codex":
        lines.append("Note: if Codex was already open, start a fresh thread in the matching workspace before testing the skill.")
    return lines


def cli_install_dry_run_lines(*, cli_items: Sequence[tuple[Any, str]], action: str) -> list[str]:
    lines = [f"Preview: would {action} CLI {record.cli_id} with `{output}`" for record, output in cli_items]
    lines.append("Next: rerun without `--dry-run` to apply the CLI install.")
    return lines


def cli_install_applied_lines(
    *,
    cli_items: Sequence[tuple[Any, str]],
    action: str,
    include_operator_hint: bool,
) -> list[str]:
    lines: list[str] = []
    for record, output in cli_items:
        lines.append(f"Success: {action}ed CLI {record.cli_id}")
        if output:
            lines.append(output)
    if include_operator_hint:
        lines.append("Hint: install `harness-ai-kit-ops` separately if you want the operator workflow skill.")
        lines.append("Hint: run `harness-ai-kit install skill harness-ai-kit-ops`.")
    lines.append("Next: run the installed CLI directly or `harness-ai-kit doctor`.")
    return lines


def bulk_upgrade_dry_run_lines(
    *,
    lock_skill_items: Sequence[tuple[Any, Path, str, str]],
    repo_skill_items: Sequence[tuple[Any, Path, str, str, str]],
    cli_items: Sequence[tuple[Any, str]],
    skipped_self_records: Sequence[Any],
    recovery_command: str,
) -> list[str]:
    lines: list[str] = []
    for node, destination, runtime, scope in lock_skill_items:
        lines.append(
            f"Preview: would upgrade skill {node.id}@{node.version} -> {destination} "
            f"({runtime}/{scope}, source={node.source})"
        )
    for record, destination, runtime, scope, source in repo_skill_items:
        lines.append(f"Preview: would upgrade skill {record.skill_id} -> {destination} ({runtime}/{scope}, source={source})")
    for record, output in cli_items:
        lines.append(f"Preview: would upgrade CLI {record.cli_id} with `{output}`")
    for record in skipped_self_records:
        lines.append(f"Preview: skipping self-upgrade for CLI {record.cli_id}; run `{recovery_command}` manually.")
    lines.append("Next: rerun without `--dry-run` to apply the upgrade.")
    return lines


def bulk_upgrade_applied_lines(
    *,
    lock_skill_nodes: Sequence[Any],
    repo_skill_records: Sequence[Any],
    removed_skills: Sequence[str],
    cli_items: Sequence[tuple[Any, str]],
    skipped_self_records: Sequence[Any],
    recovery_command: str,
    lock_path: Path | None,
) -> list[str]:
    lines: list[str] = []
    for node in lock_skill_nodes:
        lines.append(f"Success: upgraded skill {node.id}@{node.version}")
    for record in repo_skill_records:
        lines.append(f"Success: upgraded skill {record.skill_id}")
    if removed_skills:
        lines.append("Success: pruned project skills -> " + ", ".join(removed_skills))
    for record, output in cli_items:
        lines.append(f"Success: upgraded CLI {record.cli_id}")
        if output:
            lines.append(output)
    for record in skipped_self_records:
        lines.append(f"Warning: skipped self-upgrade for CLI {record.cli_id}. Run `{recovery_command}` manually.")
    if lock_path is not None:
        lines.append(f"Success: lockfile refreshed -> {lock_path}")
    lines.append("Next: verify the updated tools in your local workflows.")
    return lines


def publish_skill_dry_run_lines(
    *,
    archive_path: Path,
    archive_url: str,
    metadata_url: str,
    checksum_url: str,
    index_url: str,
) -> list[str]:
    return [
        f"Preview: would build skill archive -> {archive_path}",
        f"Preview: would upload archive -> {archive_url}",
        f"Preview: would upload metadata -> {metadata_url}",
        f"Preview: would upload checksum -> {checksum_url}",
        f"Preview: would refresh index -> {index_url}",
        "Next: rerun without `--dry-run` to publish the skill artifact.",
    ]


def publish_asset_dry_run_lines(
    *,
    asset_kind: str,
    archive_path: Path,
    archive_url: str,
    metadata_url: str,
    checksum_url: str,
    index_url: str,
) -> list[str]:
    return [
        f"Preview: would build {asset_kind} archive -> {archive_path}",
        f"Preview: would upload archive -> {archive_url}",
        f"Preview: would upload metadata -> {metadata_url}",
        f"Preview: would upload checksum -> {checksum_url}",
        f"Preview: would refresh index -> {index_url}",
        f"Next: rerun without `--dry-run` to publish the {asset_kind} artifact.",
    ]


def publish_skill_success_lines(
    *,
    skill_id: str,
    archive_url: str,
    checksum_url: str,
    index_url: str,
) -> list[str]:
    return [
        f"Success: published skill archive -> {archive_url}",
        f"Success: uploaded checksum -> {checksum_url}",
        f"Success: updated skill index -> {index_url}",
        f"Next: verify with `harness-ai-kit install skill {skill_id} --dry-run`.",
    ]


def publish_asset_success_lines(
    *,
    asset_kind: str,
    asset_id: str,
    archive_url: str,
    checksum_url: str,
    index_url: str,
) -> list[str]:
    return [
        f"Success: published {asset_kind} archive -> {archive_url}",
        f"Success: uploaded checksum -> {checksum_url}",
        f"Success: updated {asset_kind} index -> {index_url}",
        f"Next: verify with `harness-ai-kit show {asset_kind} {asset_id}`.",
    ]


def publish_cli_dry_run_lines(
    *,
    package_name: str,
    version: str,
    build_root: Path,
    upload_command: str,
    metadata_url: str,
    index_url: str,
) -> list[str]:
    return [
        f"Preview: would publish CLI package -> {package_name}@{version}",
        f"Preview: would build CLI package -> {build_root}",
        f"Preview: would upload package(s) -> {upload_command}",
        f"Preview: would upload CLI metadata -> {metadata_url}",
        f"Preview: would refresh CLI index -> {index_url}",
        "Next: rerun without `--dry-run` to publish the CLI package and registry metadata.",
    ]


def publish_cli_success_lines(
    *,
    cli_id: str,
    package_name: str,
    version: str,
    metadata_url: str,
    index_url: str,
) -> list[str]:
    return [
        f"Success: published CLI package -> {package_name}@{version}",
        f"Success: uploaded CLI metadata -> {metadata_url}",
        f"Success: updated CLI index -> {index_url}",
        f"Next: verify with `harness-ai-kit install cli {cli_id} --dry-run`.",
    ]


def release_skill_build_success_lines(*, skill_id: str, archive_path: Path) -> list[str]:
    return [
        f"Success: built skill archive -> {archive_path}",
        f"Next: run `harness-ai-kit release skill-publish {skill_id} --dry-run`.",
    ]


def release_bump_dry_run_lines(*, current_version: str, next_version: str) -> list[str]:
    return [
        f"Preview: version would change from {current_version} to {next_version}",
        "Next: rerun without `--dry-run` to write the new version.",
    ]


def release_bump_success_lines(*, current_version: str, next_version: str) -> list[str]:
    return [
        f"Success: version updated from {current_version} to {next_version}",
        "Next: run `harness-ai-kit release build`.",
    ]


def release_build_success_lines() -> list[str]:
    return [
        "Success: built wheel and sdist.",
        "Next: run `harness-ai-kit release check`.",
    ]


def release_check_success_lines() -> list[str]:
    return [
        "Success: twine check passed.",
        "Next: run `harness-ai-kit release publish --dry-run` or publish for real.",
    ]


def release_publish_dry_run_lines(*, upload_command: str, tag_name: str, tag: bool, push_tag: bool) -> list[str]:
    lines = [f"Preview: upload command -> {upload_command}"]
    if tag:
        lines.append(f"Preview: would create git tag {tag_name}")
        if push_tag:
            lines.append(f"Preview: would push git tag {tag_name} to origin")
    lines.append("Next: rerun without `--dry-run` to publish the release.")
    return lines


def release_publish_success_lines() -> list[str]:
    return [
        "Success: release artifacts uploaded.",
        "Next: verify installation from the configured package index.",
    ]


def publish_selection_dry_run_lines(*, selections: Sequence[str]) -> list[str]:
    lines: list[str] = []
    if selections:
        lines.append("Preview: the following paths would be published:")
        lines.extend(f"- {item}" for item in selections)
    else:
        lines.append("Preview: all repository changes would be published.")
    lines.append("Next: rerun the same command without `--dry-run` to publish.")
    return lines


def publish_selection_success_lines(*, selections: Sequence[str]) -> list[str]:
    if selections:
        first = f"Success: published paths -> {', '.join(selections)}"
    else:
        first = "Success: published all staged repository changes."
    return [first, "Next: open the remote PR or notify reviewers."]


def create_scaffold_success_lines(*, subject: str, path: Path) -> list[str]:
    if subject == "skill":
        return [
            f"Success: created skill scaffold -> {path}",
            "Next: fill in the skill content, then run `harness-ai-kit submit skill ...`.",
        ]
    if subject == "cli":
        return [
            f"Success: created CLI scaffold -> {path}",
            "Next: implement the CLI tasks, then run `harness-ai-kit submit cli ...`.",
        ]
    return [
        f"Success: created {subject} scaffold -> {path}",
        f"Next: fill in the content, then run `harness-ai-kit submit {subject} ...`.",
    ]


def lifecycle_deprecated_success_lines(*, asset_kind: str, asset_id: str, replacement: str) -> list[str]:
    label = "CLI" if asset_kind == "cli" else asset_kind
    return [f"Success: deprecated {label} {asset_id} -> {replacement}"]


def lifecycle_retired_success_lines(*, asset_kind: str, asset_id: str, replacement: str | None = None) -> list[str]:
    label = "CLI" if asset_kind == "cli" else asset_kind
    suffix = f" -> {replacement}" if replacement else ""
    return [
        f"Success: retired {label} {asset_id}{suffix}",
        "Next: publish the updated metadata before hiding the asset from registry listings.",
    ]


def config_set_success_lines(*, config_path: Path) -> list[str]:
    return [
        f"Success: saved config -> {config_path}",
        "Next: run `harness-ai-kit doctor` or `harness-ai-kit bootstrap`.",
    ]


def init_success_lines(*, checkout_message: str, config_path: Path) -> list[str]:
    return [
        f"Success: {checkout_message}",
        f"Success: initialized config -> {config_path}",
        "Next: run `harness-ai-kit doctor` or `harness-ai-kit list assets`.",
    ]


def bootstrap_success_lines(*, checkout_message: str) -> list[str]:
    return [
        f"Success: {checkout_message}",
        "Next: run `harness-ai-kit doctor` or `harness-ai-kit list`.",
    ]


def init_project_success_lines(*, manifest_path: Path) -> list[str]:
    return [
        f"Success: wrote project manifest -> {manifest_path}",
        "Next: run `harness-ai-kit sync` or `harness-ai-kit doctor sources` in this project.",
    ]


def uninstall_skill_missing_line(*, asset_id: str, target_dir: Path) -> str:
    return f"No installed skill payload found for {asset_id} at {target_dir}."


def uninstall_skill_success_line(*, asset_id: str, target_dir: Path) -> str:
    return f"Success: uninstalled skill {asset_id} from {target_dir}"


def uninstall_cli_binary_dry_run_line(*, install_path: Path) -> str:
    return f"Preview: would remove `{install_path}`"


def uninstall_cli_binary_missing_line(*, install_path: Path) -> str:
    return f"No installed CLI binary found at {install_path}."


def uninstall_cli_binary_success_line(*, install_path: Path) -> str:
    return f"Success: removed CLI binary {install_path}"


def uninstall_cli_package_dry_run_line(*, command: Sequence[str]) -> str:
    return "Preview: would run `" + " ".join(command) + "`"


def uninstall_cli_package_success_line(*, package_name: str) -> str:
    return f"Success: uninstalled CLI package {package_name}"


def uninstall_managed_missing_line(*, asset_kind: str, asset_id: str, root: Path) -> str:
    return f"No installed {asset_kind} payload found for {asset_id} under {root}."


def uninstall_managed_success_line(*, asset_kind: str, asset_id: str, root: Path) -> str:
    return f"Success: uninstalled {asset_kind} {asset_id} from {root}"


def uninstall_manifest_removed_line(*, asset_kind: str, asset_id: str, manifest_path: Path) -> str:
    return f"Success: removed {asset_kind} {asset_id} declaration from {manifest_path}"


def uninstall_manifest_not_found_line() -> str:
    return "Note: no harness-ai-kit.yml found in scope; skipping manifest cleanup."


def uninstall_manifest_not_declared_line(*, asset_kind: str, asset_id: str, manifest_path: Path) -> str:
    return f"Note: {asset_kind} {asset_id} is not declared in {manifest_path}; skipping manifest cleanup."


def uninstall_cascade_removed_line(*, removed_ids: list[str], target_dir: Path) -> str:
    return f"Success: removed {len(removed_ids)} orphaned dependency(ies) from {target_dir}: {', '.join(removed_ids)}"


def uninstall_cascade_none_line() -> str:
    return "Note: no orphaned dependencies found."


def extends_chain_summary_line(*, extends_count: int, base_count: int) -> str | None:
    if extends_count == 0:
        return None
    return f"Extends: resolved {extends_count} extending skill(s) across {base_count} base skill(s)"


def extends_merge_progress_line(*, skill_id: str, base_id: str, strategy: str = "prepend") -> str:
    return f"Extends: merging SKILL.md for {skill_id} (extends {base_id}, strategy={strategy})"


def extends_merge_skip_line(*, skill_id: str, base_id: str, reason: str) -> str:
    return f"Extends: skipping merge for {skill_id} -> {base_id}: {reason}"


def multi_runtime_sync_lines(results: dict[str, list[Any]]) -> list[str]:
    """生成多 runtime 同步摘要行。"""
    if not results:
        return []
    lines: list[str] = ["", "Multi-runtime sync:"]
    for runtime, paths in sorted(results.items()):
        lines.append(f"  {runtime}: {len(paths)} skill(s) synced")
    return lines
