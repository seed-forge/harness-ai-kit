#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.metadata
import io
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from base64 import b64encode
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Literal, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator
import yaml

if __package__:
    from . import package_manager as pm
    from .application.project_manifest import ProjectManifestPorts, ProjectManifestService
    from .commands.assembly import (
        build_bootstrap_handler_map,
        build_health_handler_map,
        build_inspect_handler_map,
        build_install_handler_map,
        build_project_command_context,
        build_resolution_handler_map,
        build_upgrade_handler_map,
    )
    from .commands.bind import command_bind
    from .commands.use import command_use
    from .commands.shared_resources import (
        command_shared_resources_list,
        command_shared_resources_add,
        command_shared_resources_use,
        command_shared_resources_remove,
    )
    from .commands.cache import command_cache
    from .commands.config_cmd import command_config
    from .commands.dispatch import CommandRouter
    from .commands.errors import HANDLED_COMMAND_EXCEPTIONS, command_error_message
    from .main_bridge import activate_main_bridge
    from .product import ProductProfile, activate_product, active_product_profile
    from .commands.parser_builders import (
        add_asset_config_parser,
        add_config_bootstrap_parsers,
        add_inspect_resolution_parsers,
        add_project_runtime_parsers,
    )
    from .commands.project import build_project_config_handlers, build_project_plain_handlers
    from .commands.routes import register_command_routes
    from .domain import cli_assets
    from .domain import managed_assets
    from .domain import managed_install
    from .domain import materialization
    from .domain import project_state
    from .domain import project_manifest_state
    from .domain import project_locking
    from .domain import project_sync
    from .domain import project_sync_presentation
    from .domain import project_sync_results
    from .domain import report_presentation
    from .domain import runtime_install
    from .domain import skill_install
    from .domain.versions import (
        bump_version_string,
        compare_versions,
        compare_versions_safe,
        highest_version,
        parse_version_from_text,
        sort_versions,
        spec_matches_version,
        upgrade_status_for_versions,
        version_to_pinned,
    )
    from .infrastructure.artifact_builder import (
        build_artifacts,
        build_skill_archive,
        clean_release_artifacts,
        read_project_version,
        upload_artifacts,
        write_project_version,
    )
    from .infrastructure.filesystem_store import backup_file_once
    from .infrastructure.git_ops import create_git_tag, ensure_checkout, git_available, run_git, sync_repo
    from .infrastructure.registry_client import (
        download_skill_archive,
        download_skill_metadata,
        registry_auth_headers,
        registry_skill_metadata_url,
        upload_file,
    )
    from .usage_docs import render_usage_doc
else:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from ai_kit import package_manager as pm
    from ai_kit.application.project_manifest import ProjectManifestPorts, ProjectManifestService
    from ai_kit.commands.assembly import (
        build_bootstrap_handler_map,
        build_health_handler_map,
        build_inspect_handler_map,
        build_install_handler_map,
        build_project_command_context,
        build_resolution_handler_map,
        build_upgrade_handler_map,
    )
    from ai_kit.commands.cache import command_cache
    from ai_kit.commands.config_cmd import command_config as _command_config_alt
    from ai_kit.commands.dispatch import CommandRouter
    from ai_kit.commands.errors import HANDLED_COMMAND_EXCEPTIONS, command_error_message
    from ai_kit.main_bridge import activate_main_bridge
    from ai_kit.product import ProductProfile, activate_product, active_product_profile
    from ai_kit.commands.parser_builders import (
        add_asset_config_parser,
        add_config_bootstrap_parsers,
        add_inspect_resolution_parsers,
        add_project_runtime_parsers,
    )
    from ai_kit.commands.project import build_project_config_handlers, build_project_plain_handlers
    from ai_kit.commands.routes import register_command_routes
    from ai_kit.domain import cli_assets
    from ai_kit.domain import managed_assets
    from ai_kit.domain import managed_install
    from ai_kit.domain import materialization
    from ai_kit.domain import project_state
    from ai_kit.domain import project_manifest_state
    from ai_kit.domain import project_locking
    from ai_kit.domain import project_sync
    from ai_kit.domain import project_sync_presentation
    from ai_kit.domain import project_sync_results
    from ai_kit.domain import report_presentation
    from ai_kit.domain import runtime_install
    from ai_kit.domain import skill_install
    from ai_kit.domain.versions import (
        bump_version_string,
        compare_versions,
        compare_versions_safe,
        highest_version,
        parse_version_from_text,
        sort_versions,
        spec_matches_version,
        upgrade_status_for_versions,
        version_to_pinned,
    )
    from ai_kit.infrastructure.artifact_builder import (
        build_artifacts,
        build_skill_archive,
        clean_release_artifacts,
        read_project_version,
        upload_artifacts,
        write_project_version,
    )
    from ai_kit.infrastructure.filesystem_store import backup_file_once
    from ai_kit.infrastructure.git_ops import create_git_tag, ensure_checkout, git_available, run_git, sync_repo
    from ai_kit.infrastructure.registry_client import (
        download_skill_archive,
        download_skill_metadata,
        registry_auth_headers,
        registry_skill_metadata_url,
        upload_file,
    )
    from ai_kit.usage_docs import render_usage_doc


if __package__:
    from . import core as _core
else:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from ai_kit import core as _core


activate_main_bridge(__name__, globals(), _core)


def activate_entry_product(product_key: str | None = None) -> ProductProfile:
    profile = activate_product(product_key) if product_key else active_product_profile()
    if hasattr(_core, "apply_product_profile"):
        _core.apply_product_profile(profile)
    activate_main_bridge(__name__, globals(), _core)
    return profile


def _get_cli_version() -> str:
    """Return the installed package version, falling back to pyproject.toml."""
    try:
        return importlib.metadata.version("ai-kit")
    except importlib.metadata.PackageNotFoundError:
        pass
    pyproject = Path(__file__).resolve().parent.parent.parent / "pyproject.toml"
    if pyproject.exists():
        import re as _re
        text = pyproject.read_text(encoding="utf-8")
        m = _re.search(r'^version\s*=\s*"([^"]+)"', text, _re.MULTILINE)
        if m:
            return m.group(1)
    return "unknown"


def build_parser() -> argparse.ArgumentParser:
    profile = _core.ACTIVE_PRODUCT_PROFILE
    parser = argparse.ArgumentParser(description=profile.cli_description)
    parser.add_argument(
        "--version", "-V",
        action="version",
        version=f"ai-kit {_get_cli_version()}",
        help="Show the CLI version and exit.",
    )
    parser.add_argument(
        "--config-path",
        help=f"Override the CLI config path. Defaults to ~/{profile.config_dirname}/config.yaml.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    runtime_choices = sorted(RUNTIME_PROFILES)
    add_config_bootstrap_parsers(subparsers, runtime_choices=runtime_choices)
    add_inspect_resolution_parsers(subparsers, runtime_choices=runtime_choices)
    add_project_runtime_parsers(subparsers, runtime_choices=runtime_choices, all_asset_types=tuple(ALL_ASSET_TYPES))
    add_asset_config_parser(subparsers)
    return parser


def build_command_router(config_path: Path) -> CommandRouter:
    router = CommandRouter()
    load_effective_config = lambda path: effective_config(load_config(path))
    project_context = build_project_command_context(_core, pm, load_effective_config)
    bootstrap_handlers = build_bootstrap_handler_map(_core)
    resolution_handlers = build_resolution_handler_map(_core, load_effective_config)
    inspect_handlers = build_inspect_handler_map(_core, load_effective_config)
    install_handlers = build_install_handler_map(_core, pm)
    upgrade_handlers = build_upgrade_handler_map(_core, pm, install_handlers)
    health_handlers = build_health_handler_map(_core)
    config_path_handlers = {
        "asset-config": command_config,
        "bind": command_bind,
        "use": command_use,
    }

    # Shared resources: route sub-commands via wrapper
    _sr_handlers = {
        "list": command_shared_resources_list,
        "add": command_shared_resources_add,
        "use": command_shared_resources_use,
        "remove": command_shared_resources_remove,
    }

    def _shared_resources_router(args: argparse.Namespace, config_path: Path) -> int:
        sub = getattr(args, "sr_command", "")
        handler = _sr_handlers.get(sub)
        if handler is None:
            print(f"Error: unknown shared-resources sub-command: {sub}", file=sys.stderr)
            return 2
        return handler(args, config_path)

    config_path_handlers["shared-resources"] = _shared_resources_router

    config_path_handlers.update(bootstrap_handlers)
    config_path_handlers.update(resolution_handlers)
    config_path_handlers.update(inspect_handlers)
    config_path_handlers.update(health_handlers)
    config_path_handlers.update(install_handlers)
    config_path_handlers.update(upgrade_handlers)
    config_path_handlers.update(build_project_config_handlers(project_context))
    register_command_routes(
        router,
        config_path=config_path,
        config_path_handlers=config_path_handlers,
        plain_handlers={
            "cache": command_cache,
            **build_project_plain_handlers(project_context),
        },
        config_path_alias_handlers=[],
    )
    return router


def main(argv: list[str] | None = None, *, product_key: str | None = None) -> int:
    activate_entry_product(product_key)
    parser = build_parser()
    args = parser.parse_args(argv)
    config_path = resolve_config_path(getattr(args, "config_path", None))

    try:
        return build_command_router(config_path).dispatch(args, parser)
    except HANDLED_COMMAND_EXCEPTIONS as exc:
        print(f"Error: {command_error_message(exc)}", file=sys.stderr)
        return 1


def ai_kit_main(argv: list[str] | None = None) -> int:
    return main(argv, product_key="ai-kit")


def ai_kit_main(argv: list[str] | None = None) -> int:
    return main(argv, product_key="ai-kit")


if __name__ == "__main__":
    raise SystemExit(main())
