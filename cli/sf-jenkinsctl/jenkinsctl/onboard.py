"""onboard 组合命令：项目端到端接入。"""
import sys

import click

from jenkinsctl import output


@click.command("onboard")
@click.argument("project_name")
@click.option("--repo-url", required=True, help="Git 仓库 URL")
@click.option("--credentials-id", default=None, help="Git 凭据 ID")
@click.option("--branch", default="main", help="默认分支")
@click.option("--folder", default=None, help="父 Folder 路径")
@click.option("--shared-lib", default=None, help="Shared Library 名称（如已注册则跳过）")
@click.option("--notify-type", default=None,
              type=click.Choice(["mattermost", "slack"]),
              help="通知类型")
@click.option("--webhook-url", default=None, help="Webhook URL（通知用）")
@click.pass_context
def onboard(ctx, project_name, repo_url, credentials_id, branch, folder,
            shared_lib, notify_type, webhook_url):
    """项目端到端接入。

    自动执行:
    1. 注册 Shared Library（如未注册）
    2. 创建 Folder（如指定且不存在）
    3. 创建 Multi-branch Pipeline
    4. 配置通知（如指定）
    5. 输出 onboard 报告

    示例:
      jenkinsctl onboard my-project --repo-url http://git.example.com/my-project.git
    """
    conn = ctx.obj["connection"]
    report = {"steps": [], "warnings": [], "project": project_name}

    click.echo(f"开始接入项目: {project_name}\n")

    # ── Step 1: Shared Library ──
    click.echo("1. Shared Library 检查")
    if shared_lib:
        script = f"""
import org.jenkinsci.plugins.workflow.libs.GlobalLibraries
def libs = GlobalLibraries.get().getLibraries()
def found = libs.find {{ it.getName() == '{shared_lib}' }}
println(found ? "EXISTS" : "NOT_FOUND")
"""
        try:
            resp = conn.api_post("/scriptText", data={"script": script})
            if "NOT_FOUND" in resp.text:
                output.print_warn(f"Shared Library '{shared_lib}' 未注册，请先运行:")
                click.echo(f"  jenkinsctl sharedlib register --name {shared_lib} --repo-url <url>")
                report["warnings"].append(f"Shared Library '{shared_lib}' 未注册")
            else:
                output.print_ok(f"Shared Library '{shared_lib}' 已注册")
                report["steps"].append("sharedlib: verified")
        except Exception as e:
            output.print_warn(f"Shared Library 检查失败: {e}")
    else:
        click.echo("  (跳过 - 未指定 --shared-lib)")

    # ── Step 2: Folder ──
    click.echo("\n2. Folder 创建")
    if folder:
        parts = folder.split("/")
        parent = ""
        for part in parts:
            current_path = "/".join([parent, part]) if parent else part
            script = f"""
import hudson.model.Jenkins
def item = Jenkins.instance.getItemByFullName('{current_path}')
if (item) {{
    println("EXISTS")
}} else {{
    def parentItem
    if ('{parent}') {{
        parentItem = Jenkins.instance.getItemByFullName('{parent}')
    }} else {{
        parentItem = Jenkins.instance
    }}
    def xml = '<com.cloudbees.hudson.plugins.folder.Folder><description>Auto-created by jenkinsctl</description></com.cloudbees.hudson.plugins.folder.Folder>'
    parentItem.createProjectFromXML('{part}', new java.io.ByteArrayInputStream(xml.bytes))
    println("CREATED")
}}
"""
            try:
                resp = conn.api_post("/scriptText", data={"script": script})
                if "CREATED" in resp.text:
                    output.print_ok(f"Folder {current_path} 已创建")
                    report["steps"].append(f"folder: created {current_path}")
                else:
                    output.print_ok(f"Folder {current_path} 已存在")
                    report["steps"].append(f"folder: exists {current_path}")
            except Exception as e:
                output.print_err(f"创建 Folder 失败: {e}")
                report["warnings"].append(f"folder creation failed: {e}")
            parent = current_path
    else:
        click.echo("  (跳过 - 未指定 --folder)")

    # ── Step 3: Multi-branch Pipeline ──
    click.echo("\n3. Multi-branch Pipeline 创建")
    full_name = f"{folder}/{project_name}" if folder else project_name

    # 检查是否已存在
    script = f"""
import hudson.model.Jenkins
def item = Jenkins.instance.getItemByFullName('{full_name}')
println(item ? "EXISTS" : "NOT_FOUND")
"""
    try:
        resp = conn.api_post("/scriptText", data={"script": script})
        if "EXISTS" in resp.text:
            output.print_warn(f"Pipeline {full_name} 已存在，跳过创建")
            report["steps"].append("pipeline: already exists")
        else:
            # 创建 Multi-branch Pipeline
            cred_xml = f"<credentialsId>{credentials_id}</credentialsId>" if credentials_id else ""
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

            parent_path = folder or ""
            create_script = f"""
import hudson.model.Jenkins
def parent
if ('{parent_path}') {{
    parent = Jenkins.instance.getItemByFullName('{parent_path}')
}} else {{
    parent = Jenkins.instance
}}
def xml = '''{config_xml}'''
parent.createProjectFromXML('{project_name}', new java.io.ByteArrayInputStream(xml.bytes))
println("CREATED")
"""
            resp = conn.api_post("/scriptText", data={"script": create_script})
            if "CREATED" in resp.text:
                output.print_ok(f"Pipeline {full_name} 已创建")
                click.echo(f"  仓库: {repo_url}")
                report["steps"].append(f"pipeline: created {full_name}")
            else:
                output.print_err(f"Pipeline 创建失败: {resp.text}")
                report["warnings"].append("pipeline creation failed")
    except Exception as e:
        output.print_err(f"Pipeline 创建失败: {e}")
        report["warnings"].append(f"pipeline error: {e}")

    # ── Step 4: 通知配置 ──
    click.echo("\n4. 通知配置")
    if notify_type and webhook_url:
        # 将 webhook URL 注册为凭据
        cred_id = f"{project_name}-{notify_type}-webhook"
        script = f"""
import com.cloudbees.plugins.credentials.*
import com.cloudbees.plugins.credentials.domains.*
import org.jenkinsci.plugins.plaincredentials.impl.*
import hudson.util.Secret

def store = Jenkins.instance.getExtensionList(SystemCredentialsProvider.class)[0].getStore()
def domain = Domain.global()
def existing = store.getCredentials(domain).find {{ it.id == '{cred_id}' }}
if (existing) {{
    println("EXISTS")
}} else {{
    def cred = new StringCredentialsImpl(
        CredentialsScope.GLOBAL, '{cred_id}',
        '{project_name} {notify_type} webhook',
        Secret.fromString('{webhook_url}'))
    store.addCredentials(domain, cred)
    println("CREATED")
}}
"""
        try:
            resp = conn.api_post("/scriptText", data={"script": script})
            if "CREATED" in resp.text:
                output.print_ok(f"通知凭据 {cred_id} 已注册")
                report["steps"].append(f"notify: {notify_type} webhook registered")
            else:
                output.print_ok(f"通知凭据 {cred_id} 已存在")
                report["steps"].append(f"notify: {notify_type} webhook exists")
        except Exception as e:
            output.print_warn(f"通知配置失败: {e}")
            report["warnings"].append(f"notify error: {e}")
    else:
        click.echo("  (跳过 - 未指定 --notify-type 或 --webhook-url)")

    # ── Step 5: Onboard 报告 ──
    click.echo("\n" + "=" * 50)
    click.echo(f"Onboard 报告: {project_name}")
    click.echo("=" * 50)
    click.echo(f"  仓库: {repo_url}")
    click.echo(f"  Pipeline: {full_name}")
    click.echo(f"  完成步骤: {len(report['steps'])}")
    if report["warnings"]:
        click.echo(f"  警告: {len(report['warnings'])}")
        for w in report["warnings"]:
            click.echo(f"    - {w}")
    click.echo(f"\n下一步:")
    click.echo(f"  1. 在 Pipeline 根目录创建 Jenkinsfile")
    click.echo(f"  2. 触发首次构建:")
    click.echo(f"     jenkinsctl job build {full_name}")
    click.echo(f"  3. 查看构建日志:")
    click.echo(f"     jenkinsctl job console {full_name}")
