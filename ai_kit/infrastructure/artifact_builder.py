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

from .main_compat import bridged_main_function

_PROTECTED_INFRA = {'read_project_version', 'write_project_version', 'build_skill_archive', 'clean_release_artifacts', 'build_artifacts', 'upload_artifacts'}


def read_project_version(pyproject_file: Path) -> str:
    content = pyproject_file.read_text(encoding="utf-8")
    match = re.search(r'(?m)^version = "([^"]+)"$', content)
    if not match:
        raise ValueError(f"Unable to find project version in {pyproject_file}")
    return match.group(1)


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


def build_skill_archive(repo_root: Path, record: SkillRecord, output_dir: Path | None = None) -> Path:
    target_dir = output_dir or (repo_root / "dist" / "skills")
    target_dir.mkdir(parents=True, exist_ok=True)
    archive_path = target_dir / skill_archive_name(record)
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        from ai_kit.infrastructure.registry_skill import _is_publishable
        for file_path in sorted(record.path.rglob("*")):
            if file_path.is_file() and _is_publishable(file_path, record.path):
                archive.write(file_path, arcname=str(file_path.relative_to(record.path.parent)).replace("\\", "/"))
    return archive_path


def clean_release_artifacts(repo_root: Path) -> None:
    for relative_path in ("dist", "build", ".tmp-release"):
        target = repo_root / relative_path
        if target.exists():
            shutil.rmtree(target)


def build_artifacts(repo_root: Path) -> str:
    result = subprocess.run(
        [sys.executable, "-m", "build"],
        cwd=repo_root,
        env=release_subprocess_env(repo_root),
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return console_safe_text(result.stdout.strip())


def upload_artifacts(
    repo_root: Path,
    repository_url: str,
    trusted_host: str,
    dry_run: bool,
) -> str:
    files = [str(path) for path in dist_files(repo_root)]
    command = twine_upload_command(files, repository_url)

    if dry_run:
        return console_safe_text(" ".join(command))

    result = subprocess.run(
        command,
        cwd=repo_root,
        env=twine_subprocess_env(repo_root),
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return console_safe_text(result.stdout.strip())


read_project_version = bridged_main_function(globals(), _PROTECTED_INFRA)(read_project_version)
write_project_version = bridged_main_function(globals(), _PROTECTED_INFRA)(write_project_version)
build_skill_archive = bridged_main_function(globals(), _PROTECTED_INFRA)(build_skill_archive)
clean_release_artifacts = bridged_main_function(globals(), _PROTECTED_INFRA)(clean_release_artifacts)
build_artifacts = bridged_main_function(globals(), _PROTECTED_INFRA)(build_artifacts)
upload_artifacts = bridged_main_function(globals(), _PROTECTED_INFRA)(upload_artifacts)
