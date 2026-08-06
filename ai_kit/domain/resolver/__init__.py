"""Dependency resolver package.

Re-exports all public symbols from sub-modules so that existing
``from ai_kit.domain.resolver import ...`` imports continue to work.
"""
from .git_source import (
    DiscoveredGitSkill,
    GitRepoCheckout,
    GitSkillResolver,
    GitSourceSpec,
    default_git_repo_checkout,
    default_git_skill_resolver,
    discover_git_skills,
    git_skill_checkout_root,
    git_source_commit,
    git_source_repo_name,
    github_raw_metadata_url,
    is_git_source_selector,
    load_git_skill_manifest,
    loop_dirs_under,
    normalize_git_source_url,
    parse_git_source_ref,
    skill_dirs_under,
)
from .plan_builder import (
    DEFAULT_RESOLUTION_TIMEOUT,
    build_resolution_plan,
)
from .provider import (
    CircularExtendsError,
    RegistryManifestDownloader,
    RegistryUrlResolver,
    ResolutionProvider,
)

__all__ = [
    "CircularExtendsError",
    "DEFAULT_RESOLUTION_TIMEOUT",
    "DiscoveredGitSkill",
    "GitRepoCheckout",
    "GitSkillResolver",
    "GitSourceSpec",
    "RegistryManifestDownloader",
    "RegistryUrlResolver",
    "ResolutionProvider",
    "build_resolution_plan",
    "default_git_repo_checkout",
    "default_git_skill_resolver",
    "discover_git_skills",
    "git_skill_checkout_root",
    "git_source_commit",
    "git_source_repo_name",
    "github_raw_metadata_url",
    "is_git_source_selector",
    "load_git_skill_manifest",
    "loop_dirs_under",
    "normalize_git_source_url",
    "parse_git_source_ref",
    "skill_dirs_under",
]
