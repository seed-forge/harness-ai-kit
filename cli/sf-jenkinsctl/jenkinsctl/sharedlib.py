"""sharedlib 子命令组：Shared Library 管理。"""
import sys

import click

from jenkinsctl import output


@click.group("sharedlib")
def sharedlib_group():
    """Shared Library 管理。"""
    pass


@sharedlib_group.command("list")
@click.pass_context
def sharedlib_list(ctx):
    """列出已注册的 Shared Library。"""
    conn = ctx.obj["connection"]
    script = """
import org.jenkinsci.plugins.workflow.libs.GlobalLibraries
import hudson.model.Jenkins

def libs = GlobalLibraries.get().getLibraries()
libs.each { lib ->
    println(lib.getName() + "|" + lib.getDefaultVersion() + "|" + lib.getRetriever().getClass().getSimpleName())
}
"""
    try:
        resp = conn.api_post("/scriptText", data={"script": script})
        fmt = ctx.obj["output_format"]
        if fmt == "json":
            libs = []
            for line in resp.text.strip().split("\n"):
                if "|" in line:
                    parts = line.split("|")
                    libs.append({"name": parts[0], "version": parts[1], "retriever": parts[2]})
            output.print_json(libs)
        else:
            rows = []
            for line in resp.text.strip().split("\n"):
                if "|" in line and line.strip():
                    parts = line.split("|")
                    rows.append([parts[0], parts[1], parts[2]])
            if rows:
                output.print_table(["名称", "默认版本", "检索器"], rows, title="Shared Libraries")
            else:
                click.echo("未注册 Shared Library")
    except Exception as e:
        output.print_err(f"获取 Shared Library 列表失败: {e}")
        sys.exit(1)


@sharedlib_group.command("register")
@click.option("--name", required=True, help="Library 名称")
@click.option("--repo-url", required=True, help="Git 仓库 URL")
@click.option("--branch", default="main", help="分支名（默认 main）")
@click.option("--credentials-id", default=None, help="Git 凭据 ID")
@click.option("--implicit", is_flag=True, default=False, help="隐式加载（Pipeline 中无需 @Library 声明）")
@click.pass_context
def sharedlib_register(ctx, name, repo_url, branch, credentials_id, implicit):
    """注册 Shared Library（Git SCM + 凭据）。"""
    conn = ctx.obj["connection"]

    cred_xml = ""
    if credentials_id:
        cred_xml = f"<credentialsId>{credentials_id}</credentialsId>"

    implicit_val = "true" if implicit else "false"
    cred_id_val = credentials_id or ""

    script = f"""
import org.jenkinsci.plugins.workflow.libs.*
import hudson.model.Jenkins
import hudson.plugins.git.*

def scm = new GitSCMSource(
    '{repo_url}',
    '{cred_id_val}',
    null, null, null,
    [new BranchDiscoveryTrait()]
)

def retriever = new SCMSourceRetriever(scm)

def lib = new LibraryConfiguration('{name}', retriever)
lib.setDefaultVersion('{branch}')
lib.setImplicit({implicit_val})
lib.setAllowVersionOverride(true)

def globalLibs = GlobalLibraries.get()
def existingLibs = globalLibs.getLibraries().toList()
existingLibs.removeAll {{ it.getName() == '{name}' }}
existingLibs.add(lib)
globalLibs.setLibraries(existingLibs)

Jenkins.instance.save()
println("REGISTERED")
"""
    try:
        resp = conn.api_post("/scriptText", data={"script": script})
        result = resp.text.strip()
        if "REGISTERED" in result:
            output.print_ok(f"Shared Library '{name}' 已注册")
            click.echo(f"  仓库: {repo_url}")
            click.echo(f"  分支: {branch}")
            if credentials_id:
                click.echo(f"  凭据: {credentials_id}")
            if implicit:
                click.echo(f"  隐式加载: 是")
        else:
            output.print_err(f"注册失败: {result}")
            sys.exit(1)
    except Exception as e:
        output.print_err(f"注册失败: {e}")
        sys.exit(1)


@sharedlib_group.command("remove")
@click.argument("name")
@click.pass_context
def sharedlib_remove(ctx, name):
    """移除 Shared Library。"""
    conn = ctx.obj["connection"]

    script = f"""
import org.jenkinsci.plugins.workflow.libs.GlobalLibraries
import hudson.model.Jenkins

def globalLibs = GlobalLibraries.get()
def libs = globalLibs.getLibraries().toList()
def before = libs.size()
libs.removeAll {{ it.getName() == '{name}' }}
if (libs.size() < before) {{
    globalLibs.setLibraries(libs)
    Jenkins.instance.save()
    println("REMOVED")
}} else {{
    println("NOT_FOUND")
}}
"""
    try:
        resp = conn.api_post("/scriptText", data={"script": script})
        result = resp.text.strip()
        if "REMOVED" in result:
            output.print_ok(f"Shared Library '{name}' 已移除")
        elif "NOT_FOUND" in result:
            output.print_err(f"Shared Library '{name}' 不存在")
            sys.exit(1)
        else:
            output.print_err(f"移除失败: {result}")
            sys.exit(1)
    except Exception as e:
        output.print_err(f"移除失败: {e}")
        sys.exit(1)
