from __future__ import annotations

import io
import json
import tempfile
import unittest
import sys
from datetime import timedelta
from email.message import Message
from pathlib import Path
from urllib.error import HTTPError
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pypi_release_verify as verify


class FakeResponse:
    def __init__(self, payload: object) -> None:
        self._body = json.dumps(payload).encode("utf-8")

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self._body


def not_found(url: str = "https://test.pypi.org/pypi/example/1.0.0/json", retry_after: str | None = None) -> HTTPError:
    headers = Message()
    if retry_after is not None:
        headers["Retry-After"] = retry_after
    return HTTPError(url, 404, "not found", headers, io.BytesIO())


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

    def test_first_404_then_success(self) -> None:
        local = self.local_artifacts()
        payload = {"urls": [{"filename": name, "digests": {"sha256": digest}} for name, digest in local.items()]}
        sleeps: list[float] = []
        with patch.object(verify, "urlopen", side_effect=[not_found(), FakeResponse(payload)]):
            result = verify.fetch_release(
                "testpypi", "example", "1.0.0", max_attempts=2, max_total_seconds=10, sleep=sleeps.append
            )
        self.assertEqual(result, payload)
        self.assertEqual(sleeps, [2.0])

    def test_pending_then_success(self) -> None:
        local = self.local_artifacts()
        payload = {"urls": [{"filename": name, "digests": {"sha256": digest}} for name, digest in local.items()]}
        with patch.object(verify, "urlopen", side_effect=[FakeResponse({"urls": []}), FakeResponse(payload)]):
            result = verify.fetch_release(
                "testpypi", "example", "1.0.0", max_attempts=2, max_total_seconds=10, sleep=lambda _delay: None
            )
        self.assertEqual(result, payload)

    def test_retry_after_seconds_is_preferred_to_exponential_backoff(self) -> None:
        sleeps: list[float] = []
        with patch.object(verify, "urlopen", side_effect=[not_found(retry_after="7"), FakeResponse({"urls": []})]):
            with self.assertRaisesRegex(RuntimeError, "still pending"):
                verify.fetch_release(
                    "testpypi", "example", "1.0.0", max_attempts=2, max_total_seconds=10,
                    sleep=sleeps.append,
                )
        self.assertEqual(sleeps, [7.0])

    def test_retry_after_http_date_is_parsed(self) -> None:
        now = verify.datetime(2026, 8, 24, 0, 0, tzinfo=verify.timezone.utc)
        value = verify.email.utils.format_datetime(now + timedelta(seconds=5), usegmt=True)
        self.assertEqual(verify.parse_retry_after(value, now=now), 5.0)

    def test_retry_timeout_fails_with_diagnostic(self) -> None:
        ticks = [0.0]

        def clock() -> float:
            return ticks[0]

        def advance(seconds: float) -> None:
            ticks[0] += seconds

        with patch.object(verify, "urlopen", return_value=FakeResponse({"urls": []})):
            with self.assertRaisesRegex(RuntimeError, r"still pending.*after 2 attempt\(s\).*metadata has no complete"):
                verify.fetch_release(
                    "testpypi", "example", "1.0.0", max_attempts=10, max_total_seconds=3,
                    base_backoff_seconds=2, max_backoff_seconds=30, sleep=advance, clock=clock,
                )


if __name__ == "__main__":
    unittest.main()
