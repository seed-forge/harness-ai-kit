from __future__ import annotations

from pathlib import Path
from typing import Any

from harness_ai_kit import package_manager as pm
from harness_ai_kit.domain.models.constants import REFERENCE_DOC_RE
from harness_ai_kit.domain.inventory import (
    managed_asset_document_paths,
    reference_doc_paths,
    validate_usage_doc,
)


# These paths identify the maintainer checkout, not a member's installed asset.
# Keep the check deliberately narrow: deployment paths and user-configured
# workspace locations are valid contracts when expressed through placeholders.
_NON_PORTABLE_CHECKOUT_MARKERS = (
    "工程规范/harness-ai-kit",
    "工程规范\\harness-ai-kit",
    "工程规范/harness-ai-kit",
    "工程规范\\harness-ai-kit",
    "02-工程工作空间/工程规范/harness-ai-kit",
    "02-工程工作空间\\工程规范\\harness-ai-kit",
    "02-工程工作空间/工程规范/harness-ai-kit",
    "02-工程工作空间\\工程规范\\harness-ai-kit",
)
_PORTABILITY_EXCLUDED_NAMES = {
    "CHANGELOG.md",
    ".publish-lag.json",
    "schedule-ledger.yaml",
    # This governance reference intentionally shows forbidden examples.
    "REFERENCE-ASSET-PORTABILITY.md",
}
_PORTABILITY_EXCLUDED_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", ".tmp"}


def validate_asset_portability(asset_dir: Path) -> list[str]:
    """Reject maintainer checkout paths from installable asset payloads."""
    errors: list[str] = []
    for path in asset_dir.rglob("*"):
        if not path.is_file() or path.name in _PORTABILITY_EXCLUDED_NAMES:
            continue
        if any(part in _PORTABILITY_EXCLUDED_DIRS for part in path.parts) or any(
            part.startswith(".bak-") for part in path.parts
        ):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for marker in _NON_PORTABLE_CHECKOUT_MARKERS:
            if marker in text:
                errors.append(
                    f"{asset_dir.name}: non-portable maintainer checkout path "
                    f"'{marker}' in {path.relative_to(asset_dir).as_posix()}; "
                    "use a package-relative reference or {checkout_dir}"
                )
                break
    return errors


def validate_cli_portability(cli_dir: Path) -> list[str]:
    """Apply the same checkout-path guard to CLI docs and config defaults."""
    return validate_asset_portability(cli_dir)


def skill_has_reference_section(entry_text: str) -> bool:
    for line in entry_text.splitlines():
        heading = line.strip()
        if not heading.startswith("##"):
            continue
        if "引用" in heading or "Reference" in heading:
            return True
    return False


def validate_reference_docs(asset_dir: Path, manifest: pm.SkillManifest) -> list[str]:
    if manifest.package_type != "skill":
        return []
    errors: list[str] = []
    entry_path = asset_dir / manifest.entry
    entry_text = entry_path.read_text(encoding="utf-8") if entry_path.exists() else ""
    reference_paths = reference_doc_paths(asset_dir)
    invalid_reference_paths = [path for path in reference_paths if not REFERENCE_DOC_RE.fullmatch(path.name)]
    for path in invalid_reference_paths:
        errors.append(f"{asset_dir.name}: reference doc must use REFERENCE-*.md naming: {path.relative_to(asset_dir)}")
    if reference_paths:
        for path in reference_paths:
            if path.name not in entry_text and path.as_posix().replace("references/", "") not in entry_text:
                errors.append(f"{asset_dir.name}: SKILL.md must link or mention {path.relative_to(asset_dir).as_posix()}")
    legacy_paths = [path for path in asset_dir.glob("REFERENCE.md") if path.is_file()]
    for path in legacy_paths:
        errors.append(f"{asset_dir.name}: replace legacy reference filename with semantic REFERENCE-*.md: {path.name}")
    return errors


def validate_companion_docs(asset_dir: Path, manifest: pm.SkillManifest) -> list[str]:
    errors: list[str] = []
    for label, path, required in managed_asset_document_paths(asset_dir, manifest):
        if required and not path.exists():
            errors.append(f"{asset_dir.name}: missing {path.name}")
    errors.extend(validate_usage_doc(asset_dir, asset_dir / manifest.companion_docs.usage))
    errors.extend(validate_reference_docs(asset_dir, manifest))
    return errors


def validate_cli_companion_docs(cli_dir: Path) -> list[str]:
    usage_path = cli_dir / "USAGE.md"
    errors: list[str] = []
    if not usage_path.exists():
        errors.append(f"{cli_dir.name}: missing USAGE.md")
    errors.extend(validate_usage_doc(cli_dir, usage_path))
    return errors
