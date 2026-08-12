from __future__ import annotations

import re
import shutil
import tempfile
from pathlib import Path
from typing import Callable

from harness_ai_kit.domain.lockfile import Lockfile, LockNode
from harness_ai_kit.domain.lockfile_io import topological_skill_nodes_from_lock
from harness_ai_kit.domain.policies import SOURCE_GIT_REPO, SOURCE_PUBLIC_REGISTRY, SOURCE_REGISTRY, SOURCE_REPO
from harness_ai_kit.domain.runtime_install import runtime_install_destination, runtime_profile
from harness_ai_kit.domain.versions import compare_versions_safe


SkillVersionReader = Callable[[Path, str, str], str]
SkillChecksumReader = Callable[[Path, str, str], str]
SkillDirectoryInstaller = Callable[[Path, Path, str], Path]
RegistrySkillInstaller = Callable[[LockNode], Path]
SameVersionDriftWarner = Callable[[LockNode, str, str, str, str], bool]


def _build_extends_attribution(
    base_canonical_id: str,
    base_version: str,
    strategy: str,
) -> str:
    """Build the extends attribution HTML comment for merged SKILL.md."""
    if base_canonical_id:
        return f"<!-- Extends: {base_canonical_id}@{base_version} ({strategy}) -- Do not edit this line -->"
    return f"<!-- Extends: ({strategy}) -->"


def _filter_markdown_sections(md_text: str, section_names: list[str]) -> str:
    """Extract only named markdown sections from text.

    Parses ATX headings (``#`` through ``######``) and returns only sections
    whose heading text matches one of the given names.  Content before the
    first heading is always included.
    """
    if not section_names:
        return md_text

    lines = md_text.splitlines(keepends=True)
    result: list[str] = []
    current_lines: list[str] = []
    in_match: bool = False
    current_section: str | None = None

    heading_pattern = re.compile(r"^(#{1,6})\s+(.+?)(?:\s*\{.*\})?\s*$")

    for line in lines:
        match = heading_pattern.match(line)
        if match:
            if current_section is not None:
                if in_match:
                    result.extend(current_lines)
            else:
                # Before the first heading: always include preamble
                result.extend(current_lines)

            heading_text = match.group(2).strip()
            current_section = heading_text
            current_lines = [line]
            in_match = heading_text in section_names
        else:
            current_lines.append(line)

    # Flush the final section
    if current_section is None:
        result.extend(current_lines)
    elif in_match:
        result.extend(current_lines)

    return "".join(result)


def merge_skill_md(
    extending_md: str,
    base_md: str,
    strategy: str = "prepend",
    merge_sections: list[str] | None = None,
    base_canonical_id: str = "",
    base_version: str = "",
) -> str:
    """Merge extending skill SKILL.md content with base skill content.

    Supports three merge strategies:

    * ``replace`` -- Only extending content is used (base content ignored).
    * ``prepend``  -- Base content appears before extending content.
    * ``append``   -- Extending content appears before base content.

    Args:
        extending_md: The extending skill's SKILL.md content.
        base_md: The base (extended) skill's SKILL.md content.
        strategy: One of ``"replace"``, ``"prepend"``, ``"append"``.
        merge_sections: Optional list of markdown heading names to filter.
            When set, only those named sections are merged.
        base_canonical_id: Canonical ID of the base skill for attribution.
        base_version: Version of the base skill for attribution.

    Returns:
        Merged markdown content as a string.
    """
    attribution = _build_extends_attribution(base_canonical_id, base_version, strategy)

    if not extending_md.strip():
        if base_md.strip():
            return f"{attribution}\n{base_md}"
        return attribution

    if not base_md.strip():
        return (
            f"{attribution}\n"
            f"<!-- Warning: base skill has no SKILL.md content -->\n"
            f"{extending_md}"
        )

    if strategy == "replace":
        return f"{attribution}\n{extending_md}"

    if merge_sections:
        extending_md = _filter_markdown_sections(extending_md, merge_sections)
        base_md = _filter_markdown_sections(base_md, merge_sections)

    if strategy == "prepend":
        return f"{attribution}\n{base_md}\n\n{extending_md}"

    if strategy == "append":
        return f"{attribution}\n{extending_md}\n\n{base_md}"

    raise ValueError(
        f"Unknown merge strategy: {strategy}. Supported: prepend, append, replace."
    )


def _resolve_installed_skill_dir(
    installed_path: Path,
    target_dir: Path,
    runtime_id: str,
) -> Path:
    """Resolve the actual skill directory from an installed destination path.

    For ``skill_dir`` mode the installed path *is* the directory.
    For ``kiro_steering`` / ``cursor_rule`` mode the installed path is a
    wrapper file; the actual skill directory lives under the runtime asset root.
    """
    profile = runtime_profile(runtime_id)
    if profile.install_mode == "skill_dir":
        return installed_path
    # kiro_steering / cursor_rule: skill dir is under asset_root
    from harness_ai_kit.domain.runtime_install import runtime_asset_root

    asset_root = runtime_asset_root(target_dir, runtime_id)
    return asset_root / installed_path.stem


def _perform_extends_merge(
    node: LockNode,
    installed_dir: Path,
    target_dir: Path,
    runtime_id: str,
    lockfile: Lockfile,
    installed_skill_dirs: dict[str, Path],
    *,
    _merge_fn: Callable[..., str] | None = None,
) -> bool:
    """Merge base skill SKILL.md content into the extending skill's installed dir.

    Reads the extending skill's SKILL.md, locates each base skill's SKILL.md
    via *installed_skill_dirs*, calls :func:`merge_skill_md`, and writes the
    merged result back.

    Returns ``True`` if any merge was performed.
    """
    if not node.extends:
        return False

    merge_fn = _merge_fn or merge_skill_md
    extending_skill_md_path = installed_dir / "SKILL.md"
    if not extending_skill_md_path.exists():
        return False

    extending_content = extending_skill_md_path.read_text(encoding="utf-8")
    merged = extending_content
    performed = False

    for ext_edge in node.extends:
        base_canonical_id = str(ext_edge.get("base_skill_id", ""))
        base_version = str(ext_edge.get("base_version", ""))
        strategy = str(ext_edge.get("merge_strategy", "prepend"))
        sections = ext_edge.get("merge_sections") or None

        base_dir = installed_skill_dirs.get(base_canonical_id)
        if base_dir is None:
            continue

        base_skill_md_path = base_dir / "SKILL.md"
        if not base_skill_md_path.exists():
            continue

        base_content = base_skill_md_path.read_text(encoding="utf-8")
        merged = merge_fn(
            extending_md=merged,
            base_md=base_content,
            strategy=strategy,
            merge_sections=sections,
            base_canonical_id=base_canonical_id,
            base_version=base_version,
        )
        performed = True

    if performed:
        extending_skill_md_path.write_text(merged, encoding="utf-8")

    return performed


def _collect_installed_skill_dirs(
    installed_destinations: list[Path],
    nodes: list[LockNode],
    target_dir: Path,
    runtime_id: str,
) -> dict[str, Path]:
    """Build mapping from canonical_id to installed skill directory path."""
    mapping: dict[str, Path] = {}
    for node, installed_path in zip(nodes, installed_destinations):
        key = node.canonical_id or node.id
        mapping[key] = _resolve_installed_skill_dir(installed_path, target_dir, runtime_id)
    return mapping


def apply_skill_lockfile(
    lockfile: Lockfile,
    target_dir: Path,
    runtime_id: str,
    *,
    installed_version: SkillVersionReader,
    installed_materialized_checksum: SkillChecksumReader,
    install_skill_directory: SkillDirectoryInstaller,
    install_registry_skill: RegistrySkillInstaller,
    warn_same_version_drift: SameVersionDriftWarner,
) -> list[Path]:
    ordered_nodes = topological_skill_nodes_from_lock(lockfile)
    backups: list[tuple[Path, Path | None]] = []
    installed: list[Path] = []

    # Track installed skill directories indexed by canonical_id
    # so extends merge can resolve base skill SKILL.md paths.
    installed_skill_dirs: dict[str, Path] = {}

    def _base_skill_md_reader(base_canonical_id: str) -> str | None:
        base_dir = installed_skill_dirs.get(base_canonical_id)
        if base_dir is None:
            return None
        skill_md_path = base_dir / "SKILL.md"
        if skill_md_path.exists():
            return skill_md_path.read_text(encoding="utf-8")
        return None

    def _track_and_merge(node: LockNode, installed_path: Path) -> None:
        installed_dir = _resolve_installed_skill_dir(installed_path, target_dir, runtime_id)
        installed_skill_dirs[node.canonical_id or node.id] = installed_dir
        # Post-install merge: ensure SKILL.md on disk is merged for skill_dir mode.
        # For kiro/cursor mode the merge happens inside install_skill_directory
        # (pre-wrapper), but we also run it here as a safety net.
        _perform_extends_merge(
            node, installed_dir, target_dir, runtime_id,
            lockfile, installed_skill_dirs,
        )

    try:
        for node in ordered_nodes:
            destination = runtime_install_destination(target_dir, node.id, runtime_id)
            backup_path: Path | None = None
            if destination.exists():
                current_version = installed_version(target_dir, node.id, runtime_id)
                if current_version and compare_versions_safe(current_version, node.version) == 0:
                    warn_same_version_drift(
                        node,
                        runtime_id,
                        "target",
                        current_version,
                        installed_materialized_checksum(target_dir, node.id, runtime_id),
                    )
                    installed.append(destination)
                    backups.append((destination, None))
                    _track_and_merge(node, destination)
                    continue
                if node.source in {SOURCE_REPO, SOURCE_GIT_REPO}:
                    installed_path = install_skill_directory(
                        Path(node.source_ref or ""), target_dir, runtime_id,
                        extends_edges=node.extends,
                        resolve_base_skill_md=_base_skill_md_reader,
                    )
                    installed.append(installed_path)
                    backups.append((destination, None))
                    _track_and_merge(node, installed_path)
                    continue
                backup_root = Path(tempfile.mkdtemp(prefix=f"harness-ai-kit-backup-{node.id}-"))
                backup_path = backup_root / destination.name
                if backup_path.exists():
                    if backup_path.is_dir():
                        shutil.rmtree(backup_path, ignore_errors=True)
                    else:
                        backup_path.unlink()
                shutil.move(str(destination), str(backup_path))
            backups.append((destination, backup_path))
            if node.source in {SOURCE_REPO, SOURCE_GIT_REPO}:
                installed_path = install_skill_directory(
                    Path(node.source_ref or ""), target_dir, runtime_id,
                    extends_edges=node.extends,
                    resolve_base_skill_md=_base_skill_md_reader,
                )
                installed.append(installed_path)
                _track_and_merge(node, installed_path)
                continue
            if node.source in {SOURCE_REGISTRY, SOURCE_PUBLIC_REGISTRY}:
                installed_path = install_registry_skill(node)
                installed.append(installed_path)
                _track_and_merge(node, installed_path)
                continue
            raise ValueError(f"Unsupported install source for skill {node.id}: {node.source}")
        return installed
    except Exception:
        for destination, backup_path in reversed(backups):
            if destination.exists():
                if destination.is_dir():
                    shutil.rmtree(destination, ignore_errors=True)
                else:
                    destination.unlink()
            if backup_path and backup_path.exists():
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(backup_path), str(destination))
        raise
    finally:
        for _, backup_path in backups:
            if backup_path and backup_path.exists():
                if backup_path.is_dir():
                    shutil.rmtree(backup_path, ignore_errors=True)
                else:
                    backup_path.unlink()
                backup_root = backup_path.parent
                if backup_root.exists():
                    try:
                        backup_root.rmdir()
                    except OSError:
                        pass
