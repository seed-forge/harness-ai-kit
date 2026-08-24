from __future__ import annotations

import json
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import public_release_gate as gate


class PublicReleaseGateTests(unittest.TestCase):
    def make_package(self, root: Path, *, cli_version: str = "1.2.3", init_version: str = "1.2.3") -> dict[str, object]:
        package_root = root / "cli" / "example"
        package_root.mkdir(parents=True)
        (package_root / "pyproject.toml").write_text(
            "[project]\nname = 'example-cli'\nversion = '1.2.3'\n",
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

    def test_matrix_rejects_non_string_install_command(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            package = self.make_package(root)
            package["install_command"] = True
            matrix = {"public": {"repository": "seed-forge/harness-ai-kit"}, "packages": [package]}
            errors = gate.validate_matrix(root, matrix)
        self.assertIn("install_command must be a string when set: example-cli", errors)

    def test_run_command_replaces_python_placeholder_without_windows_path_escaping(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ok, returncode = gate.run_command('{python} -c "print(123)"', Path(temp_dir))
        self.assertTrue(ok)
        self.assertEqual(returncode, 0)

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
        self.assertEqual(plan["waves"]["1"][0]["dist_path"], "dist/cli")

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
