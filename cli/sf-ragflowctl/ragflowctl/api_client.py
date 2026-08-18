"""RAGFlow HTTP API client (v0.24 OpenAPI, /api/v1, Bearer auth).

Stdlib-only (urllib) to keep ragflowctl dependency-free. Response envelope:
    {"code": 0, "data": ..., "message": "..."}
code == 0 means success.
"""
from __future__ import annotations

import json
import mimetypes
import uuid
from typing import Any
from urllib import error, parse, request


class RagflowError(RuntimeError):
    """Raised when RAGFlow returns a non-zero code or transport fails."""


class RagflowClient:
    def __init__(self, base_url: str, api_key: str, timeout: int = 60) -> None:
        if not base_url:
            raise RagflowError("base_url is empty (set assets.ragflowctl.base_url)")
        if not api_key:
            raise RagflowError("api_key is empty (set assets.ragflowctl.api_key)")
        self.base = base_url.rstrip("/")
        self.api = f"{self.base}/api/v1"
        self.api_key = api_key
        self.timeout = timeout

    # ── low-level ──────────────────────────────────────────────────────────
    def _headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        h = {"Authorization": f"Bearer {self.api_key}"}
        if extra:
            h.update(extra)
        return h

    def _request(self, method: str, path: str, *, json_body: Any = None,
                 data: bytes | None = None, headers: dict[str, str] | None = None) -> dict:
        url = f"{self.api}{path}"
        body = data
        hdrs = self._headers(headers)
        if json_body is not None:
            body = json.dumps(json_body).encode("utf-8")
            hdrs["Content-Type"] = "application/json"
        req = request.Request(url, data=body, method=method, headers=hdrs)
        try:
            with request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise RagflowError(f"HTTP {exc.code} {method} {path}: {detail}") from exc
        except OSError as exc:
            raise RagflowError(f"transport error {method} {path}: {exc}") from exc
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError as exc:
            raise RagflowError(f"non-JSON response {method} {path}: {raw[:300]}") from exc
        if isinstance(payload, dict) and payload.get("code", 0) not in (0, None):
            raise RagflowError(f"code={payload.get('code')} {method} {path}: {payload.get('message')}")
        return payload

    # ── health ─────────────────────────────────────────────────────────────
    def ping(self) -> dict:
        """Authenticated liveness: list datasets (page_size=1)."""
        return self._request("GET", "/datasets?page=1&page_size=1")

    # ── datasets ─────────────────────────────────────────────────────────────
    def dataset_list(self, name: str | None = None) -> list[dict]:
        """List datasets.

        Returns:
            Unwrapped ``data`` payload: ``list`` of dataset dicts with keys
            ``id``/``name``/``chunk_count``/``document_count``/``embedding_model``/
            ``parser_config``/``status`` etc. Empty list when none.
        """
        # NOTE: RAGFlow returns code=108 (permission) when ?name= matches nothing,
        # so we always list all and filter client-side.
        # v0.26: page_size is capped at 100 server-side (#15292).
        data = self._request("GET", "/datasets?page=1&page_size=100").get("data", []) or []
        if name:
            data = [d for d in data if d.get("name") == name]
        return data

    def dataset_create(self, name: str, *, embedding_model: str | None = None,
                       chunk_method: str = "naive") -> dict:
        """Create a dataset.

        Returns:
            Unwrapped ``data`` payload: the created dataset dict (same shape as
            ``dataset_list`` entries; new dataset inherits the tenant default
            embedding model when ``embedding_model`` is omitted).
        """
        body: dict[str, Any] = {"name": name, "chunk_method": chunk_method}
        if embedding_model:
            body["embedding_model"] = embedding_model
        return self._request("POST", "/datasets", json_body=body).get("data", {})

    def dataset_update(self, dataset_id: str, fields: dict) -> dict:
        """Update dataset fields (e.g. ``{"embedding_model": "bge-m3@inst@provider"}``).

        Returns:
            Full response envelope ``{"code", "data", "message"}`` — **not
            unwrapped** (unlike ``dataset_list``/``dataset_create``); success is
            already enforced by ``_request`` (code==0), so callers usually
            ignore the return value.
        """
        return self._request("PUT", f"/datasets/{dataset_id}", json_body=fields)

    def dataset_delete(self, dataset_ids: list[str]) -> dict:
        """Delete datasets by id list.

        Returns:
            Full response envelope ``{"code", "data", "message"}`` — **not
            unwrapped**; ``data`` is typically ``true``/``null``. Success is
            enforced by ``_request`` (code==0).
        """
        return self._request("DELETE", "/datasets", json_body={"ids": dataset_ids})

    def dataset_find(self, name: str) -> dict | None:
        """Find one dataset by exact name.

        Returns:
            The dataset dict (same shape as ``dataset_list`` entries), or
            ``None`` when no exact name match.
        """
        for ds in self.dataset_list(name=name):
            if ds.get("name") == name:
                return ds
        return None

    # ── documents ────────────────────────────────────────────────────────────
    def document_list(self, dataset_id: str) -> dict:
        """List documents of a dataset.

        Returns:
            Unwrapped ``data`` payload: ``{"docs": [...], "total": n, ...}``;
            each doc dict has ``id``/``name``/``run``/``progress``/``chunk_count``
            etc. Older servers may return a bare list — callers should use
            ``data.get("docs", data)`` defensively.
        """
        # v0.26: page_size is capped at 100 server-side (#15292).
        return self._request("GET", f"/datasets/{dataset_id}/documents?page=1&page_size=100").get("data", {})

    def document_upload(self, dataset_id: str, files: list[tuple[str, bytes]]) -> list[dict]:
        """files: list of (filename, content_bytes). Multipart field name 'file'."""
        boundary = f"----ragflowctl{uuid.uuid4().hex}"
        parts: list[bytes] = []
        for filename, content in files:
            ctype = mimetypes.guess_type(filename)[0] or "application/octet-stream"
            parts.append(f"--{boundary}\r\n".encode())
            parts.append(
                f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode()
            )
            parts.append(f"Content-Type: {ctype}\r\n\r\n".encode())
            parts.append(content)
            parts.append(b"\r\n")
        parts.append(f"--{boundary}--\r\n".encode())
        body = b"".join(parts)
        headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
        return self._request(
            "POST", f"/datasets/{dataset_id}/documents", data=body, headers=headers
        ).get("data", []) or []

    def parse_start(self, dataset_id: str, document_ids: list[str]) -> dict:
        return self._request(
            "POST", f"/datasets/{dataset_id}/chunks", json_body={"document_ids": document_ids}
        )

    def document_delete(self, dataset_id: str, document_ids: list[str]) -> dict:
        return self._request(
            "DELETE", f"/datasets/{dataset_id}/documents", json_body={"ids": document_ids}
        )

    # ── retrieval ────────────────────────────────────────────────────────────
    def retrieval(self, question: str, dataset_ids: list[str], *, top_k: int = 8,
                  similarity_threshold: float = 0.2,
                  vector_similarity_weight: float = 0.3) -> dict:
        """Run retrieval against datasets.

        Returns:
            Unwrapped ``data`` payload: ``{"chunks": [...], "doc_aggs": [...],
            "total": n}``; each chunk dict has ``content``/``similarity``/
            ``vector_similarity``/``term_similarity``/``document_id``/
            ``dataset_id`` etc.
        """
        body = {
            "question": question,
            "dataset_ids": dataset_ids,
            "page": 1,
            "page_size": top_k,
            "similarity_threshold": similarity_threshold,
            "vector_similarity_weight": vector_similarity_weight,
        }
        return self._request("POST", "/retrieval", json_body=body).get("data", {})

    # ── model providers / governance (v0.26 restful_apis: provider_api + models_api) ──
    @staticmethod
    def _q(value: str) -> str:
        return parse.quote(str(value), safe="")

    def provider_list(self, available: bool = False) -> list[dict]:
        suffix = "?available=true" if available else ""
        return self._request("GET", f"/providers{suffix}").get("data", []) or []

    def provider_add(self, provider_name: str) -> dict:
        return self._request("PUT", "/providers", json_body={"provider_name": provider_name})

    def provider_delete(self, provider: str) -> dict:
        return self._request("DELETE", f"/providers/{self._q(provider)}")

    def provider_remote_models(self, provider: str, api_key: str = "", base_url: str = "") -> list[dict]:
        qs = []
        if api_key:
            qs.append(f"api_key={self._q(api_key)}")
        if base_url:
            qs.append(f"base_url={self._q(base_url)}")
        suffix = ("?" + "&".join(qs)) if qs else ""
        return self._request("GET", f"/providers/{self._q(provider)}/models{suffix}").get("data", []) or []

    def provider_verify(self, provider: str, api_key: str, base_url: str = "") -> dict:
        return self._request("POST", f"/providers/{self._q(provider)}/connection",
                             json_body={"api_key": api_key, "base_url": base_url})

    def instance_list(self, provider: str) -> list[dict]:
        return self._request("GET", f"/providers/{self._q(provider)}/instances").get("data", []) or []

    def instance_create(self, provider: str, instance_name: str, api_key: str,
                        base_url: str = "", region: str = "", model_info: list | None = None) -> dict:
        body: dict[str, Any] = {"instance_name": instance_name, "api_key": api_key,
                                "base_url": base_url, "region": region, "model_info": model_info or []}
        return self._request("POST", f"/providers/{self._q(provider)}/instances", json_body=body)

    def instance_models(self, provider: str, instance: str) -> list[dict]:
        return self._request(
            "GET", f"/providers/{self._q(provider)}/instances/{self._q(instance)}/models"
        ).get("data", []) or []

    def instance_add_model(self, provider: str, instance: str, model_name: str, model_type: str,
                           max_tokens: int = 8192, extra: dict | None = None) -> dict:
        body: dict[str, Any] = {"model_name": model_name, "model_type": model_type,
                                "max_tokens": max_tokens, "extra": extra or {}}
        return self._request(
            "POST", f"/providers/{self._q(provider)}/instances/{self._q(instance)}/models", json_body=body
        )

    def default_models_get(self) -> dict:
        return self._request("GET", "/models/default").get("data", {}) or {}

    def default_model_set(self, model_type: str, provider: str, instance: str, model_name: str) -> dict:
        body = {"model_type": model_type, "model_provider": provider,
                "model_instance": instance, "model_name": model_name}
        return self._request("PATCH", "/models/default", json_body=body)

    # ── chat assistants (dataset-backed 知识库半径智能体) ─────────────────────
    @staticmethod
    def _list_payload(data: Any, *keys: str) -> list:
        """Normalize list endpoints: bare list OR wrapped ``{<key>: [...], total: n}``."""
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for k in keys:
                v = data.get(k)
                if isinstance(v, list):
                    return v
        return []

    def chat_list(self) -> list[dict]:
        """List chat assistants. Returns unwrapped ``data`` normalized to list of chat dicts
        (server wraps as ``{"chats": [...], "total": n}``)."""
        return self._list_payload(self._request("GET", "/chats").get("data", []), "chats")

    def chat_create(self, name: str, dataset_ids: list[str], *,
                    llm_id: str | None = None, prompt_config: dict | None = None) -> dict:
        """Create a dataset-backed chat assistant.

        Returns:
            Unwrapped ``data``: the created chat dict (id/name/dataset_ids/llm_id).
            ``llm_id`` 省略时服务端回落租户默认 chat 模型。
        """
        body: dict[str, Any] = {"name": name, "dataset_ids": dataset_ids}
        if llm_id:
            body["llm_id"] = llm_id
        if prompt_config:
            body["prompt_config"] = prompt_config
        return self._request("POST", "/chats", json_body=body).get("data", {})

    def chat_delete(self, chat_ids: list[str]) -> dict:
        """Delete chat assistants. Returns full response envelope (not unwrapped)."""
        return self._request("DELETE", "/chats", json_body={"ids": chat_ids})

    def chat_sessions_list(self, chat_id: str) -> list[dict]:
        """List sessions of a chat assistant. Returns unwrapped ``data`` normalized to list."""
        return self._list_payload(
            self._request("GET", f"/chats/{self._q(chat_id)}/sessions").get("data", []), "sessions")

    def chat_session_create(self, chat_id: str, name: str | None = None) -> dict:
        """Create a chat session. Returns unwrapped ``data``: session dict (id/name/messages)."""
        body: dict[str, Any] = {}
        if name:
            body["name"] = name
        return self._request("POST", f"/chats/{self._q(chat_id)}/sessions", json_body=body).get("data", {})

    def chat_completion(self, chat_id: str, question: str, session_id: str | None = None) -> dict:
        """Ask a chat assistant (non-streaming).

        Returns:
            Unwrapped ``data``: ``{"answer": str, "reference": {...}, ...}``。
            session_id 省略时服务端创建新会话（返回的 data 中含 session_id）。
        """
        body: dict[str, Any] = {"chat_id": chat_id, "question": question, "stream": False}
        if session_id:
            body["session_id"] = session_id
        return self._request("POST", "/chat/completions", json_body=body).get("data", {})

    # ── agents (画布智能体) ────────────────────────────────────────────────────
    def agent_list(self) -> list[dict]:
        """List agents (user_canvas). Returns unwrapped ``data`` normalized to list of agent dicts
        (server wraps as ``{"canvas": [...], "total": n}``)."""
        return self._list_payload(self._request("GET", "/agents").get("data", []), "canvas", "agents")

    def agent_templates(self) -> list[dict]:
        """List builtin agent canvas templates (deep_research 等). Returns unwrapped ``data`` normalized to list."""
        return self._list_payload(self._request("GET", "/agents/templates").get("data", []), "templates")

    def agent_create(self, title: str, dsl: dict, canvas_type: str | None = None) -> dict:
        """Create an agent from DSL dict.

        Returns:
            Unwrapped ``data`` — v0.26.4 创建成功返回 ``true``（不回新 id），
            调用方需用 ``agent_list`` 按 title 反查。
        """
        body: dict[str, Any] = {"title": title, "dsl": dsl}
        if canvas_type:
            body["canvas_type"] = canvas_type
        return self._request("POST", "/agents", json_body=body).get("data", {})

    def agent_sessions_list(self, agent_id: str) -> list[dict]:
        """List sessions of an agent. Returns unwrapped ``data`` normalized to list."""
        return self._list_payload(
            self._request("GET", f"/agents/{self._q(agent_id)}/sessions").get("data", []), "sessions")

    def agent_session_create(self, agent_id: str) -> dict:
        """Create an agent session. Returns unwrapped ``data``: session dict (id)."""
        return self._request("POST", f"/agents/{self._q(agent_id)}/sessions", json_body={}).get("data", {})

    def agent_delete(self, agent_ids: list[str]) -> list[dict]:
        """Delete agents one by one (v0.26.4 has only DELETE /agents/<id>, no bulk).

        Returns:
            list of full response envelopes, one per deleted agent.
        """
        return [self._request("DELETE", f"/agents/{self._q(a)}") for a in agent_ids]

    def agent_chat_completion(self, agent_id: str, question: str, session_id: str | None = None) -> dict:
        """Ask an agent (non-streaming).

        Returns:
            Unwrapped ``data``: ``{"answer": str, ...}``（含 session_id/reference 等）。
        """
        body: dict[str, Any] = {"agent_id": agent_id, "question": question, "stream": False}
        if session_id:
            body["session_id"] = session_id
        return self._request("POST", "/agents/chat/completions", json_body=body).get("data", {})

    # ── graph tasks (RAPTOR / GraphRAG；/index?type= 新路径，deprecated run/trace_* 在 token 下 102) ──
    def graphrag_run(self, dataset_id: str) -> dict:
        """Trigger GraphRAG build for a dataset (POST /datasets/{id}/index?type=graph). Returns full envelope."""
        return self._request("POST", f"/datasets/{self._q(dataset_id)}/index?type=graph", json_body={})

    def graphrag_trace(self, dataset_id: str) -> dict:
        """Trace GraphRAG task status (GET /datasets/{id}/index?type=graph). Returns unwrapped ``data``."""
        return self._request("GET", f"/datasets/{self._q(dataset_id)}/index?type=graph").get("data", {})

    def raptor_run(self, dataset_id: str) -> dict:
        """Trigger RAPTOR processing for a dataset (POST /datasets/{id}/index?type=raptor). Returns full envelope."""
        return self._request("POST", f"/datasets/{self._q(dataset_id)}/index?type=raptor", json_body={})

    def raptor_trace(self, dataset_id: str) -> dict:
        """Trace RAPTOR task status (GET /datasets/{id}/index?type=raptor). Returns unwrapped ``data``."""
        return self._request("GET", f"/datasets/{self._q(dataset_id)}/index?type=raptor").get("data", {})

    # ── chunks ─────────────────────────────────────────────────────────────────
    def chunk_list(self, dataset_id: str, document_id: str) -> dict:
        """List chunks of a document.

        Returns:
            Unwrapped ``data``: ``{"chunks": [...], "total": n, "doc": {...}}``。
        """
        return self._request(
            "GET", f"/datasets/{self._q(dataset_id)}/documents/{self._q(document_id)}/chunks?page=1&page_size=100"
        ).get("data", {})

    def chunk_add(self, dataset_id: str, document_id: str, content: str) -> dict:
        """Add a chunk to a document. Returns unwrapped ``data``: ``{"chunk": {...}}``（含新 id）。"""
        return self._request(
            "POST", f"/datasets/{self._q(dataset_id)}/documents/{self._q(document_id)}/chunks",
            json_body={"content": content}
        ).get("data", {})

    def chunk_update(self, dataset_id: str, document_id: str, chunk_id: str, fields: dict) -> dict:
        """Update a chunk (content/available/keywords). Returns full response envelope."""
        return self._request(
            "PATCH", f"/datasets/{self._q(dataset_id)}/documents/{self._q(document_id)}/chunks/{self._q(chunk_id)}",
            json_body=fields
        )

    def chunk_delete(self, dataset_id: str, document_id: str, chunk_ids: list[str]) -> dict:
        """Delete chunks by id list. Returns full response envelope (not unwrapped)."""
        return self._request(
            "DELETE", f"/datasets/{self._q(dataset_id)}/documents/{self._q(document_id)}/chunks",
            json_body={"chunk_ids": chunk_ids}
        )
