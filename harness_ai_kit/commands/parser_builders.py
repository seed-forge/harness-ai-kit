from __future__ import annotations

import argparse
from typing import Any, Sequence

from ..product import active_product_profile


def add_config_bootstrap_parsers(subparsers: Any, *, runtime_choices: Sequence[str]) -> None:
    profile = active_product_profile()
    config_parser = subparsers.add_parser(
        "config",
        help=f"Inspect or update the saved {profile.command_name} CLI configuration.",
    )
    config_subparsers = config_parser.add_subparsers(dest="config_command", required=True)
    config_show_parser = config_subparsers.add_parser("show", help="Show the saved config values.")
    config_show_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    config_set_parser = config_subparsers.add_parser(
        "set",
        help="Update saved config values via flags and/or dotted KEY=VALUE pairs (e.g. assets.myctl.api_url=https://...).",
    )
    config_set_parser.add_argument(
        "pairs", nargs="*", metavar="KEY=VALUE",
        help="Dotted-path assignments written to config.yaml, e.g. assets.myctl.api_url=https://... publish.push=true. Values are parsed as YAML scalars.",
    )
    config_set_parser.add_argument("--repo-url", help=f"Persist the default {profile.command_name} remote repository URL.")
    config_set_parser.add_argument("--checkout-dir", help="Persist the default local checkout directory.")
    config_set_parser.add_argument("--registry-upload-url", help="Persist the private PyPI/Nexus upload URL.")
    config_set_parser.add_argument("--registry-index-url", help="Persist the private package install index URL.")
    config_set_parser.add_argument("--skill-registry-upload-url", help="Persist the raw skill registry upload URL.")
    config_set_parser.add_argument("--skill-registry-index-url", help="Persist the raw skill registry index URL.")
    config_set_parser.add_argument("--public-skill-registry-upload-url", help="Persist the public skill registry upload URL.")
    config_set_parser.add_argument("--public-skill-registry-index-url", help="Persist the public skill registry index URL.")
    config_set_parser.add_argument("--cli-registry-upload-url", help="Persist the raw CLI registry upload URL.")
    config_set_parser.add_argument("--cli-registry-index-url", help="Persist the raw CLI registry index URL.")
    config_set_parser.add_argument("--trusted-host", help="Persist the trusted host used for HTTP package indexes.")
    config_set_parser.add_argument("--tag-prefix", help="Persist the git tag prefix for releases, such as v.")
    config_set_parser.add_argument(
        "--role", choices=["consumer", "contributor", "maintainer"],
        help="Persist the collaborator role: consumer (install/sync only), contributor (can publish), or maintainer (full governance)."
    )
    config_set_parser.add_argument("--identity-name", help="Persist the git commit author name.")
    config_set_parser.add_argument("--identity-email", help="Persist the git commit author email.")
    config_set_parser.add_argument("--default-runtime", help="Persist the default runtime for install commands.")
    config_set_parser.add_argument("--default-scope", choices=["project", "global"], help="Persist the default scope for install commands.")
    config_set_parser.add_argument(
        "--install-external-immediately", choices=["true", "false"],
        help="When true, install/sync/update automatically install external dependencies (pip packages, etc.) without requiring --install-external."
    )

    config_get_parser = config_subparsers.add_parser("get", help="Read one config value by dotted key path (e.g. assets.myctl.api_url).")
    config_get_parser.add_argument("key", help="Dotted key path into config.yaml, e.g. role, publish.push, assets.myctl.api_url.")
    config_get_parser.add_argument("--json", action="store_true", help="Emit the value as machine-readable JSON.")

    config_unset_parser = config_subparsers.add_parser("unset", help="Remove one or more config keys by dotted path; empty parent sections are pruned.")
    config_unset_parser.add_argument("keys", nargs="+", metavar="KEY", help="Dotted key paths to delete, e.g. assets.myctl.api_url.")

    whoami_parser = subparsers.add_parser("whoami", help="Show current collaborator role, identity, and defaults.")

    init_parser = subparsers.add_parser(
        "init",
        help="Initialize this machine with default repo and registry settings, then bootstrap the team checkout.",
    )
    init_parser.add_argument("--repo-url", help=f"Override the default {profile.command_name} remote repository URL.")
    init_parser.add_argument("--checkout-dir", help="Override the default checkout directory.")
    init_parser.add_argument("--registry-upload-url", help="Override the default private registry upload URL.")
    init_parser.add_argument("--registry-index-url", help="Override the default private registry install index URL.")
    init_parser.add_argument("--skill-registry-upload-url", help="Override the default raw skill registry upload URL.")
    init_parser.add_argument("--skill-registry-index-url", help="Override the default raw skill registry index URL.")
    init_parser.add_argument("--public-skill-registry-upload-url", help="Override the public skill registry upload URL.")
    init_parser.add_argument("--public-skill-registry-index-url", help="Override the public skill registry index URL.")
    init_parser.add_argument("--cli-registry-upload-url", help="Override the default raw CLI registry upload URL.")
    init_parser.add_argument("--cli-registry-index-url", help="Override the default raw CLI registry index URL.")
    init_parser.add_argument("--trusted-host", help="Override the default trusted host.")
    init_parser.add_argument("--tag-prefix", help="Override the default release tag prefix.")
    init_parser.add_argument("--skip-sync", action="store_true", help="Skip syncing when the checkout already exists.")

    bootstrap_parser = subparsers.add_parser(
        "bootstrap",
        help=f"Clone or register the shared {profile.command_name} repository for this machine.",
    )
    bootstrap_parser.add_argument("--repo-url", help=f"Remote git URL for the {profile.command_name} repository. Falls back to the saved config value.")
    bootstrap_parser.add_argument("--checkout-dir", help=f"Local checkout directory. Defaults to ~/{profile.config_dirname}/{profile.default_checkout_dirname}.")
    bootstrap_parser.add_argument("--sync", action="store_true", help="Run git fetch/pull after clone when the checkout already exists.")
    bootstrap_parser.add_argument("--no-git-proxy", action="store_true", help="Disable HTTP(S) proxy during git clone (helpful when corporate proxy returns \"Empty reply from server\")")

    doctor_parser = subparsers.add_parser(
        "doctor",
        help=f"Check whether git, config, and the selected checkout are ready for {profile.command_name} operations.",
    )
    doctor_parser.add_argument("subject", nargs="?", help="Optional selector: runtimes, skills, deps, env, assets, versions, drift, sources, extends.")
    doctor_parser.add_argument("--repo-root", help=f"Explicit {profile.command_name} repository root.")
    doctor_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    doctor_parser.add_argument("--runtime", choices=runtime_choices, default="codex", help="Runtime selector for `doctor skills`. Defaults to codex.")
    doctor_parser.add_argument("--check-bindings", action="store_true", help="Check project metadata bindings validity in current directory.")

    validate_parser = subparsers.add_parser("validate", help=f"Validate the {profile.command_name} repository structure and skill metadata.")
    validate_parser.add_argument("--repo-root", help=f"Explicit {profile.command_name} repository root.")
    validate_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")

    sync_repo_parser = subparsers.add_parser(
        "sync-repo",
        help=f"Fetch and fast-forward the configured or selected {profile.command_name} checkout.",
    )
    sync_repo_parser.add_argument("--repo-root", help=f"Explicit {profile.command_name} repository root. Falls back to cwd discovery or saved checkout.")

    # Bind command: update project metadata bindings
    bind_parser = subparsers.add_parser(
        "bind",
        help="Update project metadata bindings in current directory.",
    )
    bind_parser.add_argument("path", help="Binding path (e.g., 'zentao.project_id', 'gitea.repo_url')")
    bind_parser.add_argument("value", help="Value to set")

    # Use command: switch working directory
    use_parser = subparsers.add_parser(
        "use",
        help="Switch working directory to another project.",
    )
    use_parser.add_argument("target", help="Target project directory path")

    # Shared resources command: manage global shared resources
    from .shared_resources import build_shared_resources_parser
    build_shared_resources_parser(subparsers)


def add_inspect_resolution_parsers(subparsers: Any, *, runtime_choices: Sequence[str]) -> None:
    list_parser = subparsers.add_parser("list", help="List installable skills from the repository.")
    list_parser.add_argument("subject", nargs="?", help="Optional selector: skills, loops, clis, or assets.")
    list_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    list_parser.add_argument("--repo-root", help="Explicit harness-ai-kit repository root.")
    list_parser.add_argument("--sync-repo", action="store_true", help="Sync the repo before listing skills.")

    resolve_parser = subparsers.add_parser("resolve", help="Resolve a skill dependency graph without installing it.")
    resolve_parser.add_argument("asset_kind", choices=["skill", "loop"], help="Asset kind to resolve.")
    resolve_parser.add_argument("asset_id", help="Root asset id to resolve.")
    resolve_parser.add_argument("--feature", action="append", default=[], help="Enable optional dependency features.")
    resolve_parser.add_argument("--repo-root", help="Explicit harness-ai-kit repository root.")
    resolve_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    resolve_parser.add_argument("--offline", action="store_true", help="Resolve using local cache only.")
    resolve_parser.add_argument("--from", dest="source_selector", choices=["auto", "workspace-repo", "internal-registry", "public-registry", "git-repo", "repo", "registry"], default="auto", help="Prefer one source family when resolving.")

    lock_parser = subparsers.add_parser("lock", help="Resolve a skill graph and write harness-ai-kit.lock.")
    lock_parser.add_argument("asset_kind", nargs="?", choices=["skill", "loop"], help="Asset kind to lock.")
    lock_parser.add_argument("asset_id", nargs="?", help="Root asset id to lock.")
    lock_parser.add_argument("--feature", action="append", default=[], help="Enable optional dependency features.")
    lock_parser.add_argument("--runtime", choices=runtime_choices, default=None, help="Override the runtime recorded in the lockfile.")
    lock_parser.add_argument("--scope", choices=["project", "global"], default=None, help="Override the install scope recorded in the lockfile.")
    lock_parser.add_argument("--repo-root", help="Explicit harness-ai-kit repository root.")
    lock_parser.add_argument("--offline", action="store_true", help="Resolve using local cache only.")
    lock_parser.add_argument("--from", dest="source_selector", choices=["auto", "workspace-repo", "internal-registry", "public-registry", "git-repo", "repo", "registry"], default="auto", help="Prefer one source family when resolving.")

    graph_parser = subparsers.add_parser("graph", help="Render the resolved dependency tree for one skill.")
    graph_parser.add_argument("asset_kind", choices=["skill", "loop"], help="Asset kind to graph.")
    graph_parser.add_argument("asset_id", help="Root asset id to graph.")
    graph_parser.add_argument("--feature", action="append", default=[], help="Enable optional dependency features.")
    graph_parser.add_argument("--repo-root", help="Explicit harness-ai-kit repository root.")
    graph_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    graph_parser.add_argument("--offline", action="store_true", help="Resolve using local cache only.")
    graph_parser.add_argument("--from", dest="source_selector", choices=["auto", "workspace-repo", "internal-registry", "public-registry", "git-repo", "repo", "registry"], default="auto", help="Prefer one source family when resolving.")

    why_parser = subparsers.add_parser("why", help="Explain why a dependency appears in the resolved graph.")
    why_parser.add_argument("asset_kind", choices=["skill", "loop"], help="Asset kind to inspect.")
    why_parser.add_argument("asset_id", help="Root asset id to inspect.")
    why_parser.add_argument("dependency_id", help="Dependency id to explain.")
    why_parser.add_argument("--feature", action="append", default=[], help="Enable optional dependency features.")
    why_parser.add_argument("--repo-root", help="Explicit harness-ai-kit repository root.")
    why_parser.add_argument("--offline", action="store_true", help="Resolve using local cache only.")
    why_parser.add_argument("--from", dest="source_selector", choices=["auto", "workspace-repo", "internal-registry", "public-registry", "git-repo", "repo", "registry"], default="auto", help="Prefer one source family when resolving.")

    show_parser = subparsers.add_parser("show", help="Show metadata for one team asset.")
    show_parser.add_argument("asset_kind", choices=["skill", "plugin", "hook", "subagent", "mcp", "loop"], help="Asset kind to inspect.")
    show_parser.add_argument("asset_id", help="Asset id to inspect.")
    show_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    show_parser.add_argument("--repo-root", help="Explicit harness-ai-kit repository root.")
    show_parser.add_argument("--source", choices=["auto", "repo", "registry"], default="auto", help="Choose where to read the asset from.")

    cat_parser = subparsers.add_parser("cat", help="Print the main document for one team asset.")
    cat_parser.add_argument("asset_kind", choices=["skill", "plugin", "hook", "subagent", "mcp", "loop"], help="Asset kind to inspect.")
    cat_parser.add_argument("asset_id", help="Asset id to print.")
    cat_parser.add_argument("--changelog", action="store_true", help="Print CHANGELOG.md instead of the main skill entry.")
    cat_parser.add_argument("--usage", action="store_true", help="Print USAGE.md.")
    cat_parser.add_argument("--example", action="store_true", help="Print EXAMPLE.md.")
    cat_parser.add_argument("--repo-root", help="Explicit harness-ai-kit repository root.")
    cat_parser.add_argument("--source", choices=["auto", "repo", "registry"], default="auto", help="Choose where to read the asset from.")
    cat_parser.add_argument("--offline", action="store_true", help="Use local cache only for registry-backed skills.")

    cache_parser = subparsers.add_parser("cache", help="Inspect or clean the local harness-ai-kit package cache.")
    cache_subparsers = cache_parser.add_subparsers(dest="cache_command", required=True)
    cache_subparsers.add_parser("list", help="List cached registry artifacts and manifests.")
    cache_subparsers.add_parser("clean", help="Remove cached registry artifacts and manifests.")


def add_project_runtime_parsers(subparsers: Any, *, runtime_choices: Sequence[str], all_asset_types: Sequence[str]) -> None:
    init_project_parser = subparsers.add_parser("init-project", help="Create harness-ai-kit.yml for the current project.")
    init_project_parser.add_argument("--runtime", choices=runtime_choices, default="codex", help="Runtime to write into harness-ai-kit.yml.")
    init_project_parser.add_argument("--scope", choices=["project", "global"], default="project", help="Scope to write into harness-ai-kit.yml.")
    init_project_parser.add_argument("--root", action="append", default=[], help="Root skill id, optionally as namespace/name.")
    init_project_parser.add_argument("--feature", action="append", default=[], help="Feature name to enable by default.")
    init_project_parser.add_argument("--force", action="store_true", help="Overwrite an existing harness-ai-kit.yml.")

    manifest_parser = subparsers.add_parser("manifest", help="Inspect or migrate the project declaration file.")
    manifest_subparsers = manifest_parser.add_subparsers(dest="manifest_command", required=True)
    manifest_migrate_parser = manifest_subparsers.add_parser("migrate", help="Rewrite harness-ai-kit.yml to the v2 unified asset format.")
    manifest_migrate_parser.add_argument("--dry-run", action="store_true", help="Print the migrated manifest without writing it.")

    add_parser = subparsers.add_parser("add", help="Add one asset to harness-ai-kit.yml and sync the project by default.")
    add_parser.add_argument("asset_kind", choices=list(all_asset_types), help="Asset kind to add.")
    add_parser.add_argument("asset_id", help="Asset id to add.")
    add_parser.add_argument("--version", help="Pinned version for CLI or MCP assets, such as ==0.1.0.")
    add_parser.add_argument("--source-ref", help="Git source for external skills, such as a GitHub URL or OWNER/REPO.")
    add_parser.add_argument("--ref", help="Git branch, tag, or commit for --source-ref.")
    add_parser.add_argument("--subpath", help="Skill directory inside the Git source.")
    add_parser.add_argument("--id", dest="override_id", help="Skill id to select when asset_id is a Git source URL.")
    add_parser.add_argument("--runtime", choices=runtime_choices, default=None, help="Runtime to use when creating a new manifest or syncing.")
    add_parser.add_argument("--scope", choices=["project", "global"], default=None, help="Install scope to use when creating a new manifest or syncing.")
    add_parser.add_argument("--target-dir", help="Override the target runtime directory during sync.")
    add_parser.add_argument("--repo-root", help="Explicit harness-ai-kit repository root.")
    add_parser.add_argument("--sync-repo", action="store_true", help="Sync the repo before resolving assets.")
    add_parser.add_argument("--offline", action="store_true", help="Resolve using local cache only for registry-backed skills.")
    add_parser.add_argument("--no-install", action="store_true", help="Only update harness-ai-kit.yml without syncing runtime state.")
    add_parser.add_argument("--no-input", action="store_true", help="Do not prompt when a Git source contains multiple skills.")
    add_parser.add_argument("--extends", action="append", default=None, help="Base skill to extend (format: namespace/id). Repeatable for multi-inheritance.")
    add_parser.add_argument("--extends-version", default=None, help="Base skill version (pinned ==X.Y.Z format). Required when --extends is specified.")
    add_parser.add_argument("--extends-strategy", choices=["prepend", "append", "replace"], default="prepend", help="Merge strategy for SKILL.md content (default: prepend).")

    remove_parser = subparsers.add_parser("remove", help="Remove one asset from harness-ai-kit.yml and reconcile runtime state.")
    remove_parser.add_argument("asset_kind", choices=list(all_asset_types), help="Asset kind to remove.")
    remove_parser.add_argument("asset_id", help="Asset id to remove.")
    remove_parser.add_argument("--runtime", choices=runtime_choices, default=None, help="Override the runtime used during sync.")
    remove_parser.add_argument("--scope", choices=["project", "global"], default=None, help="Override the install scope used during sync.")
    remove_parser.add_argument("--target-dir", help="Override the target runtime directory during sync.")
    remove_parser.add_argument("--repo-root", help="Explicit harness-ai-kit repository root.")
    remove_parser.add_argument("--sync-repo", action="store_true", help="Sync the repo before resolving assets.")
    remove_parser.add_argument("--offline", action="store_true", help="Resolve using local cache only for registry-backed skills.")
    remove_parser.add_argument("--no-install", action="store_true", help="Only update harness-ai-kit.yml without syncing runtime state.")

    sync_parser = subparsers.add_parser("sync", help="Reconcile the current project to harness-ai-kit.yml.")
    sync_parser.add_argument("--target-dir", help="Override the local runtime target directory.")
    sync_parser.add_argument("--runtime", choices=runtime_choices, default=None, help="Override the runtime used during sync.")
    sync_parser.add_argument("--scope", choices=["project", "global"], default=None, help="Override the install scope used during sync.")
    sync_parser.add_argument("--repo-root", help="Explicit harness-ai-kit repository root.")
    sync_parser.add_argument("--sync-repo", action="store_true", help="Sync the repo before applying the project state.")
    sync_parser.add_argument("--offline", action="store_true", help="Resolve using local cache only for registry-backed skills.")
    sync_parser.add_argument("--install-external", action="store_true", help="Install declared external system and Python dependencies after resolving the project graph.")
    sync_parser.add_argument("--no-install-external", action="store_true", help="Skip external dependency installation even if defaults.install_external_immediately is true.")
    sync_parser.add_argument("--dry-run", action="store_true", help="Preview the sync action.")
    sync_parser.add_argument("--all-runtimes", action="store_true", help="After syncing to canonical .agents, fan-out to all discovered runtime directories.")

    prune_parser = subparsers.add_parser("prune", help="Remove orphaned project skill installs that are no longer declared.")
    prune_parser.add_argument("--target-dir", help="Override the local runtime target directory.")
    prune_parser.add_argument("--runtime", choices=runtime_choices, default=None, help="Override the runtime used during prune.")
    prune_parser.add_argument("--scope", choices=["project", "global"], default=None, help="Override the install scope used during prune.")
    prune_parser.add_argument("--repo-root", help="Explicit harness-ai-kit repository root.")
    prune_parser.add_argument("--offline", action="store_true", help="Resolve using local cache only for registry-backed skills.")

    outdated_parser = subparsers.add_parser("outdated", help="Show upgrade status for assets declared in harness-ai-kit.yml.")
    outdated_parser.add_argument("--repo-root", help="Explicit harness-ai-kit repository root.")
    outdated_parser.add_argument("--offline", action="store_true", help="Resolve using local cache only for registry-backed skills.")

    diff_parser = subparsers.add_parser("diff", help="Compare manifest, lock, and runtime skill state for the current project.")
    diff_parser.add_argument("--target-dir", help="Override the local runtime target directory.")
    diff_parser.add_argument("--runtime", choices=runtime_choices, default=None, help="Override the runtime used during diff.")
    diff_parser.add_argument("--scope", choices=["project", "global"], default=None, help="Override the install scope used during diff.")
    diff_parser.add_argument("--repo-root", help="Explicit harness-ai-kit repository root.")
    diff_parser.add_argument("--offline", action="store_true", help="Resolve using local cache only for registry-backed skills.")

    uninstall_parser = subparsers.add_parser("uninstall", help="Remove an installed skill or CLI without touching harness-ai-kit.yml.")
    uninstall_parser.add_argument("asset_kind", choices=list(all_asset_types), help="Asset kind to uninstall.")
    uninstall_parser.add_argument("asset_id", help="Asset id to uninstall.")
    uninstall_parser.add_argument("--target-dir", help="Override the local runtime target directory for skills.")
    uninstall_parser.add_argument("--runtime", choices=runtime_choices, default="codex", help="Runtime selector for skill uninstall.")
    uninstall_parser.add_argument("--scope", choices=["project", "global"], default="project", help="Install scope selector for skill uninstall.")
    uninstall_parser.add_argument("--repo-root", help="Explicit harness-ai-kit repository root.")
    uninstall_parser.add_argument("--dry-run", action="store_true", help="Preview the uninstall action.")

    deprecate_parser = subparsers.add_parser("deprecate", help="Mark one local skill or CLI as deprecated.")
    deprecate_parser.add_argument("asset_kind", choices=["skill", "cli", "plugin", "hook", "subagent", "mcp", "loop"], help="Asset kind to deprecate.")
    deprecate_parser.add_argument("asset_id", help="Asset id to deprecate.")
    deprecate_parser.add_argument("--replacement", required=True, help="Replacement asset id to point users to.")
    deprecate_parser.add_argument("--repo-root", help="Explicit harness-ai-kit repository root.")

    retire_parser = subparsers.add_parser("retire", help="Mark one local skill or CLI as retired.")
    retire_parser.add_argument("asset_kind", choices=["skill", "cli", "plugin", "hook", "subagent", "mcp", "loop"], help="Asset kind to retire.")
    retire_parser.add_argument("asset_id", help="Asset id to retire.")
    retire_parser.add_argument("--replacement", help="Optional replacement asset id to point users to.")
    retire_parser.add_argument("--repo-root", help="Explicit harness-ai-kit repository root.")

    for command_name in ("install", "update"):
        command_parser = subparsers.add_parser(command_name, help=f"{command_name.title()} one or more skills into the local execution directory.")
        command_parser.add_argument("skill_ids", nargs="*", help="Legacy skill IDs or explicit selectors like `skill foo` or `cli harness-ai-kit`.")
        command_parser.add_argument("--all", action="store_true", help="Sync all installable skills.")
        command_parser.add_argument("--target-dir", help="Override the local .agents/skills target directory. Relative paths resolve from the current working directory.")
        command_parser.add_argument("--runtime", choices=runtime_choices, default=None, help="Target runtime for skill installation. Defaults to harness-ai-kit.yml or codex.")
        command_parser.add_argument("--scope", choices=["project", "global"], default=None, help="Install scope for skills. Defaults to harness-ai-kit.yml or project.")
        command_parser.add_argument("--with-recommended", action="store_true", help="Also install recommended companion skills declared by the selected skills.")
        command_parser.add_argument("--feature", action="append", default=[], help="Enable optional dependency features.")
        command_parser.add_argument("--offline", action="store_true", help="Use local cache only for registry-backed skills.")
        command_parser.add_argument("--from", dest="source_selector", choices=["auto", "workspace-repo", "internal-registry", "public-registry", "git-repo", "repo", "registry"], default="auto", help="Prefer one source family when resolving and installing.")
        command_parser.add_argument("--refresh-lock", action="store_true", help="Ignore the existing harness-ai-kit.lock and resolve again.")
        command_parser.add_argument("--install-external", action="store_true", help="Install declared external system and Python dependencies after resolving the asset graph.")
        command_parser.add_argument("--no-install-external", action="store_true", help="Skip external dependency installation even if defaults.install_external_immediately is true.")
        command_parser.add_argument("--repo-root", help="Explicit harness-ai-kit repository root.")
        command_parser.add_argument("--sync-repo", action="store_true", help="Sync the repo before copying skills.")
        command_parser.add_argument("--dry-run", action="store_true", help="Preview the install or update action.")

    upgrade_parser = subparsers.add_parser("upgrade", help="Upgrade synced skills, installed CLIs, or both.")
    upgrade_parser.add_argument("asset_ids", nargs="*", help="Explicit selectors like `skill writer` or `cli harness-ai-kit`. With `--all`, upgrades both skills and CLIs.")
    upgrade_parser.add_argument("--all", action="store_true", help="Upgrade all installable skills and CLIs.")
    upgrade_parser.add_argument("--target-dir", help="Override the local .agents/skills target directory used for skill upgrades.")
    upgrade_parser.add_argument("--runtime", choices=runtime_choices, default=None, help="Target runtime for skill upgrades. Defaults to harness-ai-kit.yml or codex.")
    upgrade_parser.add_argument("--scope", choices=["project", "global"], default=None, help="Install scope for skill upgrades. Defaults to harness-ai-kit.yml or project.")
    upgrade_parser.add_argument("--feature", action="append", default=[], help="Override enabled project features during upgrade.")
    upgrade_parser.add_argument("--repo-root", help="Explicit harness-ai-kit repository root.")
    upgrade_parser.add_argument("--sync-repo", action="store_true", help="Sync the repo before upgrading assets.")
    upgrade_parser.add_argument("--dry-run", action="store_true", help="Preview the upgrade actions.")


def add_loop_parsers(subparsers: Any) -> None:
    """Add loop execution parsers."""
    from harness_ai_kit.commands.loop_run import add_run_parser
    add_run_parser(subparsers)


def add_loop_extract_parsers(subparsers: Any) -> None:
    """Add loop extraction and promotion parsers."""
    extract_parser = subparsers.add_parser(
        "extract",
        help="Extract loop assets from a completed workflow session.",
    )
    extract_parser.add_argument("wfs_id", help="Workflow session ID (e.g., WFS-loop-runtime-engine).")
    extract_parser.add_argument("--dry-run", action="store_true", help="Only score the session without generating assets.")
    extract_parser.add_argument("--force", action="store_true", help="Generate assets even if score is below threshold.")
    extract_parser.add_argument("--loop-id", default=None, help="Override the generated loop ID.")
    extract_parser.add_argument("--output", "-o", default=None, help="Output directory (default: loops/{id}/draft/).")
    extract_parser.add_argument("--skill-dir", default=None, help="Explicit skill directory to read metadata from.")

    promote_parser = subparsers.add_parser(
        "promote",
        help="Promote a draft loop to official status.",
    )
    promote_parser.add_argument("loop_id", help="Loop ID to promote.")
    promote_parser.add_argument("--force", action="store_true", help="Promote even if validation fails.")


def add_authoring_publish_release_parsers(subparsers: Any, *, runtime_choices: Sequence[str]) -> None:
    create_parser = subparsers.add_parser("create", help="Scaffold a new skill or CLI inside the repository.")
    create_subparsers = create_parser.add_subparsers(dest="create_subject", required=True)
    create_skill_parser = create_subparsers.add_parser("skill", help="Create a new skill scaffold.")
    create_skill_parser.add_argument("asset_id", help="New skill ID.")
    create_skill_parser.add_argument("--repo-root", help="Explicit harness-ai-kit repository root.")
    for managed_type in ("plugin", "hook", "subagent", "mcp", "loop"):
        managed_parser = create_subparsers.add_parser(managed_type, help=f"Create a new {managed_type} scaffold.")
        managed_parser.add_argument("asset_id", help=f"New {managed_type} ID.")
        managed_parser.add_argument("--repo-root", help="Explicit harness-ai-kit repository root.")
    create_cli_parser = create_subparsers.add_parser("cli", help="Create a new CLI scaffold.")
    create_cli_parser.add_argument("asset_id", help="New CLI ID.")
    create_cli_parser.add_argument("--repo-root", help="Explicit harness-ai-kit repository root.")

    submit_parser = subparsers.add_parser("submit", help="Commit and push a member-facing skill or CLI update without exposing git steps.")
    submit_subparsers = submit_parser.add_subparsers(dest="submit_subject", required=True)
    submit_skill_parser = submit_subparsers.add_parser("skill", help="Submit one skill update.")
    submit_skill_parser.add_argument("asset_id", help="Skill ID to submit.")
    submit_skill_parser.add_argument("--message", help="Override the generated commit message.")
    submit_skill_parser.add_argument("--no-push", action="store_true", help="Commit locally without pushing.")
    submit_skill_parser.add_argument("--dry-run", action="store_true", help="Preview which files would be submitted.")
    submit_skill_parser.add_argument("--repo-root", help="Explicit harness-ai-kit repository root.")
    for managed_type in ("plugin", "hook", "subagent", "mcp", "loop"):
        managed_submit_parser = submit_subparsers.add_parser(managed_type, help=f"Submit one {managed_type} update.")
        managed_submit_parser.add_argument("asset_id", help=f"{managed_type.title()} ID to submit.")
        managed_submit_parser.add_argument("--message", help="Override the generated commit message.")
        managed_submit_parser.add_argument("--no-push", action="store_true", help="Commit locally without pushing.")
        managed_submit_parser.add_argument("--dry-run", action="store_true", help="Preview which files would be submitted.")
        managed_submit_parser.add_argument("--repo-root", help="Explicit harness-ai-kit repository root.")
    submit_cli_parser = submit_subparsers.add_parser("cli", help="Submit one CLI update.")
    submit_cli_parser.add_argument("asset_id", help="CLI ID to submit.")
    submit_cli_parser.add_argument("--message", help="Override the generated commit message.")
    submit_cli_parser.add_argument("--no-push", action="store_true", help="Commit locally without pushing.")
    submit_cli_parser.add_argument("--dry-run", action="store_true", help="Preview which files would be submitted.")
    submit_cli_parser.add_argument("--repo-root", help="Explicit harness-ai-kit repository root.")

    publish_skill_parser = subparsers.add_parser("publish-skill", help="Package one skill and publish it to the configured raw skill registry.")
    publish_skill_parser.add_argument("skill_id", help="Skill ID to package and publish.")
    publish_skill_parser.add_argument("--repo-root", help="Explicit harness-ai-kit repository root.")
    publish_skill_parser.add_argument("--dry-run", action="store_true", help="Preview the skill publish steps.")
    publish_skill_parser.add_argument(
        "--from", dest="source_scope",
        choices=["repo", "project", "global"], default="repo",
        help="Where to find the skill: repo (default), project (.agents/skills), or global (~/.agents/skills)"
    )
    publish_skill_parser.add_argument("--git", action="store_true", help="Git add + commit after publish")
    publish_skill_parser.add_argument("--no-git", action="store_true", help="Override config to skip git")
    publish_skill_parser.add_argument("--push", action="store_true", help="Git pull --rebase + push (implies --git)")
    publish_skill_parser.add_argument("--no-sync", action="store_true", help="Skip auto sync after publish")
    publish_skill_parser.add_argument("--no-sync-repo", action="store_true", help="Skip SSOT repo pull before publish")
    publish_skill_parser.add_argument("-m", "--message", help="Custom git commit message")

    publish_cli_parser = subparsers.add_parser("publish-cli", help="Build one CLI package, upload it to the configured package registry, and refresh the raw CLI registry.")
    publish_cli_parser.add_argument("cli_id", help="CLI ID to package and publish.")
    publish_cli_parser.add_argument("--repo-root", help="Explicit harness-ai-kit repository root.")
    publish_cli_parser.add_argument("--dry-run", action="store_true", help="Preview the CLI publish steps.")

    publish_parser = subparsers.add_parser("publish", help="Stage, commit, and optionally push skill or repository changes without manual git ceremony.")
    publish_parser.add_argument("paths", nargs="*", help="Repo-relative file or directory paths to stage, such as catalog.md or cli/harness_ai_kit/main.py.")
    publish_parser.add_argument("--skill-id", action="append", default=[], help="Convenience selector for skills/<skill-id>. Repeat for multiple skills.")
    publish_parser.add_argument("--all", action="store_true", help="Stage all repo changes before committing.")
    publish_parser.add_argument("--message", required=True, help="Git commit message to use for the publish operation.")
    publish_parser.add_argument("--push", action="store_true", help="Push the resulting commit to origin.")
    publish_parser.add_argument("--dry-run", action="store_true", help="Preview which paths would be published without staging, committing, or pushing.")
    publish_parser.add_argument("--repo-root", help="Explicit harness-ai-kit repository root.")

    release_parser = subparsers.add_parser("release", help="Run version bump, package build, metadata check, and registry publish workflows.")
    release_subparsers = release_parser.add_subparsers(dest="release_command", required=True)
    release_skill_build_parser = release_subparsers.add_parser("skill-build", help="Build a zip artifact for one skill.")
    release_skill_build_parser.add_argument("skill_id", help="Skill ID to package.")
    release_skill_build_parser.add_argument("--repo-root", help="Explicit harness-ai-kit repository root.")
    release_skill_publish_parser = release_subparsers.add_parser("skill-publish", help="Upload one skill zip and refresh the raw skill registry index.")
    release_skill_publish_parser.add_argument("skill_id", help="Skill ID to publish.")
    release_skill_publish_parser.add_argument("--repo-root", help="Explicit harness-ai-kit repository root.")
    release_skill_publish_parser.add_argument("--dry-run", action="store_true", help="Preview the skill publish steps.")
    release_version_parser = release_subparsers.add_parser("version", help="Show the current project version.")
    release_version_parser.add_argument("--repo-root", help="Explicit harness-ai-kit repository root.")
    release_bump_parser = release_subparsers.add_parser("bump", help="Bump the project version.")
    release_bump_parser.add_argument("part", choices=["patch", "minor", "major"], nargs="?", default="patch", help="Version part to bump. Defaults to patch.")
    release_bump_parser.add_argument("--set-version", help="Set an explicit version instead of bumping.")
    release_bump_parser.add_argument("--repo-root", help="Explicit harness-ai-kit repository root.")
    release_bump_parser.add_argument("--dry-run", action="store_true", help="Preview the version change without writing.")
    release_build_parser = release_subparsers.add_parser("build", help="Clean and build wheel plus sdist.")
    release_build_parser.add_argument("--repo-root", help="Explicit harness-ai-kit repository root.")
    release_build_parser.add_argument("--skip-clean", action="store_true", help="Keep existing build artifacts.")
    release_check_parser = release_subparsers.add_parser("check", help="Run twine check on built artifacts.")
    release_check_parser.add_argument("--repo-root", help="Explicit harness-ai-kit repository root.")
    release_publish_parser = release_subparsers.add_parser("publish", help="Upload built artifacts to the configured private registry and optionally tag the release.")
    release_publish_parser.add_argument("--repo-root", help="Explicit harness-ai-kit repository root.")
    release_publish_parser.add_argument("--repository-url", help="Override the registry upload URL for this publish.")
    release_publish_parser.add_argument("--trusted-host", help="Override the trusted host for this publish.")
    release_publish_parser.add_argument("--skip-build", action="store_true", help="Skip rebuilding artifacts before upload.")
    release_publish_parser.add_argument("--skip-check", action="store_true", help="Skip twine check before upload.")
    release_publish_parser.add_argument("--tag", action="store_true", help="Create a git tag after successful upload.")
    release_publish_parser.add_argument("--push-tag", action="store_true", help="Push the created git tag to origin.")
    release_publish_parser.add_argument("--dry-run", action="store_true", help="Preview the upload and tagging steps.")
    publish_loop_parser = subparsers.add_parser("publish-loop", help="Package one loop and publish it to the configured raw asset registry.")
    publish_loop_parser.add_argument("loop_id", help="Loop ID to package and publish.")
    publish_loop_parser.add_argument("--repo-root", help="Explicit harness-ai-kit repository root.")
    publish_loop_parser.add_argument("--dry-run", action="store_true", help="Preview the loop publish steps.")

    release_loop_publish_parser = release_subparsers.add_parser("loop-publish", help="Upload one loop zip and refresh the raw asset registry index.")
    release_loop_publish_parser.add_argument("loop_id", help="Loop ID to publish.")
    release_loop_publish_parser.add_argument("--repo-root", help="Explicit harness-ai-kit repository root.")
    release_loop_publish_parser.add_argument("--dry-run", action="store_true", help="Preview the loop publish steps.")


def add_asset_config_parser(subparsers: Any) -> None:
    """Add the ``asset-config`` subcommand for inspecting asset configuration."""
    p = subparsers.add_parser(
        "asset-config",
        help="Show effective merged configuration for an asset (L1→L2→L3).",
    )
    p.add_argument("asset_id", help="Asset ID (e.g. infra-jenkins-pipeline-ops).")
    p.add_argument("--keys", action="store_true", help="Show declared config keys with metadata instead of effective values.")
    p.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    p.add_argument("--repo-root", help="Explicit harness-ai-kit repository root.")
