"""woodpeckerctl 主 CLI 入口。

命令结构:
  woodpeckerctl doctor                              健康检查
  woodpeckerctl repo list                           列出仓库
  woodpeckerctl repo activate --gitea-id <id> | --repo <owner/name>  激活仓库
  woodpeckerctl repo deactivate --id <wp_repo_id>   停用仓库
  woodpeckerctl repo update --id <wp_repo_id> [--enabled/--trusted/--timeout/--branch]  修改仓库配置
  woodpeckerctl build list --repo <owner/name>      列出构建
  woodpeckerctl build info --repo <owner/name> --number <n>  构建详情
  woodpeckerctl build log --repo <owner/name> --number <n> --step <id>  步骤日志
  woodpeckerctl secret list/add/remove --repo <owner/name>  仓库 secret 管理
  woodpeckerctl queue status                        队列状态
  woodpeckerctl agent list                          Agent 列表
  woodpeckerctl audit builds --since 7d             构建审计报表 (Phase 1)
  woodpeckerctl config show                         显示配置
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

import yaml

from . import __version__
from .api import (
    activate_repo,
    add_secret,
    deactivate_repo,
    get_build,
    get_build_logs,
    get_queue,
    get_repo_by_id,
    get_user,
    list_agents,
    list_builds,
    list_repos,
    list_secrets,
    remove_secret,
    restart_build,
    trigger_build,
    update_repo,
)
from .config import resolve_config


def _str2bool(v: str) -> bool:
    """argparse 布尔参数解析（接受 true/false/1/0/yes/no）。"""
    s = str(v).strip().lower()
    if s in ("true", "1", "yes", "y"):
        return True
    if s in ("false", "0", "no", "n"):
        return False
    raise argparse.ArgumentTypeError(f"应为 true/false，收到: {v}")


def _gitea_config() -> dict:
    """读取 giteactl 连接配置。

    优先级: ~/.harness-ai-kit/config.yaml 的 assets.giteactl 段 >
    环境变量 GITEA_URL/GITEA_TOKEN（仅作 CI/CD fallback）。
    """
    section: dict = {}
    cfg_file = Path.home() / ".harness-ai-kit" / "config.yaml"
    if cfg_file.is_file():
        try:
            with open(cfg_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            assets = data.get("assets", {}) if isinstance(data, dict) else {}
            if isinstance(assets, dict):
                sec = assets.get("giteactl", {})
                if isinstance(sec, dict):
                    section = sec
        except Exception:
            section = {}
    gitea_url = (section.get("gitea_url") or os.environ.get("GITEA_URL") or "").rstrip("/")
    token = section.get("token") or section.get("gitea_token") or os.environ.get("GITEA_TOKEN") or ""
    return {"gitea_url": gitea_url, "token": token}


def _gitea_repo_id(owner: str, name: str) -> int | None:
    """通过 Gitea API 查询仓库 id（GET <gitea_url>/api/v1/repos/<owner>/<name>）。"""
    cfg = _gitea_config()
    if not cfg["gitea_url"] or not cfg["token"]:
        return None
    url = f"{cfg['gitea_url']}/api/v1/repos/{owner}/{name}"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/json")
    req.add_header("Authorization", f"token {cfg['token']}")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        rid = data.get("id")
        return int(rid) if rid else None
    except Exception:
        return None


def cmd_doctor(args) -> int:
    """健康检查（通过 /api/user 验证连接和认证）。"""
    try:
        user = get_user(args)
        login = user.get("login", "?")
        if args.json:
            print(json.dumps({"ok": True, "command": "doctor", "user": login, "data": user}, ensure_ascii=False, indent=2))
        else:
            print(f"Woodpecker: connected (user: {login})")
        return 0
    except SystemExit:
        if args.json:
            print(json.dumps({"ok": False, "command": "doctor", "message": "连接或认证失败"}, ensure_ascii=False, indent=2))
        else:
            print("Woodpecker: 连接或认证失败")
        return 1


def cmd_repo_list(args) -> int:
    """列出已激活仓库。"""
    repos = list_repos(args)
    if args.json:
        print(json.dumps({"ok": True, "command": "repo list", "count": len(repos), "data": repos}, ensure_ascii=False, indent=2))
    else:
        if not repos:
            print("(no activated repos)")
            return 0
        header = f"{'full_name':<50} {'default_branch':<15} {'visibility':<12}"
        print(header)
        print("-" * len(header))
        for r in repos:
            full = r.get("full_name", "")
            branch = r.get("default_branch", "")
            vis = r.get("visibility", "")
            print(f"{full:<50} {branch:<15} {vis:<12}")
    return 0


def cmd_build_list(args) -> int:
    """列出构建。"""
    repo = args.repo  # owner/name format
    parts = repo.split("/", 1)
    if len(parts) != 2:
        print("error: --repo 格式应为 owner/name", file=sys.stderr)
        return 1
    owner, name = parts
    builds = list_builds(args, owner, name)

    if args.json:
        print(json.dumps({"ok": True, "command": "build list", "repo": repo, "count": len(builds), "data": builds}, ensure_ascii=False, indent=2))
    else:
        if not builds:
            print(f"(no builds for {repo})")
            return 0
        header = f"{'#':<6} {'status':<12} {'branch':<20} {'message':<40} {'created':<20}"
        print(header)
        print("-" * len(header))
        for b in builds[:30]:
            num = str(b.get("number", ""))
            status = b.get("status", "")
            branch = b.get("branch", "")[:18]
            msg = b.get("message", "")[:38]
            created = b.get("created", 0)
            if isinstance(created, (int, float)) and created > 0:
                created_str = datetime.fromtimestamp(created).strftime("%Y-%m-%d %H:%M")
            else:
                created_str = str(created)[:20]
            print(f"{num:<6} {status:<12} {branch:<20} {msg:<40} {created_str:<20}")
    return 0


def cmd_build_info(args) -> int:
    """构建详情。"""
    repo = args.repo
    parts = repo.split("/", 1)
    if len(parts) != 2:
        print("error: --repo 格式应为 owner/name", file=sys.stderr)
        return 1
    owner, name = parts
    build = get_build(args, owner, name, args.number)

    if args.json:
        print(json.dumps({"ok": True, "command": "build info", "repo": repo, "number": args.number, "data": build}, ensure_ascii=False, indent=2))
    else:
        print(f"Build #{build.get('number', '?')} ({repo})")
        print(f"  Status:   {build.get('status', '?')}")
        print(f"  Branch:   {build.get('branch', '?')}")
        print(f"  Commit:   {build.get('commit', '?')[:12]}")
        print(f"  Message:  {build.get('message', '?')}")
        print(f"  Author:   {build.get('author', '?')}")
        started = build.get("started", 0)
        finished = build.get("finished", 0)
        if started:
            print(f"  Started:  {datetime.fromtimestamp(started).strftime('%Y-%m-%d %H:%M:%S')}")
        if finished:
            print(f"  Finished: {datetime.fromtimestamp(finished).strftime('%Y-%m-%d %H:%M:%S')}")
        # Steps
        steps = build.get("steps", [])
        if steps:
            print(f"  Steps ({len(steps)}):")
            for s in steps:
                sname = s.get("name", "?")
                sstatus = s.get("status", "?")
                sid = s.get("id", "?")
                print(f"    [{sstatus}] {sname} (step_id={sid})")
    return 0


def cmd_build_log(args) -> int:
    """步骤日志。"""
    repo = args.repo
    parts = repo.split("/", 1)
    if len(parts) != 2:
        print("error: --repo 格式应为 owner/name", file=sys.stderr)
        return 1
    owner, name = parts
    logs = get_build_logs(args, owner, name, args.number, args.step)

    if args.json:
        print(json.dumps({"ok": True, "command": "build log", "data": logs}, ensure_ascii=False, indent=2))
    else:
        if not logs:
            print("(no log output)")
            return 0
        for entry in logs:
            pos = entry.get("pos", 0)
            out = entry.get("out", "")
            print(out, end="")
        print()
    return 0


def cmd_audit_builds(args) -> int:
    """批量构建审计报表（Phase 1 治理能力）。"""
    repos = list_repos(args)
    if not repos:
        print("无已激活仓库")
        return 0

    report: list[dict] = []
    for repo in repos:
        full_name = repo.get("full_name", "")
        parts = full_name.split("/", 1)
        if len(parts) != 2:
            continue
        owner, name = parts
        builds = list_builds(args, owner, name)
        for b in builds:
            created = b.get("created", 0)
            if isinstance(created, (int, float)) and created > 0:
                age_days = (datetime.now() - datetime.fromtimestamp(created)).days
            else:
                age_days = -1
            report.append({
                "repo": full_name,
                "number": b.get("number"),
                "status": b.get("status"),
                "branch": b.get("branch"),
                "duration_sec": b.get("finished", 0) - b.get("started", 0) if b.get("started") and b.get("finished") else 0,
                "age_days": age_days,
            })

    # Filter by --since
    since_days = 7
    if hasattr(args, "since") and args.since:
        try:
            since_days = int(args.since.rstrip("d"))
        except ValueError:
            pass

    filtered = [r for r in report if r["age_days"] >= 0 and r["age_days"] <= since_days]

    # Stats
    total = len(filtered)
    success = len([r for r in filtered if r["status"] == "success"])
    failure = len([r for r in filtered if r["status"] == "failure"])
    other = total - success - failure
    success_rate = round(success / total * 100, 1) if total > 0 else 0

    if args.json:
        print(json.dumps({
            "ok": True, "command": "audit builds",
            "since": f"{since_days}d", "total": total,
            "success": success, "failure": failure, "other": other,
            "success_rate": f"{success_rate}%",
            "data": filtered,
        }, ensure_ascii=False, indent=2))
    else:
        print(f"构建审计报表（最近 {since_days} 天）:")
        print(f"  总构建数: {total}")
        print(f"  成功: {success} ({success_rate}%)")
        print(f"  失败: {failure}")
        print(f"  其他: {other}")
        if filtered:
            print()
            header = f"{'repo':<40} {'#':<6} {'status':<12} {'branch':<15} {'duration':<10} {'age':<6}"
            print(header)
            print("-" * len(header))
            for r in filtered[:30]:
                dur = f"{r['duration_sec']}s" if r['duration_sec'] else "-"
                age = f"{r['age_days']}d" if r['age_days'] >= 0 else "-"
                print(f"{r['repo']:<40} {str(r['number']):<6} {r['status']:<12} {r['branch'][:13]:<15} {dur:<10} {age:<6}")
    return 0


def cmd_repo_show(args) -> int:
    """通过内部 repo_id 查询仓库（id→slug 解析）。"""
    repo = get_repo_by_id(args, args.id)
    if args.json:
        print(json.dumps({"ok": True, "command": "repo show", "id": args.id, "data": repo}, ensure_ascii=False, indent=2))
    else:
        full = repo.get("full_name", "?")
        rid = repo.get("id", "?")
        branch = repo.get("default_branch", "?")
        print(f"Repo #{rid}: {full} (default_branch={branch})")
    return 0


def cmd_build_restart(args) -> int:
    """重启构建。"""
    repo = args.repo
    parts = repo.split("/", 1)
    if len(parts) != 2:
        print("error: --repo 格式应为 owner/name", file=sys.stderr)
        return 1
    owner, name = parts
    new_build = restart_build(args, owner, name, args.number)
    if args.json:
        print(json.dumps({"ok": True, "command": "build restart", "repo": repo, "number": args.number, "new_build": new_build}, ensure_ascii=False, indent=2))
    else:
        new_num = new_build.get("number", "?")
        status = new_build.get("status", "?")
        print(f"Build #{args.number} restarted -> new build #{new_num} (status={status})")
    return 0


def cmd_build_trigger(args) -> int:
    """手动触发新构建。"""
    repo = args.repo
    parts = repo.split("/", 1)
    if len(parts) != 2:
        print("error: --repo 格式应为 owner/name", file=sys.stderr)
        return 1
    owner, name = parts
    branch = getattr(args, "branch", "main")
    event = getattr(args, "event", "manual")
    new_build = trigger_build(args, owner, name, branch, event)
    if args.json:
        print(json.dumps({"ok": True, "command": "build trigger", "repo": repo, "branch": branch, "event": event, "new_build": new_build}, ensure_ascii=False, indent=2))
    else:
        new_num = new_build.get("number", "?")
        print(f"Triggered build #{new_num} for {repo} (branch={branch}, event={event})")
    return 0


def cmd_config_show(args) -> int:
    """显示配置。"""
    cfg = resolve_config(args)
    display = dict(cfg)
    if display.get("token"):
        display["token"] = "***" + display["token"][-4:] if len(display["token"]) > 4 else "***"
    if args.json:
        print(json.dumps({"ok": True, "command": "config show", "config": display}, ensure_ascii=False, indent=2))
    else:
        print("woodpeckerctl 当前配置:")
        for k, v in display.items():
            print(f"  {k}: {v}")
    return 0


def cmd_repo_activate(args) -> int:
    """激活仓库（--gitea-id 直接激活；--repo 先经 gitea 解析 id 再激活）。"""
    gitea_id = getattr(args, "gitea_id", None)
    slug = getattr(args, "repo", None)
    if gitea_id is None:
        parts = slug.split("/", 1)
        if len(parts) != 2:
            print("error: --repo 格式应为 owner/name", file=sys.stderr)
            return 1
        owner, name = parts
        gitea_id = _gitea_repo_id(owner, name)
        if not gitea_id:
            print(f"error: 无法解析 {slug} 的 gitea repo id（giteactl 配置不可用或仓库不存在）", file=sys.stderr)
            print("hint: 检查 ~/.harness-ai-kit/config.yaml 的 assets.giteactl 段，或改用 --gitea-id 手动指定", file=sys.stderr)
            return 1
    repo = activate_repo(args, gitea_id)
    if args.json:
        print(json.dumps({"ok": True, "command": "repo activate", "gitea_id": gitea_id, "data": repo}, ensure_ascii=False, indent=2))
    else:
        rid = repo.get("id", "?")
        full = repo.get("full_name", slug or "?")
        print(f"已激活仓库: {full} (wp_repo_id={rid}, gitea_id={gitea_id})")
    return 0


def cmd_repo_deactivate(args) -> int:
    """停用仓库。"""
    info = get_repo_by_id(args, args.id)
    slug = info.get("full_name", "?")
    deactivate_repo(args, args.id)
    if args.json:
        print(json.dumps({"ok": True, "command": "repo deactivate", "id": args.id, "repo": slug}, ensure_ascii=False, indent=2))
    else:
        print(f"已停用仓库: {slug} (wp_repo_id={args.id})")
    return 0


def cmd_repo_update(args) -> int:
    """修改仓库配置。"""
    fields: dict = {}
    if getattr(args, "enabled", None) is not None:
        fields["active"] = args.enabled
    if getattr(args, "trusted", None) is not None:
        fields["trusted"] = args.trusted
    if getattr(args, "timeout", None) is not None:
        fields["timeout"] = args.timeout
    if getattr(args, "branch", None):
        fields["default_branch"] = args.branch.split(",")[0].strip()
    if not fields:
        print("error: 未指定修改字段（--enabled/--trusted/--timeout/--branch 至少一个）", file=sys.stderr)
        return 1
    repo = update_repo(args, args.id, fields)
    if args.json:
        print(json.dumps({"ok": True, "command": "repo update", "id": args.id, "fields": fields, "data": repo}, ensure_ascii=False, indent=2))
    else:
        full = repo.get("full_name", "?")
        changed = ", ".join(f"{k}={v}" for k, v in fields.items())
        print(f"已更新仓库: {full} (wp_repo_id={args.id}) [{changed}]")
    return 0


def cmd_secret_list(args) -> int:
    """列出仓库 secrets（永不显示值）。"""
    repo = args.repo
    parts = repo.split("/", 1)
    if len(parts) != 2:
        print("error: --repo 格式应为 owner/name", file=sys.stderr)
        return 1
    owner, name = parts
    secrets = list_secrets(args, owner, name)
    if args.json:
        print(json.dumps({"ok": True, "command": "secret list", "repo": repo, "count": len(secrets), "data": secrets}, ensure_ascii=False, indent=2))
    else:
        if not secrets:
            print(f"(no secrets for {repo})")
            return 0
        header = f"{'name':<32} {'events':<24} {'images'}"
        print(header)
        print("-" * len(header))
        for s in secrets:
            sname = s.get("name", "")
            events = ",".join(s.get("events") or s.get("event") or [])
            images = ",".join(s.get("images") or [])
            print(f"{sname:<32} {events:<24} {images}")
    return 0


def cmd_secret_add(args) -> int:
    """添加仓库 secret（--value-file 避免 shell 历史泄露）。"""
    repo = args.repo
    parts = repo.split("/", 1)
    if len(parts) != 2:
        print("error: --repo 格式应为 owner/name", file=sys.stderr)
        return 1
    owner, name = parts
    if getattr(args, "value_file", None):
        try:
            value = Path(args.value_file).read_text(encoding="utf-8").strip()
        except OSError as exc:
            print(f"error: 无法读取 --value-file {args.value_file}: {exc}", file=sys.stderr)
            return 1
    else:
        value = args.value
    events = [e.strip() for e in (args.events or "").split(",") if e.strip()]
    result = add_secret(args, owner, name, args.key, value, events)
    if args.json:
        safe = {k: v for k, v in result.items() if k != "value"}
        print(json.dumps({"ok": True, "command": "secret add", "repo": repo, "key": args.key, "events": events, "data": safe}, ensure_ascii=False, indent=2))
    else:
        print(f"已添加 secret: {args.key} -> {repo} (events={','.join(events)})")
    return 0


def cmd_secret_remove(args) -> int:
    """删除仓库 secret。"""
    repo = args.repo
    parts = repo.split("/", 1)
    if len(parts) != 2:
        print("error: --repo 格式应为 owner/name", file=sys.stderr)
        return 1
    owner, name = parts
    remove_secret(args, owner, name, args.key)
    if args.json:
        print(json.dumps({"ok": True, "command": "secret remove", "repo": repo, "key": args.key}, ensure_ascii=False, indent=2))
    else:
        print(f"已删除 secret: {args.key} ({repo})")
    return 0


def cmd_queue_status(args) -> int:
    """队列状态（pending / waiting_on_deps / running）。"""
    q = get_queue(args)
    if args.json:
        print(json.dumps({"ok": True, "command": "queue status", "data": q}, ensure_ascii=False, indent=2))
        return 0
    if not q:
        print("(queue empty or unavailable)")
        return 0
    if isinstance(q, list):
        print(f"队列任务数: {len(q)}")
        return 0
    pending = q.get("pending") or []
    waiting = q.get("waiting_on_deps") or []
    running = q.get("running") or []
    stats = q.get("stats") if isinstance(q.get("stats"), dict) else {}
    print("队列状态:")
    print(f"  pending:         {len(pending)}")
    print(f"  waiting_on_deps: {len(waiting)}")
    print(f"  running:         {len(running)}")
    if stats:
        print("  stats:")
        for k, v in stats.items():
            print(f"    {k}: {v}")
    if running:
        print("  运行中任务:")
        for t in running[:10]:
            if isinstance(t, dict):
                labels = t.get("labels") or {}
                head = f"{labels.get('repo', '')} #{labels.get('build_number', '')}".strip(" #") or str(t.get("id", "?"))
            else:
                head = str(t)
            print(f"    {head}")
    return 0


def cmd_agent_list(args) -> int:
    """Agent 列表（在线/离线判定: last_contact 距今 < 5 分钟视为 online）。"""
    agents = list_agents(args)
    if args.json:
        print(json.dumps({"ok": True, "command": "agent list", "count": len(agents), "data": agents}, ensure_ascii=False, indent=2))
    else:
        if not agents:
            print("(no agents)")
            return 0
        header = f"{'id':<6} {'name':<24} {'version':<12} {'backend':<10} {'capacity':<9} {'status':<8} {'last_contact':<18}"
        print(header)
        print("-" * len(header))
        now = datetime.now().timestamp()
        for a in agents:
            aid = str(a.get("id", ""))
            aname = str(a.get("name", ""))[:22]
            ver = str(a.get("version", "") or "-")[:10]
            backend = str(a.get("backend", "") or "-")[:8]
            cap = str(a.get("capacity", "-") if a.get("capacity") is not None else "-")
            last = a.get("last_contact") or 0
            if isinstance(last, (int, float)) and last > 0:
                status = "online" if (now - last) < 300 else "offline"
                last_str = datetime.fromtimestamp(last).strftime("%Y-%m-%d %H:%M")
            else:
                status = "unknown"
                last_str = "-"
            print(f"{aid:<6} {aname:<24} {ver:<12} {backend:<10} {cap:<9} {status:<8} {last_str:<18}")
    return 0


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="woodpeckerctl",
        description="Woodpecker CI wrapper CLI（治理 + 别名路由）",
    )
    parser.add_argument("--server", help="Woodpecker server URL")
    parser.add_argument("--token", help="API token")
    parser.add_argument("--profile", default="default", help="Profile name")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    parser.add_argument("--version", "-V", action="version", version=f"woodpeckerctl {__version__}")

    sub = parser.add_subparsers(dest="command", required=True)

    # doctor
    sub.add_parser("doctor", help="健康检查")

    # repo
    repo = sub.add_parser("repo", help="仓库管理")
    repo_sub = repo.add_subparsers(dest="repo_command", required=True)
    repo_sub.add_parser("list", help="列出已激活仓库")
    p_rs = repo_sub.add_parser("show", help="通过内部 repo_id 查询仓库（id→slug 解析）")
    p_rs.add_argument("--id", required=True, type=int, help="Woodpecker 内部 repo_id")

    p_ra = repo_sub.add_parser("activate", help="激活仓库")
    ra_group = p_ra.add_mutually_exclusive_group(required=True)
    ra_group.add_argument("--gitea-id", type=int, help="Gitea 仓库 ID（forge_remote_id）")
    ra_group.add_argument("--repo", help="owner/name（自动经 giteactl 配置解析 gitea id）")

    p_rd = repo_sub.add_parser("deactivate", help="停用仓库")
    p_rd.add_argument("--id", required=True, type=int, help="Woodpecker 内部 repo_id")

    p_ru = repo_sub.add_parser("update", help="修改仓库配置")
    p_ru.add_argument("--id", required=True, type=int, help="Woodpecker 内部 repo_id")
    p_ru.add_argument("--enabled", type=_str2bool, help="启用/停用仓库（true/false）")
    p_ru.add_argument("--trusted", type=_str2bool, help="是否信任（true/false）")
    p_ru.add_argument("--timeout", type=int, help="流水线超时时间（分钟）")
    p_ru.add_argument("--branch", help="默认分支（逗号分隔时取第一个）")

    # build
    build = sub.add_parser("build", help="构建管理")
    build_sub = build.add_subparsers(dest="build_command", required=True)

    p_bl = build_sub.add_parser("list", help="列出构建")
    p_bl.add_argument("--repo", required=True, help="owner/name")

    p_bi = build_sub.add_parser("info", help="构建详情")
    p_bi.add_argument("--repo", required=True, help="owner/name")
    p_bi.add_argument("--number", required=True, type=int, help="构建编号")

    p_blog = build_sub.add_parser("log", help="步骤日志")
    p_blog.add_argument("--repo", required=True, help="owner/name")
    p_blog.add_argument("--number", required=True, type=int, help="构建编号")
    p_blog.add_argument("--step", required=True, type=int, help="Step ID")

    p_br = build_sub.add_parser("restart", help="重启构建")
    p_br.add_argument("--repo", required=True, help="owner/name")
    p_br.add_argument("--number", required=True, type=int, help="构建编号")

    p_bt = build_sub.add_parser("trigger", help="手动触发新构建")
    p_bt.add_argument("--repo", required=True, help="owner/name")
    p_bt.add_argument("--branch", default="main", help="分支名")
    p_bt.add_argument("--event", default="manual", help="触发事件（默认 manual）")
    audit = sub.add_parser("audit", help="审计（治理）")
    audit_sub = audit.add_subparsers(dest="audit_command", required=True)
    p_ab = audit_sub.add_parser("builds", help="构建审计报表")
    p_ab.add_argument("--since", default="7d", help="时间范围（如 7d, 30d）")

    # secret
    secret = sub.add_parser("secret", help="仓库 secret 管理")
    secret_sub = secret.add_subparsers(dest="secret_command", required=True)

    p_sl = secret_sub.add_parser("list", help="列出仓库 secrets（不显示值）")
    p_sl.add_argument("--repo", required=True, help="owner/name")

    p_sa = secret_sub.add_parser("add", help="添加仓库 secret")
    p_sa.add_argument("--repo", required=True, help="owner/name")
    p_sa.add_argument("--key", required=True, help="secret 名称")
    sa_group = p_sa.add_mutually_exclusive_group(required=True)
    sa_group.add_argument("--value", help="secret 值")
    sa_group.add_argument("--value-file", help="从文件读取 secret 值（避免 shell 历史泄露）")
    p_sa.add_argument("--events", default="push,tag,manual", help="触发事件，逗号分隔（默认 push,tag,manual）")

    p_sr = secret_sub.add_parser("remove", help="删除仓库 secret")
    p_sr.add_argument("--repo", required=True, help="owner/name")
    p_sr.add_argument("--key", required=True, help="secret 名称")

    # queue
    queue = sub.add_parser("queue", help="队列管理")
    queue_sub = queue.add_subparsers(dest="queue_command", required=True)
    queue_sub.add_parser("status", help="队列状态（pending/running pipelines）")

    # agent
    agent = sub.add_parser("agent", help="Agent 管理")
    agent_sub = agent.add_subparsers(dest="agent_command", required=True)
    agent_sub.add_parser("list", help="Agent 列表（在线/离线/标签/版本）")

    # config
    cfg = sub.add_parser("config", help="配置管理")
    cfg_sub = cfg.add_subparsers(dest="config_command", required=True)
    cfg_sub.add_parser("show", help="显示当前配置")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    dispatch = {"doctor": cmd_doctor}
    repo_dispatch = {"list": cmd_repo_list, "show": cmd_repo_show, "activate": cmd_repo_activate, "deactivate": cmd_repo_deactivate, "update": cmd_repo_update}
    build_dispatch = {"list": cmd_build_list, "info": cmd_build_info, "log": cmd_build_log, "restart": cmd_build_restart, "trigger": cmd_build_trigger}
    audit_dispatch = {"builds": cmd_audit_builds}
    secret_dispatch = {"list": cmd_secret_list, "add": cmd_secret_add, "remove": cmd_secret_remove}
    queue_dispatch = {"status": cmd_queue_status}
    agent_dispatch = {"list": cmd_agent_list}
    config_dispatch = {"show": cmd_config_show}

    try:
        if args.command == "repo":
            h = repo_dispatch.get(args.repo_command)
            return h(args) if h else 2
        elif args.command == "build":
            h = build_dispatch.get(args.build_command)
            return h(args) if h else 2
        elif args.command == "audit":
            h = audit_dispatch.get(args.audit_command)
            return h(args) if h else 2
        elif args.command == "secret":
            h = secret_dispatch.get(args.secret_command)
            return h(args) if h else 2
        elif args.command == "queue":
            h = queue_dispatch.get(args.queue_command)
            return h(args) if h else 2
        elif args.command == "agent":
            h = agent_dispatch.get(args.agent_command)
            return h(args) if h else 2
        elif args.command == "config":
            h = config_dispatch.get(args.config_command)
            return h(args) if h else 2
        else:
            h = dispatch.get(args.command)
            return h(args) if h else 2
    except ValueError as exc:
        print(f"配置错误: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
