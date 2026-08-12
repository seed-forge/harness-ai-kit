"""Governance summaries and lifecycle status application."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from harness_ai_kit import package_manager as pm
from harness_ai_kit.domain.models import ASSET_DIRECTORY_NAMES, CliAssetRecord, SkillRecord
from harness_ai_kit.domain.inventory import load_skill_record
from harness_ai_kit.infrastructure.release_ops import (
    append_note_to_top_changelog,
    ensure_catalog_entry,
    prepend_document_banner,
)


def governance_summary(status: str, replacement: str | None = None) -> str:
    if status == "deprecated":
        return f"[已废弃] 请迁移到 `{replacement}`。" if replacement else "[已废弃] 该资产即将下线。"
    if replacement:
        return f"[已退役] 请迁移到 `{replacement}`。"
    return "[已退役] 该资产已下线，不再维护。"




def merge_governance_summary(summary: str, governance_prefix: str) -> str:
    summary = summary.strip()
    if summary.startswith("[已废弃]"):
        summary = summary[len("[已废弃]"):].strip()
    if summary.startswith("[已退役]"):
        summary = summary[len("[已退役]"):].strip()
    if governance_prefix in summary:
        return summary
    if summary:
        return f"{governance_prefix}{summary}".strip()
    return governance_prefix.strip()




def apply_skill_lifecycle_status(
    repo_root: Path,
    skill_id: str,
    *,
    status: str,
    replacement: str | None = None,
) -> None:
    skill_dir = repo_root / "skills" / skill_id
    metadata_path = skill_dir / "skill.json"
    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    payload["status"] = status
    payload["summary"] = merge_governance_summary(str(payload.get("summary", "")), governance_summary(status, replacement))
    hints = list(payload.get("post_install_hints", []))
    lifecycle_note = (
        f"Deprecated: migrate to {replacement}."
        if status == "deprecated" and replacement
        else (f"Retired: migrate to {replacement}." if replacement else "Retired: no replacement is planned.")
    )
    if lifecycle_note not in hints:
        hints.append(lifecycle_note)
    payload["post_install_hints"] = hints
    metadata_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    banner = (
        f"> **⚠️ 已废弃**：请迁移到 `{replacement}`。\n\n"
        if status == "deprecated"
        else (
            f"> **🛑 已退役**：请迁移到 `{replacement}`。\n\n"
            if replacement
            else "> **🛑 已退役**：该 Skill 已下线，不再维护。\n\n"
        )
    )
    prepend_document_banner(skill_dir / "SKILL.md", banner)
    changelog_note = (
        f"Deprecated in favor of `{replacement}`."
        if status == "deprecated"
        else (f"Retired in favor of `{replacement}`." if replacement else "Retired with no replacement.")
    )
    append_note_to_top_changelog(skill_dir / "CHANGELOG.md", changelog_note)
    ensure_catalog_entry(repo_root, load_skill_record(skill_dir))




def apply_cli_lifecycle_status(
    repo_root: Path,
    cli_id: str,
    *,
    status: str,
    replacement: str | None = None,
) -> None:
    cli_dir = repo_root / "cli" / cli_id
    metadata_path = cli_dir / "cli.json"
    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    payload["status"] = status
    payload["summary"] = merge_governance_summary(str(payload.get("summary", "")), governance_summary(status, replacement))
    metadata_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    changelog_note = (
        f"Deprecated in favor of `{replacement}`."
        if status == "deprecated"
        else (f"Retired in favor of `{replacement}`." if replacement else "Retired with no replacement.")
    )
    append_note_to_top_changelog(cli_dir / "CHANGELOG.md", changelog_note)




def apply_managed_asset_lifecycle_status(
    repo_root: Path,
    asset_type: str,
    asset_id: str,
    *,
    status: str,
    replacement: str | None = None,
) -> None:
    asset_dir = repo_root / ASSET_DIRECTORY_NAMES[asset_type] / asset_id
    metadata_path = asset_dir / pm.manifest_metadata_filename(asset_type)
    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    payload["status"] = status
    payload["summary"] = merge_governance_summary(str(payload.get("summary", "")), governance_summary(status, replacement))
    hints = list(payload.get("post_install_hints", []))
    lifecycle_note = (
        f"Deprecated: migrate to {replacement}."
        if status == "deprecated" and replacement
        else (f"Retired: migrate to {replacement}." if replacement else "Retired: no replacement is planned.")
    )
    if lifecycle_note not in hints:
        hints.append(lifecycle_note)
    payload["post_install_hints"] = hints
    metadata_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    changelog_note = (
        f"Deprecated in favor of `{replacement}`."
        if status == "deprecated"
        else (f"Retired in favor of `{replacement}`." if replacement else "Retired with no replacement.")
    )
    append_note_to_top_changelog(asset_dir / "CHANGELOG.md", changelog_note)
    ensure_catalog_entry(repo_root, load_skill_record(asset_dir))




