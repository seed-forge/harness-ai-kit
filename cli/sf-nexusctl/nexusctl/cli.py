from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from ._api import (
    FORMAT_HELP,
    api_call,
    get_base_url,
    get_repo_api,
    get_status_api,
    resolve_format,
    resolve_request_class,
)
from .blobstore import cmd_blobstore_create_file, cmd_blobstore_delete, cmd_blobstore_list
from .cleanup import cmd_cleanup_get, cmd_cleanup_list
from .inventory import diff_inventory, export_inventory, print_summary
from .presets import PRESETS, get_preset, list_presets
from .security import (
    cmd_role_list,
    cmd_user_create,
    cmd_user_create_readonly,
    cmd_user_delete,
    cmd_user_list,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _emit(payload: dict, as_json: bool) -> int:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    else:
        ok = payload.get("ok", False)
        msg = payload.get("message", "")
        status = "ok" if ok else "failed"
        print(f"{payload.get('command', '?')}: {status}" + (f" — {msg}" if msg else ""))
    return 0 if payload.get("ok") else 1


def _to_dict(obj) -> dict:
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if isinstance(obj, dict):
        return obj
    return {"raw": str(obj)}


def _verbose(args) -> bool:
    return getattr(args, "verbose", False)


# ---------------------------------------------------------------------------
# Repo body builders
# ---------------------------------------------------------------------------

def _build_proxy_body(fmt: str, name: str, remote_url: str, blob_store: str | None,
                      cleanup_policies: list[str] | None,
                      distribution: str | None = None,
                      flat: bool = False) -> dict:
    sdk_fmt = resolve_format(fmt)
    if blob_store is None or blob_store == "default":
        blob_store = f"{sdk_fmt}-proxy-store"
    body = {
        "name": name,
        "online": True,
        "proxy": {"remoteUrl": remote_url, "contentMaxAge": 1440, "metadataMaxAge": 1440},
        "storage": {"blobStoreName": blob_store, "strictContentTypeValidation": True},
        "negativeCache": {"enabled": True, "timeToLive": 1440},
        "httpClient": {"autoBlock": True, "blocked": False},
    }
    if cleanup_policies:
        body["cleanup"] = {"policyNames": cleanup_policies}
    if sdk_fmt == "apt":
        apt_attrs: dict = {"flat": flat}
        if distribution:
            apt_attrs["distribution"] = distribution
            apt_attrs["enforceDistribution"] = False
        body["apt"] = apt_attrs
    return body


def _build_hosted_body(fmt: str, name: str, blob_store: str, write_policy: str) -> dict:
    sdk_fmt = resolve_format(fmt)
    if blob_store == "default":
        blob_store = f"{sdk_fmt}-hosted-store"
    return {
        "name": name,
        "online": True,
        "storage": {"blobStoreName": blob_store, "strictContentTypeValidation": True, "writePolicy": write_policy.upper()},
    }


def _build_group_body(fmt: str, name: str, members: list[str], blob_store: str) -> dict:
    return {
        "name": name,
        "online": True,
        "storage": {"blobStoreName": blob_store, "strictContentTypeValidation": True},
        "group": {"memberNames": members},
    }


# ---------------------------------------------------------------------------
# SDK dispatch
# ---------------------------------------------------------------------------

def _create_repo_via_sdk(api, fmt: str, repo_type: str, body: dict):
    sdk_fmt = resolve_format(fmt)
    method_name = f"create_{sdk_fmt}_{repo_type}_repository"
    method = getattr(api, method_name, None)
    if method is None:
        print(f"错误: SDK 不支持 {fmt}/{repo_type} 组合", file=sys.stderr)
        sys.exit(2)
    cls = resolve_request_class(sdk_fmt, repo_type)
    if cls:
        return method(cls.from_dict(body))
    return method(body)


def _update_repo_via_sdk(api, fmt: str, repo_type: str, name: str, body: dict):
    sdk_fmt = resolve_format(fmt)
    method_name = f"update_{sdk_fmt}_{repo_type}_repository"
    method = getattr(api, method_name, None)
    if method is None:
        print(f"错误: SDK 不支持 update {fmt}/{repo_type}", file=sys.stderr)
        sys.exit(2)
    cls = resolve_request_class(sdk_fmt, repo_type)
    if cls:
        return method(name, cls.from_dict(body))
    return method(name, body)


def _get_repo_detail(api, fmt: str, repo_type: str, name: str):
    sdk_fmt = resolve_format(fmt)
    method_name = f"get_{sdk_fmt}_{repo_type}_repository"
    method = getattr(api, method_name, None)
    if method is None:
        return None
    try:
        return method(name)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

def cmd_doctor(args) -> int:
    status_api = get_status_api(args)
    base = get_base_url(args)
    result = api_call(status_api.list_status, verbose=_verbose(args))
    data = _to_dict(result) if result else {}
    return _emit({"command": "doctor", "profile": args.profile, "base_url": base, "ok": True, "data": data}, args.json)


def cmd_repo_list(args) -> int:
    api = get_repo_api(args)
    base = get_base_url(args)
    result = api_call(api.list_repository_settings, verbose=_verbose(args))
    repos = [_to_dict(r) for r in (result or [])]
    return _emit({"command": "repo list", "base_url": base, "ok": True, "count": len(repos), "data": repos}, args.json)


def cmd_repo_get(args) -> int:
    api = get_repo_api(args)
    fmt = resolve_format(args.format)
    result = _get_repo_detail(api, fmt, args.type, args.name)
    if result is None:
        # Fallback: search in full list
        all_repos = api_call(api.list_repository_settings, verbose=_verbose(args))
        result = next((r for r in (all_repos or []) if getattr(r, "name", None) == args.name), None)
    if result is None:
        return _emit({"command": f"repo get {args.name}", "ok": False, "message": f"未找到仓库: {args.name}"}, args.json)
    return _emit({"command": f"repo get {args.format}/{args.type}/{args.name}", "ok": True, "data": _to_dict(result)}, args.json)


def cmd_repo_create_proxy(args) -> int:
    cleanup = args.cleanup_policy.split(",") if args.cleanup_policy else None
    distribution = getattr(args, "distribution", None)
    flat = getattr(args, "flat", False)
    body = _build_proxy_body(args.format, args.name, args.remote_url, args.blob_store, cleanup, distribution, flat)
    if args.dry_run:
        print("[DRY-RUN] 将创建 proxy 仓库:")
        print(json.dumps(body, ensure_ascii=False, indent=2))
        return 0
    api = get_repo_api(args)
    api_call(_create_repo_via_sdk, api, args.format, "proxy", body, verbose=_verbose(args))
    base = get_base_url(args)
    return _emit({"command": f"repo create-proxy {args.format}/{args.name}", "ok": True, "message": f"已创建: {base}/repository/{args.name}/"}, args.json)


def cmd_repo_create_hosted(args) -> int:
    body = _build_hosted_body(args.format, args.name, args.blob_store, args.write_policy)
    if args.dry_run:
        print("[DRY-RUN] 将创建 hosted 仓库:")
        print(json.dumps(body, ensure_ascii=False, indent=2))
        return 0
    api = get_repo_api(args)
    api_call(_create_repo_via_sdk, api, args.format, "hosted", body, verbose=_verbose(args))
    base = get_base_url(args)
    return _emit({"command": f"repo create-hosted {args.format}/{args.name}", "ok": True, "message": f"已创建: {base}/repository/{args.name}/"}, args.json)


def cmd_repo_create_group(args) -> int:
    members = [m.strip() for m in args.members.split(",") if m.strip()]
    body = _build_group_body(args.format, args.name, members, args.blob_store)
    if args.dry_run:
        print("[DRY-RUN] 将创建 group 仓库:")
        print(json.dumps(body, ensure_ascii=False, indent=2))
        return 0
    api = get_repo_api(args)
    api_call(_create_repo_via_sdk, api, args.format, "group", body, verbose=_verbose(args))
    base = get_base_url(args)
    return _emit({"command": f"repo create-group {args.format}/{args.name}", "ok": True, "message": f"已创建: {base}/repository/{args.name}/"}, args.json)


def cmd_repo_delete(args) -> int:
    if not args.yes:
        print(f"即将删除仓库: {args.name}\n使用 --yes 确认删除。")
        return 1
    api = get_repo_api(args)
    api_call(api.delete_repositories, args.name, verbose=_verbose(args))
    return _emit({"command": f"repo delete {args.name}", "ok": True, "message": f"已删除: {args.name}"}, args.json)


def cmd_repo_update_group(args) -> int:
    api = get_repo_api(args)
    fmt = resolve_format(args.format)
    # Get current config
    detail = _get_repo_detail(api, fmt, "group", args.name)
    if detail is None:
        return _emit({"command": f"repo update-group {args.name}", "ok": False, "message": f"未找到 group: {args.name}"}, args.json)
    d = _to_dict(detail)
    current_members = d.get("group", {}).get("memberNames", [])
    new_members = list(current_members)
    if args.add_members:
        for m in args.add_members.split(","):
            m = m.strip()
            if m and m not in new_members:
                new_members.append(m)
    if args.remove_members:
        for m in args.remove_members.split(","):
            m = m.strip()
            if m in new_members:
                new_members.remove(m)
    d["group"] = {"memberNames": new_members}
    if args.dry_run:
        print(f"[DRY-RUN] 更新 group {args.name}: members = {new_members}")
        return 0
    api_call(_update_repo_via_sdk, api, args.format, "group", args.name, d, verbose=_verbose(args))
    return _emit({"command": f"repo update-group {args.name}", "ok": True, "message": f"成员已更新: {new_members}"}, args.json)


def cmd_repo_update_proxy(args) -> int:
    api = get_repo_api(args)
    fmt = resolve_format(args.format)
    detail = _get_repo_detail(api, fmt, "proxy", args.name)
    if detail is None:
        return _emit({"command": f"repo update-proxy {args.name}", "ok": False, "message": f"未找到: {args.name}"}, args.json)
    d = _to_dict(detail)
    if args.remote_url:
        d.setdefault("proxy", {})["remoteUrl"] = args.remote_url
    if args.dry_run:
        print(f"[DRY-RUN] 更新 proxy {args.name}:")
        print(json.dumps(d, ensure_ascii=False, indent=2))
        return 0
    api_call(_update_repo_via_sdk, api, args.format, "proxy", args.name, d, verbose=_verbose(args))
    return _emit({"command": f"repo update-proxy {args.name}", "ok": True, "message": "已更新"}, args.json)


def cmd_repo_update_hosted(args) -> int:
    api = get_repo_api(args)
    fmt = resolve_format(args.format)
    detail = _get_repo_detail(api, fmt, "hosted", args.name)
    if detail is None:
        return _emit({"command": f"repo update-hosted {args.name}", "ok": False, "message": f"未找到: {args.name}"}, args.json)
    d = _to_dict(detail)
    if args.write_policy:
        d.setdefault("storage", {})["writePolicy"] = args.write_policy.upper()
    if args.dry_run:
        print(f"[DRY-RUN] 更新 hosted {args.name}:")
        print(json.dumps(d, ensure_ascii=False, indent=2))
        return 0
    api_call(_update_repo_via_sdk, api, args.format, "hosted", args.name, d, verbose=_verbose(args))
    return _emit({"command": f"repo update-hosted {args.name}", "ok": True, "message": "已更新"}, args.json)


def cmd_repo_create_from_preset(args) -> int:
    preset = get_preset(args.preset_name)
    if preset is None:
        print(f"错误: 未找到预设 '{args.preset_name}'\n可用: {', '.join(PRESETS.keys())}", file=sys.stderr)
        sys.exit(2)
    body = _build_proxy_body(preset["format"], preset["name"], preset["remote_url"], preset["blob_store"], None)
    if args.dry_run:
        print(f"[DRY-RUN] 从预设 '{args.preset_name}' 创建:")
        print(json.dumps(body, ensure_ascii=False, indent=2))
        return 0
    api = get_repo_api(args)
    api_call(_create_repo_via_sdk, api, preset["format"], "proxy", body, verbose=_verbose(args))
    base = get_base_url(args)
    return _emit({"command": f"repo create-from-preset {args.preset_name}", "ok": True, "message": f"已创建: {base}/repository/{preset['name']}/"}, args.json)


def cmd_repo_list_presets(args) -> int:
    presets = list_presets()
    if args.json:
        print(json.dumps(presets, ensure_ascii=False, indent=2))
    else:
        print(f"{'预设名称':<30} {'格式':<10} {'上游地址':<45} {'说明'}")
        print("-" * 110)
        for p in presets:
            print(f"{p['id']:<30} {p['format']:<10} {p['remote_url']:<45} {p['description']}")
    return 0


def cmd_probe(args) -> int:
    api = get_repo_api(args)
    all_repos = api_call(api.list_repository_settings, verbose=_verbose(args))
    found = next((r for r in (all_repos or []) if getattr(r, "name", None) == args.repository), None)
    if found:
        d = _to_dict(found)
        return _emit({"command": "probe", "repository": args.repository, "ok": True, "status": 200, "data": d}, args.json)
    return _emit({"command": "probe", "repository": args.repository, "ok": False, "message": "仓库不存在"}, args.json)


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    # Common args inherited by all subcommands
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help="Output as JSON")
    common.add_argument("--verbose", action="store_true", help="Verbose debug output")

    parser = argparse.ArgumentParser(prog="nexusctl", description="Nexus Repository Manager CLI")
    parser.add_argument("--base-url", help="Nexus base URL")
    parser.add_argument("--user", help="Nexus username")
    parser.add_argument("--password", help="Nexus password")
    parser.add_argument("--profile", default="default", help="Profile name (~/.nexusctl/profiles.yaml)")
    parser.add_argument("--json", action="store_true", help="Output as JSON (global)")
    parser.add_argument("--verbose", action="store_true", help="Verbose (global)")
    parser.add_argument("--version", "-V", action="version", version=f"nexusctl {__version__}")

    sub = parser.add_subparsers(dest="command", required=True)

    # --- doctor ---
    sub.add_parser("doctor", parents=[common], help="Health check")

    # --- repo ---
    repo = sub.add_parser("repo", parents=[common], help="Repository management")
    repo_sub = repo.add_subparsers(dest="repo_command", required=True)

    repo_sub.add_parser("list", parents=[common], help="List all repositories")

    p_get = repo_sub.add_parser("get", parents=[common], help="Get repository details")
    p_get.add_argument("--format", required=True, metavar=FORMAT_HELP, help="Repository format")
    p_get.add_argument("--type", required=True, choices=["proxy", "hosted", "group"])
    p_get.add_argument("--name", required=True)

    p_cp = repo_sub.add_parser("create-proxy", parents=[common], help="Create proxy repository")
    p_cp.add_argument("--format", required=True, metavar=FORMAT_HELP)
    p_cp.add_argument("--name", required=True)
    p_cp.add_argument("--remote-url", required=True)
    p_cp.add_argument("--blob-store", default="default")
    p_cp.add_argument("--cleanup-policy", help="Comma-separated cleanup policy names")
    p_cp.add_argument("--dry-run", action="store_true")
    p_cp.add_argument("--distribution", help="APT distribution (apt only)")
    p_cp.add_argument("--flat", action="store_true", help="APT flat structure (apt only)")

    p_ch = repo_sub.add_parser("create-hosted", parents=[common], help="Create hosted repository")
    p_ch.add_argument("--format", required=True, metavar=FORMAT_HELP)
    p_ch.add_argument("--name", required=True)
    p_ch.add_argument("--blob-store", default="default")
    p_ch.add_argument("--write-policy", default="allow_once", choices=["allow_once", "allow", "deny"])
    p_ch.add_argument("--dry-run", action="store_true")

    p_cg = repo_sub.add_parser("create-group", parents=[common], help="Create group repository")
    p_cg.add_argument("--format", required=True, metavar=FORMAT_HELP)
    p_cg.add_argument("--name", required=True)
    p_cg.add_argument("--members", required=True, help="Comma-separated member names")
    p_cg.add_argument("--blob-store", default="default")
    p_cg.add_argument("--dry-run", action="store_true")

    p_del = repo_sub.add_parser("delete", parents=[common], help="Delete a repository")
    p_del.add_argument("--name", required=True)
    p_del.add_argument("--yes", action="store_true", help="Confirm deletion")

    p_ug = repo_sub.add_parser("update-group", parents=[common], help="Update group members")
    p_ug.add_argument("--format", required=True, metavar=FORMAT_HELP)
    p_ug.add_argument("--name", required=True)
    p_ug.add_argument("--add-members", help="Comma-separated members to add")
    p_ug.add_argument("--remove-members", help="Comma-separated members to remove")
    p_ug.add_argument("--dry-run", action="store_true")

    p_up = repo_sub.add_parser("update-proxy", parents=[common], help="Update proxy repository")
    p_up.add_argument("--format", required=True, metavar=FORMAT_HELP)
    p_up.add_argument("--name", required=True)
    p_up.add_argument("--remote-url", help="New upstream URL")
    p_up.add_argument("--dry-run", action="store_true")

    p_uh = repo_sub.add_parser("update-hosted", parents=[common], help="Update hosted repository")
    p_uh.add_argument("--format", required=True, metavar=FORMAT_HELP)
    p_uh.add_argument("--name", required=True)
    p_uh.add_argument("--write-policy", choices=["allow_once", "allow", "deny"])
    p_uh.add_argument("--dry-run", action="store_true")

    p_preset = repo_sub.add_parser("create-from-preset", parents=[common], help="Create from preset")
    p_preset.add_argument("preset_name")
    p_preset.add_argument("--dry-run", action="store_true")

    repo_sub.add_parser("list-presets", parents=[common], help="List available presets")

    # --- probe ---
    p_probe = sub.add_parser("probe", parents=[common], help="Probe repository")
    p_probe.add_argument("--repository", required=True)

    # --- inventory ---
    inv = sub.add_parser("inventory", parents=[common], help="Inventory & fleet-platform")
    inv_sub = inv.add_subparsers(dest="inv_command", required=True)

    p_export = inv_sub.add_parser("export", parents=[common], help="Export inventory")
    p_export.add_argument("--output", default="yaml", choices=["yaml", "json", "fleet-platform"])
    p_export.add_argument("--output-path", help="File path (stdout if omitted)")
    p_export.add_argument("--skip-detail", action="store_true", help="Skip detail API enrichment")

    inv_sub.add_parser("summary", parents=[common], help="Print summary table")

    p_diff = inv_sub.add_parser("diff", parents=[common], help="Diff against fleet-platform ledger")
    p_diff.add_argument("--against", required=True, help="Path to artifact-registry.yaml")

    # --- blobstore ---
    bs = sub.add_parser("blobstore", parents=[common], help="Blob store management")
    bs_sub = bs.add_subparsers(dest="bs_command", required=True)
    bs_sub.add_parser("list", parents=[common], help="List blob stores")

    p_bsc = bs_sub.add_parser("create-file", parents=[common], help="Create file blob store")
    p_bsc.add_argument("--name", required=True)
    p_bsc.add_argument("--path", help="Server-side path (default: /nexus-data/blobs/{name})")
    p_bsc.add_argument("--dry-run", action="store_true")

    p_bsd = bs_sub.add_parser("delete", parents=[common], help="Delete blob store")
    p_bsd.add_argument("--name", required=True)
    p_bsd.add_argument("--yes", action="store_true")

    # --- cleanup-policy ---
    cp = sub.add_parser("cleanup-policy", parents=[common], help="Cleanup policy management")
    cp_sub = cp.add_subparsers(dest="cp_command", required=True)
    cp_sub.add_parser("list", parents=[common], help="List cleanup policies")

    p_cpg = cp_sub.add_parser("get", parents=[common], help="Get cleanup policy details")
    p_cpg.add_argument("--name", required=True)

    # --- user ---
    usr = sub.add_parser("user", parents=[common], help="User management")
    usr_sub = usr.add_subparsers(dest="user_command", required=True)

    usr_sub.add_parser("list", parents=[common], help="List all users")

    p_uc = usr_sub.add_parser("create", parents=[common], help="Create user")
    p_uc.add_argument("name", help="User ID")
    p_uc.add_argument("--new-password", required=True, dest="new_password", help="Password for the new user")
    p_uc.add_argument("--role", default=None, help="Role to assign (default: nx-anonymous)")
    p_uc.add_argument("--dry-run", action="store_true")

    p_ucr = usr_sub.add_parser("create-readonly", parents=[common], help="Create read-only user with dedicated role")
    p_ucr.add_argument("name", help="User ID")
    p_ucr.add_argument("--new-password", required=True, dest="new_password", help="Password for the new user")
    p_ucr.add_argument("--dry-run", action="store_true")

    p_ud = usr_sub.add_parser("delete", parents=[common], help="Delete user")
    p_ud.add_argument("name", help="User ID")
    p_ud.add_argument("--yes", action="store_true", help="Confirm deletion")

    # --- role ---
    role = sub.add_parser("role", parents=[common], help="Role management")
    role_sub = role.add_subparsers(dest="role_command", required=True)
    role_sub.add_parser("list", parents=[common], help="List all roles")


    # ── config ──
    cfg = sub.add_parser("config", help="Manage local CLI config.")
    cfg_sub = cfg.add_subparsers(dest="config_command", required=True)
    cfg_sub.add_parser("show", help="Show effective config.")
    cfg_init = cfg_sub.add_parser("init", help="Initialize config file.")
    cfg_get = cfg_sub.add_parser("get", help="Get a config value.")
    cfg_get.add_argument("key", help="Dot-notation config key.")
    cfg_set = cfg_sub.add_parser("set", help="Set a config value.")
    cfg_set.add_argument("key", help="Dot-notation config key.")
    cfg_set.add_argument("value", help="Value to set.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # ── Role-based access control（制品仓库中枢场景）────────────
    # Nexus 被 CI 与全体开发者消费：
    # - repo create-*：新仓库登记是扩容性操作（均有 --dry-run）→ contributor
    # - repo update-*：改存量仓库（group 成员/proxy 上游/写策略）直接影响
    #   所有消费方解析 → maintainer
    # - repo delete / blobstore create-file/delete：存储层破坏性 → maintainer
    # - user/role：IAM 凭据面 → maintainer（create-readonly 是只读账号发放，
    #   属日常消费者接入 → contributor）
    # - inventory/cleanup-policy/config/probe/doctor：只读或本地 → 开放
    from .role import require_role, check_dry_run_override
    _rbac_map = {
        ("repo", "create-proxy"): "contributor",
        ("repo", "create-hosted"): "contributor",
        ("repo", "create-group"): "contributor",
        ("repo", "create-from-preset"): "contributor",
        ("repo", "update-group"): "maintainer",
        ("repo", "update-proxy"): "maintainer",
        ("repo", "update-hosted"): "maintainer",
        ("repo", "delete"): "maintainer",
        ("blobstore", "create-file"): "maintainer",
        ("blobstore", "delete"): "maintainer",
        ("user", "create"): "maintainer",
        ("user", "create-readonly"): "contributor",
        ("user", "delete"): "maintainer",
    }
    _dest_by_cmd = {"repo": "repo_command", "blobstore": "bs_command", "user": "user_command"}
    _dest = _dest_by_cmd.get(args.command)
    if _dest:
        _sub = getattr(args, _dest, None)
        _minimum = _rbac_map.get((args.command, _sub))
        if _minimum and not check_dry_run_override(args, _minimum):
            require_role(_minimum, f"{args.command} {_sub}")

    # Merge global --json/--verbose into args if subcommand didn't set them
    # (subcommand-level takes priority via parents inheritance)

    dispatch = {"doctor": cmd_doctor, "probe": cmd_probe}
    repo_dispatch = {
        "list": cmd_repo_list, "get": cmd_repo_get,
        "create-proxy": cmd_repo_create_proxy, "create-hosted": cmd_repo_create_hosted,
        "create-group": cmd_repo_create_group, "delete": cmd_repo_delete,
        "update-group": cmd_repo_update_group, "update-proxy": cmd_repo_update_proxy,
        "update-hosted": cmd_repo_update_hosted,
        "create-from-preset": cmd_repo_create_from_preset, "list-presets": cmd_repo_list_presets,
    }
    inv_dispatch = {"export": export_inventory, "summary": print_summary, "diff": diff_inventory}
    bs_dispatch = {"list": cmd_blobstore_list, "create-file": cmd_blobstore_create_file, "delete": cmd_blobstore_delete}
    cp_dispatch = {"list": cmd_cleanup_list, "get": cmd_cleanup_get}
    user_dispatch = {
        "list": cmd_user_list,
        "create": cmd_user_create,
        "create-readonly": cmd_user_create_readonly,
        "delete": cmd_user_delete,
    }
    role_dispatch = {"list": cmd_role_list}

    if args.command == "repo":
        h = repo_dispatch.get(args.repo_command)
        return h(args) if h else 2
    elif args.command == "inventory":
        h = inv_dispatch.get(args.inv_command)
        return h(args) if h else 2
    elif args.command == "blobstore":
        h = bs_dispatch.get(args.bs_command)
        return h(args) if h else 2
    elif args.command == "cleanup-policy":
        h = cp_dispatch.get(args.cp_command)
        return h(args) if h else 2
    elif args.command == "user":
        h = user_dispatch.get(args.user_command)
        return h(args) if h else 2
    elif args.command == "role":
        h = role_dispatch.get(args.role_command)
        return h(args) if h else 2
    else:
        h = dispatch.get(args.command)
        return h(args) if h else 2


if __name__ == "__main__":
    raise SystemExit(main())

