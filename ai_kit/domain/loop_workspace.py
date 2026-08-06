"""Workspace manager: provides isolated workspaces for loop iterations.

Supports git_worktree, docker, and temp_dir isolation strategies.
Each workspace is managed through a WorkspaceHandle that provides
commit, rollback, and cleanup operations.
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

logger = logging.getLogger(__name__)


@dataclass
class WorkspaceHandle:
    """Handle to an isolated workspace.

    Provides commit, rollback, and cleanup operations.
    """

    workspace_path: Path
    isolation_type: str
    loop_id: str
    _original_branch: str | None = None
    _worktree_path: Path | None = None
    _temp_dir: Path | None = None
    _is_cleaned: bool = False

    def commit(self, message: str = "Auto-commit from loop iteration") -> None:
        """Commit changes in the workspace (for git-based isolation)."""
        if self.isolation_type == "git_worktree" and self._worktree_path:
            try:
                self._run_git(["add", "-A"], cwd=self._worktree_path)
                self._run_git(["commit", "-m", message], cwd=self._worktree_path)
                logger.info("Committed changes in worktree %s", self._worktree_path)
            except subprocess.CalledProcessError as exc:
                logger.warning("Git commit failed in worktree: %s", exc)

    def rollback(self) -> None:
        """Discard changes in the workspace."""
        if self.isolation_type == "git_worktree" and self._worktree_path:
            try:
                self._run_git(["checkout", "--", "."], cwd=self._worktree_path)
                logger.info("Rolled back changes in worktree %s", self._worktree_path)
            except subprocess.CalledProcessError as exc:
                logger.warning("Git rollback failed in worktree: %s", exc)

    def cleanup(self) -> None:
        """Clean up the workspace based on isolation type."""
        if self._is_cleaned:
            return

        if self.isolation_type == "git_worktree" and self._worktree_path:
            self._cleanup_worktree()
        elif self.isolation_type == "temp_dir" and self._temp_dir:
            self._cleanup_temp_dir()

        self._is_cleaned = True

    def _cleanup_worktree(self) -> None:
        """Remove the git worktree."""
        try:
            # First prune the worktree from git
            if self._worktree_path:
                # Remove the worktree reference
                cmd = ["worktree", "remove", "--force", str(self._worktree_path)]
                self._run_git(cmd, check=False)
            logger.info("Cleaned up worktree %s", self._worktree_path)
        except subprocess.CalledProcessError as exc:
            logger.warning("Worktree cleanup failed: %s", exc)
            # Fallback: manually remove directory
            if self._worktree_path and self._worktree_path.exists():
                try:
                    shutil.rmtree(self._worktree_path)
                except OSError:
                    pass

    def _cleanup_temp_dir(self) -> None:
        """Remove the temporary directory."""
        if self._temp_dir and self._temp_dir.exists():
            try:
                shutil.rmtree(self._temp_dir)
                logger.info("Cleaned up temp directory %s", self._temp_dir)
            except OSError as exc:
                logger.warning("Temp dir cleanup failed: %s", exc)

    @staticmethod
    def _run_git(args: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
        """Run a git command."""
        cmd = ["git"] + list(args)
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(cwd) if cwd else None,
            check=check,
        )


class WorkspaceManager:
    """Manages isolated workspaces for loop iterations.

    Supports three isolation strategies:
    - git_worktree: Creates a git worktree branch (recommended)
    - temp_dir: Creates a temporary directory (fallback)
    - docker: Placeholder for future Docker isolation
    """

    def __init__(
        self,
        *,
        isolation: str = "git_worktree",
        base_branch: str = "main",
        branch_prefix: str = "loop/",
        root_dir: Path | None = None,
    ) -> None:
        self.isolation = isolation
        self.base_branch = base_branch
        self.branch_prefix = branch_prefix
        self.root_dir = root_dir or Path.cwd()

    def isolate(self, loop_id: str) -> WorkspaceHandle:
        """Create an isolated workspace for the given loop_id.

        Returns a WorkspaceHandle that can be used to commit, rollback,
        or cleanup the workspace.
        """
        if self.isolation == "git_worktree":
            return self._isolate_git_worktree(loop_id)
        elif self.isolation == "temp_dir":
            return self._isolate_temp_dir(loop_id)
        else:
            # Default to temp_dir for unknown strategies
            logger.warning(
                "Unknown isolation type '%s', falling back to temp_dir",
                self.isolation,
            )
            return self._isolate_temp_dir(loop_id)

    def _isolate_git_worktree(self, loop_id: str) -> WorkspaceHandle:
        """Create a git worktree for isolation."""
        import time

        branch_name = f"{self.branch_prefix}{loop_id}-{int(time.time())}"
        worktree_path = self.root_dir / f".worktrees" / loop_name_safe(loop_id) / branch_name

        try:
            # Create the worktree branch
            worktree_path.parent.mkdir(parents=True, exist_ok=True)

            cmd = [
                "git", "worktree", "add",
                str(worktree_path),
                "-b", branch_name,
                self.base_branch,
            ]
            subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.root_dir),
                check=True,
            )

            logger.info("Created worktree %s from branch %s", worktree_path, branch_name)

            return WorkspaceHandle(
                workspace_path=worktree_path,
                isolation_type="git_worktree",
                loop_id=loop_id,
                _original_branch=self.base_branch,
                _worktree_path=worktree_path,
            )

        except subprocess.CalledProcessError as exc:
            logger.warning(
                "Git worktree creation failed: %s, falling back to temp_dir",
                exc,
            )
            return self._isolate_temp_dir(loop_id)
        except FileNotFoundError:
            # git not available
            logger.warning("git not found, falling back to temp_dir")
            return self._isolate_temp_dir(loop_id)

    def _isolate_temp_dir(self, loop_id: str) -> WorkspaceHandle:
        """Create a temporary directory for isolation."""
        temp_dir = Path(tempfile.mkdtemp(prefix=f"loop-{loop_name_safe(loop_id)}-"))
        logger.info("Created temp workspace %s", temp_dir)

        return WorkspaceHandle(
            workspace_path=temp_dir,
            isolation_type="temp_dir",
            loop_id=loop_id,
            _temp_dir=temp_dir,
        )


def loop_name_safe(name: str) -> str:
    """Convert a loop name to a filesystem-safe string."""
    import re
    return re.sub(r"[^a-zA-Z0-9_-]", "_", name)
