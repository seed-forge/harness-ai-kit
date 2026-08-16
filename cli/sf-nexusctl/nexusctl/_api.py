"""Thin wrapper around nexus_api_client SDK.

Handles auth, configuration, error translation, verbose logging,
and provides factory functions for the various API classes.
"""
from __future__ import annotations

import argparse
import sys

from nexus_api_client import (
    ApiClient,
    BlobStoreApi,
    CleanupPoliciesApi,
    Configuration,
    RepositoryManagementApi,
    StatusApi,
)
from nexus_api_client.exceptions import ApiException

from .profile import resolve_config

DEFAULT_BASE_URL = ""

# Format -> SDK method name mapping (lowercase).
FORMAT_ALIASES: dict[str, str] = {
    "pypi": "pypi",
    "npm": "npm",
    "maven": "maven",
    "maven2": "maven",
    "docker": "docker",
    "raw": "raw",
    "nuget": "nuget",
    "go": "go",
    "golang": "go",
    "rubygems": "rubygems",
    "apt": "apt",
}

# Class name prefix overrides for formats where capitalize() doesn't match SDK
CLASS_NAME_OVERRIDES: dict[str, str] = {
    "go": "Golang",
    "rubygems": "RubyGems",
}

FORMAT_HELP = "{pypi,npm,maven,maven2,docker,raw,nuget,go,rubygems,apt}"


def resolve_format(fmt: str) -> str:
    """Resolve user-facing format name to SDK method suffix."""
    key = fmt.lower()
    if key not in FORMAT_ALIASES:
        supported = ", ".join(sorted(set(FORMAT_ALIASES.values())))
        print(f"错误: 不支持的格式 '{fmt}'。支持的格式: {supported}", file=sys.stderr)
        sys.exit(2)
    return FORMAT_ALIASES[key]


def resolve_request_class(sdk_fmt: str, repo_type: str):
    """Dynamically resolve the SDK request class for a format+type combo."""
    import nexus_api_client
    prefix = CLASS_NAME_OVERRIDES.get(sdk_fmt, sdk_fmt.capitalize())
    class_name = f"{prefix}{repo_type.capitalize()}RepositoryApiRequest"
    return getattr(nexus_api_client, class_name, None)


def _build_config(args: argparse.Namespace) -> Configuration:
    """Build SDK Configuration using profile-aware resolution."""
    cfg_dict = resolve_config(args)
    base_url = cfg_dict["base_url"]

    # SDK resource paths are relative (e.g. /v1/...),
    # so host must include the /service/rest prefix.
    if not base_url.endswith("/service/rest"):
        base_url = f"{base_url}/service/rest"

    cfg = Configuration(host=base_url)
    if cfg_dict["user"] and cfg_dict["password"]:
        cfg.username = cfg_dict["user"]
        cfg.password = cfg_dict["password"]
    return cfg


def get_base_url(args: argparse.Namespace) -> str:
    """Return the resolved base URL string (without /service/rest)."""
    return resolve_config(args)["base_url"]


def get_repo_api(args: argparse.Namespace) -> RepositoryManagementApi:
    """Factory: return an authenticated RepositoryManagementApi."""
    return RepositoryManagementApi(ApiClient(_build_config(args)))


def get_status_api(args: argparse.Namespace) -> StatusApi:
    """Factory: return a StatusApi (no auth required for status endpoint)."""
    return StatusApi(ApiClient(_build_config(args)))


def get_blobstore_api(args: argparse.Namespace) -> BlobStoreApi:
    """Factory: return a BlobStoreApi."""
    return BlobStoreApi(ApiClient(_build_config(args)))


def get_cleanup_api(args: argparse.Namespace) -> CleanupPoliciesApi:
    """Factory: return a CleanupPoliciesApi."""
    return CleanupPoliciesApi(ApiClient(_build_config(args)))


def api_call(func, *args, verbose: bool = False, **kwargs) -> object:
    """Execute an SDK call with unified error handling.

    Returns the result on success; prints a human-readable error and
    calls sys.exit(1) on failure.
    """
    if verbose:
        print(f"[VERBOSE] 调用: {func.__qualname__}", file=sys.stderr)
    try:
        result = func(*args, **kwargs)
        if verbose:
            print(f"[VERBOSE] 成功", file=sys.stderr)
        return result
    except ApiException as exc:
        status = getattr(exc, "status", "?")
        reason = getattr(exc, "reason", str(exc))
        body = getattr(exc, "body", "")
        print(f"Nexus API 错误 [{status}]: {reason}", file=sys.stderr)
        if body:
            print(f"  响应体: {body[:500]}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"请求失败: {exc}", file=sys.stderr)
        sys.exit(1)
