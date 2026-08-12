"""Git source parsing, discovery, and checkout helpers for the resolver."""
from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.parse import quote, urlparse

from harness_ai_kit.domain.artifacts import git_source_cache_path
from harness_ai_kit.domain.manifest import SkillManifest
from harness_ai_kit.domain.manifest_io import load_skill_manifest, manifest_metadata_path


GitRepoCheckout = Callable[[str, str | None], Path]


@dataclass(frozen=True)
class GitSourceSpec:
    source_ref: str
    clone_url: str
    ref: str | None = None
    subpath: str | None = None
    normalized_source_ref: str | None = None


@dataclass(frozen=True)
class DiscoveredGitSkill:
    namespace: str | None
    id: str
    source_ref: str
    ref: str | None
    subpath: str | None
    path: Path
    name: str
    summary: str = ""


def normalize_git_source_url(source_ref: str) -> str:
    return parse_git_source_ref(source_ref).clone_url


def _github_url_with_scheme(value: str) -> str:
    if value.lower().startswith("github.com/"):
        return f"https://{value}"
    return value


def _split_fragment_ref_and_subpath(fragment: str) -> tuple[str | None, str | None]:
    text = fragment.strip().strip("/")
    if not text:
        return None, None
    ref, _, subpath = text.partition("/")
    return ref or None, subpath or None


def parse_git_source_ref(source_ref: str) -> GitSourceSpec:
    value = source_ref.strip()
    if not value:
        raise ValueError("Git source_ref cannot be empty.")
    if re.match(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", value):
        return GitSourceSpec(
            source_ref=value,
            clone_url=f"https://github.com/{value}.git",
            normalized_source_ref=f"https://github.com/{value}",
        )
    if value.startswith("git@") or value.startswith("ssh://"):
        return GitSourceSpec(source_ref=value, clone_url=value, normalized_source_ref=value)
    parse_value = _github_url_with_scheme(value)
    parsed = urlparse(parse_value)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        fragment_ref, fragment_subpath = _split_fragment_ref_and_subpath(parsed.fragment)
        ref = fragment_ref
        subpath = fragment_subpath
        if parsed.netloc.lower() == "github.com":
            parts = [part for part in parsed.path.strip("/").split("/") if part]
            if len(parts) >= 2:
                repo = parts[1].removesuffix(".git")
                clone_url = f"https://github.com/{parts[0]}/{repo}.git"
                if len(parts) >= 4 and parts[2] == "tree":
                    ref = parts[3]
                    subpath = "/".join(parts[4:]) or None
                return GitSourceSpec(
                    source_ref=value,
                    clone_url=clone_url,
                    ref=ref,
                    subpath=subpath,
                    normalized_source_ref=f"https://github.com/{parts[0]}/{repo}",
                )
        return GitSourceSpec(source_ref=value, clone_url=parse_value, ref=ref, subpath=subpath, normalized_source_ref=parse_value)
    raise ValueError(f"Unsupported git source_ref: {source_ref}")


def git_source_repo_name(source_ref: str) -> str:
    source = parse_git_source_ref(source_ref)
    parsed = urlparse(source.clone_url)
    if parsed.path:
        name = Path(parsed.path).name.removesuffix(".git")
        if name:
            return name
    text = source_ref.rstrip("/")
    if "/" in text:
        return text.rsplit("/", 1)[-1].removesuffix(".git")
    return ""


def is_git_source_selector(value: str) -> bool:
    text = value.strip()
    if not text:
        return False
    if text.startswith(("git@", "ssh://")):
        return True
    parsed = urlparse(_github_url_with_scheme(text))
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def git_source_commit(checkout_dir: Path) -> str | None:
    if not (checkout_dir / ".git").exists():
        return None
    try:
        result = subprocess.run(
            ["git", "-C", str(checkout_dir), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    commit = result.stdout.strip()
    return commit or None


def github_raw_metadata_url(source_ref: str, commit: str | None, subpath: str | None) -> str | None:
    if not commit:
        return None
    source = parse_git_source_ref(source_ref)
    parsed = urlparse(source.clone_url)
    if parsed.netloc.lower() != "github.com":
        return None
    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if len(parts) < 2:
        return None
    repo = parts[1].removesuffix(".git")
    metadata_path = "/".join(part for part in [subpath, "skill.json"] if part)
    return (
        f"https://raw.githubusercontent.com/{quote(parts[0])}/{quote(repo)}/"
        f"{quote(commit)}/{quote(metadata_path, safe='/')}"
    )


def default_git_repo_checkout(source_ref: str, ref: str | None = None, *, force_refresh: bool = False) -> Path:
    source = parse_git_source_ref(source_ref)
    clone_url = source.clone_url
    effective_ref = ref or source.ref
    checkout_dir = git_source_cache_path(clone_url, effective_ref)
    if not (checkout_dir / ".git").exists():
        if checkout_dir.exists():
            shutil.rmtree(checkout_dir)
        checkout_dir.parent.mkdir(parents=True, exist_ok=True)
        command = ["git", "clone", "--depth", "1"]
        if effective_ref:
            command.extend(["--branch", effective_ref])
        command.extend([clone_url, str(checkout_dir)])
        subprocess.run(command, check=True, capture_output=True, text=True, encoding="utf-8", errors="replace")
    elif force_refresh:
        refresh_git_checkout(checkout_dir)
    return checkout_dir


def refresh_git_checkout(checkout_dir: Path) -> bool:
    """Force-fetch latest from remote.

    Returns ``True`` when new commits were retrieved (i.e. the local HEAD
    changed after the fetch), ``False`` otherwise.
    """
    if not (checkout_dir / ".git").exists():
        return False
    try:
        before = git_source_commit(checkout_dir)
        subprocess.run(
            ["git", "-C", str(checkout_dir), "fetch", "--depth", "1", "origin"],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        subprocess.run(
            ["git", "-C", str(checkout_dir), "reset", "--hard", "FETCH_HEAD"],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        after = git_source_commit(checkout_dir)
    except (OSError, subprocess.CalledProcessError):
        return False
    return before != after


def skill_dirs_under(root: Path) -> list[Path]:
    candidates: list[Path] = []
    if (root / "SKILL.md").exists():
        candidates.append(root)
    search_roots = [root / "skills", root]
    for search_root in search_roots:
        if not search_root.exists() or not search_root.is_dir():
            continue
        for child in sorted(item for item in search_root.iterdir() if item.is_dir() and item.name != ".git"):
            if (child / "SKILL.md").exists() and child not in candidates:
                candidates.append(child)
    if candidates:
        return candidates
    for skill_md in sorted(root.rglob("SKILL.md")):
        if ".git" in skill_md.parts:
            continue
        skill_dir = skill_md.parent
        try:
            skill_dir.relative_to(root)
        except ValueError:
            continue
        if len(skill_dir.relative_to(root).parts) <= 4 and skill_dir not in candidates:
            candidates.append(skill_dir)
    return candidates


def loop_dirs_under(root: Path) -> list[Path]:
    """Discover loop asset directories under a repo root (loops/ directory)."""
    candidates: list[Path] = []
    loops_root = root / "loops"
    if not loops_root.exists() or not loops_root.is_dir():
        return candidates
    for child in sorted(item for item in loops_root.iterdir() if item.is_dir() and item.name != ".git"):
        if (child / "loop.json").exists() and child not in candidates:
            candidates.append(child)
    return candidates


def load_git_skill_manifest(skill_dir: Path, fallback_id: str | None = None) -> SkillManifest:
    metadata_path = manifest_metadata_path(skill_dir)
    if metadata_path.exists():
        return load_skill_manifest(skill_dir)
    skill_id = (fallback_id or skill_dir.name).strip() or skill_dir.name
    return SkillManifest.model_validate(
        {
            "id": skill_id,
            "name": skill_id,
            "owner": "external",
            "version": "0.0.0",
            "status": "external",
            "entry": "SKILL.md",
            "package_type": "skill",
            "visibility": "public",
        }
    )


def discover_git_skills(
    source_ref: str,
    ref: str | None = None,
    subpath: str | None = None,
    *,
    git_repo_checkout: GitRepoCheckout = default_git_repo_checkout,
) -> list[DiscoveredGitSkill]:
    source = parse_git_source_ref(source_ref)
    effective_ref = ref or source.ref
    effective_subpath = subpath or source.subpath
    checkout_dir = git_repo_checkout(source_ref, effective_ref)
    base_dir = checkout_dir / effective_subpath if effective_subpath else checkout_dir
    if not base_dir.exists():
        raise KeyError(f"Git source subpath not found: {effective_subpath}")
    discovered: list[DiscoveredGitSkill] = []
    for skill_dir in skill_dirs_under(base_dir):
        relative_subpath = skill_dir.relative_to(checkout_dir).as_posix()
        fallback_id = git_source_repo_name(source_ref) if relative_subpath == "." else skill_dir.name
        manifest = load_git_skill_manifest(skill_dir, fallback_id=fallback_id)
        discovered.append(
            DiscoveredGitSkill(
                namespace=manifest.namespace,
                id=manifest.id,
                source_ref=source_ref,
                ref=effective_ref,
                subpath=relative_subpath if relative_subpath != "." else None,
                path=skill_dir,
                name=manifest.name,
                summary=manifest.summary,
            )
        )
    return discovered


def default_git_skill_resolver(source_ref: str, ref: str | None, subpath: str | None, skill_id: str) -> Path:
    source = parse_git_source_ref(source_ref)
    effective_ref = ref or source.ref
    effective_subpath = subpath or source.subpath
    checkout_dir = default_git_repo_checkout(source_ref, effective_ref)
    if effective_subpath:
        candidate = checkout_dir / effective_subpath
    elif (checkout_dir / "SKILL.md").exists():
        candidate = checkout_dir
    elif (checkout_dir / "skills" / skill_id / "SKILL.md").exists():
        candidate = checkout_dir / "skills" / skill_id
    else:
        candidate = checkout_dir / skill_id
    if not (candidate / "SKILL.md").exists():
        raise KeyError(f"Skill {skill_id} not found in git source {source_ref}.")
    if candidate.name == skill_id:
        return candidate
    materialized = checkout_dir.parent / f"{checkout_dir.name}-materialized" / skill_id
    if materialized.exists():
        shutil.rmtree(materialized)
    materialized.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(candidate, materialized, ignore=shutil.ignore_patterns(".git"))
    return materialized


def git_skill_checkout_root(skill_dir: Path, source_ref: str, ref: str | None) -> Path:
    source = parse_git_source_ref(source_ref)
    checkout_dir = git_source_cache_path(source.clone_url, ref or source.ref)
    if (checkout_dir / ".git").exists():
        return checkout_dir
    for parent in [skill_dir, *skill_dir.parents]:
        if (parent / ".git").exists():
            return parent
    return skill_dir


GitSkillResolver = Callable[[str, str | None, str | None, str], Path]
