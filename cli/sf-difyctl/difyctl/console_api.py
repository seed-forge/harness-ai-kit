from __future__ import annotations

import json
import re
from dataclasses import dataclass
from urllib import error, request

from difyctl.api_client import ApiResult


@dataclass(frozen=True)
class ConsoleAuth:
    """Console authentication credential with CSRF support.

    Dify Community Edition uses cookie-based auth with CSRF protection.
    The credential string can be:

    - A plain Bearer token (Cloud/SaaS Admin API Key)
    - A cookie header from ``difyctl provider login`` containing
      ``access_token=...; csrf_token=...``
    """

    type: str  # "bearer" | "cookie"
    value: str  # raw token or full cookie string
    csrf_token: str = ""  # extracted CSRF JWT (cookie auth only)

    @staticmethod
    def detect(raw: str) -> ConsoleAuth:
        """Auto-detect auth type and extract CSRF token if present.

        - Contains ``csrf_token=`` → cookie with CSRF
        - Starts with ``session=`` → cookie (legacy)
        - Otherwise → bearer
        """
        stripped = raw.strip()
        if not stripped:
            raise ValueError("console_key must not be empty")

        # Extract csrf_token if present in a cookie-style value
        csrf_match = re.search(r"csrf_token=([^;]+)", stripped)
        csrf = csrf_match.group(1).strip() if csrf_match else ""

        if stripped.lower().startswith("session="):
            return ConsoleAuth(type="cookie", value=stripped, csrf_token=csrf)
        if "access_token=" in stripped:
            return ConsoleAuth(type="cookie", value=stripped, csrf_token=csrf)
        return ConsoleAuth(type="bearer", value=stripped, csrf_token="")


# Dify CE v1.13.3 Console API endpoints (verified 2026-06-09)
CONSOLE_ENDPOINTS = {
    "providers": "/console/api/workspaces/current/model-providers",
    "provider": "/console/api/workspaces/current/model-providers/{provider}",
    # The actual endpoint for adding/updating a model with credentials
    "model_credentials": "/console/api/workspaces/current/model-providers/{provider}/models/credentials",
    "models_list": "/console/api/workspaces/current/model-providers/{provider}/models",
    "model_validate": "/console/api/workspaces/current/model-providers/{provider}/models/credentials/validate",
    # App DSL import/export (Dify app_dsl_service; stable across 1.13.x-1.16.x)
    "apps_imports": "/console/api/apps/imports",
    "apps_import_confirm": "/console/api/apps/imports/{import_id}/confirm",
    "app_export": "/console/api/apps/{app_id}/export?include_secret=false",
    "apps_list": "/console/api/apps?page={page}&limit={limit}",
    # App service API keys (Dify /v1 access tokens; stable across 1.13.x-1.16.x)
    "app_api_keys": "/console/api/apps/{app_id}/api-keys",
    "app_api_key_delete": "/console/api/apps/{app_id}/api-keys/{api_key_id}",
    # App lifecycle (rename/description via PUT, delete)
    "app_detail": "/console/api/apps/{app_id}",
    # Publish the current draft workflow (workflow / advanced-chat apps)
    "app_workflow_publish": "/console/api/apps/{app_id}/workflows/publish",
    # Knowledge bases (datasets) — Console API, cookie auth (stable 1.13.x-1.16.x)
    "datasets": "/console/api/datasets?page={page}&limit={limit}",
    "dataset_detail": "/console/api/datasets/{dataset_id}",
    "dataset_documents": "/console/api/datasets/{dataset_id}/documents?page={page}&limit={limit}",
    "dataset_api_keys": "/console/api/datasets/api-keys",
    "app_annotations": "/console/api/apps/{app_id}/annotations?page={page}&limit={limit}",
    # Tool plugins (builtin tool providers, e.g. MCP SSE) — routes verified against
    # Dify CE 1.16.1 api/controllers/console/workspace/tool_providers.py (2026-08-12)
    "tool_providers": "/console/api/workspaces/current/tool-providers?type={type}",
    "tool_builtin_info": "/console/api/workspaces/current/tool-provider/builtin/{provider}/info",
    "tool_builtin_tools": "/console/api/workspaces/current/tool-provider/builtin/{provider}/tools",
    "tool_builtin_credentials": "/console/api/workspaces/current/tool-provider/builtin/{provider}/credentials",
    "tool_builtin_add": "/console/api/workspaces/current/tool-provider/builtin/{provider}/add",
    "tool_builtin_update": "/console/api/workspaces/current/tool-provider/builtin/{provider}/update",
    "tool_builtin_delete": "/console/api/workspaces/current/tool-provider/builtin/{provider}/delete",
}

# HTTP status codes that SHOULD trigger browser fallback
FALLBACK_ELIGIBLE_STATUSES: frozenset[int] = frozenset({408, 429, 500, 502, 503, 504})


def should_fallback(status_code: int) -> bool:
    """Determine whether an HTTP status code triggers browser fallback."""
    return status_code in FALLBACK_ELIGIBLE_STATUSES or status_code >= 500


def _build_headers(auth: ConsoleAuth) -> dict[str, str]:
    headers: dict[str, str] = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if auth.type == "cookie":
        headers["Cookie"] = auth.value
        if auth.csrf_token:
            headers["X-CSRF-Token"] = auth.csrf_token
    else:
        headers["Authorization"] = f"Bearer {auth.value}"
    return headers


def _build_url(base_url: str, path: str) -> str:
    normalized_base = base_url.rstrip("/")
    normalized_path = path if path.startswith("/") else f"/{path}"
    return f"{normalized_base}{normalized_path}"


def _safe_json(text: str):
    """Parse JSON, returning None on empty or non-JSON bodies (never raises).

    Dify error responses are sometimes HTML (e.g. Flask 404 pages); callers must
    not crash on those.
    """
    if not text:
        return None
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        return None


def _parse_response(response) -> ApiResult:
    text = response.read().decode("utf-8", errors="replace")
    return ApiResult(status_code=response.status, payload=_safe_json(text), text=text)


def _parse_error(exc: error.HTTPError) -> ApiResult:
    text = exc.read().decode("utf-8", errors="replace")
    return ApiResult(status_code=exc.code, payload=_safe_json(text), text=text)


# ── Credential form schema defaults for openai_api_compatible (Dify CE v1.13.3) ──

def build_model_credential_payload(
    *,
    model_name: str,
    model_type: str = "llm",
    credential_name: str = "default",
    api_key: str = "",
    endpoint_url: str = "",
    context_size: str = "128000",
    max_tokens: str = "128000",
    mode: str = "chat",
    function_calling_type: str = "tool_call",
    display_name: str = "",
) -> dict[str, object]:
    """Build the full credential_form_schemas payload required by Dify CE.

    This matches the 30-field schema that Dify v1.13.3 expects for
    openai_api_compatible model credentials.
    """
    model_display = display_name or f"newapi-{model_name}"
    return {
        "credentials": {
            "display_name": model_display,
            "api_key": api_key,
            "language": "zh",
            "initial_prompt": None,
            "endpoint_url": endpoint_url,
            "endpoint_model_name": model_name,
            "mode": mode,
            "context_size": str(context_size),
            "max_chunks": "1",
            "encoding_format": "not_set",
            "vision_support": "no_support",
            "max_tokens_to_sample": str(max_tokens),
            "agent_thought_support": "not_supported",
            "compatibility_mode": "strict",
            "token_param_name": "auto",
            "function_calling_type": function_calling_type,
            "stream_function_calling": "not_supported",
            "video_support": "no_support",
            "audio_support": "no_support",
            "document_support": "no_support",
            "structured_output_support": "supported",
            "stream_mode_auth": "not_use",
            "stream_mode_delimiter": "\\n\\n",
            "voices": "alloy",
            "document_prefix": "",
            "query_prefix": "",
            "__model_name": model_name,
            "__model_type": model_type,
        },
        "name": credential_name,
        "model": model_name,
        "model_type": model_type,
    }


class ConsoleApiClient:
    """HTTP client for Dify Console API with dual auth + CSRF support."""

    def __init__(self, base_url: str, auth: ConsoleAuth, timeout_seconds: int = 20, retries: int = 2) -> None:
        self.base_url = base_url
        self.auth = auth
        self.timeout_seconds = timeout_seconds
        self.retries = retries

    @staticmethod
    def _should_retry(method: str, status_code: int) -> bool:
        """Retry only when it is SAFE. GET is idempotent (retry any transient).
        429/503 are server load-shedding with no side-effect (retry any method).
        Ambiguous 5xx on writes are NOT retried to avoid double create/update.
        """
        if status_code in (429, 503):
            return True
        if method.upper() == "GET" and (status_code == 0 or status_code >= 500):
            return True
        return False

    def _request(self, method: str, path: str, body: dict[str, object] | None = None) -> ApiResult:
        import time as _time

        url = _build_url(self.base_url, path)
        data_bytes: bytes | None = None
        if body is not None:
            data_bytes = json.dumps(body, ensure_ascii=False).encode("utf-8")
        attempts = max(1, self.retries + 1)
        result = ApiResult(status_code=0, payload=None, text="no attempt")
        for attempt in range(attempts):
            req = request.Request(url, data=data_bytes, headers=_build_headers(self.auth), method=method)
            try:
                with request.urlopen(req, timeout=self.timeout_seconds) as response:
                    result = _parse_response(response)
            except error.HTTPError as exc:
                result = _parse_error(exc)
            except OSError as exc:
                result = ApiResult(status_code=0, payload=None, text=f"Network error: {exc}")
            if attempt < attempts - 1 and self._should_retry(method, result.status_code):
                _time.sleep(0.5 * (attempt + 1))
                continue
            return result
        return result

    def get(self, path: str) -> ApiResult:
        return self._request("GET", path)

    def post(self, path: str, body: dict[str, object] | None = None) -> ApiResult:
        return self._request("POST", path, body or {})

    def patch(self, path: str, body: dict[str, object] | None = None) -> ApiResult:
        return self._request("PATCH", path, body or {})

    def delete(self, path: str) -> ApiResult:
        return self._request("DELETE", path)

    def resolve_path(self, endpoint_key: str, **kwargs: str) -> str:
        template = CONSOLE_ENDPOINTS[endpoint_key]
        return template.format(**kwargs)

    # ── High-level provider operations ──

    def provider_list(self) -> ApiResult:
        """List all registered model providers."""
        return self.get(CONSOLE_ENDPOINTS["providers"])

    def provider_add_model(
        self,
        provider: str,
        model_name: str,
        model_type: str = "llm",
        credential_name: str = "default",
        api_key: str = "",
        endpoint_url: str = "",
    ) -> ApiResult:
        """Add a model with credentials to a customizable-model provider.

        *provider* is the full provider path, e.g.
        ``langgenius/openai_api_compatible/openai_api_compatible``.
        """
        path = self.resolve_path("model_credentials", provider=provider)
        payload = build_model_credential_payload(
            model_name=model_name,
            model_type=model_type,
            credential_name=credential_name,
            api_key=api_key,
            endpoint_url=endpoint_url,
        )
        return self.post(path, payload)

    def provider_list_models(self, provider: str, model_type: str = "llm") -> ApiResult:
        """List configured models for a provider."""
        path = self.resolve_path("models_list", provider=provider)
        return self.get(f"{path}?model_type={model_type}")

    def provider_validate_model(
        self,
        provider: str,
        model_name: str,
        model_type: str = "llm",
        api_key: str = "",
        endpoint_url: str = "",
    ) -> ApiResult:
        """Validate model credentials without saving."""
        path = self.resolve_path("model_validate", provider=provider)
        payload = build_model_credential_payload(
            model_name=model_name,
            model_type=model_type,
            api_key=api_key,
            endpoint_url=endpoint_url,
        )
        return self.post(path, payload)

    def provider_remove_model(self, provider: str, model_name: str) -> ApiResult:
        """Remove a model from a provider."""
        path = self.resolve_path("models_list", provider=provider)
        return self.delete(f"{path}/{model_name}")

    # ── App DSL import / export operations ──

    def app_import_dsl(self, yaml_content: str, app_id: str = "") -> ApiResult:
        """Import a DSL document via the Console API.

        When ``app_id`` is empty, creates a NEW app. When ``app_id`` is set,
        imports INTO that existing app (update-in-place: replaces its draft
        without creating a duplicate). Uses ``mode: yaml-content`` so no
        multipart upload is needed. Response payload carries ``id`` (import id),
        ``status`` (``completed`` / ``completed-with-warnings`` / ``pending`` /
        ``failed``), ``app_id``, and ``imported_dsl_version``.
        """
        body: dict[str, object] = {"mode": "yaml-content", "yaml_content": yaml_content}
        if app_id:
            body["app_id"] = app_id
        return self.post(CONSOLE_ENDPOINTS["apps_imports"], body)

    def app_import_confirm(self, import_id: str) -> ApiResult:
        """Confirm a pending DSL import (version-mismatch approval)."""
        path = self.resolve_path("apps_import_confirm", import_id=import_id)
        return self.post(path, {})

    def app_export_dsl(self, app_id: str) -> ApiResult:
        """Export an app's DSL YAML. Payload shape: ``{"data": "<yaml>"}``."""
        path = self.resolve_path("app_export", app_id=app_id)
        return self.get(path)

    def apps_list(self, page: int = 1, limit: int = 100) -> ApiResult:
        """List workspace apps (paginated)."""
        path = self.resolve_path("apps_list", page=str(page), limit=str(limit))
        return self.get(path)

    # ── App service API keys + lifecycle ──

    def app_keys_list(self, app_id: str) -> ApiResult:
        """List an app's service API keys. Payload: {"data": [{id, token, created_at}]}."""
        return self.get(self.resolve_path("app_api_keys", app_id=app_id))

    def app_key_create(self, app_id: str) -> ApiResult:
        """Create a service API key. Response carries the full `app-*` token (only visible once)."""
        return self.post(self.resolve_path("app_api_keys", app_id=app_id), {})

    def app_key_delete(self, app_id: str, api_key_id: str) -> ApiResult:
        """Revoke a service API key by its id."""
        return self.delete(self.resolve_path("app_api_key_delete", app_id=app_id, api_key_id=api_key_id))

    def app_delete(self, app_id: str) -> ApiResult:
        """Delete (retire) an app via the Console API."""
        return self.delete(self.resolve_path("app_detail", app_id=app_id))

    # ── Knowledge bases (datasets) ──

    def datasets_list(self, page: int = 1, limit: int = 30) -> ApiResult:
        """List knowledge bases (datasets). Payload: {data, has_more, total, page, limit}."""
        return self.get(self.resolve_path("datasets", page=str(page), limit=str(limit)))

    def dataset_get(self, dataset_id: str) -> ApiResult:
        """Get one knowledge base's detail."""
        return self.get(self.resolve_path("dataset_detail", dataset_id=dataset_id))

    def dataset_create(self, name: str, indexing_technique: str = "high_quality", permission: str = "only_me", description: str = "") -> ApiResult:
        """Create a knowledge base. Response 201 carries the full dataset object (incl. id)."""
        body: dict[str, object] = {"name": name, "indexing_technique": indexing_technique, "permission": permission}
        if description:
            body["description"] = description
        return self.post("/console/api/datasets", body)

    def dataset_delete(self, dataset_id: str) -> ApiResult:
        """Delete a knowledge base (204 on success)."""
        return self.delete(self.resolve_path("dataset_detail", dataset_id=dataset_id))

    def dataset_documents(self, dataset_id: str, page: int = 1, limit: int = 30) -> ApiResult:
        """List documents inside a knowledge base."""
        return self.get(self.resolve_path("dataset_documents", dataset_id=dataset_id, page=str(page), limit=str(limit)))

    def dataset_api_keys(self) -> ApiResult:
        """List dataset service API keys (Bearer dataset-* tokens for the /v1 datasets API)."""
        return self.get(CONSOLE_ENDPOINTS["dataset_api_keys"])

    def app_annotations(self, app_id: str, page: int = 1, limit: int = 20) -> ApiResult:
        """List an app's annotations (Q&A cache / human-labeled replies)."""
        return self.get(self.resolve_path("app_annotations", app_id=app_id, page=str(page), limit=str(limit)))

    def app_get(self, app_id: str) -> ApiResult:
        """Fetch app detail (name/icon/description) via GET /console/api/apps/{id}."""
        return self.get(self.resolve_path("app_detail", app_id=app_id))

    def app_update(self, app_id: str, fields: dict[str, object]) -> ApiResult:
        """Update app name/description/icon via PUT /console/api/apps/{id}."""
        return self._request("PUT", self.resolve_path("app_detail", app_id=app_id), fields)

    def app_workflow_publish(self, app_id: str) -> ApiResult:
        """Publish the current draft workflow (required before /v1 run for workflow/advanced-chat apps)."""
        return self.post(self.resolve_path("app_workflow_publish", app_id=app_id), {})

    # ── Tool plugins (builtin tool providers / MCP servers) ──

    def tool_providers_list(self, provider_type: str = "builtin") -> ApiResult:
        """List tool providers of a type (builtin/api/workflow/mcp/model)."""
        return self.get(self.resolve_path("tool_providers", type=provider_type))

    def tool_builtin_info(self, provider: str) -> ApiResult:
        """Provider detail (label, schema, team credentials summary)."""
        return self.get(self.resolve_path("tool_builtin_info", provider=provider))

    def tool_builtin_tools(self, provider: str) -> ApiResult:
        """List tools a provider exposes (for MCP SSE: discovered MCP server tools)."""
        return self.get(self.resolve_path("tool_builtin_tools", provider=provider))

    def tool_builtin_credentials(self, provider: str) -> ApiResult:
        """List credential entries of a provider. Payload: list of {id, name, credential_type, is_default, credentials}."""
        return self.get(self.resolve_path("tool_builtin_credentials", provider=provider))

    def tool_builtin_credential_add(
        self,
        provider: str,
        credentials: dict[str, object],
        *,
        name: str = "",
        credential_type: str = "api-key",
    ) -> ApiResult:
        """Create a credential entry (BuiltinToolAddPayload: credentials/name/type)."""
        body: dict[str, object] = {"credentials": credentials, "type": credential_type}
        if name:
            body["name"] = name
        return self.post(self.resolve_path("tool_builtin_add", provider=provider), body)

    def tool_builtin_credential_update(
        self,
        provider: str,
        credential_id: str,
        *,
        credentials: dict[str, object] | None = None,
        name: str = "",
    ) -> ApiResult:
        """Update an existing credential entry (BuiltinToolUpdatePayload: credential_id/credentials/name)."""
        body: dict[str, object] = {"credential_id": credential_id}
        if credentials is not None:
            body["credentials"] = credentials
        if name:
            body["name"] = name
        return self.post(self.resolve_path("tool_builtin_update", provider=provider), body)

    def tool_builtin_credential_delete(self, provider: str, credential_id: str) -> ApiResult:
        """Delete a credential entry (BuiltinToolCredentialDeletePayload: credential_id)."""
        return self.post(self.resolve_path("tool_builtin_delete", provider=provider), {"credential_id": credential_id})
