"""Product profile for the harness-ai-kit OSS CLI."""
from __future__ import annotations

import os
from dataclasses import dataclass


PRODUCT_ENV_VAR = "AI_KIT_PRODUCT"


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
    "ai-kit": ProductProfile(
        key="ai-kit",
        display_name="harness-ai-kit",
        command_name="harness-ai-kit",
        config_dirname=".harness-ai-kit",
        default_checkout_dirname="ai-kit",
        default_repo_url="https://github.com/seed-forge/harness-ai-kit.git",
        self_cli_package_name="harness-ai-kit",
        cli_description="Package manager for AI agent assets (skills / CLIs / MCPs / loops).",
        project_manifest_filename="ai-kit.yml",
        lockfile_name="ai-kit.lock",
        managed_asset_bundle_root="",
        runtime_skill_bundle_root="ai-kit-skills",
        runtime_wrapper_prefix="ai-kit",
    ),
}


def activate_product(product_key: str) -> ProductProfile:
    profile = PRODUCT_PROFILES.get(product_key)
    if profile is None:
        raise KeyError(f"Unknown product profile: {product_key}")
    os.environ[PRODUCT_ENV_VAR] = profile.key
    return profile


def active_product_profile() -> ProductProfile:
    requested = os.environ.get(PRODUCT_ENV_VAR, "ai-kit").strip() or "ai-kit"
    return PRODUCT_PROFILES.get(requested, PRODUCT_PROFILES["ai-kit"])
