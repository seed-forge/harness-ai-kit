"""Product profile for the harness-ai-kit OSS CLI."""
from __future__ import annotations

import os
from dataclasses import dataclass


PRODUCT_ENV_VAR = "HARNESS_AI_KIT_PRODUCT"


@dataclass(frozen=True)
class ProductProfile:
    key: str
    display_name: str
    command_name: str
    config_dirname: str
    default_checkout_dirname: str
    default_repo_url: str
    self_cli_package_name: str
    cli_description: str
    project_manifest_filename: str
    lockfile_name: str
    managed_asset_bundle_root: str
    runtime_skill_bundle_root: str
    runtime_wrapper_prefix: str


PRODUCT_PROFILES: dict[str, ProductProfile] = {
    "harness-ai-kit": ProductProfile(
        key="harness-ai-kit",
        display_name="harness-ai-kit",
        command_name="harness-ai-kit",
        config_dirname=".harness-ai-kit",
        default_checkout_dirname="harness-ai-kit",
        # Repository endpoints belong in ~/.harness-ai-kit/config.yaml.
        default_repo_url="",
        self_cli_package_name="harness-ai-kit",
        cli_description=(
            "Package manager for AI agent assets (skills / CLIs / MCPs / plugins / loops) "
            "across Codex, Claude Code, Cursor, Kiro and DeepSeek Harness (dsh)."
        ),
        project_manifest_filename="harness-ai-kit.yml",
        lockfile_name="harness-ai-kit.lock",
        managed_asset_bundle_root="",
        runtime_skill_bundle_root="harness-ai-kit-skills",
        runtime_wrapper_prefix="harness-ai-kit",
    ),
}


def activate_product(product_key: str) -> ProductProfile:
    profile = PRODUCT_PROFILES.get(product_key)
    if profile is None:
        raise KeyError(f"Unknown product profile: {product_key}")
    os.environ[PRODUCT_ENV_VAR] = profile.key
    return profile


def active_product_profile() -> ProductProfile:
    requested = os.environ.get(PRODUCT_ENV_VAR, "harness-ai-kit").strip() or "harness-ai-kit"
    return PRODUCT_PROFILES.get(requested, PRODUCT_PROFILES["harness-ai-kit"])
