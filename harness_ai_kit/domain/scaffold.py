"""Scaffold new skills, managed assets, and CLIs."""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

from harness_ai_kit import package_manager as pm
from harness_ai_kit.domain.models import CliAssetRecord, SkillRecord
from harness_ai_kit.domain.models.constants import ASSET_DIRECTORY_NAMES
from harness_ai_kit.domain.inventory import load_cli_record, load_skill_record
from harness_ai_kit.infrastructure.git_ops_extra import normalize_module_name
from harness_ai_kit.infrastructure.release_ops import ensure_catalog_entry
from harness_ai_kit.usage_docs import render_usage_doc


def scaffold_skill(repo_root: Path, skill_id: str) -> SkillRecord:
    template_dir = repo_root / "skills" / "_template"
    target_dir = repo_root / "skills" / skill_id
    if target_dir.exists():
        raise FileExistsError(f"Skill already exists: {target_dir}")
    if not template_dir.exists():
        raise FileNotFoundError(f"Skill template not found: {template_dir}")

    shutil.copytree(template_dir, target_dir)
    metadata_path = target_dir / "skill.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata = {
        "id": skill_id,
        "name": skill_id,
        "owner": "team",
        "version": "0.1.0",
        "status": "draft",
        "entry": "SKILL.md",
        "package_type": "skill",
        "tags": metadata.get("tags", []),
        "summary": f"Describe what {skill_id} solves for the team.",
        "compatible_clients": metadata.get("compatible_clients", ["codex"]),
        "installation": {"default_scope": "project"},
        "dependencies": [],
        "sources": {"preferred": ["repo-checkout", "team-skill-registry"], "allow_fallback": True},
        "companion_docs": {"usage": "USAGE.md", "example": "EXAMPLE.md", "example_required": False},
        "environment": {
            "dependency_groups": [],
            "system": [],
            "python_strategy": "none",
            "python_packages": [],
            "fonts": [],
            "verify_commands": [],
        },
        "runtime_requirements": [],
        "post_install_hints": [],
        "agents_md_inject": "",
        "config_schema": None,
        "updated_at": "2026-05-09",
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (target_dir / "SKILL.md").write_text(
        (
            f"# {skill_id}\n\n"
            "## 用途\n\n"
            "描述这个 Skill 解决的重复性工作。\n\n"
            "## 输入\n\n"
            "- 输入项 1\n\n"
            "## 输出\n\n"
            "- 输出项 1\n\n"
            "## 工作流\n\n"
            "1. 收集执行所需上下文。\n"
            "2. 按固定方法处理任务。\n"
            "3. 产出符合预期的结果格式。\n\n"
            "## 约束\n\n"
            "- 明确说明前提假设。\n"
            "- 不要依赖私有凭证。\n"
            "- 外部依赖统一写入 skill.json 的 environment 字段，并支持校验与安装。\n\n"
            "## 专题引用\n\n"
            "- 暂无。若某个专题需要详细正文，请新增 `REFERENCE-<TOPIC>.md` 或 `references/REFERENCE-<TOPIC>.md`，"
            "主 `SKILL.md` 只保留摘要和引用入口。\n"
        ),
        encoding="utf-8",
    )
    (target_dir / "USAGE.md").write_text(render_usage_doc(metadata), encoding="utf-8", newline="\n")
    record = load_skill_record(target_dir)
    ensure_catalog_entry(repo_root, record)
    return record


def scaffold_managed_asset(repo_root: Path, asset_type: str, asset_id: str) -> SkillRecord:
    template_dir = repo_root / ASSET_DIRECTORY_NAMES[asset_type] / "_template"
    target_dir = repo_root / ASSET_DIRECTORY_NAMES[asset_type] / asset_id
    if target_dir.exists():
        raise FileExistsError(f"{asset_type.title()} already exists: {target_dir}")
    if not template_dir.exists():
        raise FileNotFoundError(f"{asset_type.title()} template not found: {template_dir}")

    shutil.copytree(template_dir, target_dir)
    metadata_filename = pm.manifest_metadata_filename(asset_type)
    metadata_path = target_dir / metadata_filename
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata.update(
        {
            "id": asset_id,
            "name": asset_id,
            "owner": "team",
            "version": "0.1.0",
            "status": "draft",
            "entry": "README.md",
            "package_type": asset_type,
            "summary": f"Describe what {asset_id} does for the team.",
            "installation": metadata.get(
                "installation",
                {
                    "default_scope": "project",
                    "install_mode": "manual" if asset_type in {"hook", "mcp"} else "bundle",
                },
            ),
            "dependencies": [],
            "companion_docs": {"usage": "USAGE.md", "example": "EXAMPLE.md", "example_required": False},
            "environment": metadata.get("environment", {}),
            "runtime_requirements": [],
            "post_install_hints": [],
            "agents_md_inject": "",
            "config_schema": None,
            "updated_at": "2026-05-11",
        }
    )
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (target_dir / "USAGE.md").write_text(render_usage_doc(metadata), encoding="utf-8", newline="\n")
    record = load_skill_record(target_dir)
    ensure_catalog_entry(repo_root, record)
    return record


def scaffold_cli(repo_root: Path, cli_id: str) -> CliAssetRecord:
    cli_root = repo_root / "cli" / cli_id
    if cli_root.exists():
        raise FileExistsError(f"CLI already exists: {cli_root}")

    module_name = normalize_module_name(cli_id)
    package_name = cli_id
    cli_root.mkdir(parents=True, exist_ok=False)
    package_dir = cli_root / module_name
    package_dir.mkdir(parents=True, exist_ok=True)

    metadata = {
        "id": cli_id,
        "name": cli_id,
        "owner": "team",
        "version": "0.1.0",
        "status": "draft",
        "package_type": "cli",
        "summary": f"Task-oriented CLI for {cli_id}.",
        "package_name": package_name,
        "install_type": "python-package",
        "publish_paths": [f"cli/{cli_id}"],
    }
    (cli_root / "cli.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (cli_root / "README.md").write_text(f"# {cli_id}\n\nDescribe the member-facing tasks this CLI solves.\n", encoding="utf-8")
    (cli_root / "USAGE.md").write_text(render_usage_doc(metadata), encoding="utf-8", newline="\n")
    (cli_root / "INSTALL.md").write_text(
        f"# {cli_id} 安装\n\n```bash\npip install {package_name}\n```\n",
        encoding="utf-8",
    )
    (cli_root / "RELEASE.md").write_text(
        "# 发布流程\n\n1. 补充测试\n2. 构建 wheel 与 sdist\n3. 发布到团队私有源\n",
        encoding="utf-8",
    )
    (cli_root / "CHANGELOG.md").write_text("# Changelog\n\n## 0.1.0\n\n- Initial scaffold.\n", encoding="utf-8")
    (cli_root / "pyproject.toml").write_text(
        "\n".join(
            [
                "[build-system]",
                'requires = ["setuptools>=68"]',
                'build-backend = "setuptools.build_meta"',
                "",
                "[project]",
                f'name = "{package_name}"',
                'version = "0.1.0"',
                f'description = "Task-oriented CLI for {cli_id}."',
                'requires-python = ">=3.10"',
                "",
                "[project.scripts]",
                f'{cli_id} = "{module_name}.main:main"',
                "",
                "[tool.setuptools]",
                'py-modules = []',
                "",
                "[tool.setuptools.packages.find]",
                'where = ["."]',
                f'include = ["{module_name}", "{module_name}.*"]',
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (package_dir / "__init__.py").write_text('__all__ = ["main"]\n', encoding="utf-8")
    (package_dir / "main.py").write_text(
        "\n".join(
            [
                "from __future__ import annotations",
                "",
                "import argparse",
                "",
                "",
                "def build_parser() -> argparse.ArgumentParser:",
                f'    return argparse.ArgumentParser(description="Task-oriented CLI for {cli_id}.")',
                "",
                "",
                "def main(argv: list[str] | None = None) -> int:",
                "    parser = build_parser()",
                "    parser.parse_args(argv)",
                '    print("TODO: implement task commands.")',
                "    return 0",
                "",
                "",
                'if __name__ == "__main__":',
                "    raise SystemExit(main())",
                "",
            ]
        ),
        encoding="utf-8",
    )

    # -- config.py (unified config thin wrapper) --------------------------------
    (package_dir / "config.py").write_text(
        "\n".join(
            [
                f'"""Unified config for {cli_id} — thin wrapper over asset_config_loader."""',
                "from __future__ import annotations",
                "",
                "from pathlib import Path",
                "from typing import Any",
                "",
                "from harness_ai_kit.infrastructure.asset_config_loader import (",
                "    load_asset_config,",
                "    state_dir,",
                ")",
                "",
                f'ASSET_ID = "{cli_id}"',
                "ASSET_DIR = Path(__file__).parent",
                "LEGACY_PATHS: list[Path] = []",
                "",
                "",
                "def get_config(cli_overrides: dict[str, str] | None = None) -> dict[str, Any]:",
                '    """Return effective config (L1 defaults \u2192 L2 unified \u2192 L3 overrides)."""',
                "    return load_asset_config(",
                "        ASSET_ID,",
                "        asset_dir=ASSET_DIR,",
                "        legacy_config_paths=LEGACY_PATHS,",
                "        cli_overrides=cli_overrides,",
                "    )",
                "",
                "",
                "def get_state_dir() -> Path:",
                f'    """Return ~/.harness-ai-kit/state/{cli_id}/, creating if needed."""',
                "    return state_dir(ASSET_ID)",
                "",
            ]
        ),
        encoding="utf-8",
    )

    # -- data/config.defaults.yaml -------------------------------------------
    data_dir = package_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "config.defaults.yaml").write_text(
        "\n".join(
            [
                "$schema: harness-ai-kit-config/v1",
                "",
                "config: []",
                "# Populate with asset-specific config keys as needed.",
                "# See config-governance.md \u00a73.1 for the format specification.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    return load_cli_record(cli_root)
