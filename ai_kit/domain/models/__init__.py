"""Domain models for ai-kit.

Re-exports all public symbols for convenient imports::

    from ai_kit.domain.models import SkillRecord, CliConfig, ProjectManifest
"""
from .config import CliConfig, DEFAULT_ROLE, VALID_ROLES, effective_role, role_at_least
from .constants import (
    ALL_ASSET_TYPES,
    ASSET_DIRECTORY_NAMES,
    CONFIG_FILENAME,
    DEFAULT_CLI_REGISTRY_INDEX_URL,
    DEFAULT_CLI_REGISTRY_UPLOAD_URL,
    DEFAULT_REGISTRY_INDEX_URL,
    DEFAULT_REGISTRY_UPLOAD_URL,
    DEFAULT_SKILL_REGISTRY_INDEX_URL,
    DEFAULT_SKILL_REGISTRY_UPLOAD_URL,
    DEFAULT_TAG_PREFIX,
    DEFAULT_TRUSTED_HOST,
    LEGACY_PROJECT_MANIFEST_SCHEMA_VERSION,
    MANAGED_ASSET_TYPES,
    PROJECT_MANIFEST_SCHEMA_VERSION,
    REFERENCE_DOC_RE,
    REQUIRED_CLI_FIELDS,
    REQUIRED_SKILL_FIELDS,
    USAGE_PROMPT_CJK_RE,
    USAGE_PROMPT_SECTION_RE,
    VERSIONED_ASSET_TYPES,
)
from .install_state import (
    CliInstallState,
    InstalledManagedAssetLocation,
    InstalledSkillLocation,
    ManagedAssetInstallState,
    SkillInstallState,
)
from .project_manifest import (
    ProjectManifest,
    ProjectManifestAssets,
    ProjectRootSpec,
    ProjectVersionedAssetSpec,
)
from .records import CliAssetRecord, SkillRecord

__all__ = [
    "CliAssetRecord",
    "CliConfig",
    "DEFAULT_ROLE",
    "VALID_ROLES",
    "effective_role",
    "role_at_least",
    "CliInstallState",
    "InstalledManagedAssetLocation",
    "InstalledSkillLocation",
    "ManagedAssetInstallState",
    "ProjectManifest",
    "ProjectManifestAssets",
    "ProjectRootSpec",
    "ProjectVersionedAssetSpec",
    "SkillInstallState",
    "SkillRecord",
]
