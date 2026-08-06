from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any

import yaml

from ..domain import project_sync_presentation, report_presentation
from ..domain.models.config import IdentityConfig, DefaultsConfig, PublishConfig, VALID_ROLES, effective_role
from ..infrastructure.config_io import (
    get_nested_config_value,
    parse_config_scalar,
    read_raw_config,
    set_nested_config_value,
    unset_nested_config_value,
    write_raw_config,
)


def _parse_config_pairs(pairs: list[str]) -> list[tuple[str, Any]]:
    """Parse `KEY=VALUE` assignments into (dotted_key, parsed_value) tuples.

    Managed top-level keys keep their validation (currently `role`).
    """
    parsed: list[tuple[str, Any]] = []
    for pair in pairs:
        key, separator, raw_value = pair.partition("=")
        key = key.strip()
        if not separator or not key:
            raise ValueError(f"Invalid assignment `{pair}`: expected KEY=VALUE, e.g. assets.myctl.api_url=https://...")
        value = parse_config_scalar(raw_value)
        if key == "role":
            if value not in VALID_ROLES:
                raise ValueError(f"Invalid role: {value}. Must be one of: {', '.join(VALID_ROLES)}")
        parsed.append((key, value))
    return parsed


def _merge_seed_config(config_path: Path) -> bool:
    """Merge global defaults from config-seed.yaml into config.yaml.

    Only merges the 'global' section; does not overwrite existing values.
    Returns True if seed was merged, False if skipped or already present.
    """
    seed_path = files("ai_kit").joinpath("data", "config-seed.yaml")
    try:
        seed_text = seed_path.read_text(encoding="utf-8")
    except (FileNotFoundError, TypeError):
        return False

    seed = yaml.safe_load(seed_text)
    if not isinstance(seed, dict) or "global" not in seed:
        return False

    # Read existing config
    if config_path.exists():
        existing = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    else:
        existing = {}

    # Only merge if 'global' section doesn't already exist
    if "global" in existing:
        return False

    existing["global"] = seed["global"]
    config_path.write_text(
        yaml.safe_dump(existing, default_flow_style=False, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return True


def _resolve_bool(cli_value: str | None, current: bool) -> bool:
    """Resolve a boolean config value from CLI arg (\"true\"/\"false\") or current value."""
    if cli_value is None:
        return current
    return cli_value.lower() == "true"


@dataclass(frozen=True)
class BootstrapCommandContext:
    load_config: Callable[[Path], Any]
    effective_config: Callable[[Any], Any]
    save_config: Callable[[Any, Path], None]
    create_config: Callable[..., Any]
    default_checkout_dir: Callable[[], Path]
    ensure_checkout: Callable[[str, Path, bool], str]
    resolve_repo_root: Callable[[str | None, Any], Path]
    sync_repo: Callable[[Path], str]
    defaults: Mapping[str, str]


def build_bootstrap_handlers(context: BootstrapCommandContext) -> Mapping[str, Callable[[argparse.Namespace, Path], int]]:
    return {
        "config": lambda args, config_path: command_config(args, config_path, context),
        "init": lambda args, config_path: command_init(args, config_path, context),
        "bootstrap": lambda args, config_path: command_bootstrap(args, config_path, context),
        "sync-repo": lambda args, config_path: command_sync_repo(args, config_path, context),
        "whoami": lambda args, config_path: command_whoami(args, config_path, context),
    }


def command_config(args: argparse.Namespace, config_path: Path, context: BootstrapCommandContext) -> int:
    config = context.load_config(config_path)
    if args.config_command == "get":
        raw = read_raw_config(config_path)
        try:
            value = get_nested_config_value(raw, args.key)
        except KeyError as exc:
            print(f"Error: {exc.args[0]}")
            return 1
        if getattr(args, "json", False):
            print(json.dumps(value, ensure_ascii=False, indent=2))
        elif isinstance(value, (dict, list)):
            print(yaml.safe_dump(value, default_flow_style=False, allow_unicode=True, sort_keys=False).rstrip())
        else:
            print(value)
        return 0

    if args.config_command == "unset":
        raw = read_raw_config(config_path)
        for dotted_key in args.keys:
            try:
                unset_nested_config_value(raw, dotted_key)
            except KeyError as exc:
                print(f"Error: {exc.args[0]}")
                return 1
            print(f"Unset: {dotted_key}")
        write_raw_config(raw, config_path)
        print(f"Saved: {config_path}")
        return 0

    if args.config_command == "show":
        payload = {
            "repo_url": config.repo_url,
            "checkout_dir": config.checkout_dir,
            "registry_upload_url": config.registry_upload_url,
            "registry_index_url": config.registry_index_url,
            "skill_registry_upload_url": config.skill_registry_upload_url,
            "skill_registry_index_url": config.skill_registry_index_url,
            "public_skill_registry_upload_url": config.public_skill_registry_upload_url,
            "public_skill_registry_index_url": config.public_skill_registry_index_url,
            "cli_registry_upload_url": config.cli_registry_upload_url,
            "cli_registry_index_url": config.cli_registry_index_url,
            "trusted_host": config.trusted_host,
            "tag_prefix": config.tag_prefix,
            "role": config.role or "(not set)",
            "identity.name": config.identity.name or "(not set)",
            "identity.email": config.identity.email or "(not set)",
            "defaults.runtime": config.defaults.runtime or "(not set)",
            "defaults.scope": config.defaults.scope or "(not set)",
            "defaults.install_external_immediately": config.defaults.install_external_immediately,
            "publish.git": config.publish.git,
            "publish.push": config.publish.push,
            "publish.sync_repo": config.publish.sync_repo,
            "publish.commit_prefix": config.publish.commit_prefix,
            "config_path": str(config_path),
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            for key, value in payload.items():
                print(f"{key}: {value}")
        return 0

    if args.config_command == "set":
        # Fail fast on malformed KEY=VALUE pairs before any write happens.
        pairs = _parse_config_pairs(list(getattr(args, "pairs", []) or []))
        new_role = getattr(args, "role", None)
        if new_role is not None and new_role not in VALID_ROLES:
            raise ValueError(f"Invalid role: {new_role}. Must be one of: {', '.join(VALID_ROLES)}")
        new_identity = IdentityConfig(
            name=(getattr(args, "identity_name", None) or config.identity.name).strip(),
            email=(getattr(args, "identity_email", None) or config.identity.email).strip(),
        )
        new_defaults = DefaultsConfig(
            runtime=(getattr(args, "default_runtime", None) or config.defaults.runtime).strip(),
            scope=(getattr(args, "default_scope", None) or config.defaults.scope).strip(),
            install_external_immediately=_resolve_bool(
                getattr(args, "install_external_immediately", None),
                config.defaults.install_external_immediately,
            ),
        )
        next_config = context.create_config(
            repo_url=(args.repo_url if args.repo_url is not None else config.repo_url).strip(),
            checkout_dir=_resolved_checkout_dir(args.checkout_dir if args.checkout_dir is not None else config.checkout_dir),
            registry_upload_url=(args.registry_upload_url if args.registry_upload_url is not None else config.registry_upload_url).strip(),
            registry_index_url=(args.registry_index_url if args.registry_index_url is not None else config.registry_index_url).strip(),
            skill_registry_upload_url=(args.skill_registry_upload_url if args.skill_registry_upload_url is not None else config.skill_registry_upload_url).strip(),
            skill_registry_index_url=(args.skill_registry_index_url if args.skill_registry_index_url is not None else config.skill_registry_index_url).strip(),
            public_skill_registry_upload_url=(args.public_skill_registry_upload_url if args.public_skill_registry_upload_url is not None else config.public_skill_registry_upload_url).strip(),
            public_skill_registry_index_url=(args.public_skill_registry_index_url if args.public_skill_registry_index_url is not None else config.public_skill_registry_index_url).strip(),
            cli_registry_upload_url=(args.cli_registry_upload_url if args.cli_registry_upload_url is not None else config.cli_registry_upload_url).strip(),
            cli_registry_index_url=(args.cli_registry_index_url if args.cli_registry_index_url is not None else config.cli_registry_index_url).strip(),
            trusted_host=(args.trusted_host if args.trusted_host is not None else config.trusted_host).strip(),
            tag_prefix=((args.tag_prefix if args.tag_prefix is not None else config.tag_prefix).strip() or context.defaults["tag_prefix"]),
            role=(new_role if new_role is not None else config.role),
            identity=new_identity,
            defaults=new_defaults,
        )
        context.save_config(next_config, config_path)
        # Apply dotted-path assignments on top of the dataclass write so that
        # nested sections (assets.<cli-id>.*, global.*, custom keys) are
        # first-class citizens of `config set`.
        if pairs:
            raw = read_raw_config(config_path)
            for dotted_key, value in pairs:
                set_nested_config_value(raw, dotted_key, value)
                print(f"Set: {dotted_key} = {value}")
            write_raw_config(raw, config_path)
        for line in project_sync_presentation.config_set_success_lines(config_path=config_path):
            print(line)
        # Hint when switching to roles that need repo access
        if new_role in ("contributor", "maintainer") and not config.role:
            checkout_dir = Path((next_config.checkout_dir or "").strip() or context.default_checkout_dir()).expanduser().resolve()
            print(f"")
            print("Hint: You switched to a role that uses Git repository access.")
            print(f"     Next step: run `ai-kit bootstrap` to clone the repository to {checkout_dir}.")
            print("     If you don't have repository credentials configured, clone will fail with git authentication errors.")
        return 0

    raise ValueError(f"Unsupported config command: {args.config_command}")


ROLE_DESCRIPTIONS = {
    "consumer": "Install, sync, list, show, cat, upgrade shared assets (read-only).",
    "contributor": "All consumer capabilities + create, submit, publish-skill (read + write).",
    "maintainer": "All contributor capabilities + deprecate, retire, rename, catalog management (full governance).",
}


def command_whoami(args: argparse.Namespace, config_path: Path, context: BootstrapCommandContext) -> int:
    import os
    
    raw_config = context.load_config(config_path)
    config = context.effective_config(raw_config)
    effective = effective_role(config)
    
    # Determine role source
    if raw_config.role.strip():
        role_source = "config.yaml"
        env_override_note = ""
    elif os.environ.get("AI_KIT_ROLE"):
        role_source = "config.yaml (env var AI_KIT_ROLE overrides temporarily)"
        env_override_note = f" (temp override: {os.environ['AI_KIT_ROLE']})"
    else:
        role_source = "default (consumer)"
        env_override_note = ""
    
    role_desc = ROLE_DESCRIPTIONS.get(effective, "Run `ai-kit config set --role <role>` to choose: consumer, contributor, or maintainer.")
    
    # Role permissions summary
    permissions = {
        "consumer": ["Read-only operations", "Install from registry", "Local sync"],
        "contributor": ["Consumer + dry-run writes", "Draft submission"],
        "maintainer": ["Full write access", "Publish to Nexus", "Governance"]
    }
    perm_list = "; ".join(permissions.get(effective, []))
    
    print(f"Role:      {effective}{env_override_note}")
    print(f"Source:    {role_source}")
    print(f"Permits:   {perm_list}")
    print(f"Description:\n           {role_desc}")
    
    # Existing identity output...
    explicit_name = bool(raw_config.identity.name.strip())
    explicit_email = bool(raw_config.identity.email.strip())
    name_source = "config" if explicit_name else ("git" if config.identity.name else "not set")
    email_source = "config" if explicit_email else ("git" if config.identity.email else "not set")
    print(f"Name:      {config.identity.name or '(not set)'} ({name_source})")
    print(f"Email:     {config.identity.email or '(not set)'} ({email_source})")
    print(f"Runtime:   {config.defaults.runtime or '(not set)'}")
    print(f"Scope:     {config.defaults.scope or '(not set)'}")
    print(f"InstallExt:{'auto' if config.defaults.install_external_immediately else 'manual'}  (config set --install-external-immediately true/false)")
    print(f"Git:       {config.publish.git}  Push: {config.publish.push}")
    print(f"Config:    {config_path}")
    if not raw_config.role.strip() and not os.environ.get("AI_KIT_ROLE"):
        print()
        print("Hint: role not set — running as consumer (registry-only installs, no local repo needed).")
        print("      Maintainers/contributors opt in: `ai-kit config set --role maintainer` (or contributor).")
    return 0


def command_init(args: argparse.Namespace, config_path: Path, context: BootstrapCommandContext) -> int:
    config = context.effective_config(context.load_config(config_path))
    next_config = context.create_config(
        repo_url=(args.repo_url or config.repo_url).strip() or context.defaults["repo_url"],
        checkout_dir=str(Path((args.checkout_dir or config.checkout_dir).strip() or context.default_checkout_dir()).expanduser().resolve()),
        registry_upload_url=(args.registry_upload_url or config.registry_upload_url).strip() or context.defaults["registry_upload_url"],
        registry_index_url=(args.registry_index_url or config.registry_index_url).strip() or context.defaults["registry_index_url"],
        skill_registry_upload_url=(args.skill_registry_upload_url or config.skill_registry_upload_url).strip() or context.defaults["skill_registry_upload_url"],
        skill_registry_index_url=(args.skill_registry_index_url or config.skill_registry_index_url).strip() or context.defaults["skill_registry_index_url"],
        public_skill_registry_upload_url=(args.public_skill_registry_upload_url or config.public_skill_registry_upload_url).strip(),
        public_skill_registry_index_url=(args.public_skill_registry_index_url or config.public_skill_registry_index_url).strip(),
        cli_registry_upload_url=(args.cli_registry_upload_url or config.cli_registry_upload_url).strip() or context.defaults["cli_registry_upload_url"],
        cli_registry_index_url=(args.cli_registry_index_url or config.cli_registry_index_url).strip() or context.defaults["cli_registry_index_url"],
        trusted_host=(args.trusted_host or config.trusted_host).strip() or context.defaults["trusted_host"],
        tag_prefix=(args.tag_prefix or config.tag_prefix).strip() or context.defaults["tag_prefix"],
        role=config.role,
    )
    context.save_config(next_config, config_path)
    # Seed global defaults on first init
    if _merge_seed_config(config_path):
        print("[init] Merged global infrastructure defaults from config-seed.yaml")
    if effective_role(next_config) == "consumer":
        # Consumers never depend on a local repo checkout: skills/CLIs install
        # straight from the registry. Skip the git clone entirely.
        message = "consumer role: skipped repo clone (skills/CLIs install from the registry)"
    else:
        message = context.ensure_checkout(next_config.repo_url, Path(next_config.checkout_dir), sync_after_clone=not args.skip_sync, no_git_proxy=getattr(args, "no_git_proxy", False))
    for line in project_sync_presentation.init_success_lines(checkout_message=message, config_path=config_path):
        print(line)
    return 0


def command_bootstrap(args: argparse.Namespace, config_path: Path, context: BootstrapCommandContext) -> int:
    config = context.effective_config(context.load_config(config_path))
    repo_url = (args.repo_url or config.repo_url).strip()
    if not repo_url:
        raise ValueError("bootstrap requires --repo-url when no saved repo URL exists.")

    checkout_dir_arg = (args.checkout_dir or config.checkout_dir).strip()
    checkout_dir = Path(checkout_dir_arg).expanduser().resolve() if checkout_dir_arg else context.default_checkout_dir()

    if effective_role(config) == "consumer":
        # Consumers resolve assets from the registry; no local repo clone needed.
        message = "consumer role: skipped repo clone (skills/CLIs install from the registry)"
    else:
        message = context.ensure_checkout(repo_url, checkout_dir, sync_after_clone=args.sync, no_git_proxy=getattr(args, "no_git_proxy", False))
    context.save_config(
        context.create_config(
            repo_url=repo_url,
            checkout_dir=str(checkout_dir),
            registry_upload_url=config.registry_upload_url,
            registry_index_url=config.registry_index_url,
            skill_registry_upload_url=config.skill_registry_upload_url,
            skill_registry_index_url=config.skill_registry_index_url,
            public_skill_registry_upload_url=config.public_skill_registry_upload_url,
            public_skill_registry_index_url=config.public_skill_registry_index_url,
            cli_registry_upload_url=config.cli_registry_upload_url,
            cli_registry_index_url=config.cli_registry_index_url,
            trusted_host=config.trusted_host,
            tag_prefix=config.tag_prefix,
            role=config.role,
        ),
        config_path,
    )
    # Seed global defaults on first bootstrap
    if _merge_seed_config(config_path):
        print("[bootstrap] Merged global infrastructure defaults from config-seed.yaml")
    for line in project_sync_presentation.bootstrap_success_lines(checkout_message=message):
        print(line)
    return 0


def command_sync_repo(args: argparse.Namespace, config_path: Path, context: BootstrapCommandContext) -> int:
    config = context.load_config(config_path)
    repo_root = context.resolve_repo_root(getattr(args, "repo_root", None), config)
    message = context.sync_repo(repo_root)
    for line in report_presentation.sync_repo_success_lines(message=message):
        print(line)
    return 0


def _resolved_checkout_dir(value: str) -> str:
    return str(Path(value).expanduser().resolve()) if value.strip() else ""
    return str(Path(value).expanduser().resolve()) if value.strip() else ""
