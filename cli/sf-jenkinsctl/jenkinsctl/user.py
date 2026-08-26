"""user 子命令组：用户管理（REST API）。"""
import secrets
import string
import sys

import click

from jenkinsctl import output


@click.group("user")
def user_group():
    """用户管理（增删/token）。"""
    pass


@user_group.command("list")
@click.pass_context
def user_list(ctx):
    """列出所有用户。"""
    conn = ctx.obj["connection"]
    try:
        data = conn.api_get("/asynchPeople/api/json?tree=users[user[fullName,absoluteUrl]]")
        users = data.get("users", [])
        fmt = ctx.obj["output_format"]
        if fmt == "json":
            output.print_json(users)
        else:
            rows = [[u.get("user", {}).get("fullName", "?")] for u in users]
            output.print_table(["用户名"], rows, title="Jenkins 用户")
    except Exception as e:
        output.print_err(f"获取用户列表失败: {e}")
        sys.exit(1)


@user_group.command("add")
@click.argument("username")
@click.option("--fullname", default=None, help="全名（默认同 username）")
@click.option("--email", default=None, help="邮箱")
@click.option("--generate-password", is_flag=True, default=False, help="自动生成随机密码")
@click.pass_context
def user_add(ctx, username, fullname, email, generate_password):
    """创建用户。"""
    conn = ctx.obj["connection"]
    fullname = fullname or username

    password = None
    if generate_password:
        password = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(20))

    # 构建创建用户的 Groovy 脚本
    script = f"""
import hudson.model.User
import jenkins.security.ApiTokenProperty

def user = User.get('{username}', true)
user.setFullName('{fullname}')
"""
    if email:
        script += f"""
import hudson.tasks.Mailer
def mailer = new Mailer.UserProperty('{email}')
user.addProperty(mailer)
"""
    if password:
        script += f"""
import hudson.security.HudsonPrivateSecurityRealm
def realm = jenkins.model.Jenkins.instance.getSecurityRealm()
if (realm instanceof HudsonPrivateSecurityRealm) {{
    realm.createAccount('{username}', '{password}')
}}
"""
    script += """
user.save()
println("CREATED")
"""
    try:
        resp = conn.api_post("/scriptText", data={"script": script})
        result = resp.text.strip()
        if "CREATED" in result:
            output.print_ok(f"用户 {username} 已创建")
            if password:
                click.echo(f"  密码: {password}")
                click.echo("  请妥善保存此密码")
        else:
            output.print_err(f"创建失败: {result}")
            sys.exit(1)
    except Exception as e:
        output.print_err(f"创建用户失败: {e}")
        sys.exit(1)


@user_group.command("remove")
@click.argument("username")
@click.pass_context
def user_remove(ctx, username):
    """删除用户。"""
    conn = ctx.obj["connection"]

    script = f"""
import hudson.model.User
def user = User.get('{username}', false)
if (user) {{
    user.delete()
    println("DELETED")
}} else {{
    println("NOT_FOUND")
}}
"""
    try:
        resp = conn.api_post("/scriptText", data={"script": script})
        result = resp.text.strip()
        if "DELETED" in result:
            output.print_ok(f"用户 {username} 已删除")
        elif "NOT_FOUND" in result:
            output.print_err(f"用户 {username} 不存在")
            sys.exit(1)
        else:
            output.print_err(f"删除失败: {result}")
            sys.exit(1)
    except Exception as e:
        output.print_err(f"删除用户失败: {e}")
        sys.exit(1)


@user_group.command("token")
@click.argument("username")
@click.option("--name", "token_name", default="jenkinsctl-token", help="Token 名称")
@click.pass_context
def user_token(ctx, username, token_name):
    """生成 API Token。"""
    conn = ctx.obj["connection"]

    script = f"""
import hudson.model.User
import jenkins.security.ApiTokenProperty

def user = User.get('{username}', false)
if (!user) {{
    println("NOT_FOUND")
    return
}}

def apiToken = user.getProperty(ApiTokenProperty.class)
if (apiToken == null) {{
    apiToken = new ApiTokenProperty()
    user.addProperty(apiToken)
}}

def result = apiToken.generateNewToken('{token_name}')
println("TOKEN:" + result.plainValue)
"""
    try:
        resp = conn.api_post("/scriptText", data={"script": script})
        result = resp.text.strip()
        if "NOT_FOUND" in result:
            output.print_err(f"用户 {username} 不存在")
            sys.exit(1)
        elif "TOKEN:" in result:
            token = result.split("TOKEN:")[1].strip()
            fmt = ctx.obj["output_format"]
            if fmt == "json":
                output.print_json({"username": username, "token": token})
            else:
                click.echo(f"用户: {username}")
                click.echo(f"Token: {token}")
                click.echo("\n请妥善保存此 Token，它只会显示一次")
        else:
            output.print_err(f"生成 Token 失败: {result}")
            sys.exit(1)
    except Exception as e:
        output.print_err(f"生成 Token 失败: {e}")
        sys.exit(1)
