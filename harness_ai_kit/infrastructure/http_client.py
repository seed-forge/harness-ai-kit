"""HTTP client and registry authentication helpers.

Uses ``httpx`` instead of ``urllib`` for better timeout handling,
connection pooling, and error messages.  Re-raises errors as
``urllib.error.HTTPError`` / ``urllib.error.URLError`` so that
existing callers continue to work during the transition.
"""
from __future__ import annotations

import io
import os
import urllib.error
import urllib.request
from base64 import b64encode
from pathlib import Path

import httpx
import yaml


def slash_join(base_url: str, *parts: str) -> str:
    """Join URL path segments, stripping extra slashes."""
    base = base_url.rstrip("/")
    suffix = "/".join(part.strip("/") for part in parts if part)
    return f"{base}/{suffix}" if suffix else base


def _registry_credentials_from_config() -> tuple[str | None, str | None]:
    """Read publish credentials from the unified config.yaml.

    The provider-neutral ``publish.registry`` block is the canonical schema.
    The legacy ``assets.nexusctl`` lookup remains only as a compatibility
    bridge for existing private installations and can be removed after their
    config files migrate.
    """
    try:
        from harness_ai_kit.infrastructure.config_io import default_config_path

        config_path = default_config_path()
        if not config_path.is_file():
            return None, None
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        publish = payload.get("publish") or {}
        if isinstance(publish, dict):
            registry = publish.get("registry") or publish.get("credentials") or {}
            if isinstance(registry, dict):
                username = str(registry.get("username") or registry.get("user") or "").strip() or None
                password = str(registry.get("password") or "").strip() or None
                if username and password:
                    return username, password

        # Compatibility bridge for pre-migration private config files.
        assets = payload.get("assets") or {}
        legacy = assets.get("nexusctl") if isinstance(assets, dict) else None
        if isinstance(legacy, dict):
            username = str(legacy.get("user") or "").strip() or None
            password = str(legacy.get("password") or "").strip() or None
            return username, password
        return None, None
    except Exception:  # noqa: BLE001 - credential lookup must never crash publish flows
        return None, None


def _registry_credentials() -> tuple[str | None, str | None]:
    """Resolve registry credentials: config.yaml first (source of truth), env fallback."""
    username, password = _registry_credentials_from_config()
    if username and password:
        return username, password
    username = os.environ.get("HARNESS_AI_KIT_REGISTRY_USERNAME") or os.environ.get("TWINE_USERNAME")
    password = os.environ.get("HARNESS_AI_KIT_REGISTRY_PASSWORD") or os.environ.get("TWINE_PASSWORD")
    return username or None, password or None


def registry_auth_headers() -> dict[str, str]:
    """Return HTTP Basic-Auth headers for registry uploads.

    Reads credentials from ``~/.harness-ai-kit/config.yaml`` (``publish.registry``,
    source of truth), falling back to ``HARNESS_AI_KIT_REGISTRY_USERNAME`` /
    ``HARNESS_AI_KIT_REGISTRY_PASSWORD`` (then ``TWINE_USERNAME`` /
    ``TWINE_PASSWORD``) for CI/CD automation.
    """
    username, password = _registry_credentials()
    if not username or not password:
        return {}
    token = b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {token}"}


def skill_registry_headers() -> dict[str, str]:
    """Alias for :func:`registry_auth_headers` (skill registry uses the same creds)."""
    return registry_auth_headers()


def skill_registry_write_ready() -> bool:
    """Return True when both registry username and password are set."""
    username, password = _registry_credentials()
    return bool(username and password)


def http_request(
    url: str,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    data: bytes | None = None,
    timeout: int = 30,
) -> bytes:
    """Perform an HTTP request via httpx and return the response body.

    Raises ``urllib.error.HTTPError`` for HTTP 4xx/5xx responses and
    ``urllib.error.URLError`` for connection failures, so existing
    ``except urllib.error.*`` clauses continue to work.
    """
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.request(method, url, headers=headers, content=data)
            response.raise_for_status()
            return response.content
    except httpx.HTTPStatusError as exc:
        raise urllib.error.HTTPError(
            url=str(exc.request.url),
            code=exc.response.status_code,
            msg=str(exc.response.reason_phrase),
            hdrs=dict(exc.response.headers),
            fp=io.BytesIO(exc.response.content),
        ) from exc
    except httpx.RequestError as exc:
        raise urllib.error.URLError(reason=str(exc)) from exc


def upload_file(url: str, source_path: Path, content_type: str) -> None:
    """Upload a local file to *url* via HTTP PUT."""
    http_request(
        url,
        method="PUT",
        headers={"Content-Type": content_type, **skill_registry_headers()},
        data=source_path.read_bytes(),
    )
