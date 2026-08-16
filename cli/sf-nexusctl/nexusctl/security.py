"""Nexus Security (User / Role) 管理。

使用 raw REST API 而非 SDK，因为 nexus_api_client 的 SecurityApi
在不同版本中导出名称不一致，raw 调用更可靠且行为可预测。

Nexus OSS REST API:
- GET  /service/rest/v1/security/users          列出用户
- POST /service/rest/v1/security/users          创建用户
- PUT  /service/rest/v1/security/users/{id}     更新用户
- DELETE /service/rest/v1/security/users/{id}   删除用户
- GET  /service/rest/v1/security/roles          列出角色
- POST /service/rest/v1/security/roles          创建角色
"""
from __future__ import annotations

import json
import sys
import urllib.request
from base64 import b64encode

from .profile import resolve_config


def _auth_header(args) -> str:
    """构建 Basic Auth header。"""
    cfg = resolve_config(args)
    creds = b64encode(f"{cfg['user']}:{cfg['password']}".encode()).decode()
    return f"Basic {creds}"


def _base(args) -> str:
    """返回 service/rest base URL。"""
    base = resolve_config(args)["base_url"].rstrip("/")
    if not base.endswith("/service/rest"):
        base = f"{base}/service/rest"
    return base


def _request(method: str, url: str, auth: str, body: dict | None = None, timeout: int = 15):
    """发起 HTTP 请求，返回解析后的 JSON 或 None。"""
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", auth)
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode()
            if raw:
                return json.loads(raw)
            return None
    except urllib.error.HTTPError as exc:
        body_text = ""
        try:
            body_text = exc.read().decode()[:500]
        except Exception:
            pass
        print(f"Nexus API 错误 [{exc.code}]: {exc.reason}", file=sys.stderr)
        if body_text:
            print(f"  响应体: {body_text}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"请求失败: {exc}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# User commands
# ---------------------------------------------------------------------------

def cmd_user_list(args) -> int:
    """列出所有 Nexus 用户。"""
    url = f"{_base(args)}/v1/security/users"
    auth = _auth_header(args)
    result = _request("GET", url, auth)
    users = result if isinstance(result, list) else []
    if args.json:
        print(json.dumps({"ok": True, "command": "user list", "count": len(users), "data": users}, ensure_ascii=False, indent=2))
    else:
        if not users:
            print("(no users)")
            return 0
        # Table output
        header = f"{'userId':<25} {'firstName':<15} {'lastName':<15} {'email':<30} {'status':<10} {'source':<10}"
        print(header)
        print("-" * len(header))
        for u in users:
            uid = u.get("userId", "")
            fn = u.get("firstName", "")
            ln = u.get("lastName", "")
            email = u.get("emailAddress", "")
            status = u.get("status", "")
            source = u.get("source", "")
            print(f"{uid:<25} {fn:<15} {ln:<15} {email:<30} {status:<10} {source:<10}")
    return 0


def cmd_user_create(args) -> int:
    """创建用户。"""
    body = {
        "userId": args.name,
        "firstName": args.name,
        "lastName": "",
        "emailAddress": f"{args.name}@noreply.local",
        "password": args.new_password,
        "status": "active",
        "roles": [args.role] if args.role else ["nx-anonymous"],
    }
    url = f"{_base(args)}/v1/security/users"
    auth = _auth_header(args)
    if args.dry_run:
        print("[DRY-RUN] 将创建用户:")
        print(json.dumps(body, ensure_ascii=False, indent=2))
        return 0
    _request("POST", url, auth, body)
    if args.json:
        print(json.dumps({"ok": True, "command": f"user create {args.name}", "message": f"用户 {args.name} 已创建"}, ensure_ascii=False, indent=2))
    else:
        print(f"ok: 用户 '{args.name}' 已创建 (roles: {body['roles']})")
    return 0


def cmd_user_create_readonly(args) -> int:
    """创建只读用户（自动创建角色 + 用户）。"""
    role_id = "devlab-readonly-role"
    role_name = "DevLab Readonly"
    # Step 1: Create role (ignore if exists)
    role_body = {
        "id": role_id,
        "name": role_name,
        "description": "Read-only access to all repositories for devlab-infractl",
        "privileges": [
            "nx-repository-view-*-*-browse",
            "nx-repository-view-*-*-read",
            "nx-search-read",
        ],
        "roles": [],
    }
    url_role = f"{_base(args)}/v1/security/roles"
    auth = _auth_header(args)
    if not args.dry_run:
        try:
            _request("POST", url_role, auth, role_body)
        except SystemExit:
            pass  # Role may already exist
    # Step 2: Create user
    user_body = {
        "userId": args.name,
        "firstName": "DevLab",
        "lastName": "Readonly",
        "emailAddress": f"{args.name}@noreply.local",
        "password": args.new_password,
        "status": "active",
        "roles": [role_id],
    }
    url_user = f"{_base(args)}/v1/security/users"
    if args.dry_run:
        print("[DRY-RUN] 将创建只读角色:")
        print(json.dumps(role_body, ensure_ascii=False, indent=2))
        print("[DRY-RUN] 将创建只读用户:")
        print(json.dumps(user_body, ensure_ascii=False, indent=2))
        return 0
    _request("POST", url_user, auth, user_body)
    if args.json:
        print(json.dumps({
            "ok": True,
            "command": f"user create-readonly {args.name}",
            "role": role_id,
            "message": f"只读用户 {args.name} 已创建 (role: {role_id})",
        }, ensure_ascii=False, indent=2))
    else:
        print(f"ok: 只读角色 '{role_id}' 已创建")
        print(f"ok: 只读用户 '{args.name}' 已创建 (role: {role_id})")
        print(f"   权限: browse + read (all repos), search")
    return 0


def cmd_user_delete(args) -> int:
    """删除用户。"""
    if not args.yes:
        print(f"确认删除用户 '{args.name}'？使用 --yes 确认", file=sys.stderr)
        return 1
    url = f"{_base(args)}/v1/security/users/{args.name}"
    auth = _auth_header(args)
    _request("DELETE", url, auth)
    if args.json:
        print(json.dumps({"ok": True, "command": f"user delete {args.name}", "message": f"用户 {args.name} 已删除"}, ensure_ascii=False, indent=2))
    else:
        print(f"ok: 用户 '{args.name}' 已删除")
    return 0


# ---------------------------------------------------------------------------
# Role commands
# ---------------------------------------------------------------------------

def cmd_role_list(args) -> int:
    """列出所有角色。"""
    url = f"{_base(args)}/v1/security/roles"
    auth = _auth_header(args)
    result = _request("GET", url, auth)
    roles = result if isinstance(result, list) else []
    if args.json:
        print(json.dumps({"ok": True, "command": "role list", "count": len(roles), "data": roles}, ensure_ascii=False, indent=2))
    else:
        if not roles:
            print("(no roles)")
            return 0
        header = f"{'id':<35} {'name':<35} {'description':<50}"
        print(header)
        print("-" * len(header))
        for r in roles:
            rid = r.get("id", "")
            name = r.get("name", "")
            desc = r.get("description", "")[:50]
            print(f"{rid:<35} {name:<35} {desc:<50}")
    return 0
