from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from harness_ai_kit.domain.doctor_checks import doctor_versions_results, public_catalog_path


class PublicDoctorVersionTests(unittest.TestCase):
    def test_private_catalog_is_not_mistaken_for_the_public_layout(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            (repo_root / "catalog.md").write_text("# Internal catalog\n", encoding="utf-8")

            self.assertIsNone(public_catalog_path(repo_root))

    def test_public_staging_uses_the_public_catalog_contract(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]

        self.assertEqual(public_catalog_path(repo_root), repo_root / "CATALOG.md")

        errors = [
            result
            for result in doctor_versions_results(repo_root)
            if result["status"] == "error"
        ]
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
