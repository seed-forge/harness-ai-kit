#!/usr/bin/env python3
"""Validate the explicit OSS release matrix and create checked distributions."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

import yaml


VERSION_RE = re.compile(r"__version__\s*=\s*[\"']([^\"']+)[\"']")
REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
PRIVATE_NETWORK_RE = re.compile(
    r"\b(?:10(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2})\b"
)
LOCAL_PATH_RE = re.compile(r"(?i)(?:[a-z]:\\users\\[a-z0-9._-]+\\|/(?:users|home)/[a-z0-9._-]+/)")
TOKEN_PREFIXES = ("gh" + "p_", "gh" + "o_", "gh" + "s_", "github" + "_pat_", "pypi" + "-")
TOKEN_RE = re.compile(r"\b(?:" + "|".join(re.escape(prefix) for prefix in TOKEN_PREFIXES) + r")[A-Za-z0-9_]{20,}\b")
ASSIGNED_SECRET_RE = re.compile(
    r"(?i)\b(?:api[_-]?key|password|secret|token)\s*[:=]\s*[\"'](?!\$\{|<)[^\"'\r\n]{16,}[\"']"
)
SCAN_RULES = (
    ("private-network", PRIVATE_NETWORK_RE),
    ("machine-local-path", LOCAL_PATH_RE),
    ("known-token-prefix", TOKEN_RE),
    ("assigned-secret", ASSIGNED_SECRET_RE),
)
IGNORED_PARTS = {".git", ".tmp", ".venv", "venv", "build", "dist", "dist3", "__pycache__", ".pytest_cache"}
PUBLIC_PYPI_SIMPLE_URL = "https://pypi.org/simple"
CORE_PUBLIC_RELEASE_INPUTS = frozenset(
    {
        "harness_ai_kit",
        "cli/harness-ai-kit",
        "cli/harness-ai-kit/cli.json",
        "pyproject.toml",
        "README.md",
        "README.zh-CN.md",
        "INSTALL.md",
        "CATALOG.md",
        "docs/quickstart.md",
        "ROADMAP.md",
        "CHANGELOG.md",
        "LICENSE",
    }
)
SNAPSHOT_METADATA_PATHS = frozenset(
    {"docs/oss-public-release.yaml", "docs/oss-staging-manifest.json"}
)
CORE_PUBLIC_README_MARKERS: dict[str, tuple[str, ...]] = {
    "README.md": (
        "# harness-ai-kit",
        "## Why",
        "## The REMIX Method",
        "## No Lock-In",
        "## Quick Start",
        "## Team Workflow",
        "## Architecture",
        "## Documentation",
        "## License",
    ),
    "README.zh-CN.md": (
        "# harness-ai-kit",
        "## 为什么需要它",
        "## REMIX 方法论",
        "## 不锁定内容",
        "## 快速开始",
        "## 团队协作",
        "## 架构",
        "## 文档入口",
        "## 许可证",
    ),
}


def is_ignored_path(path: Path, root: Path) -> bool:
    """Exclude transient files which are neither source nor release input."""
    return any(part in IGNORED_PARTS or part.endswith(".egg-info") for part in path.relative_to(root).parts)


def load_matrix(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"release matrix must be a mapping: {path}")
    return loaded


def read_toml(path: Path) -> dict[str, Any]:
    try:
        import tomllib
    except ModuleNotFoundError as exc:  # pragma: no cover - Python 3.10 fallback
        raise RuntimeError("Python 3.11+ is required to parse pyproject.toml") from exc
    with path.open("rb") as handle:
        return tomllib.load(handle)


def iter_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if path.is_file() and not is_ignored_path(path, root):
            yield path


def scan_release_surface(repo_root: Path) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for path in iter_files(repo_root):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        relative = path.relative_to(repo_root).as_posix()
        for line_number, line in enumerate(text.splitlines(), 1):
            for rule, pattern in SCAN_RULES:
                if pattern.search(line):
                    findings.append({"path": relative, "line": str(line_number), "rule": rule})
    return findings


def package_versions(repo_root: Path, package: dict[str, Any]) -> tuple[dict[str, list[str]], list[str]]:
    root = repo_root / str(package["source_path"])
    values: dict[str, list[str]] = {}
    errors: list[str] = []
    for source in package.get("version_sources", ["pyproject"]):
        if source == "pyproject":
            path = root / "pyproject.toml"
            if not path.exists():
                errors.append("missing-pyproject")
                continue
            project = read_toml(path).get("project", {})
            value = project.get("version") if isinstance(project, dict) else None
            if not isinstance(value, str):
                errors.append("missing-pyproject-version")
            else:
                values[source] = [value]
        elif source == "cli_json":
            path = root / "cli.json"
            if not path.exists():
                errors.append("missing-cli-json")
                continue
            payload = json.loads(path.read_text(encoding="utf-8"))
            value = payload.get("version") if isinstance(payload, dict) else None
            if not isinstance(value, str):
                errors.append("missing-cli-json-version")
            else:
                values[source] = [value]
        elif source == "init":
            found: list[str] = []
            for init_path in root.rglob("__init__.py"):
                found.extend(VERSION_RE.findall(init_path.read_text(encoding="utf-8")))
            if not found:
                errors.append("missing-init-version")
            else:
                values[source] = sorted(set(found))
        else:
            errors.append(f"unsupported-version-source:{source}")
    all_values = {value for source_values in values.values() for value in source_values}
    if len(all_values) > 1:
        errors.append("version-drift")
    return values, errors


def core_public_documentation_errors(repo_root: Path) -> list[str]:
    """Reject a staging projection that keeps filenames but loses product documentation."""
    errors: list[str] = []
    for relative_path, required_markers in CORE_PUBLIC_README_MARKERS.items():
        path = repo_root / relative_path
        if not path.is_file():
            continue
        contents = path.read_text(encoding="utf-8")
        missing_markers = [marker for marker in required_markers if marker not in contents]
        if missing_markers:
            errors.append(
                f"harness-ai-kit documentation contract missing sections in {relative_path}: "
                + ", ".join(missing_markers)
            )
    return errors


def validate_matrix(repo_root: Path, matrix: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    public = matrix.get("public")
    if not isinstance(public, dict) or public.get("repository") != "seed-forge/harness-ai-kit":
        errors.append("public.repository must be seed-forge/harness-ai-kit")
    packages = matrix.get("packages")
    if not isinstance(packages, list) or not packages:
        return [*errors, "packages must be a non-empty list"]
    ids: set[str] = set()
    names: set[str] = set()
    waves: set[int] = set()
    for item in packages:
        if not isinstance(item, dict):
            errors.append("package entry must be a mapping")
            continue
        package_id = item.get("id")
        package_name = item.get("package_name")
        source_path = item.get("source_path")
        if not all(isinstance(value, str) and value for value in (package_id, package_name, source_path)):
            errors.append("package id, package_name and source_path are required")
            continue
        if package_id in ids:
            errors.append(f"duplicate package id: {package_id}")
        if package_name in names:
            errors.append(f"duplicate package name: {package_name}")
        ids.add(package_id)
        names.add(package_name)
        if not (repo_root / source_path).is_dir():
            errors.append(f"source path is missing for {package_id}: {source_path}")
        if package_id == "harness-ai-kit":
            included_paths = item.get("included_paths")
            if not isinstance(included_paths, list) or not all(isinstance(path, str) and path for path in included_paths):
                errors.append("harness-ai-kit included_paths must list the core public release inputs")
            else:
                missing_inputs = sorted(CORE_PUBLIC_RELEASE_INPUTS - set(included_paths))
                if missing_inputs:
                    errors.append(
                        "harness-ai-kit included_paths missing core public release inputs: "
                        + ", ".join(missing_inputs)
                    )
                absent_inputs = sorted(
                    path for path in CORE_PUBLIC_RELEASE_INPUTS if not (repo_root / path).exists()
                )
                if absent_inputs:
                    errors.append(
                        "harness-ai-kit core public release inputs are missing from checkout: "
                        + ", ".join(absent_inputs)
                    )
                normalized_inputs = [path.replace("\\", "/").strip("/") for path in included_paths]
                recursive_snapshot_inputs = sorted(
                    snapshot_path
                    for snapshot_path in SNAPSHOT_METADATA_PATHS
                    if any(
                        snapshot_path == input_path or snapshot_path.startswith(input_path + "/")
                        for input_path in normalized_inputs
                    )
                )
                if recursive_snapshot_inputs:
                    errors.append(
                        "harness-ai-kit included_paths must not include staging snapshot metadata: "
                        + ", ".join(recursive_snapshot_inputs)
                    )
                errors.extend(core_public_documentation_errors(repo_root))
        if item.get("ci"):
            if not isinstance(item.get("test_command"), str):
                errors.append(f"ci package is missing test_command: {package_id}")
            if not isinstance(item.get("entrypoint"), str) or not item["entrypoint"]:
                errors.append(f"ci package is missing entrypoint: {package_id}")
            else:
                pyproject_path = repo_root / source_path / "pyproject.toml"
                if pyproject_path.is_file():
                    project = read_toml(pyproject_path).get("project", {})
                    scripts = project.get("scripts", {}) if isinstance(project, dict) else {}
                    if not isinstance(scripts, dict) or item["entrypoint"] not in scripts:
                        errors.append(f"ci entrypoint is not declared by pyproject: {package_id}")
            if not isinstance(item.get("smoke_command"), str):
                errors.append(f"ci package is missing smoke_command: {package_id}")
        if item.get("publish"):
            if not item.get("public"):
                errors.append(f"publish package is not public: {package_id}")
            wave = item.get("release_wave")
            if not isinstance(wave, int) or wave < 0 or wave > 3:
                errors.append(f"publish package needs release_wave 0-3: {package_id}")
            else:
                waves.add(wave)
    if waves and waves != set(range(max(waves) + 1)):
        errors.append("publish release waves must be contiguous from 0")
    packages_by_id = {str(item.get("id")): item for item in packages if isinstance(item, dict)}
    for item in packages_by_id.values():
        if not item.get("publish"):
            continue
        package_id = str(item["id"])
        dependencies = item.get("depends_on", [])
        if not isinstance(dependencies, list) or not all(isinstance(value, str) for value in dependencies):
            errors.append(f"publish package depends_on must be a list of ids: {package_id}")
            continue
        for dependency_id in dependencies:
            dependency = packages_by_id.get(dependency_id)
            if dependency is None:
                errors.append(f"publish dependency is absent from the matrix: {package_id} -> {dependency_id}")
            elif not dependency.get("publish"):
                errors.append(f"publish dependency is not selected: {package_id} -> {dependency_id}")
            else:
                dependency_wave = dependency.get("release_wave")
                package_wave = item.get("release_wave")
                if isinstance(dependency_wave, int) and isinstance(package_wave, int) and dependency_wave >= package_wave:
                    errors.append(f"publish dependency must be in an earlier release wave: {package_id} -> {dependency_id}")
    return errors


def run_command(
    command: str,
    cwd: Path,
    *,
    python_executable: Path | str | None = None,
    token_replacements: dict[str, str] | None = None,
    environment: dict[str, str] | None = None,
) -> tuple[bool, int]:
    """Run an explicit matrix command without shell interpolation."""
    rendered = command.format(python="{python}", entrypoint="{entrypoint}")
    replacements = {"{python}": str(python_executable or sys.executable)}
    if token_replacements:
        replacements.update({f"{{{key}}}": value for key, value in token_replacements.items()})
    args = [replacements.get(item, item) for item in shlex.split(rendered)]
    completed = subprocess.run(args, cwd=cwd, env=environment, check=False)
    return completed.returncode == 0, completed.returncode


def clear_previous_artifacts(output: Path, *, attempts: int = 5, delay_seconds: float = 0.25) -> None:
    """Remove only prior distribution files, tolerating short Windows locks.

    Antivirus/indexing and a just-finished archive reader can keep a wheel or
    sdist handle open briefly on Windows.  A bounded retry makes the release
    gate deterministic without hiding persistent cleanup failures.
    """
    for artifact in (*output.glob("*.whl"), *output.glob("*.tar.gz")):
        for attempt in range(attempts):
            try:
                artifact.unlink()
                break
            except PermissionError:
                if attempt == attempts - 1:
                    raise
                time.sleep(delay_seconds * (attempt + 1))


def build_package(source_root: Path, output: Path) -> tuple[bool, int]:
    output.mkdir(parents=True, exist_ok=True)
    clear_previous_artifacts(output)
    command = [sys.executable, "-m", "build", "--outdir", str(output), str(source_root)]
    completed = subprocess.run(command, cwd=source_root, check=False)
    if completed.returncode:
        return False, completed.returncode
    artifacts = sorted((*output.glob("*.whl"), *output.glob("*.tar.gz")))
    check = subprocess.run([sys.executable, "-m", "twine", "check", *map(str, artifacts)], check=False)
    return check.returncode == 0, check.returncode


def package_wheel(output: Path, package_name: str) -> Path | None:
    """Return the one wheel built for a package from its isolated output path."""
    normalized = re.sub(r"[-_.]+", "_", package_name).lower()
    wheels = [path for path in output.glob("*.whl") if path.name.lower().startswith(f"{normalized}-")]
    return wheels[0] if len(wheels) == 1 else None


def venv_executable(venv_root: Path, name: str) -> Path:
    directory = "Scripts" if os.name == "nt" else "bin"
    suffix = ".exe" if os.name == "nt" else ""
    return venv_root / directory / f"{name}{suffix}"


def public_pip_environment() -> dict[str, str]:
    """Prevent local Python and private index configuration from leaking into a smoke test."""
    environment = os.environ.copy()
    for key in ("PYTHONPATH", "PYTHONHOME", "PIP_INDEX_URL", "PIP_EXTRA_INDEX_URL", "PIP_TRUSTED_HOST"):
        environment.pop(key, None)
    environment["PIP_CONFIG_FILE"] = os.devnull
    environment["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    environment["PYTHONUTF8"] = "1"
    return environment


def source_test_install_command(python: Path, repo_root: Path, source_root: Path) -> list[str]:
    """Build the public-only dependency install for a source-test environment."""
    editable_sources = [repo_root]
    if source_root != repo_root:
        editable_sources.append(source_root)
    command = [
        str(python),
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--no-input",
        "--index-url",
        PUBLIC_PYPI_SIMPLE_URL,
        "pytest",
    ]
    for source in editable_sources:
        command.extend(("-e", str(source)))
    return command


def run_isolated_source_test(
    command: str,
    repo_root: Path,
    source_root: Path,
    package_id: str,
) -> tuple[bool, int]:
    """Run source tests with only declared public dependencies available.

    A checkout can satisfy imports from a maintainer's global environment. The
    release gate deliberately avoids that so source tests and wheel smoke tests
    exercise the same public dependency boundary.
    """
    with tempfile.TemporaryDirectory(prefix=f"public-source-test-{package_id}-") as temp_dir:
        venv_root = Path(temp_dir) / "venv"
        environment = public_pip_environment()
        created = subprocess.run(
            [sys.executable, "-m", "venv", str(venv_root)],
            cwd=source_root,
            env=environment,
            check=False,
        )
        if created.returncode:
            return False, created.returncode
        python = venv_executable(venv_root, "python")
        installed = subprocess.run(
            source_test_install_command(python, repo_root, source_root),
            cwd=source_root,
            env=environment,
            check=False,
        )
        if installed.returncode:
            return False, installed.returncode
        return run_command(command, source_root, python_executable=python, environment=environment)


def run_isolated_wheel_smoke(
    package: dict[str, Any],
    source_root: Path,
    output: Path,
    version: str,
    dependency_wheels: list[Path],
) -> tuple[bool, int]:
    """Install this build in a fresh venv and invoke its public entry point.

    Source tests may run with the repository on ``sys.path``. This final check
    deliberately does not: it proves the generated wheel, its declared public
    dependencies and its console script work without a maintainer's installed
    packages or private package index.
    """
    wheel = package_wheel(output, str(package["package_name"]))
    if wheel is None:
        return False, 1
    with tempfile.TemporaryDirectory(prefix=f"public-release-{package['id']}-") as temp_dir:
        venv_root = Path(temp_dir) / "venv"
        environment = public_pip_environment()
        created = subprocess.run(
            [sys.executable, "-m", "venv", str(venv_root)],
            cwd=source_root,
            env=environment,
            check=False,
        )
        if created.returncode:
            return False, created.returncode
        python = venv_executable(venv_root, "python")
        installed = subprocess.run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-input",
                "--index-url",
                PUBLIC_PYPI_SIMPLE_URL,
                *map(str, dependency_wheels),
                str(wheel),
            ],
            cwd=source_root,
            env=environment,
            check=False,
        )
        if installed.returncode:
            return False, installed.returncode
        metadata_check = (
            "import importlib.metadata as metadata; "
            f"expected = {str(version)!r}; actual = metadata.version({str(package['package_name'])!r}); "
            "raise SystemExit(0 if actual == expected else 1)"
        )
        metadata = subprocess.run(
            [str(python), "-c", metadata_check],
            cwd=source_root,
            env=environment,
            check=False,
        )
        if metadata.returncode:
            return False, metadata.returncode
        entrypoint = venv_executable(venv_root, str(package["entrypoint"]))
        return run_command(
            str(package["smoke_command"]),
            source_root,
            python_executable=python,
            token_replacements={"entrypoint": str(entrypoint)},
            environment=environment,
        )


def canonical_file_bytes(path: Path) -> bytes:
    """Hash text-like release inputs consistently across Windows and Linux."""
    return path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def tree_sha256(repo_root: Path, package: dict[str, Any]) -> str:
    includes = package.get("included_paths") or [package["source_path"]]
    digest = hashlib.sha256()
    files: list[Path] = []
    for item in includes:
        path = repo_root / str(item)
        if path.is_file():
            if not is_ignored_path(path, repo_root):
                files.append(path)
        elif path.is_dir():
            files.extend(path for path in iter_files(path) if not is_ignored_path(path, repo_root))
    for path in sorted(set(files), key=lambda value: value.relative_to(repo_root).as_posix()):
        relative = path.relative_to(repo_root).as_posix().encode("utf-8")
        digest.update(relative + b"\0" + hashlib.sha256(canonical_file_bytes(path)).hexdigest().encode("ascii") + b"\n")
    return digest.hexdigest()


def git_revision_exists(repo_root: Path, revision: str) -> bool:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), "cat-file", "-e", f"{revision}^{{commit}}"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return completed.returncode == 0


def verify_staging_manifest(repo_root: Path, matrix: dict[str, Any], packages: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    snapshot = matrix.get("source_snapshot") if isinstance(matrix.get("source_snapshot"), dict) else {}
    revision = snapshot.get("source_revision")
    expected_digest = snapshot.get("staging_manifest_sha256")
    manifest_ref = snapshot.get("staging_manifest")
    if not isinstance(revision, str) or not REVISION_RE.fullmatch(revision):
        errors.append("source_snapshot.source_revision must be an immutable 40-character commit")
    elif not git_revision_exists(repo_root, revision):
        errors.append("source_snapshot.source_revision is not available in this checkout")
    if not isinstance(expected_digest, str) or not SHA256_RE.fullmatch(expected_digest):
        errors.append("source_snapshot.staging_manifest_sha256 must be a SHA-256 digest")
    if not isinstance(manifest_ref, str):
        return [*errors, "source_snapshot.staging_manifest is required"]
    manifest_path = repo_root / manifest_ref
    if not manifest_path.is_file():
        return [*errors, f"staging manifest is missing: {manifest_ref}"]
    actual_digest = hashlib.sha256(canonical_file_bytes(manifest_path)).hexdigest()
    if isinstance(expected_digest, str) and actual_digest != expected_digest:
        errors.append("staging manifest digest does not match the release matrix")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return [*errors, "staging manifest is not valid JSON"]
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        return [*errors, "staging manifest schema_version must be 1"]
    if manifest.get("source_revision") != revision:
        errors.append("staging manifest source_revision does not match the release matrix")
    listed = {item.get("id"): item for item in manifest.get("packages", []) if isinstance(item, dict)}
    for package in packages:
        item = listed.get(package["id"])
        if not isinstance(item, dict):
            errors.append(f"staging manifest is missing package {package['id']}")
            continue
        versions, version_errors = package_versions(repo_root, package)
        if version_errors:
            errors.extend(f"{package['id']}: {error}" for error in version_errors)
            continue
        version = next(iter({value for values in versions.values() for value in values}), "")
        if item.get("package_name") != package["package_name"] or item.get("version") != version:
            errors.append(f"staging manifest metadata does not match {package['id']}")
        if item.get("tree_sha256") != tree_sha256(repo_root, package):
            errors.append(f"staging manifest tree digest does not match {package['id']}")
    return errors


def inventory(repo_root: Path, packages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Report every explicit package, including candidates held out of CI."""
    records: list[dict[str, Any]] = []
    for package in packages:
        versions, errors = package_versions(repo_root, package) if (repo_root / str(package["source_path"])).is_dir() else ({}, ["missing-source-path"])
        records.append(
            {
                "id": package["id"],
                "package_name": package["package_name"],
                "source_path": package["source_path"],
                "ci": bool(package.get("ci")),
                "publish": bool(package.get("publish")),
                "hold_reason": package.get("hold_reason"),
                "versions": versions,
                "metadata_errors": errors,
            }
        )
    return records


def staging_manifest_payload(repo_root: Path, packages: list[dict[str, Any]], source_revision: str) -> dict[str, Any]:
    """Create a reproducible manifest for explicitly selected public packages."""
    if not REVISION_RE.fullmatch(source_revision):
        raise ValueError("source revision must be an immutable 40-character commit")
    records: list[dict[str, str]] = []
    for package in packages:
        versions, errors = package_versions(repo_root, package)
        if errors:
            raise ValueError(f"{package['id']}: cannot write staging manifest: {', '.join(errors)}")
        version_values = {value for source_values in versions.values() for value in source_values}
        records.append(
            {
                "id": str(package["id"]),
                "package_name": str(package["package_name"]),
                "version": next(iter(version_values)),
                "tree_sha256": tree_sha256(repo_root, package),
            }
        )
    return {"schema_version": 1, "source_revision": source_revision, "packages": records}


def update_matrix_snapshot(path: Path, source_revision: str, manifest_digest: str) -> None:
    """Update only the two snapshot facts without reformatting reviewed YAML."""
    content = path.read_text(encoding="utf-8")
    replacements = (
        (r"(?m)^(  source_revision:)\s*.*$", source_revision),
        (r"(?m)^(  staging_manifest_sha256:)\s*.*$", manifest_digest),
    )
    for pattern, value in replacements:
        content, count = re.subn(pattern, lambda match: f"{match.group(1)} {value}", content, count=1)
        if count != 1:
            raise ValueError(f"could not update snapshot field in {path}")
    path.write_text(content, encoding="utf-8", newline="\n")


def select_packages(
    packages: list[dict[str, Any]], mode: str, max_release_wave: int | None = None
) -> list[dict[str, Any]]:
    selected = [item for item in packages if item.get("publish")] if mode == "release" else [item for item in packages if item.get("ci")]
    if mode == "release" and max_release_wave is not None:
        selected = [
            item
            for item in selected
            if isinstance(item.get("release_wave"), int) and item["release_wave"] <= max_release_wave
        ]
    return selected


def gate(
    repo_root: Path,
    matrix: dict[str, Any],
    mode: str,
    build_root: Path,
    max_release_wave: int | None = None,
) -> dict[str, Any]:
    matrix_errors = validate_matrix(repo_root, matrix)
    packages = [item for item in matrix["packages"] if isinstance(item, dict)]
    selected = select_packages(packages, mode, max_release_wave)
    errors = list(matrix_errors)
    if not selected:
        errors.append("no packages selected by the release matrix")
    scan_findings = scan_release_surface(repo_root)
    if scan_findings:
        errors.append(f"sensitive scan found {len(scan_findings)} potential public leaks")
    results: list[dict[str, Any]] = []
    result_by_id: dict[str, dict[str, Any]] = {}
    built_wheels: dict[str, Path] = {}
    for package in selected:
        result: dict[str, Any] = {"id": package["id"], "package_name": package["package_name"], "status": "passed"}
        source_root = repo_root / str(package["source_path"])
        versions, version_errors = package_versions(repo_root, package)
        result["versions"] = versions
        if version_errors:
            result["status"] = "failed"
            result["errors"] = version_errors
            errors.extend(f"{package['id']}: {error}" for error in version_errors)
        command = package.get("test_command")
        if isinstance(command, str):
            success, returncode = run_isolated_source_test(
                command,
                repo_root,
                source_root,
                str(package["id"]),
            )
            result["test_returncode"] = returncode
            if not success:
                result["status"] = "failed"
                result.setdefault("errors", []).append("test-command-failed")
                errors.append(f"{package['id']}: test-command-failed")
        else:
            result["status"] = "failed"
            result.setdefault("errors", []).append("missing-test-command")
            errors.append(f"{package['id']}: missing-test-command")
        success, returncode = build_package(source_root, build_root / str(package["id"]))
        result["build_returncode"] = returncode
        result["artifacts"] = [path.name for path in sorted((build_root / str(package["id"])).glob("*")) if path.is_file()]
        if not success:
            result["status"] = "failed"
            result.setdefault("errors", []).append("build-or-twine-check-failed")
            errors.append(f"{package['id']}: build-or-twine-check-failed")
        else:
            wheel = package_wheel(build_root / str(package["id"]), str(package["package_name"]))
            if wheel is None:
                result["status"] = "failed"
                result.setdefault("errors", []).append("missing-or-ambiguous-wheel")
                errors.append(f"{package['id']}: missing-or-ambiguous-wheel")
            else:
                built_wheels[str(package["id"])] = wheel
        results.append(result)
        result_by_id[str(package["id"])] = result
    for package in selected:
        result = result_by_id[str(package["id"])]
        if result["status"] == "failed":
            continue
        version_values = {value for values in result["versions"].values() for value in values}
        local_dependencies = [
            built_wheels[dependency]
            for dependency in package.get("depends_on", [])
            if dependency in built_wheels
        ]
        success, returncode = run_isolated_wheel_smoke(
            package,
            repo_root / str(package["source_path"]),
            build_root / str(package["id"]),
            next(iter(version_values)),
            local_dependencies,
        )
        result["isolated_smoke_returncode"] = returncode
        if not success:
            result["status"] = "failed"
            result.setdefault("errors", []).append("isolated-wheel-smoke-failed")
            errors.append(f"{package['id']}: isolated-wheel-smoke-failed")
    if mode == "release" and not errors:
        errors.extend(verify_staging_manifest(repo_root, matrix, selected))
    return {
        "schema_version": 1,
        "mode": mode,
        "ok": not errors,
        "errors": errors,
        "scan_findings": scan_findings,
        "inventory": inventory(repo_root, packages),
        "packages": results,
        "selected_package_ids": [item["id"] for item in selected],
        "held_packages": [
            {"id": item["id"], "reason": item.get("hold_reason", "publish=false")}
            for item in packages
            if not item.get("ci") and not item.get("publish")
        ],
    }


def release_plan(matrix: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    selected_ids = report.get("selected_package_ids")
    packages = [
        item
        for item in matrix["packages"]
        if isinstance(item, dict)
        and item.get("publish")
        and (not isinstance(selected_ids, list) or item["id"] in selected_ids)
    ]
    versions = {item["id"]: result.get("versions", {}) for item, result in zip(packages, report["packages"])}
    waves: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for package in packages:
        values = {value for source_values in versions[package["id"]].values() for value in source_values}
        waves[int(package["release_wave"])].append(
            {
                "id": package["id"],
                "package_name": package["package_name"],
                "version": next(iter(values)),
                "dist_path": f"public-release/{package['id']}",
            }
        )
    return {"waves": {str(index): waves.get(index, []) for index in range(4)}}


def write_github_outputs(path: Path, plan: dict[str, Any]) -> None:
    lines: list[str] = []
    for index in range(4):
        wave = plan["waves"][str(index)]
        lines.append(f"wave_{index}={json.dumps(wave, separators=(',', ':'))}")
        lines.append(f"has_wave_{index}={'true' if wave else 'false'}")
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    repo_root = Path(__file__).resolve().parents[1]
    parser.add_argument("--matrix", type=Path, default=repo_root / "docs" / "oss-public-release.yaml")
    parser.add_argument("--mode", choices=("ci", "release"), default="ci")
    parser.add_argument("--build-root", type=Path, default=repo_root / "build" / "public-release")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--write-plan", type=Path)
    parser.add_argument("--github-output", type=Path)
    parser.add_argument("--write-staging-manifest", type=Path)
    parser.add_argument("--source-revision")
    parser.add_argument("--max-release-wave", type=int, choices=range(4))
    parser.add_argument("--package-id", action="append", dest="package_ids")
    parser.add_argument("--update-matrix-snapshot", action="store_true")
    args = parser.parse_args(argv)
    try:
        matrix = load_matrix(args.matrix.resolve())
        packages = [item for item in matrix.get("packages", []) if isinstance(item, dict)]
        if args.write_staging_manifest:
            requested_ids = set(args.package_ids or [])
            selected_for_manifest = [item for item in packages if str(item.get("id")) in requested_ids]
            if not requested_ids:
                raise ValueError("--write-staging-manifest requires one or more --package-id values")
            if len(selected_for_manifest) != len(requested_ids):
                raise ValueError("one or more --package-id values are absent from the release matrix")
            if not args.source_revision:
                raise ValueError("--source-revision is required when writing a staging manifest")
            payload = staging_manifest_payload(repo_root, selected_for_manifest, args.source_revision)
            args.write_staging_manifest.parent.mkdir(parents=True, exist_ok=True)
            args.write_staging_manifest.write_text(
                json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
            )
            digest = hashlib.sha256(canonical_file_bytes(args.write_staging_manifest)).hexdigest()
            if args.update_matrix_snapshot:
                update_matrix_snapshot(args.matrix.resolve(), args.source_revision, digest)
                matrix = load_matrix(args.matrix.resolve())
        report = gate(repo_root, matrix, args.mode, args.build_root.resolve(), args.max_release_wave)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        report = {"schema_version": 1, "mode": args.mode, "ok": False, "errors": [str(exc)], "packages": []}
    content = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(content, encoding="utf-8")
    print(content, end="")
    if report["ok"] and args.mode == "release":
        plan = release_plan(matrix, report)
        if args.write_plan:
            args.write_plan.parent.mkdir(parents=True, exist_ok=True)
            args.write_plan.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if args.github_output:
            write_github_outputs(args.github_output, plan)
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
