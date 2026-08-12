"""Shared constants for harness-ai-kit domain models (OSS build)."""
from __future__ import annotations

import re

CONFIG_FILENAME = "config.yaml"
LEGACY_CONFIG_FILENAME = "config.json"
REQUIRED_SKILL_FIELDS = ("id", "name", "owner", "version", "status", "entry")
REQUIRED_CLI_FIELDS = ("id", "name", "owner", "version", "status", "package_name", "install_type")
DEFAULT_REGISTRY_UPLOAD_URL = "https://upload.pypi.org/legacy/"
DEFAULT_REGISTRY_INDEX_URL = "https://pypi.org/simple"
REFERENCE_DOC_RE = re.compile(r"^REFERENCE-[A-Z0-9][A-Z0-9-]*\.md$")
USAGE_PROMPT_SECTION_RE = re.compile(
    r"^##\s*(?:可直接复制的中文 Prompt|中文 Prompt)\s*$([\s\S]*?)(?=^##\s|\Z)",
    re.MULTILINE,
)
USAGE_PROMPT_CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
DEFAULT_SKILL_REGISTRY_UPLOAD_URL = "https://raw.githubusercontent.com/seed-forge/harness-ai-kit/main/registry/skills/"
DEFAULT_SKILL_REGISTRY_INDEX_URL = "https://raw.githubusercontent.com/seed-forge/harness-ai-kit/main/registry/skills/index.json"
DEFAULT_CLI_REGISTRY_UPLOAD_URL = "https://raw.githubusercontent.com/seed-forge/harness-ai-kit/main/registry/clis/"
DEFAULT_CLI_REGISTRY_INDEX_URL = "https://raw.githubusercontent.com/seed-forge/harness-ai-kit/main/registry/clis/index.json"
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
