from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from base64 import b64encode
from pathlib import Path
from typing import Any, Sequence

from .git_ops_extra import clone_repo as _clone_repo_with_proxy_support
from .main_compat import bridged_main_function

_PROTECTED_INFRA = {'run_git', 'sync_repo', 'ensure_checkout', 'git_available', 'create_git_tag'}


def run_git(repo_root: Path, args: Sequence[str], timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def sync_repo(repo_root: Path) -> str:
    run_git(repo_root, ["fetch", "--all", "--prune"])
    result = run_git(repo_root, ["pull", "--ff-only"])
    return result.stdout.strip() or "Repository is up to date."


def ensure_checkout(repo_url: str, checkout_dir: Path, sync_after_clone: bool, *, no_git_proxy: bool = False) -> str:
    if repo_looks_valid(checkout_dir):
        if sync_after_clone:
            return sync_repo(checkout_dir)
        return f"Repository already available at {checkout_dir}"

    _clone_repo_with_proxy_support(repo_url, checkout_dir, no_git_proxy=no_git_proxy)
    if sync_after_clone:
        return sync_repo(checkout_dir)
    return f"Cloned repository to {checkout_dir}"


def git_available() -> bool:
    return command_available(["git", "--version"])


def create_git_tag(repo_root: Path, tag_name: str, push: bool) -> tuple[str, str]:
    tag_result = run_git(repo_root, ["tag", tag_name])
    push_output = ""
    if push:
        push_result = run_git(repo_root, ["push", "origin", tag_name])
        push_output = push_result.stdout.strip() or f"Pushed tag {tag_name}."
    return tag_result.stdout.strip(), push_output


run_git = bridged_main_function(globals(), _PROTECTED_INFRA)(run_git)
sync_repo = bridged_main_function(globals(), _PROTECTED_INFRA)(sync_repo)
ensure_checkout = bridged_main_function(globals(), _PROTECTED_INFRA)(ensure_checkout)
git_available = bridged_main_function(globals(), _PROTECTED_INFRA)(git_available)
create_git_tag = bridged_main_function(globals(), _PROTECTED_INFRA)(create_git_tag)
