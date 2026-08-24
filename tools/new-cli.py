#!/usr/bin/env python3
"""Scaffold a new harness-ai-kit companion CLI under cli/sf-<name>/.

Usage:
    python tools/new-cli.py <name> [--summary "one-line summary"]

Creates a package skeleton (pyproject.toml, README.md, cli.json, <name>/cli.py
with a `main` entry). PyPI project name is `sf-<name>`; the installed command
is `<name>`. The package remains unpublished until it has a reviewed entry in
docs/oss-public-release.yaml.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CLI_ROOT = REPO_ROOT / "cli"


def die(msg: str) -> None:
    raise SystemExit(f"error: {msg}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Scaffold a new sf-<name> CLI package.")
    ap.add_argument("name", help="Command/module name, e.g. 'fooctl' (no sf- prefix).")
    ap.add_argument("--summary", default="", help="One-line summary for pyproject/cli.json.")
    args = ap.parse_args(argv)

    name = args.name.strip()
    if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
        die(f"invalid name '{name}': use lowercase letters, digits, underscore; start with a letter.")
    if name.startswith("sf-") or name.startswith("sf_"):
        die("pass the bare name without the sf- prefix (it is added automatically).")

    pkg_dir = CLI_ROOT / f"sf-{name}"
    if pkg_dir.exists():
        die(f"{pkg_dir} already exists.")

    summary = args.summary or f"{name} — a harness-ai-kit companion CLI."
    mod = pkg_dir / name
    mod.mkdir(parents=True)

    (pkg_dir / "pyproject.toml").write_text(
        f"""[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "sf-{name}"
version = "0.1.0"
description = "{summary}"
readme = "README.md"
requires-python = ">=3.10"
license = {{ text = "Apache-2.0" }}
authors = [
  {{ name = "SeedForge" }}
]
dependencies = [
  "harness-ai-kit>=0.2.0"
]

[project.urls]
Homepage = "https://github.com/seed-forge/harness-ai-kit"
Repository = "https://github.com/seed-forge/harness-ai-kit"

[project.scripts]
{name} = "{name}.cli:main"

[tool.setuptools.packages.find]
include = ["{name}", "{name}.*"]
""",
        encoding="utf-8",
    )

    (pkg_dir / "README.md").write_text(
        f"""# sf-{name}

{summary}

## Install

```bash
pip install sf-{name}
{name} --help
```

## License

Apache-2.0
""",
        encoding="utf-8",
    )

    (pkg_dir / "cli.json").write_text(
        json.dumps(
            {
                "namespace": "community",
                "id": name,
                "name": name,
                "owner": "seedforge",
                "version": "0.1.0",
                "status": "trial",
                "package_type": "cli",
                "summary": summary,
                "package_name": f"sf-{name}",
                "install_type": "python-package",
                "publish_paths": [f"cli/sf-{name}"],
                "companion_docs": {"usage": "README.md"},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    (mod / "__init__.py").write_text(f'"""sf-{name} — harness-ai-kit companion CLI."""\n', encoding="utf-8")
    (mod / "cli.py").write_text(
        f'''"""Entry point for the {name} command."""
from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="{name}", description="{summary}")
    parser.add_argument("--version", action="version", version="{name} 0.1.0")
    parser.add_subparsers(dest="command")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 0
    # TODO: dispatch subcommands here
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
        encoding="utf-8",
    )

    print(f"Created {pkg_dir.relative_to(REPO_ROOT)}")
    print(f"  PyPI package: sf-{name}   command: {name}")
    print("Next: implement tests, then add a reviewed release-matrix entry before creating a v<version> tag.")
    print(f"Before the first release, configure a Trusted Publisher for sf-{name} (workflow release.yml, matching pypi/testpypi environment).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
