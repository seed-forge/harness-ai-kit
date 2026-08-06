"""Release and publish operations: twine, artifacts, git tags."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence

from ai_kit.domain.models import CliAssetRecord, SkillRecord
from ai_kit.domain import project_sync_presentation
from ai_kit.infrastructure.config_io import console_safe_text
from ai_kit.infrastructure.git_ops_extra import run_git


def validate_publish_selection(
    repo_root: Path, skill_ids: list[str], paths: list[str], publish_all: bool
) -> list[str]:
    if publish_all:
        return []

    selections: list[str] = []
    for skill_id in skill_ids:
        skill_path = repo_root / "skills" / skill_id
        if not skill_path.exists():
            raise FileNotFoundError(f"Skill directory not found for publish: {skill_path}")
        selections.append(f"skills/{skill_id}")

    for relative_path in paths:
        candidate = (repo_root / relative_path).resolve()
        try:
            candidate.relative_to(repo_root.resolve())
        except ValueError as exc:
            raise ValueError(f"Publish path must stay inside repository: {relative_path}") from exc

        if not candidate.exists():
            raise FileNotFoundError(f"Publish path not found: {candidate}")
        selections.append(str(candidate.relative_to(repo_root)).replace("\\", "/"))

    if not selections:
        raise ValueError("Publish requires --all, at least one --skill-id, or one repo-relative path.")

    deduped: list[str] = []
    for item in selections:
        if item not in deduped:
            deduped.append(item)
    return deduped




def stage_publish_paths(repo_root: Path, selections: list[str], publish_all: bool) -> None:
    if publish_all:
        run_git(repo_root, ["add", "-A"])
        return
    run_git(repo_root, ["add", "--", *selections])




def has_staged_changes(repo_root: Path) -> bool:
    result = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.returncode != 0




def commit_and_optionally_push(repo_root: Path, message: str, push: bool) -> tuple[str, str]:
    commit_result = run_git(repo_root, ["commit", "-m", message])
    push_output = ""
    if push:
        push_result = run_git(repo_root, ["push"])
        push_output = push_result.stdout.strip() or "Pushed to remote."
    return commit_result.stdout.strip(), push_output




def render_catalog_row(
    asset_id: str,
    name: str,
    status: str,
    owner: str,
    version: str,
    summary: str,
) -> str:
    return f"| `{asset_id}` | {name} | {status} | {owner} | {version} | {summary} |"




def ensure_catalog_entry(repo_root: Path, record: SkillRecord) -> None:
    catalog_path = repo_root / "catalog.md"
    if not catalog_path.exists():
        return

    content = catalog_path.read_text(encoding="utf-8")
    line = render_catalog_row(
        record.skill_id,
        record.name,
        record.status,
        record.owner,
        record.version,
        record.summary or f"{record.name} skill.",
    )
    pattern = rf"(?m)^\| `{re.escape(record.skill_id)}` \|.*$"
    if re.search(pattern, content):
        updated = re.sub(pattern, line, content, count=1)
    else:
        marker = "## 状态说明"
        if marker in content:
            updated = content.replace(marker, f"{line}\n\n{marker}", 1)
        else:
            updated = content.rstrip() + "\n" + line + "\n"
    catalog_path.write_text(updated, encoding="utf-8")




def append_note_to_top_changelog(changelog_path: Path, note: str) -> None:
    if not changelog_path.exists():
        return
    content = changelog_path.read_text(encoding="utf-8")
    if note in content:
        return
    lines = content.splitlines()
    heading_index = next((index for index, line in enumerate(lines) if line.startswith("## ")), None)
    if heading_index is None:
        updated = content.rstrip() + "\n\n- " + note + "\n"
    else:
        insert_at = heading_index + 1
        while insert_at < len(lines) and lines[insert_at].strip():
            insert_at += 1
        if insert_at < len(lines) and not lines[insert_at].strip():
            insert_at += 1
        lines.insert(insert_at, f"- {note}")
        updated = "\n".join(lines).rstrip() + "\n"
    changelog_path.write_text(updated, encoding="utf-8")




def prepend_document_banner(document_path: Path, banner: str) -> None:
    if not document_path.exists():
        return
    content = document_path.read_text(encoding="utf-8")
    if content.startswith(banner):
        return
    document_path.write_text(banner + content, encoding="utf-8")




def publish_selection(
    repo_root: Path,
    selections: list[str],
    publish_all: bool,
    message: str,
    push: bool,
    dry_run: bool,
) -> int:
    if dry_run:
        for line in project_sync_presentation.publish_selection_dry_run_lines(selections=selections):
            print(line)
        return 0

    stage_publish_paths(repo_root, selections, publish_all)

    if not has_staged_changes(repo_root):
        raise ValueError("No staged changes found for the requested publish selection.")

    commit_output, push_output = commit_and_optionally_push(repo_root, message, push)
    success_lines = project_sync_presentation.publish_selection_success_lines(selections=selections)
    print(success_lines[0])
    if commit_output:
        print(commit_output)
    if push_output:
        print(push_output)
    print(success_lines[-1])
    return 0




def twine_environment_ready() -> bool:
    return bool(os.environ.get("TWINE_USERNAME")) and bool(os.environ.get("TWINE_PASSWORD"))




def release_workspace_dir(repo_root: Path) -> Path:
    target = repo_root / ".tmp-release"
    target.mkdir(parents=True, exist_ok=True)
    return target




def release_subprocess_env(repo_root: Path | None = None) -> dict[str, str]:
    env = dict(os.environ)
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    if repo_root is not None:
        temp_root = release_workspace_dir(repo_root)
        env["TMPDIR"] = str(temp_root)
        env["TEMP"] = str(temp_root)
        env["TMP"] = str(temp_root)
    return env




def twine_subprocess_env(repo_root: Path | None = None) -> dict[str, str]:
    env = release_subprocess_env(repo_root)
    team_username = os.environ.get("AI_KIT_REGISTRY_USERNAME")
    team_password = os.environ.get("AI_KIT_REGISTRY_PASSWORD")
    if team_username and team_password:
        env.setdefault("TWINE_USERNAME", team_username)
        env.setdefault("TWINE_PASSWORD", team_password)
    return env




def clean_release_artifacts(repo_root: Path) -> None:
    for relative_path in ("dist", "build", ".tmp-release"):
        target = repo_root / relative_path
        if target.exists():
            shutil.rmtree(target)




def build_artifacts(repo_root: Path) -> str:
    result = subprocess.run(
        [sys.executable, "-m", "build"],
        cwd=repo_root,
        env=release_subprocess_env(repo_root),
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return console_safe_text(result.stdout.strip())




def dist_files(repo_root: Path) -> list[Path]:
    target_dir = repo_root / "dist"
    if not target_dir.exists():
        raise FileNotFoundError(f"dist directory not found: {target_dir}")
    files = sorted(path for path in target_dir.iterdir() if path.is_file())
    if not files:
        raise FileNotFoundError(f"No distribution artifacts found in {target_dir}")
    return files




def twine_check_artifacts(repo_root: Path) -> str:
    files = [str(path) for path in dist_files(repo_root)]
    result = subprocess.run(
        [sys.executable, "-m", "twine", "check", *files],
        cwd=repo_root,
        env=release_subprocess_env(repo_root),
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return console_safe_text(result.stdout.strip())




def twine_upload_command(files: Sequence[str], repository_url: str) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "twine",
        "upload",
        "--disable-progress-bar",
        "--repository-url",
        repository_url,
    ]
    command.extend(files)
    return command




def upload_artifacts(
    repo_root: Path,
    repository_url: str,
    trusted_host: str,
    dry_run: bool,
) -> str:
    files = [str(path) for path in dist_files(repo_root)]
    command = twine_upload_command(files, repository_url)

    if dry_run:
        return console_safe_text(" ".join(command))

    result = subprocess.run(
        command,
        cwd=repo_root,
        env=twine_subprocess_env(repo_root),
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return console_safe_text(result.stdout.strip())




def create_git_tag(repo_root: Path, tag_name: str, push: bool) -> tuple[str, str]:
    tag_result = run_git(repo_root, ["tag", tag_name])
    push_output = ""
    if push:
        push_result = run_git(repo_root, ["push", "origin", tag_name])
        push_output = push_result.stdout.strip() or f"Pushed tag {tag_name}."
    return tag_result.stdout.strip(), push_output




