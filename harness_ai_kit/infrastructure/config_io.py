"""Configuration I/O: load, save, resolve config paths and repo roots."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml

from harness_ai_kit.domain.models import CliConfig
from harness_ai_kit.domain.models.config import PublishConfig, IdentityConfig, DefaultsConfig, VALID_ROLES
from harness_ai_kit.domain.models.constants import (
    CONFIG_FILENAME,
    LEGACY_CONFIG_FILENAME,
    DEFAULT_CLI_REGISTRY_INDEX_URL,
    DEFAULT_CLI_REGISTRY_UPLOAD_URL,
    DEFAULT_REGISTRY_INDEX_URL,
    DEFAULT_REGISTRY_UPLOAD_URL,
    DEFAULT_SKILL_REGISTRY_INDEX_URL,
    DEFAULT_SKILL_REGISTRY_UPLOAD_URL,
    DEFAULT_TAG_PREFIX,
    DEFAULT_TRUSTED_HOST,
)
from harness_ai_kit.product import active_product_profile

# Profile-dependent defaults (resolved once at import time)
_PROFILE = active_product_profile()
_DEFAULT_CONFIG_DIRNAME = _PROFILE.config_dirname
_DEFAULT_CHECKOUT_DIRNAME = _PROFILE.default_checkout_dirname
_DEFAULT_REPO_URL = _PROFILE.default_repo_url


def default_repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def default_home_dir() -> Path:
    return Path.home()


def default_config_path(home_dir: Path | None = None) -> Path:
    base_dir = home_dir or default_home_dir()
    return base_dir / _DEFAULT_CONFIG_DIRNAME / CONFIG_FILENAME


def default_checkout_dir(home_dir: Path | None = None) -> Path:
    base_dir = home_dir or default_home_dir()
    return (base_dir / _DEFAULT_CONFIG_DIRNAME / _DEFAULT_CHECKOUT_DIRNAME).resolve()


def pyproject_path(repo_root: Path) -> Path:
    return repo_root / "pyproject.toml"


def resolve_config_path(config_path: str | None) -> Path:
    if config_path:
        return Path(config_path).expanduser().resolve()
    resolved = default_config_path().resolve()
    _migrate_json_to_yaml(resolved.parent)
    return resolved


def _migrate_json_to_yaml(config_dir: Path) -> None:
    """Auto-migrate legacy config.json → config.yaml on first encounter.

    If ``config.json`` exists but ``config.yaml`` does not, convert the JSON
    data to YAML, write ``config.yaml``, and rename ``config.json`` to
    ``config.json.bak`` as a safety backup.
    """
    yaml_path = config_dir / CONFIG_FILENAME
    json_path = config_dir / LEGACY_CONFIG_FILENAME
    if yaml_path.exists() or not json_path.exists():
        return
    try:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        yaml_path.write_text(
            yaml.dump(payload, default_flow_style=False, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        backup = json_path.with_suffix(".json.bak")
        json_path.rename(backup)
        print(
            f"[harness-ai-kit] Migrated {json_path.name} → {yaml_path.name} "
            f"(backup: {backup.name})",
            file=sys.stderr,
        )
    except Exception as exc:
        print(
            f"[harness-ai-kit] WARNING: Failed to migrate {json_path} → {yaml_path}: {exc}",
            file=sys.stderr,
        )


def _load_publish_config(payload: dict[str, Any] | None) -> PublishConfig:
    if not payload or not isinstance(payload, dict):
        return PublishConfig()
    return PublishConfig(
        git=bool(payload.get("git", False)),
        push=bool(payload.get("push", False)),
        pull_before_push=bool(payload.get("pull_before_push", True)),
        sync_repo=bool(payload.get("sync_repo", True)),
        commit_prefix=str(payload.get("commit_prefix", "chore(skill):")).strip() or "chore(skill):",
    )


def _load_identity_config(payload: dict[str, Any] | None) -> IdentityConfig:
    if not payload or not isinstance(payload, dict):
        return IdentityConfig()
    return IdentityConfig(
        name=str(payload.get("name", "")).strip(),
        email=str(payload.get("email", "")).strip(),
    )


def _load_defaults_config(payload: dict[str, Any] | None) -> DefaultsConfig:
    if not payload or not isinstance(payload, dict):
        return DefaultsConfig()
    return DefaultsConfig(
        runtime=str(payload.get("runtime", "")).strip(),
        scope=str(payload.get("scope", "")).strip(),
        install_external_immediately=bool(payload.get("install_external_immediately", False)),
    )


def load_config(config_path: Path) -> CliConfig:
    if not config_path.exists():
        return CliConfig()

    text = config_path.read_text(encoding="utf-8")
    if config_path.suffix in (".yaml", ".yml"):
        payload = yaml.safe_load(text) or {}
    else:
        payload = json.loads(text)
    raw_role = str(payload.get("role", "")).strip()
    if raw_role and raw_role not in VALID_ROLES:
        raw_role = ""
    # CI/CD fallback only: env var applies when config.yaml has no role.
    # config.yaml stays the source of truth (higher priority than env).
    if not raw_role:
        env_role = str(os.environ.get("AI_KIT_ROLE", "")).strip()
        if env_role in VALID_ROLES:
            raw_role = env_role
    return CliConfig(
        repo_url=payload.get("repo_url", ""),
        checkout_dir=payload.get("checkout_dir", ""),
        registry_upload_url=payload.get("registry_upload_url", ""),
        registry_index_url=payload.get("registry_index_url", ""),
        skill_registry_upload_url=payload.get("skill_registry_upload_url", ""),
        skill_registry_index_url=payload.get("skill_registry_index_url", ""),
        public_skill_registry_upload_url=payload.get("public_skill_registry_upload_url", ""),
        public_skill_registry_index_url=payload.get("public_skill_registry_index_url", ""),
        cli_registry_upload_url=payload.get("cli_registry_upload_url", ""),
        cli_registry_index_url=payload.get("cli_registry_index_url", ""),
        trusted_host=payload.get("trusted_host", ""),
        tag_prefix=payload.get("tag_prefix", "v"),
        publish=_load_publish_config(payload.get("publish", {})),
        role=raw_role,
        identity=_load_identity_config(payload.get("identity", {})),
        defaults=_load_defaults_config(payload.get("defaults", {})),
    )


def _git_global_identity() -> tuple[str, str]:
    """Read user.name and user.email from git global config as fallback."""
    name, email = "", ""
    try:
        result = subprocess.run(
            ["git", "config", "--global", "user.name"],
            capture_output=True, text=True, encoding="utf-8", timeout=5,
        )
        if result.returncode == 0:
            name = result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    try:
        result = subprocess.run(
            ["git", "config", "--global", "user.email"],
            capture_output=True, text=True, encoding="utf-8", timeout=5,
        )
        if result.returncode == 0:
            email = result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return name, email


def effective_config(config: CliConfig, home_dir: Path | None = None) -> CliConfig:
    # Fallback identity from git global config
    git_name, git_email = "", ""
    if not config.identity.name.strip() or not config.identity.email.strip():
        git_name, git_email = _git_global_identity()
    resolved_identity = IdentityConfig(
        name=config.identity.name.strip() or git_name,
        email=config.identity.email.strip() or git_email,
    )
    return CliConfig(
        repo_url=config.repo_url.strip() or _DEFAULT_REPO_URL,
        checkout_dir=config.checkout_dir.strip() or str(default_checkout_dir(home_dir)),
        registry_upload_url=config.registry_upload_url.strip() or DEFAULT_REGISTRY_UPLOAD_URL,
        registry_index_url=config.registry_index_url.strip() or DEFAULT_REGISTRY_INDEX_URL,
        skill_registry_upload_url=config.skill_registry_upload_url.strip() or DEFAULT_SKILL_REGISTRY_UPLOAD_URL,
        skill_registry_index_url=config.skill_registry_index_url.strip() or DEFAULT_SKILL_REGISTRY_INDEX_URL,
        public_skill_registry_upload_url=config.public_skill_registry_upload_url.strip(),
        public_skill_registry_index_url=config.public_skill_registry_index_url.strip(),
        cli_registry_upload_url=config.cli_registry_upload_url.strip() or DEFAULT_CLI_REGISTRY_UPLOAD_URL,
        cli_registry_index_url=config.cli_registry_index_url.strip() or DEFAULT_CLI_REGISTRY_INDEX_URL,
        trusted_host=config.trusted_host.strip() or DEFAULT_TRUSTED_HOST,
        tag_prefix=config.tag_prefix.strip() or DEFAULT_TAG_PREFIX,
        publish=config.publish,
        role=config.role,
        identity=resolved_identity,
        defaults=config.defaults,
    )


def save_config(config: CliConfig, config_path: Path) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    data = asdict(config)
    # Preserve non-CliConfig top-level sections that the governance model keeps
    # in the same file (e.g. `global:` shared infra URLs and `assets:` per-CLI
    # config/credentials). Without this, `config set` would silently wipe them.
    if config_path.exists() and config_path.suffix in (".yaml", ".yml"):
        try:
            existing = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        except Exception:
            existing = {}
        if isinstance(existing, dict):
            preserved = {key: value for key, value in existing.items() if key not in data}
            data = {**data, **preserved}
    if config_path.suffix in (".yaml", ".yml"):
        config_path.write_text(
            yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
    else:
        config_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def console_safe_text(text: str) -> str:
    target_encoding = sys.stdout.encoding or "utf-8"
    return text.encode(target_encoding, errors="replace").decode(target_encoding, errors="replace")


# ---------------------------------------------------------------------------
# Nested (dotted-path) raw config access
#
# `config set KEY=VALUE` / `config get` / `config unset` operate on the raw
# YAML document so that governance sections (`global:`, `assets.<cli-id>:`)
# and any future nesting stay reachable without dedicated CLI flags.
# ---------------------------------------------------------------------------


def read_raw_config(config_path: Path) -> dict[str, Any]:
    """Load the raw config document (YAML/JSON) without dataclass coercion."""
    if not config_path.exists():
        return {}
    text = config_path.read_text(encoding="utf-8")
    if config_path.suffix in (".yaml", ".yml"):
        payload = yaml.safe_load(text) or {}
    else:
        payload = json.loads(text) if text.strip() else {}
    if not isinstance(payload, dict):
        raise ValueError(f"Config root must be a mapping, got {type(payload).__name__}: {config_path}")
    return payload


def write_raw_config(data: dict[str, Any], config_path: Path) -> None:
    """Persist the raw config document, preserving key order."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if config_path.suffix in (".yaml", ".yml"):
        config_path.write_text(
            yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
    else:
        config_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def split_config_key(dotted_key: str) -> list[str]:
    """Split a dotted config key into segments, rejecting empty parts."""
    segments = [segment.strip() for segment in dotted_key.split(".")]
    if not segments or any(not segment for segment in segments):
        raise ValueError(f"Invalid config key `{dotted_key}`: segments must be non-empty (e.g. assets.myctl.api_url).")
    return segments


def parse_config_scalar(raw_value: str) -> Any:
    """Parse a CLI-provided value string into a YAML scalar (bool/int/float/list/str)."""
    try:
        parsed = yaml.safe_load(raw_value)
    except yaml.YAMLError:
        return raw_value
    # yaml.safe_load("") -> None; keep explicit empty string as-is
    if parsed is None and raw_value.strip() not in ("", "null", "~", "None"):
        return raw_value
    return parsed


def get_nested_config_value(data: dict[str, Any], dotted_key: str) -> Any:
    """Return the value at a dotted path, raising KeyError when absent."""
    node: Any = data
    walked: list[str] = []
    for segment in split_config_key(dotted_key):
        walked.append(segment)
        if not isinstance(node, dict) or segment not in node:
            raise KeyError(f"Config key not found: {'.'.join(walked)}")
        node = node[segment]
    return node


def set_nested_config_value(data: dict[str, Any], dotted_key: str, value: Any) -> None:
    """Set a value at a dotted path, creating intermediate mappings as needed.

    Refuses to overwrite an existing scalar with a mapping level so that a typo
    like `role.extra=x` cannot silently destroy the managed `role` value.
    """
    segments = split_config_key(dotted_key)
    node = data
    for index, segment in enumerate(segments[:-1]):
        child = node.get(segment)
        if child is None:
            child = {}
            node[segment] = child
        elif not isinstance(child, dict):
            prefix = ".".join(segments[: index + 1])
            raise ValueError(
                f"Cannot set `{dotted_key}`: `{prefix}` already holds a non-mapping value ({child!r}). "
                f"Unset it first with `config unset {prefix}`."
            )
        node = child
    node[segments[-1]] = value


def unset_nested_config_value(data: dict[str, Any], dotted_key: str) -> None:
    """Delete the value at a dotted path and prune empty parent mappings."""
    segments = split_config_key(dotted_key)
    parents: list[tuple[dict[str, Any], str]] = []
    node: Any = data
    for segment in segments[:-1]:
        if not isinstance(node, dict) or segment not in node:
            raise KeyError(f"Config key not found: {dotted_key}")
        parents.append((node, segment))
        node = node[segment]
    if not isinstance(node, dict) or segments[-1] not in node:
        raise KeyError(f"Config key not found: {dotted_key}")
    del node[segments[-1]]
    # Prune now-empty intermediate mappings bottom-up.
    for parent, key in reversed(parents):
        child = parent.get(key)
        if isinstance(child, dict) and not child:
            del parent[key]
        else:
            break


def read_project_version(pyproject_file: Path) -> str:
    content = pyproject_file.read_text(encoding="utf-8")
    match = re.search(r'(?m)^version = "([^"]+)"$', content)
    if not match:
        raise ValueError(f"Unable to find project version in {pyproject_file}")
    return match.group(1)


def read_project_name(pyproject_file: Path) -> str:
    content = pyproject_file.read_text(encoding="utf-8")
    match = re.search(r'(?m)^name = "([^"]+)"$', content)
    if not match:
        raise ValueError(f"Unable to find project name in {pyproject_file}")
    return match.group(1)


def repo_looks_valid(repo_root: Path) -> bool:
    return (repo_root / ".git").exists() and (repo_root / "skills").is_dir()


def discover_repo_root(start_dir: Path) -> Path | None:
    current = start_dir.resolve()
    for candidate in (current, *current.parents):
        if repo_looks_valid(candidate):
            return candidate
    return None


def resolve_repo_root(repo_root_arg: str | None, config: CliConfig, cwd: Path | None = None) -> Path:
    if repo_root_arg:
        candidate = Path(repo_root_arg).expanduser().resolve()
        if repo_looks_valid(candidate):
            return candidate
        raise FileNotFoundError(f"Repository root is invalid: {candidate}")

    configured_checkout = config.checkout_dir.strip()
    if configured_checkout:
        candidate = Path(configured_checkout).expanduser().resolve()
        if repo_looks_valid(candidate):
            return candidate

    base_cwd = (cwd or Path.cwd()).resolve()
    discovered = discover_repo_root(base_cwd)
    if discovered:
        return discovered

    fallback = default_repo_root()
    if repo_looks_valid(fallback):
        return fallback

    raise FileNotFoundError(
        "Unable to resolve harness-ai-kit repository root. Run bootstrap first or pass --repo-root."
    )


def resolve_repo_root_if_available(repo_root_arg: str | None, config: CliConfig, cwd: Path | None = None) -> Path | None:
    try:
        return resolve_repo_root(repo_root_arg, config, cwd=cwd)
    except FileNotFoundError:
        return None


def read_top_changelog_version(changelog_path: Path) -> str | None:
    if not changelog_path.exists():
        return None
    content = changelog_path.read_text(encoding="utf-8")
    match = re.search(r"(?m)^##\s+\[?([0-9A-Za-z.+-]+)\]?(?:\s+-.*)?$", content)
    return match.group(1) if match else None


def read_json_file(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_project_version(pyproject_file: Path, new_version: str) -> None:
    content = pyproject_file.read_text(encoding="utf-8")
    updated, count = re.subn(
        r'(?m)^version = "([^"]+)"$',
        f'version = "{new_version}"',
        content,
        count=1,
    )
    if count != 1:
        raise ValueError(f"Unable to update project version in {pyproject_file}")
    pyproject_file.write_text(updated, encoding="utf-8")
