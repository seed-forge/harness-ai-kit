"""SKILL.md YAML frontmatter check + normalization (shared by validate/publish/tools).

Why this module exists
----------------------
AI IDEs (Codex/Cursor) load ``SKILL.md`` files and require the file to start with a
YAML frontmatter block delimited by ``---``.  The first line must be exactly ``---``
(LF, no BOM, no trailing CR), otherwise the IDE reports:

    ⚠ <path>/SKILL.md: missing YAML frontmatter delimited by ---

Historical failures observed in the harness-ai-kit fleet (2026-08-14 audit):

- Files with a UTF-8 BOM before ``---`` (``\\ufeff---``).
- Files with CRLF line endings (first line ``---\\r``).
- Files with a *duplicate* frontmatter block (a previous batch tool prepended a new
  block on top of an existing BOM/CRLF-prefixed one).
- Files with no frontmatter at all.

This module centralizes the detection rules and the idempotent normalizer so that
``tools/validate_skills.py``, the ``publish-skill`` pipeline and any batch tool share
exactly the same behavior.

Policy decisions
----------------
- **Strict first line**: ``---`` exactly (BOM stripped, no ``\\r``).  This mirrors the
  IDE loaders that produced the warnings.
- **Duplicate blocks**: keep the *last* complete block at the top of the file (that is
  the original hand-written frontmatter, which usually carries trigger keywords in
  ``description``), drop the generated blocks before it.
- **Missing frontmatter**: prepend a block derived from ``skill.json``
  (``id`` + ``summary``).
- **Line endings**: normalize the whole file to LF and strip every ``\\ufeff``.
  A repo-level ``.gitattributes`` (``*.md text eol=lf``) keeps it that way.

The module is stdlib-only (no PyYAML dependency): the structural checks (delimiters,
key presence, BOM/CRLF, duplicates) are the same checks the IDEs effectively perform.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

FRONTMATTER_DELIM = "---"
_NAME_RE = re.compile(r"^name\s*:\s*\S", re.MULTILINE)
_DESC_RE = re.compile(r"^description\s*:", re.MULTILINE)


def _decode_strict(raw: bytes) -> tuple[str, bool]:
    """Decode UTF-8, strip a leading BOM, report whether a BOM was present."""
    had_bom = raw.startswith(b"\xef\xbb\xbf")
    return raw.decode("utf-8-sig"), had_bom


def _is_delim(line: str) -> bool:
    """True when the line is exactly ``---`` (tolerating a stray BOM char)."""
    return line.replace("\ufeff", "").strip() == FRONTMATTER_DELIM


def _find_first_block(lines: list[str]) -> tuple[int, int] | None:
    """Return (start, end) of the first ``---``-delimited block at the file top.

    ``end`` is the index of the closing delimiter line.  Returns ``None`` when the
    first non-blank line is not ``---``.
    """
    start = 0
    while start < len(lines) and lines[start].strip() == "":
        start += 1
    if start >= len(lines) or not _is_delim(lines[start]):
        return None
    for end in range(start + 1, min(len(lines), start + 200)):
        if _is_delim(lines[end]):
            return start, end
    return None


def _second_block_exists(lines: list[str], first_end: int) -> bool:
    """True when another ``---`` block directly follows the first one."""
    idx = first_end + 1
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    return idx < len(lines) and _is_delim(lines[idx])


def frontmatter_problems(skill_dir: Path) -> list[str]:
    """Return a list of frontmatter problems for ``skill_dir/SKILL.md`` ([] = OK).

    The checks intentionally mirror what IDE skill loaders reject:
      - first line must be exactly ``---`` (LF, no BOM, no trailing CR)
      - a closing ``---`` delimiter must exist
      - the block must contain ``name:`` and ``description:`` keys
      - no duplicate consecutive frontmatter block at the top
      - no BOM / CR characters inside the frontmatter block
    """
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return []
    raw = skill_md.read_bytes()
    try:
        text, had_bom = _decode_strict(raw)
    except UnicodeDecodeError as exc:
        return [f"SKILL.md is not valid UTF-8: {exc}"]

    lines = text.split("\n")
    problems: list[str] = []

    first = lines[0] if lines else ""
    if first != FRONTMATTER_DELIM:
        problems.append(
            "SKILL.md missing YAML frontmatter delimited by '---' "
            f"(first line is {first[:40]!r})"
        )
        if "\r" in first:
            problems.append("SKILL.md frontmatter uses CRLF line endings")
        if had_bom:
            problems.append("SKILL.md starts with a UTF-8 BOM before '---'")
        return problems

    block = _find_first_block(lines)
    if block is None:
        problems.append("SKILL.md opening '---' has no closing delimiter")
        return problems
    _, end = block

    body = "\n".join(lines[1:end])
    if not _NAME_RE.search(body):
        problems.append("SKILL.md frontmatter missing 'name' key")
    if not _DESC_RE.search(body):
        problems.append("SKILL.md frontmatter missing 'description' key")
    if _second_block_exists(lines, end):
        problems.append("SKILL.md has duplicate frontmatter block at top")
    if had_bom:
        problems.append("SKILL.md starts with a UTF-8 BOM before '---'")
    if "\r" in first or "\r" in body:
        problems.append("SKILL.md frontmatter uses CRLF line endings")
    if "\ufeff" in body:
        problems.append("SKILL.md frontmatter contains a stray BOM character")
    return problems


def _fallback_frontmatter(skill_id: str, summary: str) -> str:
    desc = (summary or skill_id).strip()
    return f"---\nname: {skill_id}\ndescription: {desc}\n---\n"


def normalize_skill_markdown(text: str, skill_id: str, summary: str) -> str:
    """Return an idempotently normalized SKILL.md document (LF, single block)."""
    text = text.replace("\ufeff", "")
    text = re.sub(r"\r\n|\r", "\n", text)
    lines = text.split("\n")

    block = _find_first_block(lines)
    if block is None:
        # No frontmatter at all -> prepend one derived from skill.json.
        return _fallback_frontmatter(skill_id, summary) + "\n" + text.lstrip("\n")

    first_start, first_end = block
    # Drop generated blocks that were prepended in front of the original one.
    while _second_block_exists(lines, first_end):
        idx = first_end + 1
        while idx < len(lines) and lines[idx].strip() == "":
            idx += 1
        second_end = None
        for j in range(idx + 1, min(len(lines), idx + 200)):
            if _is_delim(lines[j]):
                second_end = j
                break
        if second_end is None:
            break
        first_start, first_end = idx, second_end

    kept = lines[first_start : first_end + 1]
    body = "\n".join(lines[first_start + 1 : first_end])
    if not _NAME_RE.search(body):
        kept.insert(1, f"name: {skill_id}")
    if not _DESC_RE.search(body):
        kept.insert(2 if _NAME_RE.search(body) else 1, f"description: {(summary or skill_id).strip()}")
    rest = lines[first_end + 1 :]
    while rest and rest[0].strip() == "":
        rest.pop(0)
    while rest and rest[-1].strip() == "":
        rest.pop()
    result = "\n".join(kept) + "\n\n" + "\n".join(rest) + "\n"
    return result


def skill_meta(skill_dir: Path) -> tuple[str, str]:
    """Load (id, summary) from skill.json, falling back to the directory name."""
    skill_id = skill_dir.name
    summary = ""
    meta_path = skill_dir / "skill.json"
    if meta_path.exists():
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
            skill_id = str(data.get("id") or skill_id)
            summary = str(data.get("summary") or "")
        except (json.JSONDecodeError, OSError):
            pass
    return skill_id, summary


def normalize_skill_dir(skill_dir: Path) -> tuple[bool, list[str]]:
    """Normalize ``skill_dir/SKILL.md`` in place.  Returns (changed, remaining problems)."""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return False, []
    skill_id, summary = skill_meta(skill_dir)
    text = skill_md.read_text(encoding="utf-8-sig", newline="")
    normalized = normalize_skill_markdown(text, skill_id, summary)
    changed = normalized != text
    if changed:
        skill_md.write_text(normalized, encoding="utf-8", newline="\n")
    return changed, frontmatter_problems(skill_dir)
