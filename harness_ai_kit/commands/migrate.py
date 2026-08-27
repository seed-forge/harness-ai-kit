"""One-click ``harness-ai-kit`` → ``harness-ai-kit`` migration.

Moves any remaining legacy runtime state into the canonical harness-ai-kit
locations so the legacy naming can be fully removed. Idempotent and safe:
existing target files are never overwritten.
"""
from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

from harness_ai_kit.product import active_product_profile

_LEGACY_HOME_DIRNAME = ".harness-ai-kit"
_LEGACY_MANIFEST = "harness-ai-kit.yml"
_LEGACY_LOCK = "harness-ai-kit.lock"

_HOME_ENTRIES = ("config.yaml", ".env.tak", "state", "cache", "shared-resources.yml")


def _move_entry(src: Path, dst: Path, dry_run: bool) -> str | None:
    """Move ``src`` into ``dst`` when ``dst`` is absent. Returns a description."""
    if not src.exists():
        return None
    if dst.exists():
        return None
    if dry_run:
        return f"[dry-run] move {src} -> {dst}"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    return f"moved {src} -> {dst}"


def _merge_dir(src: Path, dst: Path, dry_run: bool) -> list[str]:
    """Merge ``src`` children into ``dst``, moving only children absent in ``dst``."""
    if not src.is_dir():
        return []
    lines: list[str] = []
    for child in sorted(src.iterdir()):
        target = dst / child.name
        if target.exists():
            continue
        if dry_run:
            lines.append(f"[dry-run] move {child} -> {target}")
            continue
        dst.mkdir(parents=True, exist_ok=True)
        shutil.move(str(child), str(target))
        lines.append(f"moved {child} -> {target}")
    if not dry_run:
        try:
            src.rmdir()
        except OSError:
            pass  # non-empty: leave for manual review
    return lines


def _rewrite_manifest_ids(manifest_path: Path, dry_run: bool) -> list[str]:
    """Rewrite stale harness-ai-kit asset ids inside the canonical manifest.

    Idempotent: also fixes projects already migrated by an older CLI that only
    renamed the file. Returns human-readable action lines (empty = no change).
    """
    from harness_ai_kit.domain.asset_rename import rewrite_manifest_asset_ids
    from harness_ai_kit.domain.manifest_ops import load_project_manifest, save_project_manifest

    try:
        manifest = load_project_manifest(manifest_path)
    except Exception as exc:  # malformed manifest: report, never crash migrate
        return [f"skipped id rewrite for {manifest_path.name} (unreadable: {exc})"]
    changes = rewrite_manifest_asset_ids(manifest)
    if not changes:
        return []
    if dry_run:
        return [f"[dry-run] {manifest_path.name}: {line}" for line in changes]
    save_project_manifest(manifest_path, manifest)
    return [f"{manifest_path.name}: {line}" for line in changes]


def command_migrate(args: argparse.Namespace, config_path: Path) -> int:
    dry_run = bool(getattr(args, "dry_run", False))
    profile = active_product_profile()
    target_dirname = profile.config_dirname
    actions: list[str] = []

    # 1) Global runtime directory: ~/.harness-ai-kit → ~/.harness-ai-kit
    legacy_dir = Path.home() / _LEGACY_HOME_DIRNAME
    target_dir = Path.home() / target_dirname
    if legacy_dir.is_dir():
        for name in _HOME_ENTRIES:
            src, dst = legacy_dir / name, target_dir / name
            if src.is_dir() and dst.is_dir():
                actions.extend(_merge_dir(src, dst, dry_run))
            else:
                desc = _move_entry(src, dst, dry_run)
                if desc:
                    actions.append(desc)
        # Drop the legacy home dir once it is empty.
        if not dry_run:
            try:
                legacy_dir.rmdir()
                actions.append(f"removed empty {legacy_dir}")
            except OSError:
                actions.append(f"left non-empty {legacy_dir} for manual review")

    # 2) Project manifest + lockfile (nearest project up the tree)
    for base in [Path.cwd(), *Path.cwd().parents]:
        hits = [
            (base / _LEGACY_MANIFEST, base / profile.project_manifest_filename),
            (base / _LEGACY_LOCK, base / profile.lockfile_name),
        ]
        if not any(src.exists() for src, _ in hits):
            continue
        for src, dst in hits:
            desc = _move_entry(src, dst, dry_run)
            if desc:
                actions.append(desc)
        break

    # 2b) Rewrite stale harness-ai-kit asset ids inside the canonical manifest.
    #     Runs regardless of whether a legacy file was moved above, so projects
    #     already migrated (file renamed but ids not) are fixed idempotently.
    manifest_ids_rewritten = False
    for base in [Path.cwd(), *Path.cwd().parents]:
        manifest_path = base / profile.project_manifest_filename
        if manifest_path.exists():
            id_actions = _rewrite_manifest_ids(manifest_path, dry_run)
            if id_actions:
                actions.extend(id_actions)
                manifest_ids_rewritten = True
            break

    if not actions:
        print("Nothing to migrate: no legacy harness-ai-kit state found.")
    else:
        print(f"harness-ai-kit migration{' (dry-run)' if dry_run else ''}:")
        for line in actions:
            print(f"  {line}")

    if manifest_ids_rewritten and not dry_run:
        print("\nManifest asset ids were rewritten; the lockfile is now stale.")
        print("      Run `harness-ai-kit upgrade --all` (or `sync`) to refresh it.")

    # 3) Shell environment reminder (cannot be migrated from inside the CLI).
    if os.environ.get("HARNESS_AI_KIT_ROLE"):
        print("\nNote: HARNESS_AI_KIT_ROLE is set in your shell environment.")
        print("      Rename it to HARNESS_AI_KIT_ROLE in your shell profile.")
    return 0
