from __future__ import annotations

import io
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from harness_ai_kit.product import active_product_profile


@dataclass(frozen=True)
class RuntimeProfile:
    runtime_id: str
    display_name: str
    status: str
    config_dirname: str | None  # 用于自动发现（如 ".claude", ".codex"）
    project_target: str | None
    global_target: str | None
    install_mode: str
    notes: str


RUNTIME_PROFILES: dict[str, RuntimeProfile] = {
    "codex": RuntimeProfile(
        runtime_id="codex",
        display_name="Codex",
        status="supported",
        config_dirname=".codex",
        project_target=".agents/skills",
        global_target="~/.codex/skills",
        install_mode="skill_dir",
        notes="Project scope installs raw team skills into the nearest .agents/skills directory.",
    ),
    "dsh": RuntimeProfile(
        runtime_id="dsh",
        display_name="DeepSeek Harness",
        status="supported",
        config_dirname=".dsh",
        project_target=".agents/skills",
        global_target="~/.agents/skills",
        install_mode="skill_dir",
        notes="DSH natively scans .agents/skills (rank 200) and ~/.agents/skills (rank 500); project target reuses the codex canonical directory.",
    ),
    "pi": RuntimeProfile(
        runtime_id="pi",
        display_name="Pi Coding Agent",
        status="supported",
        config_dirname=".pi",
        project_target=".agents/skills",
        global_target="~/.agents/skills",
        install_mode="skill_dir",
        notes="Pi natively scans .agents/skills, .pi/skills, ~/.agents/skills and ~/.pi/agent/skills (Agent Skills standard); project target reuses the codex canonical directory.",
    ),
    "claude-code": RuntimeProfile(
        runtime_id="claude-code",
        display_name="Claude Code",
        status="supported",
        config_dirname=".claude",
        project_target=".claude/skills",
        global_target="~/.claude/skills",
        install_mode="skill_dir",
        notes="Claude Code uses native skills directories in .claude/skills and ~/.claude/skills.",
    ),
    "kiro": RuntimeProfile(
        runtime_id="kiro",
        display_name="Kiro",
        status="supported",
        config_dirname=".kiro",
        project_target=".kiro/steering",
        global_target="~/.kiro/steering",
        install_mode="kiro_steering",
        notes="Kiro uses steering markdown in .kiro/steering or ~/.kiro/steering.",
    ),
    "cursor": RuntimeProfile(
        runtime_id="cursor",
        display_name="Cursor",
        status="supported",
        config_dirname=".cursor",
        project_target=".cursor/skills",
        global_target=None,
        install_mode="skill_dir",
        notes="Cursor native skills live in .cursor/skills (one directory per skill with SKILL.md). Global user skills live in ~/.cursor/skills.",
    ),
    "opencode": RuntimeProfile(
        runtime_id="opencode",
        display_name="OpenCode",
        status="supported",
        config_dirname=".opencode",
        project_target=".opencode/skills",
        global_target=None,
        install_mode="skill_dir",
        notes="OpenCode uses .opencode/skills directory.",
    ),
    "qoder": RuntimeProfile(
        runtime_id="qoder",
        display_name="Qoder",
        status="supported",
        config_dirname=".qoder",
        project_target=".qoder/skills",
        global_target=None,
        install_mode="skill_dir",
        notes="Qoder uses .qoder/skills directory.",
    ),
}

# Default runtime priority: earlier entries take precedence over later ones.
# Projects can override this in harness-ai-kit.yml via the `runtime_priority` field.
DEFAULT_RUNTIME_PRIORITY: list[str] = [
    "codex",
    "dsh",
    "pi",
    "qoder",
    "claude-code",
    "opencode",
    "kiro",
    "cursor",
]


# 配置目录名 → runtime_id 映射，用于自动发现
_CONFIG_DIR_TO_RUNTIME: dict[str, str] = {
    profile.config_dirname: rid
    for rid, profile in RUNTIME_PROFILES.items()
    if profile.config_dirname
}


def discover_available_runtimes(project_root: Path) -> list[str]:
    """扫描项目根目录的 runtime 配置目录，返回匹配的 runtime ID 列表。"""
    discovered = []
    for dirname, runtime_id in _CONFIG_DIR_TO_RUNTIME.items():
        if (project_root / dirname).is_dir():
            discovered.append(runtime_id)
    # .agents 始终视为可用（权威源）
    if "codex" not in discovered and (project_root / ".agents").is_dir():
        discovered.append("codex")
    return discovered


WrapperRenderer = Callable[[Path], str]


def _merge_extends_into_skill_dir(
    skill_dir: Path,
    extends_edges: list[dict],
    resolve_base_skill_md: Callable[[str], str | None],
) -> bool:
    """Merge base skill SKILL.md content into *skill_dir*.

    Called post-copy, pre-wrapper so that generated wrappers reflect merged
    content.  Uses the same merge semantics as :func:`skill_install.merge_skill_md`.
    """
    from harness_ai_kit.domain.skill_install import merge_skill_md as _msm

    skill_md_path = skill_dir / "SKILL.md"
    if not skill_md_path.exists() or not extends_edges:
        return False

    extending_content = skill_md_path.read_text(encoding="utf-8")
    merged = extending_content
    performed = False

    for ext_edge in extends_edges:
        base_canonical_id = str(ext_edge.get("base_skill_id", ""))
        base_version = str(ext_edge.get("base_version", ""))
        strategy = str(ext_edge.get("merge_strategy", "prepend"))
        sections = ext_edge.get("merge_sections") or None

        base_md = resolve_base_skill_md(base_canonical_id) if resolve_base_skill_md else None
        if base_md is None:
            continue

        merged = _msm(
            extending_md=merged,
            base_md=base_md,
            strategy=strategy,
            merge_sections=sections,
            base_canonical_id=base_canonical_id,
            base_version=base_version,
        )
        performed = True

    if performed:
        skill_md_path.write_text(merged, encoding="utf-8")

    return performed


def runtime_profile(runtime_id: str) -> RuntimeProfile:
    if runtime_id not in RUNTIME_PROFILES:
        available = ", ".join(sorted(RUNTIME_PROFILES))
        raise ValueError(f"Unsupported runtime: {runtime_id}. Available runtimes: {available}")
    return RUNTIME_PROFILES[runtime_id]


def runtime_asset_root(target_dir: Path, runtime_id: str) -> Path:
    if runtime_id in {"kiro", "cursor"}:
        return target_dir.parent / active_product_profile().runtime_skill_bundle_root
    return target_dir


def runtime_managed_asset_root(target_dir: Path) -> Path:
    """Return the canonical .agents directory for managed assets.

    Walks up from target_dir to find the project root (where .agents exists),
    then returns .agents/ directly. Falls back to target_dir.parent if no
    .agents directory is found in ancestors.
    """
    bundle = active_product_profile().managed_asset_bundle_root
    if bundle:
        return target_dir.parent / bundle
    # Walk up to find .agents (canonical asset root)
    current = target_dir.resolve()
    for candidate in [current, *current.parents]:
        agents_dir = candidate / ".agents"
        if agents_dir.is_dir():
            return agents_dir
    return target_dir.parent


def runtime_install_destination(target_dir: Path, skill_id: str, runtime_id: str) -> Path:
    profile = runtime_profile(runtime_id)
    if profile.install_mode == "skill_dir":
        return target_dir / skill_id
    if profile.install_mode == "kiro_steering":
        return target_dir / f"{active_product_profile().runtime_wrapper_prefix}-{skill_id}.md"
    if profile.install_mode == "cursor_rule":
        return target_dir / f"{active_product_profile().runtime_wrapper_prefix}-{skill_id}.mdc"
    raise ValueError(f"Unsupported install mode for runtime {runtime_id}: {profile.install_mode}")


def managed_asset_install_destination(
    target_dir: Path,
    asset_type: str,
    asset_id: str,
    asset_directory_names: dict[str, str],
) -> Path:
    return runtime_managed_asset_root(target_dir) / asset_directory_names[asset_type] / asset_id


def installed_skill_payload_dir(target_dir: Path, skill_id: str, runtime_id: str) -> Path:
    profile = runtime_profile(runtime_id)
    if profile.install_mode == "skill_dir":
        return target_dir / skill_id
    if profile.install_mode in {"kiro_steering", "cursor_rule"}:
        return runtime_asset_root(target_dir, runtime_id) / skill_id
    raise ValueError(f"Unsupported install mode for runtime {runtime_id}: {profile.install_mode}")


def install_skill_directory(
    skill_dir: Path,
    target_dir: Path,
    runtime_id: str,
    *,
    render_kiro_steering: WrapperRenderer,
    render_cursor_rule: WrapperRenderer,
    extends_edges: list[dict] | None = None,
    resolve_base_skill_md: Callable[[str], str | None] | None = None,
) -> Path:
    profile = runtime_profile(runtime_id)
    target_dir.mkdir(parents=True, exist_ok=True)

    if profile.install_mode == "skill_dir":
        destination = target_dir / skill_dir.name
        if destination.exists():
            shutil.copytree(skill_dir, destination, dirs_exist_ok=True)
        else:
            shutil.copytree(skill_dir, destination)

        # Merge extends post-copy so the SKILL.md on disk is merged
        if extends_edges:
            _merge_extends_into_skill_dir(destination, extends_edges, resolve_base_skill_md)

        return destination

    if profile.install_mode in {"kiro_steering", "cursor_rule"}:
        asset_root = runtime_asset_root(target_dir, runtime_id)
        asset_root.mkdir(parents=True, exist_ok=True)
        copied_skill_dir = asset_root / skill_dir.name
        if copied_skill_dir.exists():
            shutil.rmtree(copied_skill_dir)
        shutil.copytree(skill_dir, copied_skill_dir)

        # Merge extends BEFORE wrapper generation so wrappers consume merged content
        if extends_edges:
            _merge_extends_into_skill_dir(copied_skill_dir, extends_edges, resolve_base_skill_md)

        destination = runtime_install_destination(target_dir, skill_dir.name, runtime_id)
        if destination.exists():
            destination.unlink()
        if profile.install_mode == "kiro_steering":
            destination.write_text(render_kiro_steering(copied_skill_dir), encoding="utf-8")
        else:
            destination.write_text(render_cursor_rule(copied_skill_dir), encoding="utf-8")
        return destination

    raise ValueError(f"Unsupported install mode for runtime {runtime_id}: {profile.install_mode}")


def install_skill_archive_bytes(
    payload: bytes,
    target_dir: Path,
    runtime_id: str,
    *,
    render_kiro_steering: WrapperRenderer,
    render_cursor_rule: WrapperRenderer,
) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        top_levels = sorted({Path(name).parts[0] for name in archive.namelist() if name.strip("/")})
        if len(top_levels) != 1:
            raise ValueError("Skill archive must contain exactly one top-level skill directory.")
        skill_root = top_levels[0]
        profile = runtime_profile(runtime_id)
        if profile.install_mode == "skill_dir":
            destination = target_dir / skill_root
            if destination.exists():
                shutil.rmtree(destination)
            archive.extractall(target_dir)
            return destination

        asset_root = runtime_asset_root(target_dir, runtime_id)
        asset_root.mkdir(parents=True, exist_ok=True)
        destination = asset_root / skill_root
        if destination.exists():
            shutil.rmtree(destination)
        archive.extractall(asset_root)

        wrapper_path = runtime_install_destination(target_dir, skill_root, runtime_id)
        if wrapper_path.exists():
            wrapper_path.unlink()
        if profile.install_mode == "kiro_steering":
            wrapper_path.write_text(render_kiro_steering(destination), encoding="utf-8")
        elif profile.install_mode == "cursor_rule":
            wrapper_path.write_text(render_cursor_rule(destination), encoding="utf-8")
        else:
            raise ValueError(f"Unsupported install mode for runtime {runtime_id}: {profile.install_mode}")
        return wrapper_path


def resolve_target_dir(
    repo_root: Path,
    target_dir: str | None,
    cwd: Path | None = None,
    runtime_id: str = "codex",
    scope: str = "project",
    home_dir: Path | None = None,
) -> Path:
    from harness_ai_kit.infrastructure.config_io import default_home_dir

    base_cwd = cwd or Path.cwd()
    if target_dir:
        candidate = Path(target_dir)
        return (candidate if candidate.is_absolute() else base_cwd / candidate).resolve()

    profile = runtime_profile(runtime_id)
    if profile.status != "supported":
        raise ValueError(
            f"Runtime {runtime_id} is {profile.status} for skill installs. {profile.notes}"
        )

    if scope == "global":
        # Global scope always uses ~/.agents/skills/ as the canonical source,
        # regardless of runtime. Runtime-specific global dirs (~/.claude/skills etc.)
        # are handled by fan-out in project_sync.
        base_home = (home_dir or default_home_dir()).resolve()
        return (base_home / ".agents" / "skills").resolve()

    if runtime_id in {"codex", "dsh", "pi"}:
        for probe in [base_cwd, *base_cwd.parents]:
            candidate = probe / ".agents" / "skills"
            if candidate.exists():
                return candidate.resolve()
        return (base_cwd / ".agents" / "skills").resolve()

    if not profile.project_target:
        raise ValueError(f"Runtime {runtime_id} does not define a project skill target yet.")
    return (base_cwd / profile.project_target).resolve()


def should_skip_for_priority(
    target_dir: Path,
    skill_id: str,
    runtime_id: str,
    priority: list[str] | None = None,
) -> tuple[bool, str]:
    """Return (should_skip, reason) based on runtime priority.

    If a higher-priority runtime already has this skill installed, the
    current (lower-priority) runtime should skip installation to avoid
    duplicate copies and version drift.

    Args:
        target_dir: The resolved target directory for the current runtime.
        skill_id: The skill being installed.
        runtime_id: The runtime being installed to.
        priority: Ordered list of runtime IDs (highest priority first).
                  Defaults to DEFAULT_RUNTIME_PRIORITY.
    """
    effective_priority = priority or DEFAULT_RUNTIME_PRIORITY
    try:
        current_idx = effective_priority.index(runtime_id)
    except ValueError:
        return (False, "")

    if current_idx == 0:
        return (False, "")

    # Infer project root: walk up from target_dir until we find a parent
    # that contains target_dir as a direct child path component.
    project_root = target_dir.parent
    current_profile = RUNTIME_PROFILES.get(runtime_id)
    if current_profile and current_profile.project_target:
        segments = Path(current_profile.project_target).parts
        for _ in segments[:-1]:
            project_root = project_root.parent
    else:
        project_root = target_dir.parent.parent
    higher_priority_runtimes = effective_priority[:current_idx]

    for higher_rt in higher_priority_runtimes:
        if higher_rt not in RUNTIME_PROFILES:
            continue
        higher_profile = RUNTIME_PROFILES[higher_rt]
        if higher_profile.install_mode != "skill_dir":
            continue
        if higher_rt == "codex":
            higher_skills_dir = project_root / ".agents" / "skills"
        elif higher_profile.project_target:
            higher_skills_dir = project_root / higher_profile.project_target
        else:
            continue
        skill_path = higher_skills_dir / skill_id
        if skill_path.is_dir() and (skill_path / "SKILL.md").exists():
            return (
                True,
                f"Skipping {runtime_id} install: higher-priority runtime '{higher_rt}' "
                f"already has '{skill_id}' at {skill_path}.",
            )

    return (False, "")
