"""Doctor diagnostic checks and environment analysis."""
from __future__ import annotations

import importlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import urllib.error
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from harness_ai_kit import package_manager as pm
from harness_ai_kit.domain import doctor_registry_lock
from harness_ai_kit.domain.models import CliAssetRecord, CliConfig, SkillRecord
from harness_ai_kit.domain.models.constants import (
    ASSET_DIRECTORY_NAMES,
    MANAGED_ASSET_TYPES,
    TEAM_NAMESPACE,
)
from harness_ai_kit.domain.inventory import (
    iter_cli_dirs,
    iter_managed_asset_dirs,
    load_cli_inventory,
    load_cli_metadata,
    load_managed_asset_inventory,
    load_skill_inventory,
    load_skill_metadata,
    load_skill_registry_inventory,
)
from harness_ai_kit.domain.identity import (
    PUBLIC_NAMESPACE,
    namespaced_asset_id,
    normalize_namespace,
)
from harness_ai_kit.domain.install_state import (
    installed_skill_payload_dir,
    installed_skill_version,
)
from harness_ai_kit.domain.manifest_ops import (
    find_project_lockfile,
    load_contextual_project_manifest,
    project_root_ids,
)
from harness_ai_kit.domain.runtime_install import resolve_target_dir
from harness_ai_kit.application.project_sync import resolve_skill_plan
from harness_ai_kit.domain.validation import (
    validate_cli_companion_docs,
    validate_companion_docs,
)
from harness_ai_kit.infrastructure.cli_installer import catalog_versions
from harness_ai_kit.infrastructure.config_io import (
    pyproject_path,
    read_project_version,
    read_top_changelog_version,
    resolve_repo_root_if_available,
)
from harness_ai_kit.infrastructure.registry_cli import load_cli_registry_index
from harness_ai_kit.infrastructure.registry_skill import (
    load_skill_registry_index,
)
from harness_ai_kit.domain.versions import compare_versions
from harness_ai_kit.product import active_product_profile

LOCKFILE_NAME = active_product_profile().lockfile_name
SELF_CLI_PACKAGE_NAME = active_product_profile().self_cli_package_name

# DSH acceptance baseline (see docs/dsh-integration.md).
DSH_BASELINE_VERSION = "0.1.0-rc.6"
PNPM_MIN_MAJOR = 10


def _run_version_command(command: list[str]) -> str:
    import subprocess

    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        return (proc.stdout or proc.stderr or "").strip().splitlines()[0] if (proc.stdout or proc.stderr) else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def doctor_dsh_results(home_dir: Path | None = None) -> list[dict[str, str]]:
    """Check the DSH environment: dsh CLI, pnpm, DSH_HOME, and profile dirs."""
    import os
    import shutil

    results: list[dict[str, str]] = []

    dsh_bin = shutil.which("dsh")
    if dsh_bin is None:
        results.append(
            {
                "subject": "dsh:cli",
                "status": "error",
                "message": "dsh not found on PATH (install via `npm i -g @deepseek-ai/dsh@0.1.0-rc.6` or `npx @deepseek-ai/dsh`)",
            }
        )
    else:
        version = _run_version_command([dsh_bin, "--version"])
        matched = version.startswith(DSH_BASELINE_VERSION)
        results.append(
            {
                "subject": "dsh:version",
                "status": "success" if matched else "warning",
                "message": f"{version or '<unknown>'} (baseline {DSH_BASELINE_VERSION})",
            }
        )

    pnpm_bin = shutil.which("pnpm")
    if pnpm_bin is None:
        results.append(
            {
                "subject": "dsh:pnpm",
                "status": "error",
                "message": "pnpm not found on PATH (required >=10 for dsh plugin management)",
            }
        )
    else:
        version = _run_version_command([pnpm_bin, "--version"])
        major_ok = False
        try:
            major_ok = int(version.split(".")[0]) >= PNPM_MIN_MAJOR
        except (ValueError, IndexError):
            major_ok = False
        results.append(
            {
                "subject": "dsh:pnpm",
                "status": "success" if major_ok else "warning",
                "message": f"{version or '<unknown>'} (required >=10)",
            }
        )

    base_home = home_dir or Path.home()
    dsh_home = os.environ.get("DSH_HOME", "").strip()
    dsh_home_path = Path(dsh_home).expanduser() if dsh_home else base_home / ".dsh"
    results.append(
        {
            "subject": "dsh:home",
            "status": "success" if dsh_home_path.exists() else "warning",
            "message": str(dsh_home_path) + (" (DSH_HOME)" if dsh_home else " (default ~/.dsh)"),
        }
    )

    profiles_dir = dsh_home_path / "profiles"
    if profiles_dir.is_dir():
        profile_names = sorted(p.name for p in profiles_dir.iterdir() if p.is_dir())
        results.append(
            {
                "subject": "dsh:profiles",
                "status": "success",
                "message": ", ".join(profile_names) if profile_names else "(none yet)",
            }
        )
    else:
        results.append(
            {
                "subject": "dsh:profiles",
                "status": "warning",
                "message": f"{profiles_dir} does not exist (created on first `dsh plugin --profile <name> add`)",
            }
        )

    return results


def doctor_pi_results(home_dir: Path | None = None, config: Any = None) -> list[dict[str, str]]:
    """Check the Pi Coding Agent environment: pi CLI, version, home, npm package dir, registry config.

    Pi evolves quickly, so no pinned version baseline: the version check only
    reports what is installed. See docs/pi-integration.md.
    """
    import shutil

    results: list[dict[str, str]] = []

    pi_bin = shutil.which("pi")
    if pi_bin is None:
        results.append(
            {
                "subject": "pi:cli",
                "status": "error",
                "message": "pi not found on PATH (install via `npm i -g --ignore-scripts @earendil-works/pi-coding-agent` or `curl -fsSL https://pi.dev/install.sh | sh`)",
            }
        )
    else:
        version = _run_version_command([pi_bin, "--version"])
        results.append(
            {
                "subject": "pi:version",
                "status": "success" if version else "warning",
                "message": version or "<unknown> (no pinned baseline; see docs/pi-integration.md)",
            }
        )

    base_home = home_dir or Path.home()
    pi_home = base_home / ".pi" / "agent"
    results.append(
        {
            "subject": "pi:home",
            "status": "success" if pi_home.is_dir() else "warning",
            "message": str(pi_home) + ("" if pi_home.is_dir() else " (created on first pi run)"),
        }
    )

    npm_dir = pi_home / "npm"
    if npm_dir.is_dir():
        packages = sorted(p.name for p in npm_dir.iterdir() if p.is_dir())
        results.append(
            {
                "subject": "pi:npm-packages",
                "status": "success",
                "message": ", ".join(packages) if packages else "(none installed)",
            }
        )
    else:
        results.append(
            {
                "subject": "pi:npm-packages",
                "status": "warning",
                "message": f"{npm_dir} does not exist (no pi packages installed yet)",
            }
        )

    install_url = getattr(config, "npm_registry_install_url", "") if config is not None else ""
    results.append(
        {
            "subject": "pi:npm-registry",
            "status": "success" if str(install_url or "").strip() else "warning",
            "message": str(install_url or "").strip()
            or "npm_registry_install_url not configured; pi package installs will fail (see docs/pi-integration.md)",
        }
    )

    return results


def public_catalog_path(repo_root: Path) -> Path | None:
    """Return the reviewed public catalog when this is an OSS checkout."""
    try:
        return next(
            path for path in repo_root.iterdir() if path.name == "CATALOG.md" and path.is_file()
        )
    except (FileNotFoundError, StopIteration):
        return None


def doctor_versions_results(repo_root: Path) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    catalog_path = public_catalog_path(repo_root) or repo_root / "catalog.md"
    is_public_checkout = catalog_path.name == "CATALOG.md"
    catalog_map = catalog_versions(catalog_path)

    for record in load_skill_inventory(repo_root).values():
        changelog_version = read_top_changelog_version(record.path / "CHANGELOG.md") if record.path else None
        if changelog_version == record.version:
            changelog_status = "success"
            changelog_message = f"skill.json={record.version}; CHANGELOG.md={changelog_version}"
        else:
            changelog_status = "error"
            changelog_message = f"skill.json={record.version}; CHANGELOG.md={changelog_version or '<missing>'}"
        results.append(
            {
                "subject": f"skill:{record.skill_id}:changelog",
                "status": changelog_status,
                "message": changelog_message,
            }
        )

        catalog_version = catalog_map.get(record.skill_id)
        if catalog_version == record.version:
            catalog_status = "success"
            catalog_message = f"skill.json={record.version}; {catalog_path.name}={catalog_version}"
        else:
            catalog_status = "error"
            catalog_message = f"skill.json={record.version}; {catalog_path.name}={catalog_version or '<missing>'}"
        results.append(
            {
                "subject": f"skill:{record.skill_id}:catalog",
                "status": catalog_status,
                "message": catalog_message,
            }
        )

    cli_inventory = load_cli_inventory(repo_root)
    cli_root_record = cli_inventory.get("harness-ai-kit")
    project_version = read_project_version(pyproject_path(repo_root))
    cli_metadata_version = cli_root_record.version if cli_root_record else None
    results.append(
        {
            "subject": "cli:harness-ai-kit:pyproject",
            "status": "success" if cli_metadata_version == project_version else "error",
            "message": f"cli.json={cli_metadata_version or '<missing>'}; pyproject.toml={project_version}",
        }
    )

    version_documents = ("README.md", "INSTALL.md")
    if is_public_checkout:
        version_documents = ("README.md", "README.zh-CN.md", "INSTALL.md", "docs/quickstart.md")
    for relative_path in version_documents:
        document_path = repo_root / relative_path
        if not document_path.exists():
            results.append(
                {
                    "subject": f"cli:harness-ai-kit:{relative_path}",
                    "status": "error",
                    "message": "Missing document.",
                }
            )
            continue
        content = document_path.read_text(encoding="utf-8")
        expected = f"{SELF_CLI_PACKAGE_NAME}=={project_version}"
        results.append(
            {
                "subject": f"cli:harness-ai-kit:{relative_path}",
                "status": "success" if expected in content else "error",
                "message": f"Expected `{expected}` in {relative_path}",
            }
        )

    skill_inventory = load_skill_inventory(repo_root)
    for skill_id in ("harness-ai-kit-ops", "harness-ai-kit-maintainer"):
        record = skill_inventory.get(skill_id)
        if record is None or record.path is None:
            if is_public_checkout:
                continue
            results.append(
                {
                    "subject": f"skill:{skill_id}:cli-dependency",
                    "status": "error",
                    "message": "Missing skill inventory record.",
                }
            )
            continue
        metadata = load_skill_metadata(record.path)
        declared_version = None
        for dependency in metadata.get("dependencies", []):
            if (
                str(dependency.get("type", "")).strip() == "cli"
                and str(dependency.get("id", "")).strip() == "harness-ai-kit"
            ):
                declared_version = str(dependency.get("version", "")).strip()
                break
        expected_version = f">={project_version}"
        # 向后兼容检查：验证声明的版本约束是否满足最小兼容要求
        # 允许 >=X.Y.Z 或 ==X.Y.Z 形式，但 >= 是推荐形式
        is_compatible = False
        if declared_version:
            if declared_version.startswith(">="):
                # >= 形式：提取版本号并比较
                declared_ver = declared_version[2:].strip()
                is_compatible = declared_ver == project_version or declared_ver < project_version
            elif declared_version.startswith("=="):
                # == 形式：精确匹配（向后兼容旧格式）
                declared_ver = declared_version[2:].strip()
                is_compatible = declared_ver == project_version
        results.append(
            {
                "subject": f"skill:{skill_id}:cli-dependency",
                "status": "success" if is_compatible else "error",
                "message": f"dependency={declared_version or '<missing>'}; expected={expected_version} (>= for backward compatibility)",
            }
        )
    return results


def registry_items_by_key(items: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    inventory: dict[str, dict[str, object]] = {}
    for item in items:
        asset_id = str(item.get("id", "")).strip()
        if not asset_id:
            continue
        key = namespaced_asset_id(normalize_namespace(item.get("namespace")), asset_id)
        inventory[key] = item
    return inventory


def check_yaml_duplicate_skills(manifest_path: Path) -> list[dict[str, str]]:
    """Check for duplicate skill entries in YAML manifest."""
    results: list[dict[str, str]] = []
    if not manifest_path.exists():
        return results

    manifest = load_project_manifest(manifest_path)
    skill_ids = [canonical_package_id(s.id, s.namespace) for s in manifest.assets.skills]
    duplicates = [sid for sid in skill_ids if skill_ids.count(sid) > 1]

    if duplicates:
        unique_dups = set(duplicates)
        results.append({
            "subject": f"manifest:{manifest_path.name}:duplicate-skills",
            "status": "warning",
            "message": f"Duplicate skill entries found: {', '.join(unique_dups)}",
        })

    return results


def check_bindings(cwd: Path) -> list[dict[str, str]]:
    """Check project metadata bindings validity in current directory."""
    results: list[dict[str, str]] = []
    metadata_path = cwd / ".platform" / "project-metadata.yml"

    if not metadata_path.exists():
        results.append({
            "subject": "bindings:metadata",
            "status": "warning",
            "message": f"No project metadata found at {metadata_path}",
        })
        return results

    import yaml
    with open(metadata_path, encoding="utf-8") as f:
        metadata = yaml.safe_load(f)

    bindings = metadata.get("bindings", {})

    # Check zentao bindings
    zentao = bindings.get("zentao", {})
    if zentao.get("product_id"):
        results.append({
            "subject": "bindings:zentao.product_id",
            "status": "success",
            "message": f"product_id={zentao['product_id']}",
        })
    if zentao.get("project_id"):
        results.append({
            "subject": "bindings:zentao.project_id",
            "status": "success",
            "message": f"project_id={zentao['project_id']}",
        })

    # Check gitea bindings
    gitea = bindings.get("gitea", {})
    if gitea.get("repo_url"):
        results.append({
            "subject": "bindings:gitea.repo_url",
            "status": "success",
            "message": f"repo_url={gitea['repo_url']}",
        })

    # Check mattermost bindings
    mattermost = bindings.get("mattermost", {})
    channels = mattermost.get("channels", {})
    for channel_name, channel_value in channels.items():
        results.append({
            "subject": f"bindings:mattermost.channels.{channel_name}",
            "status": "success",
            "message": f"channel={channel_value}",
        })

    # Check jenkins bindings
    jenkins = bindings.get("jenkins", {})
    if jenkins.get("job_name"):
        results.append({
            "subject": "bindings:jenkins.job_name",
            "status": "success",
            "message": f"job_name={jenkins['job_name']}",
        })

    # Check woodpecker bindings
    woodpecker = bindings.get("woodpecker", {})
    if woodpecker.get("repo_name"):
        results.append({
            "subject": "bindings:woodpecker.repo_name",
            "status": "success",
            "message": f"repo_name={woodpecker['repo_name']}",
        })
    if woodpecker.get("pipeline_path"):
        results.append({
            "subject": "bindings:woodpecker.pipeline_path",
            "status": "success",
            "message": f"pipeline_path={woodpecker['pipeline_path']}",
        })

    # Check cicd engine declaration
    cicd = bindings.get("cicd", {})
    if cicd.get("engine"):
        engine = cicd["engine"]
        valid_engines = {"jenkins", "woodpecker"}
        results.append({
            "subject": "bindings:cicd.engine",
            "status": "success" if engine in valid_engines else "warning",
            "message": f"engine={engine}" if engine in valid_engines else f"engine={engine} (expected: jenkins|woodpecker)",
        })

    # Check shared_resources references
    shared_refs = metadata.get("shared_resources", [])
    if shared_refs:
        global_sr_path = Path.home() / ".harness-ai-kit" / "shared-resources.yml"
        global_sr: dict = {}
        if global_sr_path.exists():
            with open(global_sr_path, encoding="utf-8") as f:
                global_sr = yaml.safe_load(f) or {}
        global_resources = global_sr.get("resources", {})

        for entry in shared_refs:
            ref = entry.get("ref", "") if isinstance(entry, dict) else str(entry)
            if not ref:
                continue
            # Resolve ref: "type.name" → global_resources[type][name]
            parts = ref.split(".", 1)
            if len(parts) == 2:
                rtype, rname = parts
                exists = rtype in global_resources and rname in global_resources.get(rtype, {})
            else:
                exists = False
            results.append({
                "subject": f"shared_resources:{ref}",
                "status": "success" if exists else "error",
                "message": "resolved" if exists else f"not found in {global_sr_path}",
            })

    return results


def doctor_drift_results(repo_root: Path, config: CliConfig) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    skill_index = load_skill_registry_index(config)
    cli_index = load_cli_registry_index(config)
    skill_items = list(skill_index.get("skills", []))
    cli_items = list(cli_index.get("clis", []))
    remote_skills = registry_items_by_key(skill_items)
    remote_clis = registry_items_by_key(cli_items)

    duplicate_skill_namespaces: dict[str, set[str]] = {}
    for item in skill_items:
        asset_id = str(item.get("id", "")).strip()
        if not asset_id:
            continue
        duplicate_skill_namespaces.setdefault(asset_id, set()).add(normalize_namespace(item.get("namespace")))
    for asset_id, namespaces in sorted(duplicate_skill_namespaces.items()):
        if len(namespaces) > 1 and "" in namespaces:
            results.append(
                {
                    "subject": f"registry:skill:{asset_id}:duplicate-namespace",
                    "status": "warning",
                    "message": "registry has both flat and namespace-aware entries",
                }
            )

    for record in load_skill_inventory(repo_root).values():
        metadata = load_skill_metadata(record.path)
        key = namespaced_asset_id(normalize_namespace(metadata.get("namespace")), record.skill_id)
        remote = remote_skills.get(key)
        if remote is None:
            results.append(
                {
                    "subject": f"skill:{key}",
                    "status": "error",
                    "message": f"local={record.version}; registry=<missing>",
                }
            )
            continue
        remote_version = str(remote.get("latest_version", "")).strip()
        comparison = compare_versions(record.version, remote_version)
        if comparison == 0:
            status = "success"
            message = f"local={record.version}; registry={remote_version}"
        elif comparison > 0:
            status = "warning"
            message = f"local={record.version}; registry={remote_version}; local is ahead"
        else:
            status = "warning"
            message = f"local={record.version}; registry={remote_version}; registry is ahead"
        results.append({"subject": f"skill:{key}", "status": status, "message": message})

    for record in load_cli_inventory(repo_root).values():
        metadata = load_cli_metadata(record.path)
        key = namespaced_asset_id(normalize_namespace(metadata.get("namespace")), record.cli_id)
        remote = remote_clis.get(key)
        if remote is None:
            results.append(
                {
                    "subject": f"cli:{key}",
                    "status": "error",
                    "message": f"local={record.version}; registry=<missing>",
                }
            )
            continue
        remote_version = str(remote.get("latest_version", "")).strip()
        comparison = compare_versions(record.version, remote_version)
        if comparison == 0:
            status = "success"
            message = f"local={record.version}; registry={remote_version}"
        elif comparison > 0:
            status = "warning"
            message = f"local={record.version}; registry={remote_version}; local is ahead"
        else:
            status = "warning"
            message = f"local={record.version}; registry={remote_version}; registry is ahead"
        results.append({"subject": f"cli:{key}", "status": status, "message": message})

    return results


def find_lock_node_by_root(lockfile: pm.Lockfile, root_id: str) -> pm.LockNode | None:
    namespace, base_id = pm.split_canonical_id(root_id)
    for node in lockfile.nodes:
        if node.type != "skill" or node.id != base_id:
            continue
        if namespace is not None and node.namespace != namespace:
            continue
        return node
    return None


def version_for_skill_record(record: SkillRecord | None, namespace: str | None) -> str | None:
    if record is None:
        return None
    if record.path is not None:
        metadata = load_skill_metadata(record.path)
        if pm.normalize_namespace(metadata.get("namespace")) != pm.normalize_namespace(namespace):
            return None
    return record.version


def source_selection_reason(
    selected_source: str | None,
    preferred_sources: list[str],
    repo_version: str | None,
    registry_version: str | None,
) -> str:
    if selected_source is None:
        return "unresolved"
    preferred = preferred_sources[0] if preferred_sources else ""
    if selected_source == pm.SOURCE_REPO:
        if preferred == pm.SOURCE_REPO and repo_version:
            return "selected repo-checkout because it is the preferred available source"
        if repo_version:
            return "selected repo-checkout because registry was unavailable or did not satisfy the request"
    if selected_source == pm.SOURCE_REGISTRY:
        if preferred == pm.SOURCE_REGISTRY and registry_version:
            return "selected team-skill-registry because it is the preferred available source"
        if registry_version:
            return "selected team-skill-registry because repo-checkout was unavailable or not selected"
    if selected_source == pm.SOURCE_PUBLIC_REGISTRY:
        if preferred == pm.SOURCE_PUBLIC_REGISTRY and registry_version:
            return "selected public-registry because it is the preferred available source"
        if registry_version:
            return "selected public-registry because workspace-repo was unavailable or not selected"
    return f"selected {selected_source}"


def doctor_sources_payload(
    config: CliConfig,
    repo_root_arg: str | None,
    target_dir_arg: str | None = None,
) -> dict[str, object]:
    repo_root = resolve_repo_root_if_available(repo_root_arg, config)
    manifest_path, manifest = load_contextual_project_manifest(target_dir_arg)
    lock_path = (
        pm.lockfile_path(manifest_path.parent)
        if manifest_path is not None
        else find_project_lockfile()
    )
    lockfile = pm.read_lockfile(lock_path) if lock_path and lock_path.exists() else None
    warnings: list[str] = []
    errors: list[str] = []

    local_inventory = load_skill_inventory(repo_root) if repo_root is not None else {}
    registry_inventory: dict[str, SkillRecord] = {}
    registry_available = True
    try:
        registry_inventory = load_skill_registry_inventory(config)
    except urllib.error.URLError as exc:
        registry_available = False
        warnings.append(f"Skill registry unavailable: {exc}")

    root_ids: list[str] = []
    runtime_id = "codex"
    install_scope = "project"
    features: list[str] = []
    if manifest is not None:
        root_ids = project_root_ids(manifest)
        runtime_id = manifest.runtime
        install_scope = manifest.scope
        features = list(manifest.features)
    elif lockfile is not None:
        root_ids = list(lockfile.roots)
        runtime_id = lockfile.runtime
        install_scope = lockfile.install_scope
        features = list(lockfile.features)
        warnings.append("Project has harness-ai-kit.lock but no harness-ai-kit.yml; current state is snapshot-driven only.")

    plan = None
    if root_ids and repo_root is not None:
        try:
            plan = resolve_skill_plan(
                repo_root,
                config,
                root_ids=root_ids,
                runtime_id=runtime_id,
                install_scope=install_scope,
                features=features,
                offline=not registry_available,
            )
        except (FileNotFoundError, KeyError, ValueError) as exc:
            errors.append(f"Failed to resolve current sources: {exc}")

    roots_payload: list[dict[str, object]] = []
    for root_id in root_ids:
        namespace, base_id = pm.split_canonical_id(root_id)
        repo_record = local_inventory.get(base_id)
        registry_record = registry_inventory.get(base_id)
        repo_version = version_for_skill_record(repo_record, namespace)
        registry_version = version_for_skill_record(registry_record, namespace)
        selected_node = None
        preferred_sources = [pm.SOURCE_REGISTRY, pm.SOURCE_REPO]
        if plan is not None:
            selected_node = find_lock_node_by_root(plan.to_lockfile(), root_id)
        elif lockfile is not None:
            selected_node = find_lock_node_by_root(lockfile, root_id)
        if repo_root is not None:
            local_root_dir = repo_root / "skills" / base_id
            if local_root_dir.exists():
                local_manifest = pm.load_skill_manifest(local_root_dir)
                if namespace is None or local_manifest.namespace == namespace:
                    preferred_sources = list(local_manifest.sources.preferred)
        if repo_version and registry_version and compare_versions(repo_version, registry_version) < 0:
            warnings.append(
                f"{root_id}: local harness-ai-kit checkout is older than registry ({repo_version} < {registry_version})"
            )
        roots_payload.append(
            {
                "id": base_id,
                "namespace": namespace,
                "canonical_id": root_id,
                "repo_version": repo_version,
                "registry_version": registry_version,
                "selected_source": selected_node.source if selected_node else None,
                "selected_version": selected_node.version if selected_node else None,
                "reason": source_selection_reason(
                    selected_node.source if selected_node else None,
                    preferred_sources,
                    repo_version,
                    registry_version,
                ),
            }
        )

    if manifest is None:
        warnings.append("No harness-ai-kit.yml found in the current project.")
    if repo_root is None:
        warnings.append("harness-ai-kit repository root is not available on this machine.")

    project_root = manifest_path.parent if manifest_path is not None else None
    manifest_skill_ids = project_root_ids(manifest) if manifest is not None else []
    guard_warnings, guard_errors = doctor_registry_lock.collect_registry_lock_guardrails(
        project_root=project_root,
        manifest_root_ids=root_ids,
        manifest_skill_ids=manifest_skill_ids,
        lockfile=lockfile,
        registry_available=registry_available,
        repo_root=repo_root,
    )
    warnings.extend(guard_warnings)
    errors.extend(guard_errors)

    return {
        "manifest_path": str(manifest_path) if manifest_path is not None else "",
        "manifest_found": manifest is not None,
        "lock_path": str(lock_path) if lock_path is not None else "",
        "lock_found": bool(lockfile),
        "repo_root": str(repo_root) if repo_root is not None else "",
        "registry_available": registry_available,
        "runtime": runtime_id,
        "scope": install_scope,
        "features": features,
        "roots": roots_payload,
        "warnings": warnings,
        "errors": errors,
    }


def managed_asset_records(repo_root: Path) -> list[SkillRecord]:
    records: list[SkillRecord] = []
    for asset_type in MANAGED_ASSET_TYPES:
        records.extend(load_managed_asset_inventory(repo_root, asset_type).values())
    return records


def environment_requirements_for_records(records: list[SkillRecord]) -> list[dict[str, object]]:
    payload: list[dict[str, object]] = []
    for record in records:
        if record.path is None:
            continue
        manifest = pm.load_skill_manifest(record.path)
        environment = manifest.environment.model_dump(mode="json")
        payload.append({"asset_type": record.asset_type, "id": record.skill_id, "environment": environment})
    return payload


def python_import_name(package: str) -> str:
    base_name = package.split("[")[0].split("==")[0].split(">=")[0].split("<=")[0].strip()
    known = {
        "beautifulsoup4": "bs4",
        "pillow": "PIL",
        "pymupdf": "fitz",
        "pyyaml": "yaml",
        "python-docx": "docx",
        "python-pptx": "pptx",
    }
    return known.get(base_name.lower(), base_name.replace("-", "_"))


def current_platform_tags() -> set[str]:
    system_name = platform.system().lower()
    tags = {system_name, sys.platform.lower()}
    if system_name == "windows":
        tags.update({"win32"})
    if system_name == "darwin":
        tags.update({"macos", "mac"})
    if system_name == "linux":
        tags.update({"linux"})
    return tags


def environment_records_for_lockfile(lockfile: pm.Lockfile) -> list[dict[str, object]]:
    payload: list[dict[str, object]] = []
    for node in lockfile.nodes:
        environment = dict(node.environment or {})
        if not environment:
            continue
        payload.append({"asset_type": node.type, "id": node.id, "environment": environment})
    return payload


def executable_matches_platform(executable: dict[str, object]) -> bool:
    platforms = [str(item).strip().lower() for item in executable.get("platforms", []) if str(item).strip()]
    return not platforms or bool(current_platform_tags() & set(platforms))


def missing_environment_requirements(records: list[dict[str, object]]) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    for item in records:
        asset_ref = f"{item['asset_type']}:{item['id']}"
        environment = dict(item["environment"])
        for executable in environment.get("system", []):
            if not executable_matches_platform(executable):
                continue
            command = str(executable.get("command", "")).strip()
            name = str(executable.get("name", command)).strip()
            available = bool(command and shutil.which(command.split()[0]))
            if not available:
                results.append(
                    {
                        "asset": asset_ref,
                        "kind": "system",
                        "subject": name,
                        "detail": command,
                        "optional": "yes" if bool(executable.get("optional", False)) else "no",
                    }
                )
        python_packages = [str(pkg).strip() for pkg in environment.get("python_packages", []) if str(pkg).strip()]
        for package in python_packages:
            module_name = python_import_name(package)
            try:
                importlib.import_module(module_name)
            except Exception:
                results.append(
                    {
                        "asset": asset_ref,
                        "kind": "python",
                        "subject": package,
                        "detail": environment.get("python_strategy", "none"),
                        "optional": "no",
                    }
                )
    return results


def install_python_packages(packages: list[str], strategy: str, dry_run: bool) -> list[str]:
    if not packages:
        return []
    if strategy == "project-venv" and sys.prefix == getattr(sys, "base_prefix", sys.prefix):
        raise ValueError("project-venv dependencies require an active virtual environment before installation.")
    command = [sys.executable, "-m", "pip", "install", *packages]
    rendered = " ".join(command)
    if dry_run:
        return [rendered]
    subprocess.run(command, check=True, capture_output=True, text=True, encoding="utf-8")
    return [rendered]


def install_environment_requirements(records: list[dict[str, object]], dry_run: bool = False) -> list[str]:
    outputs: list[str] = []
    seen_system: set[tuple[str, str]] = set()
    python_groups: dict[str, list[str]] = {}
    for item in records:
        asset_ref = f"{item['asset_type']}:{item['id']}"
        environment = dict(item["environment"])
        for executable in environment.get("system", []):
            if not executable_matches_platform(executable):
                continue
            command = str(executable.get("command", "")).strip()
            if command and shutil.which(command.split()[0]):
                continue
            name = str(executable.get("name", command)).strip()
            install_commands = [str(value).strip() for value in executable.get("install_commands", []) if str(value).strip()]
            if not install_commands:
                continue
            key = (name, install_commands[0])
            if key in seen_system:
                continue
            seen_system.add(key)
            rendered = install_commands[0]
            outputs.append(f"{asset_ref}: system install -> {rendered}")
            if not dry_run:
                subprocess.run(rendered, check=True, shell=True, capture_output=True, text=True, encoding="utf-8")
        strategy = str(environment.get("python_strategy", "none")).strip() or "none"
        if strategy == "none":
            continue
        packages = [str(pkg).strip() for pkg in environment.get("python_packages", []) if str(pkg).strip()]
        if not packages:
            continue
        bucket = python_groups.setdefault(strategy, [])
        for package in packages:
            if package not in bucket:
                bucket.append(package)
    for strategy, packages in python_groups.items():
        for rendered in install_python_packages(packages, strategy, dry_run):
            outputs.append(f"python[{strategy}] -> {rendered}")
    return outputs


def doctor_env_results(repo_root: Path) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    for item in environment_requirements_for_records(managed_asset_records(repo_root)):
        asset_ref = f"{item['asset_type']}:{item['id']}"
        environment = dict(item["environment"])
        for executable in environment.get("system", []):
            if not executable_matches_platform(executable):
                continue
            command = str(executable.get("command", "")).strip()
            name = str(executable.get("name", command)).strip()
            available = bool(command and shutil.which(command.split()[0]))
            optional = bool(executable.get("optional", False))
            status = "success" if available else ("warning" if optional else "error")
            installable = bool(executable.get("install_commands", []))
            if available:
                message = f"{command} is available"
            else:
                suffix = "; install commands declared" if installable else "; no install command declared"
                message = f"{command} is missing{suffix}"
            results.append({"subject": f"{asset_ref}:system:{name}", "status": status, "message": message})
        python_packages = [str(pkg) for pkg in environment.get("python_packages", [])]
        for package in python_packages:
            module_name = python_import_name(package)
            try:
                importlib.import_module(module_name)
                status = "success"
                message = f"Python package import ok: {module_name}"
            except Exception:
                status = "warning"
                message = f"Python package not importable in current interpreter: {module_name}"
            results.append({"subject": f"{asset_ref}:python:{package}", "status": status, "message": message})
        for font in environment.get("fonts", []):
            results.append({"subject": f"{asset_ref}:font:{font}", "status": "warning", "message": "Font presence requires platform-specific verification."})
    if not results:
        results.append({"subject": "environment", "status": "success", "message": "No structured environment requirements declared."})
    return results


def doctor_assets_results(repo_root: Path) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    for record in managed_asset_records(repo_root):
        if record.path is None:
            continue
        manifest = pm.load_skill_manifest(record.path)
        doc_errors = validate_companion_docs(record.path, manifest)
        status = "success" if not doc_errors else "error"
        message = "companion docs ready" if not doc_errors else "; ".join(doc_errors)
        results.append({"subject": f"{record.asset_type}:{record.skill_id}", "status": status, "message": message})
    for cli_dir in iter_cli_dirs(repo_root / "cli"):
        doc_errors = validate_cli_companion_docs(cli_dir)
        status = "success" if not doc_errors else "error"
        message = "companion docs ready" if not doc_errors else "; ".join(doc_errors)
        results.append({"subject": f"cli:{cli_dir.name}", "status": status, "message": message})
    results.extend(check_namespace_conventions(repo_root))
    return results


# 资产 namespace 语义分组（2026-08-16 治理后生效）：
# - bundle 资产（skill/loop/plugin/subagent）：可发布、可被依赖解析，namespace = 隔离域（team/public）
# - manual 资产（hook/mcp/cli）：外部工具/分发配置，无隔离域语义，不应声明 namespace
BUNDLE_NAMESPACED_ASSET_TYPES = ("skill", "loop", "plugin", "subagent")
MANUAL_NAMESPACE_FREE_ASSET_TYPES = ("hook", "mcp")


def check_namespace_conventions(repo_root: Path) -> list[dict[str, str]]:
    """资产 namespace 治理门禁（2026-08-16 统一 team/ 后生效）。

    namespace 语义 = 隔离域，仅适用于 bundle 可发布资产：
    - skill/loop/plugin/subagent：内部一律 ``team/``，对外用 ``public/``；
      缺失 → warning（应显式声明），不在白名单 → error（namespace 仅表示隔离域，禁止二级分类）
    - hook/mcp/cli：manual 安装/分发资产，无隔离域语义；
      声明了 namespace → warning（冗余字段，应移除）
    """
    results: list[dict[str, str]] = []
    allowed_namespaces = {TEAM_NAMESPACE, PUBLIC_NAMESPACE}
    for asset_type in (*BUNDLE_NAMESPACED_ASSET_TYPES, *MANUAL_NAMESPACE_FREE_ASSET_TYPES):
        asset_root = repo_root / ASSET_DIRECTORY_NAMES[asset_type]
        for asset_dir in iter_managed_asset_dirs(asset_root):
            metadata_path = pm.manifest_metadata_path(asset_dir, asset_type)
            if not metadata_path.exists():
                continue
            try:
                manifest = pm.load_skill_manifest(asset_dir)
            except Exception:
                continue
            namespace = normalize_namespace(manifest.namespace)
            subject = f"namespace:{asset_type}:{manifest.id}"
            if asset_type in MANUAL_NAMESPACE_FREE_ASSET_TYPES:
                if namespace is not None:
                    results.append(
                        {
                            "subject": subject,
                            "status": "warning",
                            "message": f"namespace=`{namespace}` 冗余：hook/mcp 是 manual 安装的外部工具，"
                            "无隔离域语义（与 CLI 一致），请移除 namespace 字段",
                        }
                    )
                continue
            if namespace is None:
                results.append(
                    {
                        "subject": subject,
                        "status": "warning",
                        "message": "缺少顶层 namespace；内部资产应声明 `namespace: team`（对外资产用 `public`）",
                    }
                )
            elif namespace not in allowed_namespaces:
                results.append(
                    {
                        "subject": subject,
                        "status": "error",
                        "message": f"namespace=`{namespace}` 不在白名单 team/public；内部资产应归入 team/，"
                        "namespace 仅表示隔离域，禁止用作二级分类",
                    }
                )

    # cli：manual 分发资产（pip/nexus index），与 hook/mcp 同规则——无隔离域语义。
    # cli/ 目录不在 ASSET_DIRECTORY_NAMES 中，且 cli.json 结构独立，故单独扫描。
    for cli_dir in iter_cli_dirs(repo_root / "cli"):
        try:
            metadata = load_cli_metadata(cli_dir)
        except Exception:
            continue
        cli_id = str(metadata.get("id") or cli_dir.name)
        namespace = normalize_namespace(metadata.get("namespace"))
        if namespace is not None:
            results.append(
                {
                    "subject": f"namespace:cli:{cli_id}",
                    "status": "warning",
                    "message": f"namespace=`{namespace}` 冗余：cli 是 manual 分发资产，"
                    "无隔离域语义，请移除 namespace 字段",
                }
            )
    return results


def doctor_extends_results(repo_root: Path, config: Any, target_dir: Path | None = None) -> list[dict[str, str]]:
    """Check extends health across all installed skills.

    Performs three checks per skill with extends edges:
    1. BASE_AVAILABLE: base skill is installed at the correct version
    2. VERSION_MATCH: lockfile pinned version matches installed base skill
    3. SOURCE_REACHABLE: base skill source (git URL or registry) is accessible

    Returns a list of result dicts with subject, status (success/warning/error),
    and message fields.
    """
    results: list[dict[str, str]] = []

    # Find lockfile
    lock_path = find_project_lockfile() if target_dir is None else None
    if lock_path is None and target_dir is not None:
        lock_path = target_dir / LOCKFILE_NAME
    if lock_path is None or not (lock_path.exists() if lock_path else False):
        return [{"subject": "extends", "status": "error", "message": "No lockfile found for extends health check."}]

    try:
        lockfile = pm.read_lockfile(lock_path if lock_path else Path())
    except (OSError, ValidationError, json.JSONDecodeError, ValueError):
        return [{"subject": "extends", "status": "error", "message": "Failed to read lockfile."}]

    runtime_id = getattr(lockfile, "runtime", "codex")
    target_root = target_dir or lock_path.parent if lock_path else Path.cwd()
    install_target = resolve_target_dir(target_root, None, runtime_id=runtime_id, scope=getattr(lockfile, "install_scope", "project"))

    # Collect nodes with extends
    extends_nodes = [node for node in lockfile.nodes if getattr(node, "extends", None)]
    if not extends_nodes:
        return [{"subject": "extends:summary", "status": "success", "message": "No skills with extends declarations found."}]

    extends_count = 0
    base_count = 0
    seen_bases: set[str] = set()

    for node in extends_nodes:
        for ext_edge in (node.extends or []):
            base_canonical_id = str(ext_edge.get("base_skill_id", ""))
            base_version = str(ext_edge.get("base_version", ""))
            strategy = str(ext_edge.get("merge_strategy", "prepend"))
            subject = f"extends:{node.id}->{base_canonical_id}"

            if not base_canonical_id:
                results.append({"subject": subject, "status": "error", "message": "Missing base_skill_id in extends edge."})
                continue

            extends_count += 1
            if base_canonical_id not in seen_bases:
                seen_bases.add(base_canonical_id)
                base_count += 1

            # Check 1: Base availability (installed at correct version)
            base_installed_version = installed_skill_version(install_target, base_canonical_id, runtime_id)
            if not base_installed_version:
                results.append({
                    "subject": subject,
                    "status": "error",
                    "message": f"Base skill {base_canonical_id} not installed. Expected version: {base_version}.",
                })
                continue

            if base_version and base_installed_version != base_version:
                results.append({
                    "subject": subject,
                    "status": "warning",
                    "message": f"Base {base_canonical_id} installed at {base_installed_version}, expected {base_version}.",
                })
            else:
                # Check 2: Merge result integrity
                skill_dir = installed_skill_payload_dir(install_target, node.id, runtime_id)
                skill_md = skill_dir / "SKILL.md"
                if not skill_md.exists():
                    results.append({
                        "subject": subject,
                        "status": "warning",
                        "message": f"SKILL.md not found for {node.id}; merge may be incomplete.",
                    })
                    continue

                content = skill_md.read_text(encoding="utf-8")
                expected_attr = f"Extends: {base_canonical_id}"
                if expected_attr not in content:
                    results.append({
                        "subject": subject,
                        "status": "warning",
                        "message": f"Extends attribution missing in SKILL.md; merge may not have been applied.",
                    })
                else:
                    # Check 3: Source reachability
                    base_node = pm.find_lock_node(lockfile.nodes, "skill", base_canonical_id)
                    if base_node is not None:
                        source_msg = f"source={base_node.source}"
                        if base_node.source_ref:
                            source_path = Path(base_node.source_ref)
                            if source_path.exists():
                                source_msg += " (reachable)"
                            else:
                                source_msg += " (unreachable)"
                                results.append({
                                    "subject": subject,
                                    "status": "warning",
                                    "message": f"Base {base_canonical_id} source not reachable: {source_msg}. Merge valid but source may be stale.",
                                })
                                continue
                        results.append({
                            "subject": subject,
                            "status": "success",
                            "message": f"Healthy: extends {base_canonical_id}@{base_version} ({strategy}) - {source_msg}.",
                        })
                    else:
                        results.append({
                            "subject": subject,
                            "status": "warning",
                            "message": f"Healthy merge but base {base_canonical_id} not in lockfile nodes.",
                        })

    if extends_count > 0:
        results.append({
            "subject": "extends:summary",
            "status": "success",
            "message": f"Checked {extends_count} extends edge(s) across {len(extends_nodes)} skill(s) and {base_count} unique base(s).",
        })

    return results
