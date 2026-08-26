"""plugin 子命令组：插件管理（REST API）。"""
import sys
from pathlib import Path

import click
import requests
import yaml

from jenkinsctl import output


# ── 内部辅助 ──────────────────────────────────────────

def _get_installed_plugins(conn) -> list[dict]:
    """获取已安装插件列表。"""
    try:
        data = conn.api_get(
            "/pluginManager/api/json?tree=plugins[shortName,longName,version,active,enabled,hasUpdate]"
        )
        return sorted(data.get("plugins", []), key=lambda p: p.get("shortName", ""))
    except Exception as e:
        output.print_err(f"获取插件列表失败: {e}")
        return []


def _search_update_center(keyword: str) -> list[dict]:
    """从 Jenkins Update Center 搜索插件。"""
    try:
        resp = requests.get(
            "https://updates.jenkins.io/current/update-center.actual.json",
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        plugins = data.get("plugins", {})
        results = []
        kw_lower = keyword.lower()
        for name, info in plugins.items():
            if kw_lower in name.lower() or kw_lower in info.get("title", "").lower():
                results.append({
                    "name": name,
                    "title": info.get("title", ""),
                    "version": info.get("version", ""),
                    "wiki": info.get("wiki", ""),
                })
        return sorted(results, key=lambda p: p["name"])[:20]  # 限制返回 20 条
    except Exception as e:
        output.print_err(f"搜索 Update Center 失败: {e}")
        return []


def _load_required_plugins() -> list[dict]:
    """加载 Shared Library 所需插件清单。"""
    data_file = Path(__file__).parent / "data" / "required-plugins.yaml"
    if not data_file.exists():
        return []
    with open(data_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("plugins", [])


# ── CLI 命令 ──────────────────────────────────────────────

@click.group("plugin")
def plugin_group():
    """插件管理（安装/搜索/更新）。"""
    pass


@plugin_group.command("list")
@click.option("--active-only", is_flag=True, default=False, help="仅显示活跃插件")
@click.pass_context
def plugin_list(ctx, active_only):
    """列出已安装插件。"""
    conn = ctx.obj["connection"]
    plugins = _get_installed_plugins(conn)

    if active_only:
        plugins = [p for p in plugins if p.get("active")]

    fmt = ctx.obj["output_format"]
    if fmt == "json":
        output.print_json(plugins)
    else:
        rows = []
        for p in plugins:
            status = "活跃" if p.get("active") else "禁用"
            update = "有更新" if p.get("hasUpdate") else ""
            rows.append([p.get("shortName", ""), p.get("version", ""), status, update])
        output.print_table(["插件名", "版本", "状态", "更新"], rows, title="已安装插件")


@plugin_group.command("search")
@click.argument("keyword")
@click.pass_context
def plugin_search(ctx, keyword):
    """搜索可用插件（从 Jenkins Update Center）。"""
    results = _search_update_center(keyword)

    fmt = ctx.obj["output_format"]
    if fmt == "json":
        output.print_json(results)
    else:
        if not results:
            click.echo(f"未找到与 '{keyword}' 匹配的插件")
            return
        rows = [[r["name"], r["version"], r["title"]] for r in results]
        output.print_table(["插件名", "最新版本", "标题"], rows, title=f"搜索: {keyword}")


@plugin_group.command("install")
@click.argument("name")
@click.option("--restart", is_flag=True, default=False, help="安装后重启 Jenkins")
@click.pass_context
def plugin_install(ctx, name, restart):
    """安装插件。"""
    conn = ctx.obj["connection"]

    # 检查是否已安装
    installed = _get_installed_plugins(conn)
    for p in installed:
        if p.get("shortName") == name:
            output.print_warn(f"插件 {name} 已安装 (v{p.get('version', '')})")
            return

    click.echo(f"正在安装 {name} ...")
    try:
        resp = conn.api_post(f"/pluginManager/installNecessaryPlugins", data=f"<install><plugin><shortName>{name}</shortName></plugin></install>")
        resp.raise_for_status()
        output.print_ok(f"插件 {name} 已安装")

        if restart:
            click.echo("正在重启 Jenkins ...")
            conn.api_post("/restart")
            output.print_ok("Jenkins 正在重启")
        else:
            click.echo("提示: 部分插件需要重启 Jenkins 才能生效，使用 --restart 参数自动重启")

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 400:
            output.print_err(f"插件 {name} 不存在或无法安装")
        else:
            output.print_err(f"安装失败: {e}")
        sys.exit(1)
    except Exception as e:
        output.print_err(f"安装失败: {e}")
        sys.exit(1)


@plugin_group.command("remove")
@click.argument("name")
@click.pass_context
def plugin_remove(ctx, name):
    """卸载插件。"""
    conn = ctx.obj["connection"]

    # 检查是否存在
    installed = _get_installed_plugins(conn)
    found = None
    for p in installed:
        if p.get("shortName") == name:
            found = p
            break

    if not found:
        output.print_err(f"插件 {name} 未安装")
        sys.exit(1)

    try:
        resp = conn.api_post(f"/pluginManager/plugin/{name}/doUninstall")
        resp.raise_for_status()
        output.print_ok(f"插件 {name} 已卸载")
        click.echo("提示: 需要重启 Jenkins 完成卸载")
    except Exception as e:
        output.print_err(f"卸载失败: {e}")
        sys.exit(1)


@plugin_group.command("update")
@click.argument("name", required=False)
@click.option("--all", "update_all", is_flag=True, default=False, help="更新所有有更新的插件")
@click.pass_context
def plugin_update(ctx, name, update_all):
    """更新插件（单个或全部）。"""
    conn = ctx.obj["connection"]

    installed = _get_installed_plugins(conn)

    if update_all:
        updatable = [p for p in installed if p.get("hasUpdate")]
        if not updatable:
            click.echo("所有插件已是最新版本")
            return
        click.echo(f"正在更新 {len(updatable)} 个插件 ...")
        for p in updatable:
            try:
                conn.api_post(f"/pluginManager/plugin/{p['shortName']}/install")
                output.print_ok(f"{p['shortName']} ({p['version']} → 最新)")
            except Exception as e:
                output.print_err(f"{p['shortName']}: {e}")
        click.echo("\n提示: 部分插件需要重启 Jenkins 才能生效")
    elif name:
        found = None
        for p in installed:
            if p.get("shortName") == name:
                found = p
                break
        if not found:
            output.print_err(f"插件 {name} 未安装")
            sys.exit(1)
        if not found.get("hasUpdate"):
            click.echo(f"插件 {name} 已是最新版本 (v{found.get('version', '')})")
            return
        try:
            conn.api_post(f"/pluginManager/plugin/{name}/install")
            output.print_ok(f"{name} ({found['version']} → 最新)")
            click.echo("提示: 部分插件需要重启 Jenkins 才能生效")
        except Exception as e:
            output.print_err(f"更新失败: {e}")
            sys.exit(1)
    else:
        click.echo("用法: jenkinsctl plugin update <name> 或 jenkinsctl plugin update --all")
        sys.exit(1)


@plugin_group.command("required")
@click.pass_context
def plugin_required(ctx):
    """列出 Shared Library 所需插件。"""
    conn = ctx.obj["connection"]
    required = _load_required_plugins()
    installed = _get_installed_plugins(conn)

    if not required:
        click.echo("未配置 required-plugins.yaml")
        return

    installed_names = {p.get("shortName") for p in installed}

    fmt = ctx.obj["output_format"]
    if fmt == "json":
        for r in required:
            r["installed"] = r["name"] in installed_names
        output.print_json(required)
    else:
        rows = []
        for r in required:
            status = "已安装" if r["name"] in installed_names else "缺失"
            rows.append([r["name"], r.get("description", ""), status])
        output.print_table(["插件名", "说明", "状态"], rows, title="Shared Library 所需插件")

        # 汇总
        missing = [r for r in required if r["name"] not in installed_names]
        if missing:
            click.echo(f"\n缺少 {len(missing)} 个插件，运行以下命令安装:")
            for m in missing:
                click.echo(f"  jenkinsctl plugin install {m['name']}")
        else:
            output.print_ok("所有必需插件已安装")
