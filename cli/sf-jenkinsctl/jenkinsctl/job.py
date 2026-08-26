"""job 子命令组：Job/Folder 管理。"""
import sys

import click

from jenkinsctl import output


@click.group("job")
def job_group():
    """Job/Folder 管理。"""
    pass


@job_group.command("list")
@click.option("--folder", default=None, help="仅列出指定 Folder 下的 Job")
@click.pass_context
def job_list(ctx, folder):
    """列出所有 Job。"""
    conn = ctx.obj["connection"]
    try:
        if folder:
            path = f"/job/{folder}/api/json?tree=jobs[name,color,url]"
        else:
            path = "/api/json?tree=jobs[name,color,url]"
        data = conn.api_get(path)
        jobs = data.get("jobs", [])
        fmt = ctx.obj["output_format"]
        if fmt == "json":
            output.print_json(jobs)
        else:
            rows = []
            for j in jobs:
                color = j.get("color", "")
                # 转换颜色为状态
                status_map = {
                    "blue": "成功", "green": "成功",
                    "red": "失败", "yellow": "不稳定",
                    "aborted": "已中止", "disabled": "已禁用",
                    "notbuilt": "未构建",
                }
                status = status_map.get(color.replace("_anime", ""), color)
                rows.append([j.get("name", "?"), status])
            output.print_table(["Job 名", "状态"], rows, title="Jenkins Jobs")
    except Exception as e:
        output.print_err(f"获取 Job 列表失败: {e}")
        sys.exit(1)


@job_group.command("build")
@click.argument("name")
@click.option("--params", "-p", multiple=True, help="构建参数 (key=value)")
@click.pass_context
def job_build(ctx, name, params):
    """触发构建。"""
    conn = ctx.obj["connection"]
    try:
        if params:
            # 带参数构建
            param_dict = {}
            for p in params:
                if "=" in p:
                    k, v = p.split("=", 1)
                    param_dict[k] = v
            conn.api_post(f"/job/{name}/buildWithParameters", data=param_dict)
        else:
            conn.api_post(f"/job/{name}/build")
        output.print_ok(f"Job {name} 构建已触发")
    except Exception as e:
        output.print_err(f"触发构建失败: {e}")
        sys.exit(1)


@job_group.command("console")
@click.argument("name")
@click.option("--build", "build_num", default=None, help="构建号（默认最新）")
@click.option("--tail", "tail_lines", default=50, help="显示最后 N 行（默认 50）")
@click.pass_context
def job_console(ctx, name, build_num, tail_lines):
    """查看控制台日志。"""
    conn = ctx.obj["connection"]
    try:
        if build_num:
            path = f"/job/{name}/{build_num}/consoleText"
        else:
            path = f"/job/{name}/lastBuild/consoleText"

        resp = conn._session.get(f"{conn.url}{path}", timeout=60)
        resp.raise_for_status()
        text = resp.text
        lines = text.split("\n")

        if len(lines) > tail_lines:
            click.echo(f"... (省略前 {len(lines) - tail_lines} 行)")
            click.echo("\n".join(lines[-tail_lines:]))
        else:
            click.echo(text)
    except Exception as e:
        output.print_err(f"获取控制台日志失败: {e}")
        sys.exit(1)


@job_group.command("get")
@click.argument("name")
@click.pass_context
def job_get(ctx, name):
    """导出 Job 配置 XML。"""
    conn = ctx.obj["connection"]
    try:
        resp = conn._session.get(f"{conn.url}/job/{name}/config.xml", timeout=30)
        resp.raise_for_status()
        click.echo(resp.text)
    except Exception as e:
        output.print_err(f"获取 Job 配置失败: {e}")
        sys.exit(1)


# ── folder 子命令 ──────────────────────────────────────

@job_group.group("folder")
def folder_group():
    """Folder 管理。"""
    pass


@folder_group.command("list")
@click.pass_context
def folder_list(ctx):
    """列出所有 Folder。"""
    conn = ctx.obj["connection"]
    script = """
import com.cloudbees.hudson.plugins.folder.Folder
import hudson.model.Jenkins

def folders = Jenkins.instance.getAllItems(Folder.class)
folders.each { f ->
    println(f.getFullName() + "|" + f.getDescription())
}
"""
    try:
        resp = conn.api_post("/scriptText", data={"script": script})
        fmt = ctx.obj["output_format"]
        if fmt == "json":
            folders = []
            for line in resp.text.strip().split("\n"):
                if "|" in line:
                    parts = line.split("|", 1)
                    folders.append({"name": parts[0], "description": parts[1]})
            output.print_json(folders)
        else:
            rows = []
            for line in resp.text.strip().split("\n"):
                if "|" in line:
                    parts = line.split("|", 1)
                    rows.append([parts[0], parts[1]])
            output.print_table(["Folder 路径", "描述"], rows, title="Jenkins Folders")
    except Exception as e:
        output.print_err(f"获取 Folder 列表失败: {e}")
        sys.exit(1)


@folder_group.command("create")
@click.argument("path")
@click.option("--description", default="", help="Folder 描述")
@click.pass_context
def folder_create(ctx, path, description):
    """创建 Folder。

    示例: jenkinsctl job folder create my-project
    """
    conn = ctx.obj["connection"]

    # 处理多级路径
    parts = path.split("/")
    parent = ""
    for i, part in enumerate(parts):
        current_path = "/".join(parts[: i + 1])
        script = f"""
import com.cloudbees.hudson.plugins.folder.Folder
import hudson.model.Jenkins

def j = Jenkins.instance
def fullName = '{current_path}'
def existing = j.getItemByFullName(fullName)
if (existing) {{
    println("EXISTS")
}} else {{
    def parentPath = '{parent}'
    def parentItem
    if (parentPath) {{
        parentItem = j.getItemByFullName(parentPath)
    }} else {{
        parentItem = j
    }}

    def folderXml = '''<com.cloudbees.hudson.plugins.folder.Folder>
  <description>{description}</description>
</com.cloudbees.hudson.plugins.folder.Folder>'''

    def is = new java.io.ByteArrayInputStream(folderXml.bytes)
    parentItem.createProjectFromXML('{part}', is)
    println("CREATED")
}}
"""
        try:
            resp = conn.api_post("/scriptText", data={"script": script})
            result = resp.text.strip()
            if "CREATED" in result:
                output.print_ok(f"Folder {current_path} 已创建")
            elif "EXISTS" in result:
                output.print_warn(f"Folder {current_path} 已存在")
        except Exception as e:
            output.print_err(f"创建 Folder {current_path} 失败: {e}")
            sys.exit(1)
        parent = current_path


# ── multibranch 子命令 ────────────────────────────────

@job_group.group("multibranch")
def multibranch_group():
    """Multi-branch Pipeline 管理。"""
    pass


@multibranch_group.command("create")
@click.argument("name")
@click.option("--repo-url", required=True, help="Git 仓库 URL")
@click.option("--credentials-id", default=None, help="Git 凭据 ID")
@click.option("--folder", default=None, help="父 Folder 路径")
@click.pass_context
def multibranch_create(ctx, name, repo_url, credentials_id, folder):
    """创建 Multi-branch Pipeline。"""
    conn = ctx.obj["connection"]

    cred_xml = ""
    if credentials_id:
        cred_xml = f"""
        <credentialsId>{credentials_id}</credentialsId>"""

    config_xml = f"""<org.jenkinsci.plugins.workflow.multibranch.WorkflowMultiBranchProject>
  <sources class="jenkins.branch.MultiBranchProject$BranchSourceList">
    <data>
      <jenkins.branch.BranchSource>
        <source class="jenkins.plugins.git.GitSCMSource">
          <remote>{repo_url}</remote>{cred_xml}
          <traits>
            <jenkins.plugins.git.traits.BranchDiscoveryTrait/>
          </traits>
        </source>
      </jenkins.branch.BranchSource>
    </data>
  </sources>
</org.jenkinsci.plugins.workflow.multibranch.WorkflowMultiBranchProject>"""

    parent = folder or ""
    script = f"""
import hudson.model.Jenkins

def j = Jenkins.instance
def parent = j
if ('{parent}') {{
    parent = j.getItemByFullName('{parent}')
    if (!parent) {{
        println("ERROR: parent folder not found: {parent}")
        return
    }}
}}

def xml = '''{config_xml}'''
def is = new java.io.ByteArrayInputStream(xml.bytes)
parent.createProjectFromXML('{name}', is)
println("CREATED")
"""
    try:
        resp = conn.api_post("/scriptText", data={"script": script})
        result = resp.text.strip()
        if "CREATED" in result:
            full_path = f"{parent}/{name}" if parent else name
            output.print_ok(f"Multi-branch Pipeline {full_path} 已创建")
            click.echo(f"  仓库: {repo_url}")
            if credentials_id:
                click.echo(f"  凭据: {credentials_id}")
        else:
            output.print_err(f"创建失败: {result}")
            sys.exit(1)
    except Exception as e:
        output.print_err(f"创建失败: {e}")
        sys.exit(1)
