"""agents_inject: skill.json 声明的 AGENTS.md 注入器（幂等、可清理）。

契约（skill.json）:
  "agents_inject": [
    {"path": "AGENTS.md", "scope": "project", "when": "on_install", "content": "..."}
  ]

注入块以标记包裹，重复安装幂等替换，卸载时按标记移除。
"""

from __future__ import annotations

import json
from pathlib import Path


def _mark_start(skill_id: str) -> str:
    return f"<!-- agents_inject:{skill_id}:start -->"


def _mark_end(skill_id: str) -> str:
    return f"<!-- agents_inject:{skill_id}:end -->"


def _target_path(project_root: Path, entry: dict) -> Path:
    path = str(entry.get("path", "AGENTS.md"))
    p = (project_root / path).resolve()
    root = project_root.resolve()
    if p != root and root not in p.parents:
        raise ValueError(f"agents_inject path escapes project root: {path}")
    return p


def apply_agents_inject(project_root: Path, skill_meta_path: Path, skill_id: str) -> list[Path]:
    """向 project_root 注入 skill.json 声明的 agents_inject 块（幂等替换）。"""
    if not skill_meta_path.exists():
        return []
    try:
        meta = json.loads(skill_meta_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    entries = meta.get("agents_inject") or []
    touched: list[Path] = []
    for entry in entries:
        if str(entry.get("scope", "project")) != "project":
            continue
        content = str(entry.get("content", "")).strip()
        if not content:
            continue
        target = _target_path(project_root, entry)
        start_m = _mark_start(skill_id)
        end_m = _mark_end(skill_id)
        block = f"{start_m}\n{content}\n{end_m}"
        text = target.read_text(encoding="utf-8") if target.exists() else ""
        if start_m in text and end_m in text:
            pre = text.split(start_m, 1)[0]
            post = text.split(end_m, 1)[1]
            new_text = pre + block + post
        else:
            new_text = (text.rstrip() + "\n\n" + block + "\n") if text.strip() else block + "\n"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(new_text, encoding="utf-8")
        touched.append(target)
    return touched


def remove_agents_inject(project_root: Path, skill_id: str) -> list[Path]:
    """按标记移除指定 skill 的注入块（可清理）。"""
    start_m = _mark_start(skill_id)
    end_m = _mark_end(skill_id)
    touched: list[Path] = []
    for candidate in project_root.iterdir():
        if candidate.is_file() and candidate.suffix.lower() in (".md", ".mdc", ".txt", ""):
            try:
                text = candidate.read_text(encoding="utf-8")
            except Exception:
                continue
            if start_m in text and end_m in text:
                pre = text.split(start_m, 1)[0]
                post = text.split(end_m, 1)[1]
                candidate.write_text(pre + post.lstrip("\n"), encoding="utf-8")
                touched.append(candidate)
    return touched
