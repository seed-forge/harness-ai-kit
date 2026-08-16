"""Blob store management commands."""
from __future__ import annotations

import json
import sys
import urllib.request
from base64 import b64encode

from ._api import api_call, get_blobstore_api, get_base_url
from .profile import resolve_config


def _to_dict(obj) -> dict:
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if isinstance(obj, dict):
        return obj
    return {"raw": str(obj)}


def _raw_list_blobstores(args) -> list[dict]:
    """Fallback: list blob stores via raw REST API (SDK list_blobstores returns None)."""
    cfg = resolve_config(args)
    base = cfg["base_url"]
    creds = b64encode(f"{cfg['user']}:{cfg['password']}".encode()).decode()
    req = urllib.request.Request(f"{base}/service/rest/v1/blobstores")
    req.add_header("Authorization", f"Basic {creds}")
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())


def cmd_blobstore_list(args) -> int:
    # Try SDK first, fallback to raw API
    try:
        api = get_blobstore_api(args)
        result = api_call(api.list_blobstores, verbose=getattr(args, "verbose", False))
        stores = [_to_dict(s) for s in (result or [])]
    except Exception:
        stores = []
    if not stores:
        try:
            stores = _raw_list_blobstores(args)
        except Exception as exc:
            print(f"错误: 无法获取 blob store 列表: {exc}", file=sys.stderr)
            return 1
    as_json = getattr(args, "json", False)
    if as_json:
        print(json.dumps(stores, ensure_ascii=False, indent=2, default=str))
    else:
        print(f"{'名称':<30} {'类型':<10} {'可用'}")
        print("-" * 50)
        for s in stores:
            name = s.get("name", "?")
            stype = s.get("type", "?")
            avail = s.get("blobStoreAvailable", "?")
            print(f"{name:<30} {stype:<10} {avail}")
    return 0


def cmd_blobstore_create_file(args) -> int:
    api = get_blobstore_api(args)
    body = {
        "name": args.name,
        "path": args.path or f"/nexus-data/blobs/{args.name}",
        "softQuota": None,
    }
    if getattr(args, "dry_run", False):
        print("[DRY-RUN] 将创建 File blob store:")
        print(json.dumps(body, ensure_ascii=False, indent=2))
        return 0
    import nexus_api_client
    req_cls = getattr(nexus_api_client, "FileBlobStoreApiCreateRequest", None)
    if req_cls:
        req = req_cls.from_dict(body)
        api_call(api.create_blobstores_file, req)
    else:
        api_call(api.create_blobstores_file, body)
    print(f"已创建 blob store: {args.name}")
    return 0


def cmd_blobstore_delete(args) -> int:
    if not getattr(args, "yes", False):
        print(f"即将删除 blob store: {args.name}")
        print("使用 --yes 确认删除。")
        return 1
    api = get_blobstore_api(args)
    api_call(api.delete_blobstores, args.name)
    print(f"已删除 blob store: {args.name}")
    return 0
