"""jenkinsctl CLI 入口：click 命令注册。"""
import sys

import click

from jenkinsctl import __version__
from jenkinsctl.config import load_config
from jenkinsctl.connection import JenkinsConnection
from jenkinsctl import output
from jenkinsctl.credential import credential_group
from jenkinsctl.tool import tool_group
from jenkinsctl.plugin import plugin_group
from jenkinsctl.config_cmd import config_group
from jenkinsctl.user import user_group
from jenkinsctl.job import job_group
from jenkinsctl.build import build_group
from jenkinsctl.sharedlib import sharedlib_group
from jenkinsctl.notify import notify_group
from jenkinsctl.onboard import onboard
from jenkinsctl.scan import scan_group


@click.group()
@click.option("--url", "jenkins_url", default=None, help="Jenkins URL（覆盖配置）")
@click.option("--user", "jenkins_user", default=None, help="Jenkins 用户名（覆盖配置）")
@click.option("--token", "jenkins_api_token", default=None, help="Jenkins API Token（覆盖配置）")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table", help="输出格式")
@click.pass_context
def main(ctx, jenkins_url, jenkins_user, jenkins_api_token, output_format):
    """jenkinsctl - Jenkins 运维 CLI"""
    ctx.ensure_object(dict)
    ctx.obj["output_format"] = output_format
    cli_overrides = {
        k: v for k, v in {
            "jenkins_url": jenkins_url,
            "jenkins_user": jenkins_user,
            "jenkins_api_token": jenkins_api_token,
        }.items() if v is not None
    }
    ctx.obj["config_overrides"] = cli_overrides


def _get_connection(ctx) -> JenkinsConnection:
    """从 click context 获取 JenkinsConnection（延迟初始化）。"""
    if "connection" not in ctx.obj:
        try:
            config = load_config(ctx.obj.get("config_overrides"))
            ctx.obj["connection"] = JenkinsConnection(config)
        except ValueError as e:
            output.print_err(str(e))
            sys.exit(1)
    return ctx.obj["connection"]


# ── version ──────────────────────────────────────────────

@main.command()
@click.pass_context
def version(ctx):
    """显示 CLI + Jenkins 版本信息。"""
    click.echo(f"jenkinsctl {__version__}")
    try:
        conn = _get_connection(ctx)
        jenkins_ver = conn.get_version()
        click.echo(f"Jenkins   {jenkins_ver}")
    except Exception as e:
        click.echo(f"Jenkins   (连接失败: {e})")


# ── status ───────────────────────────────────────────────

@main.command()
@click.pass_context
def status(ctx):
    """显示 Jenkins 状态概览。"""
    conn = _get_connection(ctx)
    try:
        st = conn.get_status()
        jenkins_ver = conn.get_version()
    except Exception as e:
        output.print_err(f"连接 Jenkins 失败: {e}")
        sys.exit(1)

    fmt = ctx.obj["output_format"]
    if fmt == "json":
        output.print_json({"version": jenkins_ver, **st})
    else:
        output.print_kv({
            "版本": jenkins_ver,
            "模式": st["mode"],
            "描述": st["description"],
            "执行器": st["executors"],
            "Agent 数": st["agents"],
            "安全": "启用" if st["security"] else "未启用",
            "视图": ", ".join(st["views"]),
        }, title="Jenkins 状态")


# ── doctor ───────────────────────────────────────────────

@main.command()
@click.pass_context
def doctor(ctx):
    """环境完整性诊断。"""
    click.echo("jenkinsctl doctor - 环境诊断\n")

    # 1. 配置检查
    click.echo("1. 配置检查")
    try:
        config = load_config(ctx.obj.get("config_overrides"))
        output.print_ok(f"配置加载成功 (url={config['jenkins_url']})")
    except ValueError as e:
        output.print_err(str(e))
        sys.exit(1)

    # 2. 连接检查
    click.echo("\n2. 连接检查")
    conn = JenkinsConnection(config)
    try:
        ver = conn.get_version()
        output.print_ok(f"Jenkins 连接成功 (v{ver})")
    except Exception as e:
        output.print_err(f"Jenkins 连接失败: {e}")
        return

    # 3. 插件检查
    click.echo("\n3. 插件检查")
    try:
        plugins = conn.api_get("/pluginManager/api/json?tree=plugins[shortName,version,active]")
        active = [p for p in plugins.get("plugins", []) if p.get("active")]
        output.print_ok(f"已安装插件: {len(plugins.get('plugins', []))} 个（活跃: {len(active)} 个）")
    except Exception as e:
        output.print_warn(f"插件信息获取失败: {e}")

    # 4. 凭据检查
    click.echo("\n4. 凭据检查")
    try:
        creds = conn.api_get("/credentials/store/system/domain/_/api/json?tree=credentials[id,description,typeName]")
        output.print_ok(f"已注册凭据: {len(creds.get('credentials', []))} 个")
        for c in creds.get("credentials", []):
            click.echo(f"    - {c.get('id', '?')} ({c.get('typeName', '?')})")
    except Exception as e:
        output.print_warn(f"凭据信息获取失败: {e}")

    # 5. 工具链检查
    click.echo("\n5. 工具链检查")
    click.echo("  (需要在 Jenkins 容器内执行 'jenkinsctl tool verify' 进行完整检查)")
    click.echo("  提示: 可通过 'jenkinsctl passthrough' 在容器内执行工具检查")

    click.echo("\n诊断完成。")


# ── passthrough ──────────────────────────────────────────

@main.command(context_settings={"ignore_unknown_options": True})
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def passthrough(ctx, args):
    """透传参数给 jenkins-cli.jar。

    示例: jenkinsctl passthrough list-jobs
    """
    if not args:
        click.echo("用法: jenkinsctl passthrough <jenkins-cli 参数...>")
        click.echo("示例: jenkinsctl passthrough list-jobs")
        sys.exit(1)
    conn = _get_connection(ctx)
    exit_code = conn.cli_passthrough(list(args))
    sys.exit(exit_code)


# ── 注册子命令组 ──────────────────────────────────────
main.add_command(credential_group)
main.add_command(tool_group)
main.add_command(plugin_group)
main.add_command(config_group)
main.add_command(user_group)
main.add_command(job_group)
main.add_command(build_group)
main.add_command(sharedlib_group)
main.add_command(notify_group)
main.add_command(onboard)
main.add_command(scan_group)


# ── Role-based access control（CD 受控操作场景，Click 适配）───────
# jenkinsctl 基于 Click，命令分散在多个 group 模块，没有 argparse
# 式的中央 dispatch 点；因此在 entry 层用 argv 前缀做门禁：
# - job build / folder·multibranch create / onboard：CD 日常接入与触发
#   → contributor
# - credential/tool/plugin/config/user/sharedlib 写操作：平台级配置，
#   影响所有流水线与凭据面 → maintainer
# - notify 写：通知渠道配置 → contributor
# - list/get/console/status/version/scan：只读 → 开放
# - passthrough：透传上游 jenkins-cli，由上游自行控制 → 不拦截
_READ_VERBS = {"list", "get", "show", "console", "info", "status", "doctor"}
_GROUP_MINIMUM = {
    "credential": "maintainer",
    "tool": "maintainer",
    "plugin": "maintainer",
    "config": "maintainer",
    "user": "maintainer",
    "sharedlib": "maintainer",
    "job": "contributor",
    "folder": "contributor",
    "notify": "contributor",
}
_TOP_MINIMUM = {"onboard": "contributor"}


def cli_entry() -> None:
    """Entry point wrapper: argv-prefix role gate, then Click dispatch."""
    from jenkinsctl.role import require_role

    argv = [a for a in sys.argv[1:] if not a.startswith("-")]
    if argv:
        group = argv[0]
        sub = argv[1] if len(argv) > 1 else None
        minimum = _TOP_MINIMUM.get(group)
        if minimum:
            require_role(minimum, group)
        elif group in _GROUP_MINIMUM and sub and sub not in _READ_VERBS:
            require_role(_GROUP_MINIMUM[group], f"{group} {sub}")
    main()


if __name__ == "__main__":
    cli_entry()
