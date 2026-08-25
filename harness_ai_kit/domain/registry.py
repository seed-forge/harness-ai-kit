from __future__ import annotations

import json
import os
import threading
import time
from typing import Any

import httpx
from filelock import FileLock
from packaging.version import Version

from harness_ai_kit.domain.artifacts import cache_file_for_url
from harness_ai_kit.domain.identity import canonical_package_id, normalize_namespace, split_canonical_id
from harness_ai_kit.domain.manifest import SkillManifest
from harness_ai_kit.domain.manifest_io import manifest_canonical_id
from harness_ai_kit.domain.resolution import utc_now_iso


class RegistryUnavailableError(Exception):
    """Raised when the registry is unreachable (network/transport failure).

    Distinct from a "skill not found" (KeyError): a consumer with no local repo
    fallback must be able to tell "registry down / check network" apart from
    "this skill does not exist".
    """


# Lightweight retry for transient transport errors on registry index/metadata
# fetches. Consumers resolve registry-only, so a single network blip must not
# surface as "package not found".
_REGISTRY_HTTP_RETRIES = 2
_REGISTRY_RETRY_BACKOFF = 0.5
_DEFAULT_REGISTRY_CACHE_TTL = 300.0
_registry_client: httpx.Client | None = None
_registry_client_factory: Any = None
_registry_client_lock = threading.Lock()


def _shared_registry_client() -> httpx.Client:
    """Return a process-local client so registry calls reuse connections."""
    global _registry_client, _registry_client_factory
    factory = httpx.Client
    with _registry_client_lock:
        if _registry_client is None or _registry_client_factory is not factory:
            if _registry_client is not None:
                _registry_client.close()
            _registry_client = factory(timeout=30.0, follow_redirects=True)
            _registry_client_factory = factory
        return _registry_client


def registry_cache_ttl() -> float:
    """Return the online registry cache TTL in seconds.

    ``0`` disables cache reuse. Invalid values fall back to the safe default
    so a malformed environment variable cannot break sync.
    """
    raw = os.environ.get("HARNESS_AI_KIT_REGISTRY_CACHE_TTL", "")
    if not raw.strip():
        return _DEFAULT_REGISTRY_CACHE_TTL
    try:
        return max(0.0, float(raw))
    except ValueError:
        return _DEFAULT_REGISTRY_CACHE_TTL


def _online_cache_is_fresh(cache_path: Any) -> bool:
    ttl = registry_cache_ttl()
    if ttl <= 0:
        return False
    try:
        return (time.time() - cache_path.stat().st_mtime) <= ttl
    except OSError:
        return False


def registry_item_matches(item: dict[str, Any], package_ref: str) -> bool:
    namespace, package_id = split_canonical_id(package_ref)
    item_namespace = normalize_namespace(item.get("namespace"))
    item_id = str(item.get("id", "")).strip()
    item_canonical = str(item.get("canonical_id", "")).strip()
    target_canonical = canonical_package_id(package_id, namespace)
    if item_canonical and item_canonical == target_canonical:
        return True
    if namespace is not None:
        return item_id == package_id and item_namespace == namespace
    return item_id == package_id


def registry_headers() -> dict[str, str]:
    # Delegate to the single source of truth (infrastructure.http_client):
    # ~/.harness-ai-kit/config.yaml publish.registry credentials first, then
    # HARNESS_AI_KIT_REGISTRY_* / TWINE_* env fallback for CI/CD.
    from harness_ai_kit.infrastructure.http_client import registry_auth_headers

    return registry_auth_headers()


def http_request_json(
    url: str,
    *,
    method: str = "GET",
    offline: bool = False,
    cache_suffix: str,
    data: bytes | None = None,
    force_refresh: bool = False,
) -> dict[str, Any]:
    cache_path = cache_file_for_url(url, cache_suffix)
    lock = FileLock(str(cache_path) + ".lock", timeout=30)
    with lock:
        if offline:
            if not cache_path.exists():
                raise FileNotFoundError(f"Offline cache miss: {url}")
            return json.loads(cache_path.read_text(encoding="utf-8"))
        if not force_refresh and cache_path.exists() and _online_cache_is_fresh(cache_path):
            try:
                return json.loads(cache_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                # A partial/corrupt cache must not block a fresh request.
                pass
        last_exc: Exception | None = None
        for attempt in range(_REGISTRY_HTTP_RETRIES + 1):
            try:
                client = _shared_registry_client()
                response = client.request(method, url, headers=registry_headers(), content=data)
                if response.status_code == 404 and method == "GET":
                    return {"skills": []}
                response.raise_for_status()
                cache_path.write_text(response.text, encoding="utf-8")
                return response.json()
            except (httpx.TransportError, httpx.TimeoutException) as exc:
                last_exc = exc
                if attempt < _REGISTRY_HTTP_RETRIES:
                    time.sleep(_REGISTRY_RETRY_BACKOFF * (2 ** attempt))
                    continue
        raise RegistryUnavailableError(
            f"Registry unreachable after {_REGISTRY_HTTP_RETRIES + 1} attempts: {url} ({last_exc})"
        ) from last_exc


def http_request_bytes(
    url: str,
    *,
    offline: bool = False,
    cache_suffix: str,
    force_refresh: bool = False,
) -> bytes:
    cache_path = cache_file_for_url(url, cache_suffix)
    lock = FileLock(str(cache_path) + ".lock", timeout=30)
    with lock:
        if offline:
            if not cache_path.exists():
                raise FileNotFoundError(f"Offline cache miss: {url}")
            return cache_path.read_bytes()
        if not force_refresh and cache_path.exists() and _online_cache_is_fresh(cache_path):
            try:
                return cache_path.read_bytes()
            except OSError:
                pass
        last_exc: Exception | None = None
        for attempt in range(_REGISTRY_HTTP_RETRIES + 1):
            try:
                client = _shared_registry_client()
                response = client.get(url, headers=registry_headers())
                response.raise_for_status()
                cache_path.write_bytes(response.content)
                return response.content
            except (httpx.TransportError, httpx.TimeoutException) as exc:
                last_exc = exc
                if attempt < _REGISTRY_HTTP_RETRIES:
                    time.sleep(_REGISTRY_RETRY_BACKOFF * (2 ** attempt))
                    continue
        raise RegistryUnavailableError(
            f"Registry unreachable after {_REGISTRY_HTTP_RETRIES + 1} attempts: {url} ({last_exc})"
        ) from last_exc


def load_registry_index(index_url: str, *, offline: bool = False, force_refresh: bool = False) -> dict[str, Any]:
    return http_request_json(index_url, offline=offline, cache_suffix="index.json", force_refresh=force_refresh)


def registry_skill_version_entry(index_payload: dict[str, Any], skill_id: str, version: str | None = None) -> dict[str, Any]:
    for item in index_payload.get("skills", []):
        if not registry_item_matches(item, skill_id):
            continue
        candidate_version = version or item.get("latest_version")
        for entry in item.get("versions", []):
            if entry.get("version") == candidate_version:
                return entry
        raise KeyError(f"Version not found for skill {skill_id}: {candidate_version}")
    raise KeyError(f"Skill not found in registry index: {skill_id}")


def registry_metadata_url(entry: dict[str, Any]) -> str:
    explicit = str(entry.get("metadata_url", "")).strip()
    if explicit:
        return explicit
    artifact_url = str(entry.get("artifact_url") or entry.get("url") or "").strip()
    if not artifact_url:
        raise KeyError("Registry entry is missing artifact_url.")
    return f"{artifact_url.rsplit('/', 1)[0]}/skill.json"


def registry_artifact_url(entry: dict[str, Any]) -> str:
    explicit = str(entry.get("artifact_url") or entry.get("url") or "").strip()
    if not explicit:
        raise KeyError("Registry entry is missing artifact_url.")
    return explicit


def download_registry_manifest(index_url: str, skill_id: str, version: str | None = None, *, offline: bool = False, force_refresh: bool = False) -> tuple[SkillManifest, dict[str, Any]]:
    index_payload = load_registry_index(index_url, offline=offline, force_refresh=force_refresh)
    entry = registry_skill_version_entry(index_payload, skill_id, version)
    payload = http_request_json(registry_metadata_url(entry), offline=offline, cache_suffix="skill.json", force_refresh=force_refresh)
    return SkillManifest.model_validate(payload), entry


def download_registry_artifact(index_url: str, skill_id: str, version: str | None = None, *, offline: bool = False, force_refresh: bool = False) -> tuple[bytes, dict[str, Any]]:
    index_payload = load_registry_index(index_url, offline=offline, force_refresh=force_refresh)
    entry = registry_skill_version_entry(index_payload, skill_id, version)
    return http_request_bytes(registry_artifact_url(entry), offline=offline, cache_suffix="zip", force_refresh=force_refresh), entry


def update_registry_index_payload(
    current_index: dict[str, Any],
    *,
    manifest: SkillManifest,
    artifact_url: str,
    metadata_url: str,
    checksum: str,
    source: str,
) -> dict[str, Any]:
    namespace = normalize_namespace(manifest.namespace)
    canonical_id = manifest_canonical_id(manifest)
    visibility = getattr(manifest, "visibility", None) or ""
    owners = list(getattr(manifest, "owners", []) or [])
    license_name = getattr(manifest, "license", "") or ""
    homepage = getattr(manifest, "homepage", "") or ""
    repository = getattr(manifest, "repository", "") or ""
    skill_entry = {
        "namespace": namespace,
        "canonical_id": canonical_id,
        "version": manifest.version,
        "artifact_url": artifact_url,
        "metadata_url": metadata_url,
        "checksum": checksum,
        "source": source,
        "visibility": visibility,
        "status": manifest.status,
        "published_at": utc_now_iso(),
    }
    skills = list(current_index.get("skills", []))
    replaced = False
    for item in skills:
        if not registry_item_matches(item, canonical_id):
            continue
        versions = [entry for entry in item.get("versions", []) if entry.get("version") != manifest.version]
        versions.append(skill_entry)
        versions.sort(key=lambda version_entry: Version(str(version_entry["version"])))
        item["namespace"] = namespace
        item["canonical_id"] = canonical_id
        item["name"] = manifest.name
        item["latest_version"] = manifest.version
        item["summary"] = manifest.summary
        item["description"] = manifest.description
        item["owners"] = owners
        item["license"] = license_name
        item["homepage"] = homepage
        item["repository"] = repository
        item["visibility"] = visibility
        item["status"] = manifest.status
        item["versions"] = versions
        replaced = True
        break
    if not replaced:
        skills.append(
            {
                "namespace": namespace,
                "id": manifest.id,
                "canonical_id": canonical_id,
                "name": manifest.name,
                "latest_version": manifest.version,
                "summary": manifest.summary,
                "description": manifest.description,
                "owners": owners,
                "license": license_name,
                "homepage": homepage,
                "repository": repository,
                "visibility": visibility,
                "status": manifest.status,
                "versions": [skill_entry],
            }
        )
    return {"skills": sorted(skills, key=lambda item: (str(item.get("namespace") or ""), str(item["id"])))}


def upload_bytes(url: str, payload: bytes, content_type: str) -> None:
    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        response = client.put(url, headers={"Content-Type": content_type, **registry_headers()}, content=payload)
        response.raise_for_status()
