"""Additional git operations and utility helpers."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Sequence

from harness_ai_kit.infrastructure.config_io import repo_looks_valid


def run_git(repo_root: Path, args: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )




def clone_repo(repo_url: str, checkout_dir: Path, *, no_git_proxy: bool = False) -> None:
    """Clone a repository into checkout_dir.

    If ``no_git_proxy`` is True, temporarily unset HTTP(S) proxy env vars so
    Git connects directly without system proxy (useful when Gitea/Harbor behind
    corporate proxy returns "Empty reply from server").
    """
    import os

    checkout_dir.parent.mkdir(parents=True, exist_ok=True)

    # Optionally override proxy env vars for this run only
    if no_git_proxy:
        proxy_env = {
            k: None
            for k in ["http_proxy", "HTTPS_PROXY", "http_proxy", "https_proxy"]
        }
    else:
        proxy_env = {}

    # Run with modified env (original saved/restored automatically by dict)
    try:
        env = os.environ.copy()
        if proxy_env:
            for k, v in proxy_env.items():
                if v is None:
                    env.pop(k, None)  # remove only
                else:
                    env[k] = v
        result = subprocess.run(
            ["git", "clone", repo_url, str(checkout_dir)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
    except Exception as exc:
        raise RuntimeError(f"Failed to run git clone: {exc}") from exc
    if result.returncode == 0:
        return
    # Exit code != 0 → classify common causes and include stderr in message
    err = (result.stderr or "").strip()
    hint = []
    # Authentication / permission patterns (Gitea/Harbor/etc.)
    if any(p in err.lower() for p in ["permission denied", "public key", "bad credentials", "access denied", "unauthorized"]):
        hint.append("Authentication failure: ensure your Git credentials are configured.")
        hint.append("• Windows Git credential helper: run `git config --global credential.helper wincred`")
        hint.append("• Personal Access Token: set via HTTPS prompt or configure GITEA_TOKEN/GITHUB_TOKEN")
        hint.append("• If using SSH, verify keys: `ssh -T <host>` and add `~/.ssh/id_rsa.pub` to Gitea account")
    # Network / connectivity patterns
    elif any(p in err.lower() for p in ["connection refused", "network is unreachable", "timed out", "no route to host", "tls handshake"]):
        hint.append("Network/hostname resolution issue: check proxy settings or firewall rules.")
        hint.append("If on a corporate intranet, you may need HTTP proxy (set http_proxy/https_proxy env vars).")
        hint.append("Verify you can reach the host: `nslookup <host>` or `ping <host>`")
    # Repository not found patterns
    elif any(p in err.lower() for p in ["not found", "repo not found", "repository does not exist", "404"]):
        hint.append("Repository not found: confirm the URL path is correct and you have read access.")
        hint.append("Note: private repositories require authentication; see above for credential setup.")
    else:
        hint.append("Git clone failed with output below. Run with GIT_TRACE=1 for verbose logs.")
    message_lines = [
        f"Git clone failed ({result.returncode}) for repository: {repo_url}",
        ""
    ]
    if err:
        message_lines.extend(["stderr output:", err])
    message_lines.extend(["", "Suggestions:"] + hint)
    raise RuntimeError("\n".join(message_lines))




def sync_repo(repo_root: Path) -> str:
    run_git(repo_root, ["fetch", "--all", "--prune"])
    result = run_git(repo_root, ["pull", "--ff-only"])
    return result.stdout.strip() or "Repository is up to date."




def ensure_checkout(repo_url: str, checkout_dir: Path, sync_after_clone: bool, *, no_git_proxy: bool = False) -> str:
    if repo_looks_valid(checkout_dir):
        if sync_after_clone:
            return sync_repo(checkout_dir)
        return f"Repository already available at {checkout_dir}"

    if checkout_dir.exists() and any(checkout_dir.iterdir()):
        raise FileExistsError(
            f"Checkout directory exists and is not an empty harness-ai-kit clone: {checkout_dir}"
        )

    clone_repo(repo_url, checkout_dir, no_git_proxy=no_git_proxy)
    if sync_after_clone:
        return sync_repo(checkout_dir)
    return f"Cloned repository to {checkout_dir}"




def _sync_failure_hint(stderr: str) -> str:
    """Map a git failure to the concrete operator action that resolves it."""
    text = (stderr or "").lower()
    if "not possible to fast-forward" in text or "diverging" in text:
        return (
            "local checkout has diverged from origin; push/rebase your local commits "
            "(`git pull --rebase`) or reset to origin (`git fetch origin && git reset --hard origin/master`)"
        )
    if "would be overwritten" in text or "local changes" in text:
        return "checkout has uncommitted changes; commit or `git stash` them, then retry"
    if "not a git repository" in text or "no such file or directory" in text:
        return "checkout_dir is missing or not a git repo; fix `config set checkout_dir=...` (consumers need no checkout)"
    if "could not read username" in text or "authentication failed" in text or "could not resolve host" in text:
        return "git auth/network failed; check credentials, proxy, and Gitea reachability"
    if "no upstream" in text or "not currently on a branch" in text:
        return "checkout has no tracking branch (detached HEAD?); `git checkout master` and set upstream"
    return "inspect the checkout manually with `git -C <checkout_dir> pull --ff-only`"


def maybe_sync_repo(args: argparse.Namespace, repo_root: Path, *, force: bool = False) -> None:
    """Best-effort repo sync before asset resolution.

    The repo checkout is only one of several asset sources (registry is
    authoritative for consumers), so a broken/diverged/dirty checkout must not
    abort the caller. Failures degrade to a warning plus a concrete fix hint and
    resolution continues from the remaining sources.
    """
    if not (force or getattr(args, "sync_repo", False)):
        return
    if not repo_looks_valid(repo_root):
        print(f"Warning: skipped repo sync; not a usable git checkout: {repo_root}")
        return
    try:
        message = sync_repo(repo_root)
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip().splitlines()
        first = detail[-1] if detail else f"git exited with status {exc.returncode}"
        print(f"Warning: repo sync failed ({repo_root}): {first}")
        print(f"         Hint: {_sync_failure_hint(exc.stderr or exc.stdout or '')}")
        print("         Continuing with registry/lockfile sources; repo-sourced assets may be stale.")
        return
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"Warning: repo sync could not run ({repo_root}): {exc}")
        print("         Continuing with registry/lockfile sources; repo-sourced assets may be stale.")
        return
    if message:
        print(message)




def git_available() -> bool:
    return command_available(["git", "--version"])




def command_available(command: Sequence[str]) -> bool:
    result = subprocess.run(
        list(command),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.returncode == 0




def python_module_available(module_name: str) -> bool:
    return command_available([sys.executable, "-m", module_name, "--help"])




def normalize_module_name(value: str) -> str:
    return value.replace("-", "_")




def parse_asset_selector(tokens: list[str], default_kind: str) -> tuple[str, list[str]]:
    if not tokens:
        return default_kind, []

    selector = tokens[0].lower()
    if selector in {"skill", "skills"}:
        return "skill", tokens[1:]
    if selector in {"cli", "clis"}:
        return "cli", tokens[1:]
    if selector in {"plugin", "plugins"}:
        return "plugin", tokens[1:]
    if selector in {"loop", "loops"}:
        return "loop", tokens[1:]
    if selector in {"asset", "assets"}:
        return "asset", tokens[1:]
    return default_kind, tokens
