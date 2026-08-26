"""config_cmd 子命令组：配置管理（config.xml 读写/备份/恢复）。"""
import sys
import shutil
from datetime import datetime

import click

from jenkinsctl import output


@click.group("config")
def config_group():
    """Jenkins 配置管理（读写/备份/恢复）。"""
    pass


@config_group.command("get")
@click.argument("key")
@click.pass_context
def config_get(ctx, key):
    """读取 config.xml 中的值。

    示例: jenkinsctl config get numExecutors
    """
    conn = ctx.obj["connection"]
    script = f"""
import hudson.model.Jenkins
def j = Jenkins.instance
def field = j.getClass().getDeclaredField('{key}')
field.setAccessible(true)
println(field.get(j))
"""
    try:
        resp = conn.api_post("/scriptText", data={"script": script})
        value = resp.text.strip()
        fmt = ctx.obj["output_format"]
        if fmt == "json":
            output.print_json({"key": key, "value": value})
        else:
            click.echo(f"{key} = {value}")
    except Exception as e:
        output.print_err(f"读取配置失败: {e}")
        sys.exit(1)


@config_group.command("set")
@click.argument("key")
@click.argument("value")
@click.option("--restart", is_flag=True, default=False, help="修改后重启 Jenkins")
@click.pass_context
def config_set(ctx, key, value, restart):
    """设置 config.xml 中的值。

    示例: jenkinsctl config set numExecutors 4
    """
    conn = ctx.obj["connection"]
    script = f"""
import hudson.model.Jenkins
def j = Jenkins.instance
j.setNumExecutors({value})
j.save()
println("SAVED")
""" if key == "numExecutors" else f"""
import hudson.model.Jenkins
def j = Jenkins.instance
// Generic setter - tries common patterns
def setter = 'set' + '{key}'.capitalize()
try {{
    j."$setter"('{value}')
    j.save()
    println("SAVED")
}} catch (Exception e) {{
    println("ERROR: " + e.getMessage())
}}
"""
    try:
        resp = conn.api_post("/scriptText", data={"script": script})
        result = resp.text.strip()
        if "SAVED" in result:
            output.print_ok(f"{key} = {value} 已保存")
            if restart:
                click.echo("正在重启 Jenkins ...")
                conn.api_post("/restart")
                output.print_ok("Jenkins 正在重启")
        else:
            output.print_err(f"设置失败: {result}")
            sys.exit(1)
    except Exception as e:
        output.print_err(f"设置配置失败: {e}")
        sys.exit(1)


@config_group.command("show")
@click.pass_context
def config_show(ctx):
    """显示关键配置摘要。"""
    conn = ctx.obj["connection"]
    script = """
import hudson.model.Jenkins
def j = Jenkins.instance
println("numExecutors=" + j.getNumExecutors())
println("mode=" + j.getMode())
println("useSecurity=" + j.isUseSecurity())
println("markupFormatter=" + j.getMarkupFormatter().getClass().getSimpleName())
println("quietPeriod=" + j.getQuietPeriod())
println("scmCheckoutRetryCount=" + j.getScmCheckoutRetryCount())
"""
    try:
        resp = conn.api_post("/scriptText", data={"script": script})
        fmt = ctx.obj["output_format"]
        if fmt == "json":
            data = {}
            for line in resp.text.strip().split("\n"):
                if "=" in line:
                    k, v = line.split("=", 1)
                    data[k.strip()] = v.strip()
            output.print_json(data)
        else:
            kv = {}
            for line in resp.text.strip().split("\n"):
                if "=" in line:
                    k, v = line.split("=", 1)
                    kv[k.strip()] = v.strip()
            output.print_kv(kv, title="Jenkins 配置摘要")
    except Exception as e:
        output.print_err(f"获取配置失败: {e}")
        sys.exit(1)


@config_group.command("backup")
@click.option("--output", "output_path", default=None, help="备份文件路径（默认自动命名）")
@click.pass_context
def config_backup(ctx, output_path):
    """备份 config.xml。

    注意: 此命令通过 Groovy 脚本读取 config.xml 内容，
    需要在 Jenkins 可访问的环境中执行。
    """
    conn = ctx.obj["connection"]
    script = """
import hudson.model.Jenkins
def j = Jenkins.instance
def configFile = new File(j.getRootDir(), "config.xml")
println(configFile.text)
"""
    try:
        resp = conn.api_post("/scriptText", data={"script": script})
        content = resp.text.strip()

        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"jenkins_config_backup_{timestamp}.xml"

        from pathlib import Path
        Path(output_path).write_text(content, encoding="utf-8")
        output.print_ok(f"配置已备份到 {output_path} ({len(content)} bytes)")
    except Exception as e:
        output.print_err(f"备份失败: {e}")
        sys.exit(1)


@config_group.command("restore")
@click.argument("file_path")
@click.option("--restart", is_flag=True, default=False, help="恢复后重启 Jenkins")
@click.pass_context
def config_restore(ctx, file_path, restart):
    """恢复 config.xml。

    注意: 这是危险操作，恢复后需要重启 Jenkins。
    """
    conn = ctx.obj["connection"]

    from pathlib import Path
    backup_file = Path(file_path)
    if not backup_file.exists():
        output.print_err(f"备份文件不存在: {file_path}")
        sys.exit(1)

    content = backup_file.read_text(encoding="utf-8")
    # 基本验证
    if "<hudson>" not in content and "<jenkins>" not in content:
        output.print_err("文件内容不是有效的 Jenkins config.xml")
        sys.exit(1)

    if not click.confirm(f"确定要用 {file_path} 覆盖当前配置？此操作不可逆"):
        click.echo("已取消")
        return

    # 通过 Groovy 写入
    content_escaped = content.replace("\\", "\\\\").replace("'", "\\'")
    script = f"""
import hudson.model.Jenkins
def j = Jenkins.instance
def configFile = new File(j.getRootDir(), "config.xml")
configFile.text = '''{content_escaped}'''
println("RESTORED")
"""
    try:
        resp = conn.api_post("/scriptText", data={"script": script})
        result = resp.text.strip()
        if "RESTORED" in result:
            output.print_ok("config.xml 已恢复")
            if restart:
                click.echo("正在重启 Jenkins ...")
                conn.api_post("/restart")
                output.print_ok("Jenkins 正在重启")
            else:
                click.echo("提示: 需要重启 Jenkins 使配置生效")
        else:
            output.print_err(f"恢复失败: {result}")
            sys.exit(1)
    except Exception as e:
        output.print_err(f"恢复失败: {e}")
        sys.exit(1)
