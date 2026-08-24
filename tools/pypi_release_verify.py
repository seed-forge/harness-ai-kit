#!/usr/bin/env python3
"""Verify that a PyPI release can be published without hash ambiguity."""
from __future__ import annotations

import argparse
import email.utils
import hashlib
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import urlopen


REPOSITORIES = {
    "pypi": "https://pypi.org/pypi",
    "testpypi": "https://test.pypi.org/pypi",
}

DEFAULT_MAX_ATTEMPTS = 6
DEFAULT_MAX_TOTAL_SECONDS = 90.0
DEFAULT_BASE_BACKOFF_SECONDS = 2.0
DEFAULT_MAX_BACKOFF_SECONDS = 30.0
REQUEST_TIMEOUT_SECONDS = 20.0
TRANSIENT_HTTP_STATUS_CODES = frozenset({408, 425, 429, 500, 502, 503, 504})


def artifact_hashes(paths: list[Path]) -> dict[str, str]:
    """Return SHA-256 values for the wheel and sdist files in ``paths``."""
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(sorted((*path.glob("*.whl"), *path.glob("*.tar.gz"))))
        elif path.is_file():
            files.append(path)
    result = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    if not result:
        raise ValueError("no wheel or source distribution artifacts were supplied")
    return result


def parse_retry_after(value: str | None, *, now: datetime | None = None) -> float | None:
    """Parse a Retry-After value as non-negative seconds."""
    if not value:
        return None
    try:
        seconds = float(value.strip())
        return max(0.0, seconds) if math.isfinite(seconds) else None
    except ValueError:
        pass
    try:
        retry_at = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if retry_at is None:
        return None
    if retry_at.tzinfo is None:
        retry_at = retry_at.replace(tzinfo=timezone.utc)
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return max(0.0, (retry_at - current).total_seconds())


def _pending_payload(payload: object) -> bool:
    """Return whether a JSON response is not ready for immutable comparison."""
    if not isinstance(payload, dict):
        return True
    urls = payload.get("urls")
    if not isinstance(urls, list) or not urls:
        return True
    return not all(
        isinstance(item, dict)
        and isinstance(item.get("filename"), str)
        and isinstance(item.get("digests"), dict)
        and isinstance(item["digests"].get("sha256"), str)
        for item in urls
    )


def fetch_release(
    repository: str,
    package: str,
    version: str,
    *,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    max_total_seconds: float = DEFAULT_MAX_TOTAL_SECONDS,
    base_backoff_seconds: float = DEFAULT_BASE_BACKOFF_SECONDS,
    max_backoff_seconds: float = DEFAULT_MAX_BACKOFF_SECONDS,
    wait_for_404: bool = True,
    require_files: bool = True,
    sleep: Any = time.sleep,
    clock: Any = time.monotonic,
) -> dict[str, Any] | None:
    """Fetch one exact version with bounded retries for absent or pending metadata."""
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")
    if not all(
        math.isfinite(value)
        for value in (max_total_seconds, base_backoff_seconds, max_backoff_seconds)
    ) or max_total_seconds < 0 or base_backoff_seconds < 0 or max_backoff_seconds < 0:
        raise ValueError("retry timing values must be finite and non-negative")
    url = f"{REPOSITORIES[repository]}/{quote(package)}/{quote(version)}/json"
    started = clock()
    attempts = 0
    last_state = "unknown"
    last_error = ""
    while attempts < max_attempts:
        remaining = max_total_seconds - (clock() - started)
        if attempts and remaining <= 0:
            break
        attempts += 1
        retry_after: float | None = None
        try:
            request_timeout = min(REQUEST_TIMEOUT_SECONDS, max(0.1, remaining))
            with urlopen(url, timeout=request_timeout) as response:  # nosec B310 - fixed package index URLs
                payload = json.loads(response.read().decode("utf-8"))
                response_headers = getattr(response, "headers", None)
                retry_after = parse_retry_after(
                    response_headers.get("Retry-After") if response_headers else None
                )
            if not isinstance(payload, dict):
                last_state = "invalid-json"
                last_error = "response is not a JSON object"
            elif require_files and _pending_payload(payload):
                last_state = "pending"
                last_error = "metadata has no complete SHA-256 release files"
            else:
                return payload
        except HTTPError as exc:
            retry_after = parse_retry_after(exc.headers.get("Retry-After") if exc.headers else None)
            if exc.code == 404:
                if not wait_for_404:
                    return None
                last_state = "404"
                last_error = "version is not visible yet"
            elif exc.code in TRANSIENT_HTTP_STATUS_CODES:
                last_state = f"HTTP {exc.code}"
                last_error = "transient index response"
            else:
                raise RuntimeError(f"PyPI returned HTTP {exc.code} for {package} {version}") from exc
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            last_state = "invalid-json"
            last_error = str(exc)
        except (URLError, TimeoutError) as exc:
            last_state = "request-error"
            last_error = str(exc)

        remaining = max_total_seconds - (clock() - started)
        if attempts >= max_attempts or remaining <= 0:
            break
        delay = retry_after if retry_after is not None else min(
            max_backoff_seconds, base_backoff_seconds * (2 ** (attempts - 1))
        )
        delay = min(max(0.0, delay), remaining)
        if delay <= 0:
            break
        sleep(delay)

    raise RuntimeError(
        f"PyPI metadata still {last_state} for {package} {version} on {repository} "
        f"after {attempts} attempt(s) over {max_total_seconds:g}s; {last_error}. "
        "Check the package index and GitHub Actions publish logs."
    )


def remote_hashes(payload: dict[str, Any]) -> dict[str, str]:
    urls = payload.get("urls")
    if not isinstance(urls, list):
        raise RuntimeError("PyPI response does not contain release files")
    hashes: dict[str, str] = {}
    for item in urls:
        if not isinstance(item, dict):
            continue
        filename = item.get("filename")
        digest = item.get("digests", {}).get("sha256") if isinstance(item.get("digests"), dict) else None
        if isinstance(filename, str) and isinstance(digest, str):
            hashes[filename] = digest
    if not hashes:
        raise RuntimeError("PyPI response contains no SHA-256 release files")
    return hashes


def verify_release(
    repository: str,
    package: str,
    version: str,
    local: dict[str, str],
    *,
    phase: str,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    max_total_seconds: float = DEFAULT_MAX_TOTAL_SECONDS,
    base_backoff_seconds: float = DEFAULT_BASE_BACKOFF_SECONDS,
    max_backoff_seconds: float = DEFAULT_MAX_BACKOFF_SECONDS,
) -> dict[str, Any]:
    """Return a publish decision or raise if an immutable release conflicts."""
    remote = fetch_release(
        repository,
        package,
        version,
        max_attempts=max_attempts,
        max_total_seconds=max_total_seconds,
        base_backoff_seconds=base_backoff_seconds,
        max_backoff_seconds=max_backoff_seconds,
        wait_for_404=phase != "preflight",
        require_files=phase != "presence",
    )
    if remote is None:
        if phase in {"readback", "presence"}:
            raise RuntimeError(f"{package} {version} is absent from {repository} after publish")
        return {
            "status": "publish",
            "should_publish": True,
            "package": package,
            "version": version,
            "repository": repository,
        }

    if phase == "presence":
        return {
            "status": "present",
            "should_publish": False,
            "package": package,
            "version": version,
            "repository": repository,
        }

    remote_files = remote_hashes(remote)
    if remote_files != local:
        missing = sorted(set(local) - set(remote_files))
        unexpected = sorted(set(remote_files) - set(local))
        changed = sorted(name for name in set(local) & set(remote_files) if local[name] != remote_files[name])
        details = ", ".join(
            value
            for value in (
                f"missing={missing}" if missing else "",
                f"unexpected={unexpected}" if unexpected else "",
                f"hash_mismatch={changed}" if changed else "",
            )
            if value
        )
        raise RuntimeError(f"immutable version collision for {package} {version}: {details}")
    return {
        "status": "verified" if phase == "readback" else "already-published",
        "should_publish": False,
        "package": package,
        "version": version,
        "repository": repository,
    }


def write_github_output(path: Path, result: dict[str, Any]) -> None:
    path.write_text(
        "\n".join(
            (
                f"should_publish={'true' if result['should_publish'] else 'false'}",
                f"status={result['status']}",
            )
        )
        + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", choices=sorted(REPOSITORIES), required=True)
    parser.add_argument("--package", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--artifacts", type=Path, action="append", required=True)
    parser.add_argument("--phase", choices=("preflight", "readback", "presence"), default="preflight")
    parser.add_argument("--max-attempts", type=int, default=DEFAULT_MAX_ATTEMPTS)
    parser.add_argument("--max-total-seconds", type=float, default=DEFAULT_MAX_TOTAL_SECONDS)
    parser.add_argument("--base-backoff-seconds", type=float, default=DEFAULT_BASE_BACKOFF_SECONDS)
    parser.add_argument("--max-backoff-seconds", type=float, default=DEFAULT_MAX_BACKOFF_SECONDS)
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args(argv)
    try:
        result = verify_release(
            args.repository,
            args.package,
            args.version,
            artifact_hashes(args.artifacts),
            phase=args.phase,
            max_attempts=args.max_attempts,
            max_total_seconds=args.max_total_seconds,
            base_backoff_seconds=args.base_backoff_seconds,
            max_backoff_seconds=args.max_backoff_seconds,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if args.github_output:
        write_github_output(args.github_output, result)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
