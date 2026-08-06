"""Install command Git source skill selection helpers."""
from __future__ import annotations

import argparse
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .install import InstallCommandContext


def _git_skill_key(skill: Any, context: InstallCommandContext) -> str:
    return context.pm.canonical_package_id(skill.id, skill.namespace)


def _git_skill_display_name(skill: Any, context: InstallCommandContext) -> str:
    summary = str(getattr(skill, "summary", "") or "").strip()
    key = _git_skill_key(skill, context)
    return f"{key} - {summary}" if summary else key


def _select_git_source_skills(discovered: list[Any], args: argparse.Namespace, context: InstallCommandContext) -> list[Any]:
    if not discovered:
        raise ValueError("No skills were found in the git source.")
    if len(discovered) == 1 or getattr(args, "all", False):
        return discovered
    if not context.stdin_isatty():
        available = ", ".join(_git_skill_key(item, context) for item in discovered)
        raise ValueError(
            "The git source contains multiple skills. "
            f"Use `--all`, pass a GitHub `/tree/<ref>/<subpath>` URL, or choose one of: {available}."
        )
    print("Select skills to install:")
    for index, item in enumerate(discovered, start=1):
        print(f"{index}. {_git_skill_display_name(item, context)}")
    answer = context.prompt_input("Enter numbers separated by comma, or `all`: ").strip()
    if answer.lower() == "all":
        return discovered
    indexes: list[int] = []
    for token in answer.replace(",", " ").split():
        try:
            index = int(token)
        except ValueError as exc:
            raise ValueError(f"Invalid selection: {token}") from exc
        if index < 1 or index > len(discovered):
            raise ValueError(f"Selection out of range: {index}")
        if index not in indexes:
            indexes.append(index)
    if not indexes:
        raise ValueError("No skills selected.")
    return [discovered[index - 1] for index in indexes]


def _looks_like_github_shorthand(value: str) -> bool:
    return "/" in value and not value.startswith((".", "/", "\\"))


def _is_explicit_git_source(value: str, args: argparse.Namespace, context: InstallCommandContext) -> bool:
    return context.is_git_source_selector(value) or (
        getattr(args, "source_selector", None) == context.pm.SOURCE_GIT_REPO and _looks_like_github_shorthand(value)
    )


def _expand_git_source_skill_ids(
    asset_ids: list[str],
    args: argparse.Namespace,
    context: InstallCommandContext,
) -> tuple[list[str], dict[str, tuple[str, str | None, str | None]]]:
    root_ids: list[str] = []
    root_sources: dict[str, tuple[str, str | None, str | None]] = {}
    for asset_id in asset_ids:
        if not _is_explicit_git_source(asset_id, args, context):
            root_ids.append(asset_id)
            continue
        selected = _select_git_source_skills(context.discover_git_skills(asset_id), args, context)
        for item in selected:
            key = _git_skill_key(item, context)
            if key in root_sources:
                continue
            root_ids.append(key)
            root_sources[key] = (item.source_ref, item.ref, item.subpath)
    return root_ids, root_sources


def choose_git_skill_interactively(discovered: list[Any]) -> Any | None:
    print("Git source contains multiple skills:")
    for index, skill in enumerate(discovered, start=1):
        skill_id = getattr(skill, "id", "")
        namespace = getattr(skill, "namespace", None)
        canonical = f"{namespace}/{skill_id}" if namespace else skill_id
        subpath = getattr(skill, "subpath", None) or "."
        name = getattr(skill, "name", "") or canonical
        summary = getattr(skill, "summary", "") or ""
        suffix = f" - {summary}" if summary else ""
        print(f"  {index}. {canonical} ({subpath}) - {name}{suffix}")
    while True:
        try:
            answer = input("Select skill number: ").strip()
        except EOFError:
            print("No input received, aborting.")
            return None
        if not answer:
            return None
        try:
            selected_index = int(answer)
        except ValueError:
            print("Enter a number from the list, or press Enter to cancel.")
            continue
        if 1 <= selected_index <= len(discovered):
            return discovered[selected_index - 1]
        print("Selection out of range.")


