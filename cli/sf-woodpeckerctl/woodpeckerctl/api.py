"""Woodpecker CI REST API 客户端。

API 文档: https://woodpecker-ci.org/docs/usage/api
Base: /api

覆盖（Woodpecker v3.12 实测：嵌套 owner/name 路径会 SPA fallback，必须 by-id + /pipelines）:
- GET  /api/repos                    列出仓库（含 inactive）
- POST /api/repos?forge_remote_id=   激活仓库
- GET/PATCH/DELETE /api/repos/{repo_id}  查询/更新/停用仓库
- GET  /api/repos/{repo_id}/pipelines            列出构建
- POST /api/repos/{repo_id}/pipelines            手动触发构建
- GET/POST /api/repos/{repo_id}/pipelines/{number}  构建详情/重启
- GET  /api/repos/{repo_id}/logs/{pipeline}/{stepId}  步骤日志
- GET/POST/DELETE /api/repos/{repo_id}/secrets[/{key}]  secret 管理
- GET  /api/queue/info               队列状态（注意：/api/queue 会 SPA fallback）
- GET  /api/agents                   Agent 列表
- GET  /api/user                     当前用户信息
"""
from __future__ import annotations

import json
import sys
import urllib.request
from typing import Any

from .config import resolve_config


def _headers(args) -> dict[str, str]:
    cfg = resolve_config(args)
    headers = {"Accept": "application/json"}
    if cfg["token"]:
        headers["Authorization"] = f"Bearer {cfg['token']}"
    return headers


def _api_base(args) -> str:
    cfg = resolve_config(args)
    return f"{cfg['server']}/api"


def _get(url: str, headers: dict[str, str], timeout: int = 15) -> Any:
    """GET request with error handling."""
    req = urllib.request.Request(url)
    for k, v in headers.items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            try:
                return json.loads(body)
            except json.JSONDecodeError:
                print(
                    "Woodpecker API returned a non-JSON response; possible SPA fallback: "
                    f"{url}",
                    file=sys.stderr,
                )
                sys.exit(1)
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode()[:300]
        except Exception:
            pass
        print(f"Woodpecker API 错误 [{exc.code}]: {exc.reason}", file=sys.stderr)
        if body:
            print(f"  {body}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"请求失败: {exc}", file=sys.stderr)
        sys.exit(1)


def list_repos(args) -> list[dict]:
    """列出已激活的仓库。"""
    url = f"{_api_base(args)}/repos"
    return _get(url, _headers(args)) or []


def list_builds(args, owner: str, repo: str, page: int = 1) -> list[dict]:
    """列出构建。v3: by-id + /pipelines。"""
    rid = resolve_repo_id(args, owner, repo)
    url = f"{_api_base(args)}/repos/{rid}/pipelines?page={page}"
    return _get(url, _headers(args)) or []


def get_build(args, owner: str, repo: str, number: int) -> dict:
    """获取构建详情。v3: by-id + /pipelines。"""
    rid = resolve_repo_id(args, owner, repo)
    url = f"{_api_base(args)}/repos/{rid}/pipelines/{number}"
    return _get(url, _headers(args)) or {}


def get_build_logs(args, owner: str, repo: str, number: int, step_id: int) -> list[dict]:
    """获取步骤日志。Woodpecker 3.12: repo-scoped logs endpoint."""
    rid = resolve_repo_id(args, owner, repo)
    url = f"{_api_base(args)}/repos/{rid}/logs/{number}/{step_id}"
    return _get(url, _headers(args)) or []


def get_user(args) -> dict:
    """获取当前用户信息（用于 doctor）。"""
    url = f"{_api_base(args)}/user"
    return _get(url, _headers(args)) or {}


def get_repo_by_id(args, repo_id: int) -> dict:
    """通过 Woodpecker 内部 repo_id 获取仓库信息（含 full_name，用于 id→slug 解析）。"""
    url = f"{_api_base(args)}/repos/{repo_id}"
    return _get(url, _headers(args)) or {}


def resolve_repo_id(args, owner: str, name: str) -> int:
    """owner/name → Woodpecker 内部 repo_id。

    Woodpecker v3 的 /api/repos/{owner}/{name}/... 嵌套路径会落 SPA fallback（返回 HTML），
    必须用 by-id 路径。本函数通过 GET /api/repos 集合匹配 full_name 解析 id。
    """
    target = f"{owner}/{name}"
    for r in list_repos(args):
        if r.get("full_name") == target and r.get("id") is not None:
            return int(r["id"])
    print(f"error: 仓库未激活或不存在: {target}（先用 repo activate 激活）", file=sys.stderr)
    sys.exit(1)


def _post(url: str, headers: dict[str, str], data: bytes | None = None, timeout: int = 15) -> Any:
    """POST request with error handling."""
    req = urllib.request.Request(url, data=data, method="POST")
    for k, v in headers.items():
        req.add_header(k, v)
    if data is not None and "Content-Type" not in headers:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode()
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode()[:300]
        except Exception:
            pass
        print(f"Woodpecker API 错误 [{exc.code}]: {exc.reason}", file=sys.stderr)
        if body:
            print(f"  {body}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"请求失败: {exc}", file=sys.stderr)
        sys.exit(1)


def _delete(url: str, headers: dict[str, str], timeout: int = 15) -> Any:
    """DELETE request with error handling."""
    req = urllib.request.Request(url, method="DELETE")
    for k, v in headers.items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode()
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode()[:300]
        except Exception:
            pass
        print(f"Woodpecker API 错误 [{exc.code}]: {exc.reason}", file=sys.stderr)
        if body:
            print(f"  {body}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"请求失败: {exc}", file=sys.stderr)
        sys.exit(1)


def _patch(url: str, headers: dict[str, str], data: bytes | None = None, timeout: int = 15) -> Any:
    """PATCH request with error handling."""
    req = urllib.request.Request(url, data=data, method="PATCH")
    for k, v in headers.items():
        req.add_header(k, v)
    if data is not None and "Content-Type" not in headers:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode()
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode()[:300]
        except Exception:
            pass
        print(f"Woodpecker API 错误 [{exc.code}]: {exc.reason}", file=sys.stderr)
        if body:
            print(f"  {body}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"请求失败: {exc}", file=sys.stderr)
        sys.exit(1)


def restart_build(args, owner: str, repo: str, number: int) -> dict:
    """重启构建（POST 到 pipeline number 端点）。v3: by-id + /pipelines。"""
    rid = resolve_repo_id(args, owner, repo)
    url = f"{_api_base(args)}/repos/{rid}/pipelines/{number}"
    return _post(url, _headers(args)) or {}


def trigger_build(args, owner: str, repo: str, branch: str = "main", event: str = "manual") -> dict:
    """手动触发新构建（POST 到 pipelines 端点）。v3: by-id + /pipelines。"""
    from urllib.parse import urlencode
    rid = resolve_repo_id(args, owner, repo)
    qs = urlencode({"branch": branch, "event": event})
    url = f"{_api_base(args)}/repos/{rid}/pipelines?{qs}"
    return _post(url, _headers(args)) or {}


def activate_repo(args, forge_remote_id: int) -> dict:
    """激活仓库。POST /api/repos?forge_remote_id=<gitea_repo_id>"""
    url = f"{_api_base(args)}/repos?forge_remote_id={forge_remote_id}"
    return _post(url, _headers(args)) or {}


def deactivate_repo(args, repo_id: int) -> None:
    """停用仓库。DELETE /api/repos/<wp_repo_id>"""
    url = f"{_api_base(args)}/repos/{repo_id}"
    _delete(url, _headers(args))


def update_repo(args, repo_id: int, fields: dict) -> dict:
    """修改仓库配置。PATCH /api/repos/<wp_repo_id>"""
    url = f"{_api_base(args)}/repos/{repo_id}"
    return _patch(url, _headers(args), json.dumps(fields).encode()) or {}


def list_secrets(args, owner: str, name: str) -> list:
    """列出仓库 secrets。v3: by-id。GET /api/repos/<id>/secrets"""
    rid = resolve_repo_id(args, owner, name)
    url = f"{_api_base(args)}/repos/{rid}/secrets"
    return _get(url, _headers(args)) or []


def add_secret(args, owner: str, name: str, key: str, value: str, events: list[str]) -> dict:
    """添加仓库 secret。v3: by-id。POST /api/repos/<id>/secrets"""
    rid = resolve_repo_id(args, owner, name)
    url = f"{_api_base(args)}/repos/{rid}/secrets"
    body = {"name": key, "value": value, "event": events}
    return _post(url, _headers(args), json.dumps(body).encode()) or {}


def remove_secret(args, owner: str, name: str, key: str) -> None:
    """删除仓库 secret。v3: by-id。DELETE /api/repos/<id>/secrets/<key>"""
    rid = resolve_repo_id(args, owner, name)
    url = f"{_api_base(args)}/repos/{rid}/secrets/{key}"
    _delete(url, _headers(args))


def get_queue(args) -> dict:
    """队列状态。v3 正确端点：GET /api/queue/info（/api/queue 会 SPA fallback）。"""
    url = f"{_api_base(args)}/queue/info"
    return _get(url, _headers(args)) or {}


def list_agents(args) -> list:
    """Agent 列表。GET /api/agents"""
    url = f"{_api_base(args)}/agents"
    return _get(url, _headers(args)) or []
