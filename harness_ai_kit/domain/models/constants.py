"""Shared constants for harness-ai-kit domain models (OSS build)."""
from __future__ import annotations

import re

CONFIG_FILENAME = "config.yaml"
LEGACY_CONFIG_FILENAME = "config.json"
REQUIRED_SKILL_FIELDS = ("id", "name", "owner", "version", "status", "entry")
REQUIRED_CLI_FIELDS = ("id", "name", "owner", "version", "status", "package_name", "install_type")
"""Registry defaults are intentionally empty.

The active registry is an operator concern and must be supplied through the
user's global config.yaml (or an explicit CI override). Keeping endpoints out
of executable defaults prevents a private deployment from becoming an OSS
source leak.
"""

DEFAULT_REGISTRY_UPLOAD_URL = ""
DEFAULT_REGISTRY_INDEX_URL = ""
REFERENCE_DOC_RE = re.compile(r"^REFERENCE-[A-Z0-9][A-Z0-9-]*\.md$")
# Loop 命名规范：`<domain>-<scenario>-loop`，域白名单复用 skill namespace 前缀
# （2026-08-15 命名归位治理后生效；新增域需显式扩展此白名单 + namespace-conventions.md）
LOOP_DOMAIN_PREFIXES = ("homelab", "infra", "devlab", "cnt", "fin", "base", "harness-ai-kit")
LOOP_ID_RE = re.compile(
    r"^(?:" + "|".join(LOOP_DOMAIN_PREFIXES) + r")-[a-z0-9]+(?:-[a-z0-9]+)*-loop$"
)
# 资产 namespace 治理（2026-08-16 统一 team/ 后生效）：
# namespace = 隔离域（内部=team/、对外=public/），分类职责由 id 前缀承担
TEAM_NAMESPACE = "team"
USAGE_PROMPT_SECTION_RE = re.compile(
    r"^##\s*(?:可直接复制的中文 Prompt|中文 Prompt)\s*$([\s\S]*?)(?=^##\s|\Z)",
    re.MULTILINE,
)
USAGE_PROMPT_CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
DEFAULT_SKILL_REGISTRY_UPLOAD_URL = ""
DEFAULT_SKILL_REGISTRY_INDEX_URL = ""
DEFAULT_CLI_REGISTRY_UPLOAD_URL = ""
DEFAULT_CLI_REGISTRY_INDEX_URL = ""
DEFAULT_NPM_REGISTRY_UPLOAD_URL = ""
DEFAULT_NPM_REGISTRY_INSTALL_URL = ""
DEFAULT_TRUSTED_HOST = ""
DEFAULT_TAG_PREFIX = "v"
PROJECT_MANIFEST_SCHEMA_VERSION = "2"
LEGACY_PROJECT_MANIFEST_SCHEMA_VERSION = "1"
MANAGED_ASSET_TYPES = ("skill", "plugin", "hook", "subagent", "mcp", "loop")
VERSIONED_ASSET_TYPES = ("cli", "plugin", "hook", "subagent", "mcp", "loop")
ALL_ASSET_TYPES = (*MANAGED_ASSET_TYPES, "cli")
ASSET_DIRECTORY_NAMES = {
    "skill": "skills",
    "plugin": "plugins",
    "hook": "hooks",
    "subagent": "subagents",
    "mcp": "mcps",
    "loop": "loops",
}
