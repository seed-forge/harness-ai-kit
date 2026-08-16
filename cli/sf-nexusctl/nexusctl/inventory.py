"""Inventory export, summary, and diff for fleet-platform integration."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from typing import Any

import yaml

from ._api import api_call, get_repo_api, get_base_url, resolve_format


def _to_dict(obj) -> dict:
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if isinstance(obj, dict):
        return obj
    return {"raw": str(obj)}


def _enrich_repo(api, repo: dict, verbose: bool = False) -> dict:
    """Enrich a repo dict with detail API data (blob_store, write_policy, etc.)."""
    name = repo.get("name", "")
    fmt = repo.get("format", "")
    rtype = repo.get("type", "")
    if not name or not fmt or not rtype:
        return repo

    sdk_fmt = resolve_format(fmt) if fmt in ("pypi", "npm", "maven", "maven2", "docker", "raw", "nuget", "go", "golang", "rubygems", "apt") else fmt
    method_name = f"get_{sdk_fmt}_{rtype}_repository"
    method = getattr(api, method_name, None)
    if method is None:
        return repo

    try:
        detail = method(name)
        if detail is None:
            return repo
        d = _to_dict(detail)
        storage = d.get("storage", {})
        if storage.get("blobStoreName"):
            repo["blob_store"] = storage["blobStoreName"]
        if storage.get("writePolicy"):
            repo["write_policy"] = storage["writePolicy"]
        proxy = d.get("proxy", {})
        if proxy.get("remoteUrl"):
            repo["remote_url"] = proxy["remoteUrl"]
        group = d.get("group", {})
        if group.get("memberNames"):
            repo["group_members"] = group["memberNames"]
        if "online" in d:
            repo["online"] = d["online"]
    except Exception:
        pass  # detail enrichment is best-effort
    return repo


def _repo_to_instance(repo: dict, base_url: str) -> dict:
    """Convert a Nexus repository dict to a fleet-platform instance entry."""
    name = repo.get("name", "unknown")
    fmt = repo.get("format", "unknown")
    rtype = repo.get("type", "unknown")
    url = repo.get("url", "")

    tags = [fmt, rtype]
    if rtype == "proxy":
        tags.append("upstream")
    elif rtype == "group":
        tags.append("aggregator")
    elif rtype == "hosted":
        tags.append("private")

    entry: dict[str, Any] = {
        "id": f"nexus-{name}",
        "type": "nexus-repo",
        "name": name,
        "format": fmt,
        "repo_type": rtype,
        "url": url,
        "online": repo.get("online", True),
        "tags": tags,
    }

    for key in ("remote_url", "group_members", "blob_store", "write_policy"):
        if repo.get(key):
            entry[key] = repo[key]

    return entry


def _get_all_repos(args) -> list[dict]:
    """Fetch all repos as dicts."""
    api = get_repo_api(args)
    verbose = getattr(args, "verbose", False)
    repos = api_call(api.list_repository_settings, verbose=verbose)
    if repos is None:
        return []
    return [_to_dict(r) for r in repos]


def export_inventory(args) -> int:
    """Query all repos and write fleet-platform YAML."""
    api = get_repo_api(args)
    base_url = get_base_url(args)
    output_path = getattr(args, "output_path", None)
    skip_detail = getattr(args, "skip_detail", False)
    verbose = getattr(args, "verbose", False)

    repo_dicts = _get_all_repos(args)

    # Enrich with detail API unless --skip-detail
    if not skip_detail:
        for i, r in enumerate(repo_dicts):
            repo_dicts[i] = _enrich_repo(api, r, verbose)

    instances = [_repo_to_instance(r, base_url) for r in repo_dicts]

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    doc = {
        "category": "artifact-registry",
        "principles": {
            "nexus": "Sonatype Nexus Repository Manager, 语言包私服",
            "harbor": "Docker OCI 镜像仓库（独立管理，见 infra/platform.yaml）",
            "notes": "Nexus 负责 PyPI/npm/Maven/raw/go 等格式；Harbor 负责 Docker OCI",
            "generated_at": now,
        },
        "instance_count": len(instances),
        "instances": instances,
    }

    output_format = getattr(args, "output", "yaml")
    # fleet-platform is an alias for yaml
    if output_format == "fleet-platform":
        output_format = "yaml"

    if output_format == "json":
        text = json.dumps(doc, ensure_ascii=False, indent=2)
    else:
        text = yaml.dump(doc, allow_unicode=True, default_flow_style=False, sort_keys=False)

    header = "# artifact-registry.yaml — 组织内部集群 制品仓库目录\n"
    header += "# 由 nexusctl inventory export 自动生成, SSOT 在 fleet-platform/infra/\n"
    header += "# 手动修改前请先确认 nexusctl 导出结果\n\n"

    full_content = header + text

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(full_content)
        print(f"已导出 {len(instances)} 个仓库到: {output_path}")
    else:
        print(full_content)

    return 0


def print_summary(args) -> int:
    """Print a summary table of repos grouped by format/type."""
    repo_dicts = _get_all_repos(args)

    stats: dict[tuple[str, str], int] = {}
    total = 0
    for r in repo_dicts:
        fmt = r.get("format", "?")
        rtype = r.get("type", "?")
        key = (fmt, rtype)
        stats[key] = stats.get(key, 0) + 1
        total += 1

    if not stats:
        print("未发现任何仓库。")
        return 0

    by_format: dict[str, dict[str, int]] = {}
    for (fmt, rtype), count in stats.items():
        by_format.setdefault(fmt, {})[rtype] = count

    as_json = getattr(args, "json", False)
    if as_json:
        result = {
            "total": total,
            "by_format": {
                fmt: {"types": types, "total": sum(types.values())}
                for fmt, types in sorted(by_format.items())
            },
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"{'格式':<16} {'proxy':>6} {'hosted':>7} {'group':>6} {'合计':>6}")
        print("-" * 45)
        for fmt in sorted(by_format):
            types = by_format[fmt]
            p = types.get("proxy", 0)
            h = types.get("hosted", 0)
            g = types.get("group", 0)
            print(f"{fmt:<16} {p:>6} {h:>7} {g:>6} {p+h+g:>6}")
        print("-" * 45)
        print(f"{'总计':<16} {'':>6} {'':>7} {'':>6} {total:>6}")

    return 0


def diff_inventory(args) -> int:
    """Compare Nexus actual state vs fleet-platform ledger."""
    against_path = args.against
    try:
        with open(against_path, "r", encoding="utf-8") as f:
            content = f.read()
            # Strip comment lines for YAML parsing
            ledger = yaml.safe_load(content)
    except Exception as exc:
        print(f"错误: 无法读取台账文件 {against_path}: {exc}", file=sys.stderr)
        return 1

    ledger_instances = ledger.get("instances", [])
    ledger_names = {inst.get("name") for inst in ledger_instances if inst.get("name")}

    repo_dicts = _get_all_repos(args)
    live_names = {r.get("name") for r in repo_dicts if r.get("name")}

    added = live_names - ledger_names
    removed = ledger_names - live_names
    common = live_names & ledger_names

    # Check for changes in common repos
    ledger_map = {inst["name"]: inst for inst in ledger_instances if inst.get("name")}
    live_map = {r["name"]: r for r in repo_dicts if r.get("name")}
    changed = []
    for name in sorted(common):
        l = ledger_map.get(name, {})
        r = live_map.get(name, {})
        diffs = []
        if l.get("online") != r.get("online"):
            diffs.append(f"online: {l.get('online')} -> {r.get('online')}")
        if l.get("remote_url") != r.get("remote_url") and r.get("remote_url"):
            diffs.append(f"remote_url: {l.get('remote_url')} -> {r.get('remote_url')}")
        if diffs:
            changed.append({"name": name, "changes": diffs})

    as_json = getattr(args, "json", False)
    result = {
        "added": sorted(added),
        "removed": sorted(removed),
        "changed": changed,
        "summary": f"+{len(added)} 新增, -{len(removed)} 缺失, ~{len(changed)} 变更",
    }

    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"=== 漂移检测: {against_path} ===")
        print(f"  台账: {len(ledger_names)} 个仓库")
        print(f"  实际: {len(live_names)} 个仓库")
        print()
        if added:
            print(f"  新增（实际有，台账无）:")
            for n in sorted(added):
                print(f"    + {n}")
        if removed:
            print(f"  缺失（台账有，实际无）:")
            for n in sorted(removed):
                print(f"    - {n}")
        if changed:
            print(f"  变更:")
            for c in changed:
                print(f"    ~ {c['name']}: {', '.join(c['changes'])}")
        if not added and not removed and not changed:
            print("  无漂移，台账与实际一致。")

    return 0
