from __future__ import annotations

import re
from collections.abc import Iterable

from packaging.specifiers import SpecifierSet
from packaging.version import InvalidVersion, Version

PINNED_VERSION_PATTERN = "==x.y.z"
LATEST_VERSION = "latest"


def is_latest_specifier(value: str) -> bool:
    """Return True when *value* is the ``latest`` sentinel.

    The ``latest`` keyword bypasses normal PEP-440 specifier validation and
    tells the resolver to always fetch the newest available version regardless
    of source (Nexus registry, git repo, or local checkout).
    """
    return str(value).strip().lower() == LATEST_VERSION


def ensure_version(value: str) -> str:
    try:
        return str(Version(str(value)))
    except InvalidVersion as exc:
        raise ValueError(f"Invalid version: {value}") from exc


def is_pinned_specifier(value: str) -> bool:
    value = str(value).strip()
    if not value.startswith("=="):
        return False
    try:
        Version(value[2:])
    except InvalidVersion:
        return False
    return True


def is_compatible_specifier(value: str) -> bool:
    """Accept ==x.y.z or >=x.y.z for extends versions."""
    value = str(value).strip()
    if not (value.startswith("==") or value.startswith(">=")):
        return False
    try:
        Version(value[2:])
    except InvalidVersion:
        return False
    return True


def compare_versions(left: str, right: str) -> int:
    try:
        left_version = Version(left)
        right_version = Version(right)
    except InvalidVersion:
        if left == right:
            return 0
        return -1 if left < right else 1
    if left_version == right_version:
        return 0
    return -1 if left_version < right_version else 1


def compare_versions_safe(left: str, right: str) -> int | None:
    if not left or not right:
        return None
    try:
        return compare_versions(left, right)
    except InvalidVersion:
        return None


def highest_version(versions: Iterable[str]) -> str:
    version_list = [version for version in versions if version]
    if not version_list:
        return ""
    try:
        return max(version_list, key=Version)
    except InvalidVersion:
        return sorted(version_list)[-1]


def sort_versions(versions: Iterable[str]) -> tuple[str, ...]:
    version_list = [version for version in versions if version]
    if not version_list:
        return ()
    unique_versions = list(dict.fromkeys(version_list))
    try:
        return tuple(sorted(unique_versions, key=Version))
    except InvalidVersion:
        return tuple(sorted(unique_versions))


def upgrade_status_for_versions(installed_version: str, available_version: str) -> str:
    if not installed_version:
        return "not-installed"
    comparison = compare_versions_safe(installed_version, available_version)
    if comparison is None:
        return "unknown"
    if comparison == 0:
        return "up-to-date"
    if comparison < 0:
        return "upgrade-available"
    return "local-ahead"


def parse_version_from_text(text: str) -> str:
    match = re.search(r"\b\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?\b", text)
    return match.group(0) if match else ""


def bump_version_string(current_version: str, part: str) -> str:
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", current_version)
    if not match:
        raise ValueError(f"Unsupported version format: {current_version}")

    major, minor, patch = [int(piece) for piece in match.groups()]
    if part == "patch":
        patch += 1
    elif part == "minor":
        minor += 1
        patch = 0
    elif part == "major":
        major += 1
        minor = 0
        patch = 0
    else:
        raise ValueError(f"Unsupported bump part: {part}")
    return f"{major}.{minor}.{patch}"


def version_to_pinned(version: str) -> str:
    version = str(version).strip()
    if not version:
        raise ValueError("Version cannot be empty.")
    return f"=={version}"


def version_to_compatible_range(version: str) -> str:
    """Convert a version to a compatible range specifier.

    Rules:
    - 0.x (trial): >=0.y.z (direct upgrade, no upper bound)
    - 1.x+ (stable): >=x.y.z,<(x+1).0.0 (don't cross major version)
    """
    version = str(version).strip()
    if not version:
        raise ValueError("Version cannot be empty.")
    v = Version(version)
    if v.major == 0:
        return f">={version}"
    return f">={version},<{v.major + 1}.0.0"


def spec_matches_version(specifier: str, version: str) -> bool:
    """PEP-440 semantic match (0.10.12 fix: supports >= ranges).

    历史实现是 pinned 字符串相等比较，导致 `>=0.3.4` 依赖声明永远判定失败、
    依赖只能钉死 `==x.y.z`（与 dependencies 用 >= 做向后兼容的规范矛盾）。
    现在统一走 packaging.SpecifierSet；非法 specifier 回退严格相等比较。
    """
    if is_latest_specifier(specifier):
        return True
    try:
        return Version(str(version).strip()) in SpecifierSet(str(specifier).strip())
    except Exception:
        return version_to_pinned(version) == str(specifier).strip()
