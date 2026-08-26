"""build 子命令组：构建历史与日志查看。"""
import sys
from datetime import datetime

import click

from jenkinsctl import output


@click.group("build")
def build_group():
    """构建历史与日志管理。"""
    pass


@build_group.command("list")
@click.argument("name")
@click.option("--limit", "-n", default=20, help="最多显示条数（默认 20）")
@click.pass_context
def build_list(ctx, name, limit):
    """列出指定 Job 的构建历史。

    示例: jenkinsctl build list my-job
          jenkinsctl build list my-job --limit 5
    """
    conn = ctx.obj["connection"]
    try:
        path = (
            f"/job/{name}/api/json"
            f"?tree=builds[number,result,timestamp,duration,building]{{0,{limit}}}"
        )
        data = conn.api_get(path)
        builds = data.get("builds", [])
        fmt = ctx.obj["output_format"]

        if fmt == "json":
            output.print_json(builds)
        else:
            if not builds:
                click.echo(f"(Job {name} 无构建记录)")
                return
            rows = []
            for b in builds:
                num = str(b.get("number", "?"))
                result = b.get("result") or ("构建中" if b.get("building") else "未知")
                ts = b.get("timestamp", 0)
                ts_str = datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d %H:%M") if ts else "?"
                dur_ms = b.get("duration", 0)
                dur_str = f"{dur_ms // 1000}s" if dur_ms else "-"
                rows.append([num, result, ts_str, dur_str])
            output.print_table(
                ["#", "结果", "时间", "耗时"],
                rows,
                title=f"构建历史: {name}（最近 {limit} 条）",
            )
    except Exception as e:
        output.print_err(f"获取构建历史失败: {e}")
        sys.exit(1)


@build_group.command("info")
@click.argument("name")
@click.argument("number", type=int)
@click.pass_context
def build_info(ctx, name, number):
    """查看某次构建的详细信息。

    示例: jenkinsctl build info my-job 42
    """
    conn = ctx.obj["connection"]
    try:
        path = (
            f"/job/{name}/{number}/api/json"
            "?tree=number,result,building,timestamp,duration,"
            "estimatedDuration,displayName,fullDisplayName,"
            "url,actions[parameters[name,value]],"
            "changeSets[items[commitId,author[fullName],comment]],"
            "culprits[fullName]"
        )
        data = conn.api_get(path)
        fmt = ctx.obj["output_format"]

        if fmt == "json":
            output.print_json(data)
        else:
            result = data.get("result") or ("构建中" if data.get("building") else "未知")
            ts = data.get("timestamp", 0)
            ts_str = datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d %H:%M:%S") if ts else "?"
            dur_ms = data.get("duration", 0)
            dur_str = f"{dur_ms // 1000}s ({dur_ms // 60000}m{(dur_ms % 60000) // 1000}s)" if dur_ms else "-"

            click.echo(f"构建 #{data.get('number', '?')} — {data.get('fullDisplayName', name)}")
            click.echo(f"  结果:   {result}")
            click.echo(f"  时间:   {ts_str}")
            click.echo(f"  耗时:   {dur_str}")
            click.echo(f"  URL:    {data.get('url', '?')}")

            # 参数
            actions = data.get("actions", [])
            for action in actions:
                params = action.get("parameters", [])
                if params:
                    click.echo(f"  参数:")
                    for p in params:
                        click.echo(f"    {p.get('name', '?')} = {p.get('value', '?')}")

            # 变更
            change_sets = data.get("changeSets", [])
            if change_sets:
                items = change_sets[0].get("items", []) if change_sets else []
                if items:
                    click.echo(f"  变更 ({len(items)} commits):")
                    for item in items[:10]:
                        sha = item.get("commitId", "?")[:8]
                        author = item.get("author", {}).get("fullName", "?")
                        msg = item.get("comment", "").split("\n")[0][:60]
                        click.echo(f"    {sha} {author}: {msg}")

            # 责任人
            culprits = data.get("culprits", [])
            if culprits:
                names = [c.get("fullName", "?") for c in culprits]
                click.echo(f"  责任人: {', '.join(names)}")

    except Exception as e:
        output.print_err(f"获取构建详情失败: {e}")
        sys.exit(1)


@build_group.command("log")
@click.argument("name")
@click.argument("number", type=int)
@click.option("--tail", "tail_lines", default=100, help="显示最后 N 行（默认 100）")
@click.option("--full", "full_log", is_flag=True, help="输出完整日志（忽略 --tail）")
@click.option("-o", "output_file", default=None, help="将日志保存到文件")
@click.pass_context
def build_log(ctx, name, number, tail_lines, full_log, output_file):
    """查看某次构建的控制台日志。

    示例: jenkinsctl build log my-job 42
          jenkinsctl build log my-job 42 --tail 200
          jenkinsctl build log my-job 42 --full -o build.log
    """
    conn = ctx.obj["connection"]
    try:
        path = f"/job/{name}/{number}/consoleText"
        resp = conn._session.get(f"{conn.url}{path}", timeout=120)
        resp.raise_for_status()
        text = resp.text

        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(text)
            output.print_ok(f"完整日志已保存到 {output_file}（{len(text.splitlines())} 行）")
            return

        if full_log:
            click.echo(text)
        else:
            lines = text.split("\n")
            if len(lines) > tail_lines:
                click.echo(f"... (省略前 {len(lines) - tail_lines} 行，使用 --full 查看完整日志)")
                click.echo("\n".join(lines[-tail_lines:]))
            else:
                click.echo(text)

    except Exception as e:
        output.print_err(f"获取构建日志失败: {e}")
        sys.exit(1)
