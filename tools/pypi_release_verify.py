#!/usr/bin/env python3
"""Verify that a PyPI release can be published without hash ambiguity."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import urlopen


REPOSITORIES = {
    "pypi": "https://pypi.org/pypi",
    "testpypi": "https://test.pypi.org/pypi",
}


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


def fetch_release(repository: str, package: str, version: str) -> dict[str, Any] | None:
    """Fetch one exact package version, returning ``None`` when it is absent."""
    url = f"{REPOSITORIES[repository]}/{quote(package)}/{quote(version)}/json"
    try:
        with urlopen(url, timeout=20) as response:  # nosec B310 - fixed package index URLs
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code == 404:
            return None
        raise RuntimeError(f"PyPI returned HTTP {exc.code} for {package} {version}") from exc
    except (URLError, TimeoutError) as exc:
        raise RuntimeError(f"could not query {repository} for {package} {version}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"invalid JSON response for {package} {version}")
    return payload


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
) -> dict[str, Any]:
    """Return a publish decision or raise if an immutable release conflicts."""
    remote = fetch_release(repository, package, version)
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
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args(argv)
    try:
        result = verify_release(
            args.repository,
            args.package,
            args.version,
            artifact_hashes(args.artifacts),
            phase=args.phase,
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
