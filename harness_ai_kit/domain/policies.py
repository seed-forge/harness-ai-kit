from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

SOURCE_REPO = "repo-checkout"
SOURCE_REGISTRY = "skill-registry"
SOURCE_WORKSPACE_REPO = SOURCE_REPO
SOURCE_INTERNAL_REGISTRY = SOURCE_REGISTRY
SOURCE_PUBLIC_REGISTRY = "public-registry"
SOURCE_GIT_REPO = "git-repo"
SOURCE_LOCAL_CACHE = "local-cache"
SOURCE_LOCKFILE = "lockfile"
SOURCE_MANUAL = "manual"
SUPPORTED_SOURCES = {
    SOURCE_REPO,
    SOURCE_REGISTRY,
    SOURCE_PUBLIC_REGISTRY,
    SOURCE_GIT_REPO,
    SOURCE_LOCAL_CACHE,
    SOURCE_LOCKFILE,
}
LEGACY_SOURCE_ALIASES = {
    "repo": SOURCE_REPO,
    "registry": SOURCE_REGISTRY,
    SOURCE_WORKSPACE_REPO: SOURCE_REPO,
    SOURCE_INTERNAL_REGISTRY: SOURCE_REGISTRY,
}
INSTALL_SOURCE_SELECTORS = {
    "auto",
    SOURCE_WORKSPACE_REPO,
    SOURCE_INTERNAL_REGISTRY,
    SOURCE_PUBLIC_REGISTRY,
    SOURCE_GIT_REPO,
    "repo",
    "registry",
}


def normalize_source_name(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return LEGACY_SOURCE_ALIASES.get(text, text)


def display_source_name(value: str | None) -> str:
    normalized = normalize_source_name(value)
    return normalized or "-"


def selectable_install_source(value: str | None) -> str | None:
    normalized = normalize_source_name(value)
    if normalized is None or normalized == "auto":
        return None
    if normalized not in {
        SOURCE_WORKSPACE_REPO,
        SOURCE_INTERNAL_REGISTRY,
        SOURCE_PUBLIC_REGISTRY,
        SOURCE_GIT_REPO,
    }:
        raise ValueError(f"Unsupported install source selector: {value}")
    return normalized


def source_order_for_selector(selector: str | None) -> list[str] | None:
    selected = selectable_install_source(selector)
    if selected is None:
        return None
    if selected == SOURCE_WORKSPACE_REPO:
        return [SOURCE_REPO]
    return [selected]


def consumer_source_order() -> list[str]:
    """Source order for the consumer role: registry-only, no local repo/git.

    Consumers never depend on a local repo checkout, so we skip repo-checkout
    and git-repo entirely and resolve straight from the private registry
    (falling back to the public registry when configured).
    """
    return [SOURCE_REGISTRY, SOURCE_PUBLIC_REGISTRY]


class SourcePolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preferred: list[
        Literal[
            "repo-checkout",
            "skill-registry",
            "public-registry",
            "git-repo",
            "local-cache",
            "lockfile",
        ]
    ] = Field(
        default_factory=lambda: [SOURCE_REPO, SOURCE_REGISTRY, SOURCE_PUBLIC_REGISTRY, SOURCE_GIT_REPO]
    )
    allow_fallback: bool = True

    @field_validator("preferred")
    @classmethod
    def validate_preferred(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("At least one preferred source is required.")
        normalized = [normalize_source_name(item) or "" for item in value]
        unknown = [item for item in normalized if item not in SUPPORTED_SOURCES]
        if unknown:
            raise ValueError(f"Unsupported sources: {', '.join(unknown)}")
        deduped: list[str] = []
        for item in normalized:
            if item not in deduped:
                deduped.append(item)
        return deduped


class InstallationPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default_scope: Literal["project", "global"] = "project"
    install_mode: Literal["skill_dir", "bundle", "manual"] = "skill_dir"
