#!/usr/bin/env python3
"""Validate the explicit OSS release matrix and create checked distributions."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import subprocess
import sys
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
IGNORED_PARTS = {".git", ".venv", "venv", "build", "dist", "dist3", "__pycache__", ".pytest_cache"}


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
        if item.get("ci") and not isinstance(item.get("test_command"), str):
            errors.append(f"ci package is missing test_command: {package_id}")
        if "install_command" in item and not isinstance(item.get("install_command"), str):
            errors.append(f"install_command must be a string when set: {package_id}")
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


def run_command(command: str, cwd: Path) -> tuple[bool, int]:
    rendered = command.format(python="{python}")
    args = [sys.executable if item == "{python}" else item for item in shlex.split(rendered)]
    completed = subprocess.run(args, cwd=cwd, check=False)
    return completed.returncode == 0, completed.returncode


def build_package(source_root: Path, output: Path) -> tuple[bool, int]:
    output.mkdir(parents=True, exist_ok=True)
    for artifact in (*output.glob("*.whl"), *output.glob("*.tar.gz")):
        artifact.unlink()
    command = [sys.executable, "-m", "build", "--outdir", str(output), str(source_root)]
    completed = subprocess.run(command, cwd=source_root, check=False)
    if completed.returncode:
        return False, completed.returncode
    artifacts = sorted((*output.glob("*.whl"), *output.glob("*.tar.gz")))
    check = subprocess.run([sys.executable, "-m", "twine", "check", *map(str, artifacts)], check=False)
    return check.returncode == 0, check.returncode


def tree_sha256(repo_root: Path, package: dict[str, Any]) -> str:
    includes = package.get("included_paths") or [package["source_path"]]
    digest = hashlib.sha256()
    files: list[Path] = []
    for item in includes:
        path = repo_root / str(item)
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(iter_files(path))
    for path in sorted(set(files), key=lambda value: value.relative_to(repo_root).as_posix()):
        relative = path.relative_to(repo_root).as_posix().encode("utf-8")
        digest.update(relative + b"\0" + hashlib.sha256(path.read_bytes()).hexdigest().encode("ascii") + b"\n")
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
    actual_digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
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


def gate(repo_root: Path, matrix: dict[str, Any], mode: str, build_root: Path) -> dict[str, Any]:
    matrix_errors = validate_matrix(repo_root, matrix)
    packages = [item for item in matrix["packages"] if isinstance(item, dict)]
    selected = [item for item in packages if item.get("publish")] if mode == "release" else [item for item in packages if item.get("ci")]
    errors = list(matrix_errors)
    if not selected:
        errors.append("no packages selected by the release matrix")
    scan_findings = scan_release_surface(repo_root)
    if scan_findings:
        errors.append(f"sensitive scan found {len(scan_findings)} potential public leaks")
    results: list[dict[str, Any]] = []
    for package in selected:
        result: dict[str, Any] = {"id": package["id"], "package_name": package["package_name"], "status": "passed"}
        source_root = repo_root / str(package["source_path"])
        versions, version_errors = package_versions(repo_root, package)
        result["versions"] = versions
        if version_errors:
            result["status"] = "failed"
            result["errors"] = version_errors
            errors.extend(f"{package['id']}: {error}" for error in version_errors)
        install_command = package.get("install_command")
        if isinstance(install_command, str):
            success, returncode = run_command(install_command, source_root)
            result["install_returncode"] = returncode
            if not success:
                result["status"] = "failed"
                result.setdefault("errors", []).append("install-command-failed")
                errors.append(f"{package['id']}: install-command-failed")
        command = package.get("test_command")
        if isinstance(command, str):
            success, returncode = run_command(command, source_root)
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
        results.append(result)
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
        "held_packages": [
            {"id": item["id"], "reason": item.get("hold_reason", "publish=false")}
            for item in packages
            if not item.get("ci") and not item.get("publish")
        ],
    }


def release_plan(matrix: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    packages = [item for item in matrix["packages"] if isinstance(item, dict) and item.get("publish")]
    versions = {item["id"]: result.get("versions", {}) for item, result in zip(packages, report["packages"])}
    waves: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for package in packages:
        values = {value for source_values in versions[package["id"]].values() for value in source_values}
        waves[int(package["release_wave"])].append(
            {
                "id": package["id"],
                "package_name": package["package_name"],
                "version": next(iter(values)),
                "dist_path": f"dist/{package['id']}",
            }
        )
    return {"waves": {str(index): waves.get(index, []) for index in range(4)}}


def write_github_outputs(path: Path, plan: dict[str, Any]) -> None:
    lines: list[str] = []
    for index in range(4):
        wave = plan["waves"][str(index)]
        lines.append(f"wave_{index}={json.dumps(wave, separators=(',', ':'))}")
        lines.append(f"has_wave_{index}={'true' if wave else 'false'}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


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
            args.write_staging_manifest.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            digest = hashlib.sha256(args.write_staging_manifest.read_bytes()).hexdigest()
            if args.update_matrix_snapshot:
                update_matrix_snapshot(args.matrix.resolve(), args.source_revision, digest)
                matrix = load_matrix(args.matrix.resolve())
        report = gate(repo_root, matrix, args.mode, args.build_root.resolve())
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
