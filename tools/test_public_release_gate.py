from __future__ import annotations

import json
import hashlib
import os
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import public_release_gate as gate


class PublicReleaseGateTests(unittest.TestCase):
    def make_package(self, root: Path, *, cli_version: str = "1.2.3", init_version: str = "1.2.3") -> dict[str, object]:
        package_root = root / "cli" / "example"
        package_root.mkdir(parents=True)
        (package_root / "pyproject.toml").write_text(
            "[project]\nname = 'example-cli'\nversion = '1.2.3'\n\n[project.scripts]\nexamplectl = 'example.cli:main'\n",
            encoding="utf-8",
        )
        (package_root / "cli.json").write_text(json.dumps({"version": cli_version}), encoding="utf-8")
        (package_root / "example").mkdir()
        (package_root / "example" / "__init__.py").write_text(
            f'__version__ = "{init_version}"\n', encoding="utf-8"
        )
        return {
            "id": "example-cli",
            "package_name": "example-cli",
            "source_path": "cli/example",
            "public": True,
            "ci": True,
            "publish": False,
            "version_sources": ["pyproject", "cli_json", "init"],
            "test_command": "{python} -c \"print('ok')\"",
            "entrypoint": "examplectl",
            "smoke_command": "{entrypoint} --help",
        }

    def test_package_versions_reports_metadata_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            package = self.make_package(Path(temp_dir), init_version="1.2.4")
            versions, errors = gate.package_versions(Path(temp_dir), package)
        self.assertEqual(versions["pyproject"], ["1.2.3"])
        self.assertIn("version-drift", errors)

    def test_inventory_keeps_held_package_version_drift_visible(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            package = self.make_package(Path(temp_dir), init_version="1.2.4")
            package["ci"] = False
            package["hold_reason"] = "test suite is not release-ready"
            records = gate.inventory(Path(temp_dir), [package])
        self.assertEqual(records[0]["hold_reason"], "test suite is not release-ready")
        self.assertIn("version-drift", records[0]["metadata_errors"])

    def test_release_surface_scan_reports_location_without_secret_value(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            private_address = ".".join(("10", "1", "2", "3"))
            (root / "config.txt").write_text(f"endpoint = '{private_address}'\n", encoding="utf-8")
            findings = gate.scan_release_surface(root)
        self.assertEqual(findings, [{"path": "config.txt", "line": "1", "rule": "private-network"}])

    def test_release_surface_scan_ignores_package_build_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            metadata = root / "example.egg-info"
            metadata.mkdir()
            private_address = ".".join(("10", "1", "2", "3"))
            (metadata / "PKG-INFO").write_text(f"endpoint = '{private_address}'\n", encoding="utf-8")
            findings = gate.scan_release_surface(root)
        self.assertEqual(findings, [])

    def test_release_surface_scan_ignores_staging_temp_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            temporary_state = root / ".tmp" / "release-test" / "venv"
            temporary_state.mkdir(parents=True)
            private_address = ".".join(("10", "1", "2", "3"))
            (temporary_state / "pyvenv.cfg").write_text(
                f"endpoint = '{private_address}'\n", encoding="utf-8"
            )
            findings = gate.scan_release_surface(root)
        self.assertEqual(findings, [])

    def test_matrix_rejects_duplicate_package_names(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first = self.make_package(root)
            second = dict(first, id="another-cli")
            matrix = {"public": {"repository": "seed-forge/harness-ai-kit"}, "packages": [first, second]}
            errors = gate.validate_matrix(root, matrix)
        self.assertIn("duplicate package name: example-cli", errors)

    def test_matrix_rejects_dependency_in_same_release_wave(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = self.make_package(root)
            base.update({"id": "base", "package_name": "base", "publish": True, "release_wave": 0, "depends_on": []})
            cli = dict(base, id="cli", package_name="cli", depends_on=["base"])
            matrix = {"public": {"repository": "seed-forge/harness-ai-kit"}, "packages": [base, cli]}
            errors = gate.validate_matrix(root, matrix)
        self.assertIn("publish dependency must be in an earlier release wave: cli -> base", errors)

    def test_matrix_rejects_ci_package_without_wheel_smoke_command(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            package = self.make_package(root)
            package.pop("smoke_command")
            matrix = {"public": {"repository": "seed-forge/harness-ai-kit"}, "packages": [package]}
            errors = gate.validate_matrix(root, matrix)
        self.assertIn("ci package is missing smoke_command: example-cli", errors)

    def test_matrix_rejects_ci_package_without_entrypoint(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            package = self.make_package(root)
            package.pop("entrypoint")
            matrix = {"public": {"repository": "seed-forge/harness-ai-kit"}, "packages": [package]}
            errors = gate.validate_matrix(root, matrix)
        self.assertIn("ci package is missing entrypoint: example-cli", errors)

    def test_matrix_rejects_ci_entrypoint_missing_from_pyproject(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            package = self.make_package(root)
            package["entrypoint"] = "otherctl"
            matrix = {"public": {"repository": "seed-forge/harness-ai-kit"}, "packages": [package]}
            errors = gate.validate_matrix(root, matrix)
        self.assertIn("ci entrypoint is not declared by pyproject: example-cli", errors)

    def test_matrix_requires_core_public_release_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            package = self.make_package(root)
            package.update({"id": "harness-ai-kit", "package_name": "harness-ai-kit", "source_path": "."})
            matrix = {"public": {"repository": "seed-forge/harness-ai-kit"}, "packages": [package]}
            errors = gate.validate_matrix(root, matrix)

        self.assertIn(
            "harness-ai-kit included_paths must list the core public release inputs",
            errors,
        )

    def test_matrix_accepts_complete_core_public_release_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "harness_ai_kit").mkdir()
            (root / "cli" / "harness-ai-kit").mkdir(parents=True)
            (root / "docs").mkdir()
            for relative_path in (
                "cli/harness-ai-kit/cli.json",
                "README.md",
                "README.zh-CN.md",
                "INSTALL.md",
                "CATALOG.md",
                "ROADMAP.md",
                "CHANGELOG.md",
                "LICENSE",
                "docs/quickstart.md",
            ):
                contents = "release input\n"
                if relative_path in gate.CORE_PUBLIC_README_MARKERS:
                    contents = "\n".join(gate.CORE_PUBLIC_README_MARKERS[relative_path]) + "\n"
                (root / relative_path).write_text(contents, encoding="utf-8")
            (root / "pyproject.toml").write_text(
                "[project]\nname = 'harness-ai-kit'\nversion = '1.2.3'\n\n"
                "[project.scripts]\nharness-ai-kit = 'harness_ai_kit.main:main'\n",
                encoding="utf-8",
            )
            package = {
                "id": "harness-ai-kit",
                "package_name": "harness-ai-kit",
                "source_path": ".",
                "public": True,
                "ci": True,
                "publish": False,
                "version_sources": ["pyproject"],
                "test_command": "{python} -c \"print('ok')\"",
                "entrypoint": "harness-ai-kit",
                "smoke_command": "{entrypoint} --version",
                "included_paths": sorted(gate.CORE_PUBLIC_RELEASE_INPUTS),
            }
            matrix = {"public": {"repository": "seed-forge/harness-ai-kit"}, "packages": [package]}
            errors = gate.validate_matrix(root, matrix)
            package["included_paths"].append("docs")
            recursive_errors = gate.validate_matrix(root, matrix)

        self.assertEqual(errors, [])
        self.assertIn(
            "harness-ai-kit included_paths must not include staging snapshot metadata: "
            "docs/oss-public-release.yaml, docs/oss-staging-manifest.json",
            recursive_errors,
        )

    def test_matrix_rejects_simplified_core_readme(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "README.md").write_text("# harness-ai-kit\n## Quick Start\n", encoding="utf-8")
            (root / "README.zh-CN.md").write_text("# harness-ai-kit\n## 快速开始\n", encoding="utf-8")
            errors = gate.core_public_documentation_errors(root)

        self.assertIn(
            "harness-ai-kit documentation contract missing sections in README.md: "
            "## Why, ## The REMIX Method, ## No Lock-In, ## Team Workflow, ## Architecture, "
            "## Documentation, ## License",
            errors,
        )
        self.assertIn(
            "harness-ai-kit documentation contract missing sections in README.zh-CN.md: "
            "## 为什么需要它, ## REMIX 方法论, ## 不锁定内容, ## 团队协作, ## 架构, "
            "## 文档入口, ## 许可证",
            errors,
        )

    def test_run_command_replaces_python_placeholder_without_windows_path_escaping(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ok, returncode = gate.run_command('{python} -c "print(123)"', Path(temp_dir))
        self.assertTrue(ok)
        self.assertEqual(returncode, 0)

    def test_run_command_replaces_quoted_entrypoint_placeholder(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ok, returncode = gate.run_command(
                '"{entrypoint}" -c "print(123)"',
                Path(temp_dir),
                token_replacements={"entrypoint": sys.executable},
            )
        self.assertTrue(ok)
        self.assertEqual(returncode, 0)

    def test_public_pip_environment_ignores_local_python_and_indexes(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "PYTHONPATH": "private-source",
                "PYTHONHOME": "private-python",
                "PIP_INDEX_URL": "https://private.example/simple",
                "PIP_EXTRA_INDEX_URL": "https://extra.example/simple",
                "PIP_TRUSTED_HOST": "private.example",
            },
            clear=False,
        ):
            environment = gate.public_pip_environment()
        for key in ("PYTHONPATH", "PYTHONHOME", "PIP_INDEX_URL", "PIP_EXTRA_INDEX_URL", "PIP_TRUSTED_HOST"):
            self.assertNotIn(key, environment)
        self.assertEqual(environment["PIP_CONFIG_FILE"], os.devnull)

    def test_source_test_install_uses_local_core_and_public_index(self) -> None:
        root = Path("C:/staging")
        source = root / "cli" / "example"
        command = gate.source_test_install_command(Path("C:/venv/python.exe"), root, source)

        self.assertEqual(command[:9], [
            str(Path("C:/venv/python.exe")),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-input",
            "--index-url",
            gate.PUBLIC_PYPI_SIMPLE_URL,
            "pytest",
        ])
        self.assertEqual(command[9:], ["-e", str(root), "-e", str(source)])

    def test_source_test_install_does_not_install_core_twice(self) -> None:
        root = Path("C:/staging")
        command = gate.source_test_install_command(Path("C:/venv/python.exe"), root, root)
        self.assertEqual(command.count("-e"), 1)
        self.assertEqual(command[-1], str(root))

    def test_staging_manifest_requires_immutable_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            package = self.make_package(root)
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps({"schema_version": 1, "source_revision": None, "packages": []}), encoding="utf-8")
            matrix = {
                "source_snapshot": {
                    "source_revision": None,
                    "staging_manifest": "manifest.json",
                    "staging_manifest_sha256": "0" * 64,
                }
            }
            errors = gate.verify_staging_manifest(root, matrix, [package])
        self.assertIn("source_snapshot.source_revision must be an immutable 40-character commit", errors)
        self.assertIn("staging manifest digest does not match the release matrix", errors)

    def test_staging_manifest_requires_revision_available_in_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            package = self.make_package(root)
            manifest_path = root / "manifest.json"
            manifest_path.write_text(
                json.dumps({"schema_version": 1, "source_revision": "a" * 40, "packages": []}),
                encoding="utf-8",
            )
            digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
            matrix = {
                "source_snapshot": {
                    "source_revision": "a" * 40,
                    "staging_manifest": "manifest.json",
                    "staging_manifest_sha256": digest,
                }
            }
            errors = gate.verify_staging_manifest(root, matrix, [package])
        self.assertIn("source_snapshot.source_revision is not available in this checkout", errors)

    def test_release_plan_groups_explicit_waves(self) -> None:
        matrix = {
            "packages": [
                {"id": "base", "package_name": "base", "publish": True, "release_wave": 0},
                {"id": "cli", "package_name": "cli", "publish": True, "release_wave": 1},
            ]
        }
        report = {
            "packages": [
                {"versions": {"pyproject": ["1.0.0"]}},
                {"versions": {"pyproject": ["1.0.1"]}},
            ]
        }
        plan = gate.release_plan(matrix, report)
        self.assertEqual(plan["waves"]["0"][0]["id"], "base")
        self.assertEqual(plan["waves"]["1"][0]["dist_path"], "public-release/cli")

    def test_write_github_outputs_preserves_existing_values(self) -> None:
        plan = {"waves": {str(index): [] for index in range(4)}}
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "github-output"
            output.write_text("channel=testpypi\n", encoding="utf-8")
            gate.write_github_outputs(output, plan)
            content = output.read_text(encoding="utf-8")
        self.assertIn("channel=testpypi\n", content)
        self.assertIn("has_wave_0=false\n", content)

    def test_release_plan_honors_selected_package_ids(self) -> None:
        matrix = {
            "packages": [
                {"id": "base", "package_name": "base", "publish": True, "release_wave": 0},
                {"id": "cli", "package_name": "cli", "publish": True, "release_wave": 1},
            ]
        }
        report = {
            "selected_package_ids": ["base"],
            "packages": [{"versions": {"pyproject": ["1.0.0"]}}],
        }
        plan = gate.release_plan(matrix, report)
        self.assertEqual(plan["waves"]["0"][0]["id"], "base")
        self.assertEqual(plan["waves"]["1"], [])

    def test_select_packages_can_limit_release_to_wave(self) -> None:
        packages = [
            {"id": "base", "publish": True, "ci": True, "release_wave": 0},
            {"id": "cli", "publish": True, "ci": True, "release_wave": 1},
        ]
        selected = gate.select_packages(packages, "release", max_release_wave=0)
        self.assertEqual([item["id"] for item in selected], ["base"])

    def test_staging_manifest_payload_uses_package_tree_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            package = self.make_package(root)
            payload = gate.staging_manifest_payload(root, [package], "a" * 40)
        self.assertEqual(payload["source_revision"], "a" * 40)
        self.assertEqual(payload["packages"][0]["version"], "1.2.3")
        self.assertRegex(payload["packages"][0]["tree_sha256"], r"^[0-9a-f]{64}$")

    def test_package_tree_digest_ignores_generated_egg_info(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            package = self.make_package(root)
            baseline = gate.tree_sha256(root, package)
            metadata = root / "cli" / "example" / "example_cli.egg-info"
            metadata.mkdir()
            (metadata / "PKG-INFO").write_text("generated build metadata\n", encoding="utf-8")
            self.assertEqual(gate.tree_sha256(root, package), baseline)

    def test_package_tree_digest_normalizes_line_endings(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            package = self.make_package(root)
            baseline = gate.tree_sha256(root, package)
            source = root / "cli" / "example" / "README.md"
            source.write_bytes(b"line one\r\nline two\r\n")
            package["included_paths"] = ["cli/example/README.md"]
            crlf_digest = gate.tree_sha256(root, package)
            source.write_bytes(b"line one\nline two\n")
            lf_digest = gate.tree_sha256(root, package)
        self.assertNotEqual(baseline, crlf_digest)
        self.assertEqual(crlf_digest, lf_digest)

    def test_clear_previous_artifacts_retries_transient_windows_lock(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            artifact = Path(temp_dir) / "example-1.0.0.tar.gz"
            artifact.write_text("temporary artifact", encoding="utf-8")
            original_unlink = Path.unlink
            calls = 0

            def flaky_unlink(path: Path, *args, **kwargs) -> None:
                nonlocal calls
                if path == artifact and calls == 0:
                    calls += 1
                    raise PermissionError("transient file lock")
                original_unlink(path, *args, **kwargs)

            with mock.patch.object(gate.Path, "unlink", flaky_unlink), mock.patch.object(gate.time, "sleep") as sleep:
                gate.clear_previous_artifacts(Path(temp_dir), attempts=2, delay_seconds=0.01)

        self.assertFalse(artifact.exists())
        sleep.assert_called_once_with(0.01)

    def test_update_matrix_snapshot_accepts_digit_prefixed_revision(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "matrix.yaml"
            path.write_text(
                "source_snapshot:\n  source_revision: null\n  staging_manifest_sha256: null\n",
                encoding="utf-8",
            )
            gate.update_matrix_snapshot(path, "1" * 40, "2" * 64)
            content = path.read_text(encoding="utf-8")
        self.assertIn("source_revision: " + "1" * 40, content)
        self.assertIn("staging_manifest_sha256: " + "2" * 64, content)


if __name__ == "__main__":
    unittest.main()
