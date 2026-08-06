"""CLI configuration dataclass."""
from __future__ import annotations

from dataclasses import dataclass

from .constants import (
    DEFAULT_CLI_REGISTRY_INDEX_URL,
    DEFAULT_CLI_REGISTRY_UPLOAD_URL,
    DEFAULT_REGISTRY_INDEX_URL,
    DEFAULT_REGISTRY_UPLOAD_URL,
    DEFAULT_SKILL_REGISTRY_INDEX_URL,
    DEFAULT_SKILL_REGISTRY_UPLOAD_URL,
    DEFAULT_TAG_PREFIX,
    DEFAULT_TRUSTED_HOST,
)


VALID_ROLES = ("consumer", "contributor", "maintainer")

# When role is unset, the CLI behaves as a consumer: registry-only installs,
# no dependency on a local repo checkout. Maintainers/contributors opt in
# explicitly via `ai-kit config set --role`.
DEFAULT_ROLE = "consumer"

# Ordered from least to most privileged; used for "at least" role gates.
_ROLE_RANK = {"consumer": 0, "contributor": 1, "maintainer": 2}


def effective_role(config: "CliConfig") -> str:
    """Return the effective role, defaulting to consumer when unset.

    The config file remains the source of truth (empty means "not set"); this
    helper only supplies the runtime default so unset machines behave as
    consumers without erroring.
    """
    role = (getattr(config, "role", "") or "").strip()
    return role if role in VALID_ROLES else DEFAULT_ROLE


def role_at_least(config: "CliConfig", minimum: str) -> bool:
    """True when the effective role is at least ``minimum`` in privilege."""
    return _ROLE_RANK.get(effective_role(config), 0) >= _ROLE_RANK.get(minimum, 0)


@dataclass(frozen=True)
class IdentityConfig:
    """Git identity for commits."""
    name: str = ""
    email: str = ""


@dataclass(frozen=True)
class DefaultsConfig:
    """Default runtime and scope preferences."""
    runtime: str = ""
    scope: str = ""
    install_external_immediately: bool = False


@dataclass(frozen=True)
class PublishConfig:
    """Configuration for publish-skill behavior."""
    git: bool = False
    push: bool = False
    pull_before_push: bool = True
    sync_repo: bool = True
    commit_prefix: str = "chore(skill):"


@dataclass(frozen=True)
class CliConfig:
    repo_url: str = ""
    checkout_dir: str = ""
    registry_upload_url: str = ""
    registry_index_url: str = ""
    skill_registry_upload_url: str = ""
    skill_registry_index_url: str = ""
    public_skill_registry_upload_url: str = ""
    public_skill_registry_index_url: str = ""
    cli_registry_upload_url: str = ""
    cli_registry_index_url: str = ""
    trusted_host: str = ""
    tag_prefix: str = DEFAULT_TAG_PREFIX
    publish: PublishConfig = PublishConfig()
    role: str = ""
    identity: IdentityConfig = IdentityConfig()
    defaults: DefaultsConfig = DefaultsConfig()
