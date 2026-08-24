from __future__ import annotations

import tempfile
import unittest
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pypi_release_verify as verify


class PyPIReleaseVerifyTests(unittest.TestCase):
    def local_artifacts(self) -> dict[str, str]:
        with tempfile.TemporaryDirectory() as temp_dir:
            artifact = Path(temp_dir) / "example-1.0.0-py3-none-any.whl"
            artifact.write_bytes(b"wheel")
            return verify.artifact_hashes([artifact])

    def test_missing_remote_version_can_publish(self) -> None:
        with patch.object(verify, "fetch_release", return_value=None):
            result = verify.verify_release("pypi", "example", "1.0.0", self.local_artifacts(), phase="preflight")
        self.assertEqual(result["status"], "publish")
        self.assertTrue(result["should_publish"])

    def test_matching_remote_version_is_idempotent(self) -> None:
        local = self.local_artifacts()
        payload = {"urls": [{"filename": name, "digests": {"sha256": digest}} for name, digest in local.items()]}
        with patch.object(verify, "fetch_release", return_value=payload):
            result = verify.verify_release("pypi", "example", "1.0.0", local, phase="preflight")
        self.assertEqual(result["status"], "already-published")
        self.assertFalse(result["should_publish"])

    def test_different_hash_for_existing_version_fails_closed(self) -> None:
        local = self.local_artifacts()
        payload = {"urls": [{"filename": name, "digests": {"sha256": "0" * 64}} for name in local]}
        with patch.object(verify, "fetch_release", return_value=payload):
            with self.assertRaisesRegex(RuntimeError, "immutable version collision"):
                verify.verify_release("pypi", "example", "1.0.0", local, phase="preflight")

    def test_existing_testpypi_release_can_satisfy_presence_gate(self) -> None:
        with patch.object(verify, "fetch_release", return_value={"urls": []}):
            result = verify.verify_release("testpypi", "example", "1.0.0", self.local_artifacts(), phase="presence")
        self.assertEqual(result["status"], "present")
        self.assertFalse(result["should_publish"])

    def test_missing_testpypi_release_fails_presence_gate(self) -> None:
        with patch.object(verify, "fetch_release", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "absent from testpypi"):
                verify.verify_release("testpypi", "example", "1.0.0", self.local_artifacts(), phase="presence")


if __name__ == "__main__":
    unittest.main()
