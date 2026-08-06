"""Loop-level exclusive lock manager (F-007 concurrency safety).

Prevents two instances from running the same loop profile simultaneously.

Lock file path: .lock/loops/{loop_id}.json
Lock format: LockNodeData JSON (type, id, acquired_at, pid, holder)

Atomic acquisition via filelock with O_EXCL semantics. Stale locks from
crashed processes are automatically cleaned via PID liveness check.
"""
from __future__ import annotations

import atexit
import json
import os
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from filelock import FileLock, Timeout


@dataclass
class LockNodeData:
    """Runtime lock node stored in .lock/loops/{loop_id}.json."""

    type: str  # always "loop"
    id: str  # loop_id
    acquired_at: str  # ISO-8601 timestamp
    pid: int  # holding process PID
    holder: str  # human-readable holder identifier

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LockNodeData:
        return cls(
            type=data["type"],
            id=data["id"],
            acquired_at=data["acquired_at"],
            pid=data["pid"],
            holder=data["holder"],
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


class LockAcquisitionError(Exception):
    """Raised when a lock cannot be acquired (held by another live process)."""


class LoopLockManager:
    """Exclusive lock manager for loop profiles.

    Usage::

        mgr = LoopLockManager(root_dir=Path("."), loop_id="ci-auto-fix-loop")
        node = mgr.acquire(holder="loopctl run")
        try:
            # ... run loop ...
        finally:
            mgr.release()

    Or as context manager::

        with LoopLockManager(root_dir=Path("."), loop_id="ci-auto-fix-loop") as mgr:
            mgr.acquire(holder="loopctl run")
            # ... run loop ...
    """

    def __init__(
        self,
        *,
        root_dir: Path,
        loop_id: str,
        timeout: float = 0,
    ) -> None:
        self.root_dir = root_dir.resolve()
        self.loop_id = loop_id
        self.timeout = timeout
        self._lock_dir = self.root_dir / ".lock" / "loops"
        self._lock_file = self._lock_dir / f"{loop_id}.json"
        self._mutex = FileLock(str(self._lock_file) + ".mutex", timeout=timeout)
        self._acquired_node: LockNodeData | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def acquire(self, *, holder: str) -> LockNodeData:
        """Atomically acquire the exclusive lock for this loop.

        Returns the LockNodeData on success.
        Raises LockAcquisitionError if another live process holds the lock.
        """
        self._lock_dir.mkdir(parents=True, exist_ok=True)

        try:
            self._mutex.acquire()
        except Timeout:
            raise LockAcquisitionError(
                f"Lock timed out after {self.timeout}s for loop '{self.loop_id}'"
            )

        try:
            return self._try_acquire(holder)
        finally:
            self._mutex.release()

    def release(self) -> None:
        """Release the lock held by this manager."""
        self._lock_dir.mkdir(parents=True, exist_ok=True)

        try:
            self._mutex.acquire()
        except Timeout:
            return  # Cannot acquire mutex to release; best-effort

        try:
            self._do_release()
        finally:
            self._mutex.release()

    def is_locked(self) -> bool:
        """Check whether the lock file exists (without acquiring)."""
        if not self._lock_file.is_file():
            return False
        try:
            self._mutex.acquire(timeout=0)
        except Timeout:
            return True
        try:
            return self._lock_file.is_file()
        finally:
            self._mutex.release()

    @property
    def lock_file_path(self) -> Path:
        return self._lock_file

    @property
    def acquired(self) -> bool:
        return self._acquired_node is not None

    # ------------------------------------------------------------------
    # Internal: acquire logic
    # ------------------------------------------------------------------

    def _try_acquire(self, holder: str) -> LockNodeData:
        """Attempt to acquire the lock.

        Called under self._mutex (held by acquire()), so the entire
        check-and-write sequence is atomic across processes.
        """
        now_iso = _utc_iso_now()
        current_pid = os.getpid()
        candidate = LockNodeData(
            type="loop",
            id=self.loop_id,
            acquired_at=now_iso,
            pid=current_pid,
            holder=holder,
        )

        # Read existing lock atomically (under mutex held by caller)
        existing = self._read_lock_file()
        if existing is not None:
            return self._handle_existing_lock(existing, candidate)

        self._write_lock_file(candidate)
        self._acquired_node = candidate
        atexit.register(self._release_on_exit)
        return candidate

    def _handle_existing_lock(
        self, existing: LockNodeData, candidate: LockNodeData
    ) -> LockNodeData:
        """Decide what to do when a lock file already exists."""

        # Same PID -> same process re-acquiring (idempotent)
        if existing.pid == os.getpid():
            self._acquired_node = existing
            return existing

        # PID not alive -> stale lock, clean up and retry
        if not _is_pid_alive(existing.pid):
            self._remove_stale_lock()
            self._write_lock_file(candidate)
            self._acquired_node = candidate
            atexit.register(self._release_on_exit)
            return candidate

        # PID alive and different -> another process holds the lock
        raise LockAcquisitionError(
            f"Loop '{self.loop_id}' is already locked by PID {existing.pid} "
            f"(holder='{existing.holder}', acquired={existing.acquired_at}). "
            f"Current PID={os.getpid()}."
        )

    # ------------------------------------------------------------------
    # Internal: release logic
    # ------------------------------------------------------------------

    def _do_release(self) -> None:
        if self._lock_file.is_file():
            existing = self._read_lock_file()
            if existing is not None and existing.pid == os.getpid():
                self._lock_file.unlink(missing_ok=True)
        self._acquired_node = None
        try:
            atexit.unregister(self._release_on_exit)
        except (AttributeError, TypeError):
            # atexit.unregister may not be available on all platforms
            pass

    def _release_on_exit(self) -> None:
        """Called by atexit during normal interpreter shutdown."""
        try:
            self._mutex.acquire(timeout=1)
        except Timeout:
            return
        try:
            self._do_release()
        finally:
            self._mutex.release()

    # ------------------------------------------------------------------
    # Internal: file I/O
    # ------------------------------------------------------------------

    def _read_lock_file(self) -> LockNodeData | None:
        if not self._lock_file.is_file():
            return None
        try:
            raw = self._lock_file.read_text(encoding="utf-8")
            data = json.loads(raw)
            return LockNodeData.from_dict(data)
        except (json.JSONDecodeError, KeyError, TypeError):
            # Corrupted lock file -> treat as stale
            return None

    def _write_lock_file(self, node: LockNodeData) -> None:
        raw = node.to_json()
        # Write atomically via temp file + rename
        tmp_path = self._lock_file.with_suffix(".tmp")
        tmp_path.write_text(raw, encoding="utf-8")
        try:
            os.chmod(str(tmp_path), 0o600)
        except OSError:
            pass  # Windows may not support chmod
        tmp_path.replace(self._lock_file)

    def _remove_stale_lock(self) -> None:
        """Remove a stale lock file."""
        try:
            self._lock_file.unlink(missing_ok=True)
        except OSError:
            pass

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> LoopLockManager:
        return self

    def __exit__(self, *_exc: Any) -> None:
        if self.acquired:
            self.release()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _utc_iso_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _is_pid_alive(pid: int) -> bool:
    """Check whether a process with the given PID is alive.

    Uses os.kill(pid, 0) which sends no signal but performs error checking.
    Works on both POSIX and Windows (Windows maps ESRCH similarly).
    """
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False
    except Exception:
        return False
