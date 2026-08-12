from __future__ import annotations

import hashlib
import io
import zipfile
from pathlib import Path
from typing import Sequence

from harness_ai_kit.product import active_product_profile


def manifest_cache_dir() -> Path:
    return Path.home() / active_product_profile().config_dirname / "cache" / "skills"


def git_source_cache_dir() -> Path:
    return Path.home() / active_product_profile().config_dirname / "cache" / "git"


def git_source_cache_path(source_ref: str, ref: str | None = None) -> Path:
    key = f"{source_ref}#{ref or ''}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    path = git_source_cache_dir() / digest
    path.mkdir(parents=True, exist_ok=True)
    return path


def cache_inventory() -> list[Path]:
    cache_root = manifest_cache_dir()
    if not cache_root.exists():
        return []
    return sorted(path for path in cache_root.iterdir() if path.is_file())


def clean_cache() -> int:
    cache_root = manifest_cache_dir()
    if not cache_root.exists():
        return 0
    count = 0
    for path in cache_root.iterdir():
        if path.is_file():
            path.unlink()
            count += 1
    return count


def cache_file_for_url(url: str, suffix: str) -> Path:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
    path = manifest_cache_dir() / f"{digest}.{suffix}"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def hash_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def hash_file(path: Path) -> str:
    return hash_bytes(path.read_bytes())


IGNORED_HASH_FILENAMES = {".DS_Store", "Thumbs.db"}


def _should_ignore_hash_path(path: Path) -> bool:
    return any(part in IGNORED_HASH_FILENAMES or part == "__pycache__" for part in path.parts)


def hash_named_bytes(entries: Sequence[tuple[str, bytes]]) -> str:
    digest = hashlib.sha256()
    for relative_path, payload in sorted(entries, key=lambda item: item[0].replace("\\", "/")):
        normalized = relative_path.replace("\\", "/").strip("/")
        if not normalized:
            continue
        if _should_ignore_hash_path(Path(normalized)):
            continue
        digest.update(b"file\0")
        digest.update(normalized.encode("utf-8"))
        digest.update(b"\0")
        digest.update(payload)
        digest.update(b"\0")
    return digest.hexdigest()


# Directories excluded from published skill archives (producer-side working material,
# not part of the installable asset). Convention: <asset>/visual/ holds visual
# promotion kits (cnt-aikit-visual); consumers must not receive them.
PUBLISH_EXCLUDE_DIR_NAMES = frozenset({"visual", "__pycache__"})


def build_skill_archive_bytes(skill_dir: Path) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in sorted(skill_dir.rglob("*")):
            if file_path.is_file() and not any(
                part in PUBLISH_EXCLUDE_DIR_NAMES
                for part in file_path.relative_to(skill_dir).parts
            ):
                archive.write(file_path, arcname=str(file_path.relative_to(skill_dir.parent)).replace("\\", "/"))
    return buffer.getvalue()


def hash_skill_directory(skill_dir: Path) -> str:
    entries: list[tuple[str, bytes]] = []
    for file_path in sorted(skill_dir.rglob("*")):
        if not file_path.is_file():
            continue
        relative = file_path.relative_to(skill_dir)
        if _should_ignore_hash_path(relative):
            continue
        entries.append((relative.as_posix(), file_path.read_bytes()))
    return hash_named_bytes(entries)
