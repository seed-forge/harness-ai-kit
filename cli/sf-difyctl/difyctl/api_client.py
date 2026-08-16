from __future__ import annotations

import json
import mimetypes
import os
import uuid
from dataclasses import dataclass
from urllib import error, request


@dataclass(frozen=True)
class ApiResult:
    status_code: int
    payload: dict[str, object] | list[object] | None
    text: str


def get_json(base_url: str, app_api_key: str, path: str, timeout_seconds: int) -> ApiResult:
    normalized_base = base_url.rstrip("/")
    normalized_path = path if path.startswith("/") else f"/{path}"
    req = request.Request(
        f"{normalized_base}{normalized_path}",
        headers={
            "Authorization": f"Bearer {app_api_key}",
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            text = response.read().decode("utf-8")
            payload = json.loads(text) if text else None
            return ApiResult(status_code=response.status, payload=payload, text=text)
    except error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        payload = json.loads(text) if text else None
        return ApiResult(status_code=exc.code, payload=payload, text=text)


def post_json(base_url: str, app_api_key: str, path: str, body: dict, timeout_seconds: int) -> ApiResult:
    """POST JSON to a Dify /v1 app endpoint using the app-* service token (Bearer)."""
    normalized_base = base_url.rstrip("/")
    normalized_path = path if path.startswith("/") else f"/{path}"
    data_bytes = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        f"{normalized_base}{normalized_path}",
        data=data_bytes,
        headers={
            "Authorization": f"Bearer {app_api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            text = response.read().decode("utf-8")
            payload = json.loads(text) if text else None
            return ApiResult(status_code=response.status, payload=payload, text=text)
    except error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        payload = json.loads(text) if text else None
        return ApiResult(status_code=exc.code, payload=payload, text=text)
    except OSError as exc:
        return ApiResult(status_code=0, payload=None, text=f"Network error: {exc}")


def post_sse(base_url: str, app_api_key: str, path: str, body: dict, timeout_seconds: int, on_chunk=None) -> ApiResult:
    """POST with response_mode=streaming and aggregate the SSE stream.

    Dify agent-chat apps only support streaming. This reads the ``data:`` SSE
    events and concatenates the ``answer`` chunks into a single result payload
    ``{answer, conversation_id, message_id, events}``. On an ``error`` event or
    HTTP error, returns a non-2xx ApiResult carrying the error payload. When
    ``on_chunk`` is provided, it is called with each answer chunk as it arrives
    (live streaming), while the aggregated answer is still returned.
    """
    normalized_base = base_url.rstrip("/")
    normalized_path = path if path.startswith("/") else f"/{path}"
    stream_body = dict(body)
    stream_body["response_mode"] = "streaming"
    data_bytes = json.dumps(stream_body, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        f"{normalized_base}{normalized_path}",
        data=data_bytes,
        headers={
            "Authorization": f"Bearer {app_api_key}",
            "Accept": "text/event-stream",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            answer_parts: list[str] = []
            conversation_id = None
            message_id = None
            events = 0
            for raw in response:
                line = raw.decode("utf-8", errors="replace").strip()
                if not line or not line.startswith("data:"):
                    continue
                chunk = line[5:].strip()
                if not chunk:
                    continue
                try:
                    ev = json.loads(chunk)
                except Exception:
                    continue
                events += 1
                etype = ev.get("event")
                if etype in ("message", "agent_message"):
                    piece = str(ev.get("answer", "") or "")
                    answer_parts.append(piece)
                    if on_chunk and piece:
                        try:
                            on_chunk(piece)
                        except Exception:
                            pass
                conversation_id = ev.get("conversation_id") or conversation_id
                message_id = ev.get("message_id") or ev.get("id") or message_id
                if etype == "error":
                    return ApiResult(status_code=400, payload=ev, text=chunk)
            return ApiResult(
                status_code=200,
                payload={"answer": "".join(answer_parts), "conversation_id": conversation_id, "message_id": message_id, "events": events},
                text="",
            )
    except error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        payload = json.loads(text) if text else None
        return ApiResult(status_code=exc.code, payload=payload, text=text)
    except OSError as exc:
        return ApiResult(status_code=0, payload=None, text=f"Network error: {exc}")


def request_v1(method, base_url, app_api_key, path, body=None, timeout_seconds=30):
    """Generic /v1 JSON request (GET/POST/DELETE/PATCH) with app-* Bearer token."""
    normalized_base = base_url.rstrip("/")
    normalized_path = path if path.startswith("/") else f"/{path}"
    data_bytes = None
    headers = {"Authorization": f"Bearer {app_api_key}", "Accept": "application/json"}
    if body is not None:
        data_bytes = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = request.Request(f"{normalized_base}{normalized_path}", data=data_bytes, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            text = response.read().decode("utf-8")
            payload = json.loads(text) if text else None
            return ApiResult(status_code=response.status, payload=payload, text=text)
    except error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        payload = json.loads(text) if text else None
        return ApiResult(status_code=exc.code, payload=payload, text=text)
    except OSError as exc:
        return ApiResult(status_code=0, payload=None, text=f"Network error: {exc}")


def _encode_multipart(fields, file_field, file_path):
    """Build a multipart/form-data body. Returns (content_type, body_bytes)."""
    boundary = "----difyctl" + uuid.uuid4().hex
    crlf = "\r\n"
    parts = []
    for key, value in (fields or {}).items():
        parts.append(("--" + boundary + crlf).encode())
        parts.append((f'Content-Disposition: form-data; name="{key}"' + crlf + crlf).encode())
        parts.append((str(value) + crlf).encode())
    filename = os.path.basename(file_path)
    ctype = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    with open(file_path, "rb") as fh:
        file_bytes = fh.read()
    parts.append(("--" + boundary + crlf).encode())
    parts.append((f'Content-Disposition: form-data; name="{file_field}"; filename="{filename}"' + crlf).encode())
    parts.append((f"Content-Type: {ctype}" + crlf + crlf).encode())
    parts.append(file_bytes)
    parts.append(crlf.encode())
    parts.append(("--" + boundary + "--" + crlf).encode())
    return f"multipart/form-data; boundary={boundary}", b"".join(parts)


def post_multipart(base_url, app_api_key, path, file_path, fields=None, file_field="file", timeout_seconds=120):
    """POST a multipart/form-data file upload (/v1/files/upload, /v1/audio-to-text)."""
    normalized_base = base_url.rstrip("/")
    normalized_path = path if path.startswith("/") else f"/{path}"
    content_type, body_bytes = _encode_multipart(fields or {}, file_field, file_path)
    req = request.Request(
        f"{normalized_base}{normalized_path}",
        data=body_bytes,
        headers={"Authorization": f"Bearer {app_api_key}", "Accept": "application/json", "Content-Type": content_type},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            text = response.read().decode("utf-8")
            payload = json.loads(text) if text else None
            return ApiResult(status_code=response.status, payload=payload, text=text)
    except error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        payload = json.loads(text) if text else None
        return ApiResult(status_code=exc.code, payload=payload, text=text)
    except OSError as exc:
        return ApiResult(status_code=0, payload=None, text=f"Network error: {exc}")


def post_binary(base_url, app_api_key, path, body, out_path, timeout_seconds=120):
    """POST JSON and save a binary response (e.g. /v1/text-to-audio) to out_path.

    Returns ApiResult; on success payload carries {out_path, bytes, content_type}.
    """
    normalized_base = base_url.rstrip("/")
    normalized_path = path if path.startswith("/") else f"/{path}"
    data_bytes = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        f"{normalized_base}{normalized_path}",
        data=data_bytes,
        headers={"Authorization": f"Bearer {app_api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            raw = response.read()
            ctype = response.headers.get("Content-Type", "")
            if "application/json" in ctype:
                text = raw.decode("utf-8", errors="replace")
                return ApiResult(status_code=response.status, payload=json.loads(text) if text else None, text=text)
            with open(out_path, "wb") as fh:
                fh.write(raw)
            return ApiResult(status_code=response.status, payload={"out_path": out_path, "bytes": len(raw), "content_type": ctype}, text="")
    except error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        payload = json.loads(text) if text else None
        return ApiResult(status_code=exc.code, payload=payload, text=text)
    except OSError as exc:
        return ApiResult(status_code=0, payload=None, text=f"Network error: {exc}")

