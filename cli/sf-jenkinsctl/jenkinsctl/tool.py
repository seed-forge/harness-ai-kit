"""tool 子命令组：工具链管理（.tools_env/ + config.xml）。"""
import sys

import click
import yaml

from jenkinsctl import output


# ── 工具元数据 ──────────────────────────────────────────

_TOOL_VERSION_CMDS = {
    "maven": ("bin/mvn", "--version"),
    "jdk": ("bin/java", "-version"),
    "gradle": ("bin/gradle", "--version"),
    "ant": ("bin/ant", "-version"),
    "nodejs": ("bin/node", "--version"),
}

_TOOL_CONFIG_TAGS = {
    "maven": "hudson.tasks.Maven$MavenInstallation",
    "jdk": "hudson.model.JDK",
    "gradle": "hudson.plugins.gradle.GradleInstallation",
    "ant": "hudson.tasks.Ant$AntInstallation",
    "nodejs": "jenkins.plugins.nodejs.tools.NodeJSInstallation",
}


def _scan_tools_dir(conn) -> dict:
    """扫描 .tools_env/ 目录，返回 {名称: 路径} 映射。"""
    tools_env = f"{conn.jenkins_home}/.tools_env"
    script = f"""
import java.io.File
def dir = new File('{tools_env}')
dir.listFiles().each {{ f ->
    println(f.getName() + '|' + f.getAbsolutePath() + '|' + (f.isDirectory() ? 'dir' : 'file') + '|' + (new File(f, 'bin').exists() || f.getName().contains('.') ? 'tool' : 'aux'))
}}
"""
    try:
        resp = conn.api_post("/scriptText", data={"script": script})
        tools = {}
        for line in resp.text.strip().split("\n"):
            line = line.strip()
            if not line or "|" not in line:
                continue
            parts = line.split("|")
            if len(parts) >= 4:
                name, path, ftype, category = parts[0], parts[1], parts[2], parts[3]
                tools[name] = {"path": path, "type": ftype, "category": category}
        return tools
    except Exception as e:
        output.print_err(f"扫描 .tools_env/ 失败: {e}")
        return {}


def _get_registered_tools(conn) -> dict:
    """从 config.xml 获取已注册的工具。"""
    script = """
import hudson.model.Jenkins
def j = Jenkins.instance

// JDK
j.getJDKs().each { jdk ->
    println("jdk|" + jdk.getName() + "|" + jdk.getHome())
}

// Maven
j.getExtensionList(hudson.tasks.Maven.DescriptorImpl.class).each { d ->
    d.getInstallations().each { m ->
        println("maven|" + m.getName() + "|" + m.getHome())
    }
}

// Gradle
try {
    j.getExtensionList(hudson.plugins.gradle.GradleInstallation.DescriptorImpl.class).each { d ->
        d.getInstallations().each { g ->
            println("gradle|" + g.getName() + "|" + g.getHome())
        }
    }
} catch (Exception e) {}

// Ant
j.getExtensionList(hudson.tasks.Ant.DescriptorImpl.class).each { d ->
    d.getInstallations().each { a ->
        println("ant|" + a.getName() + "|" + a.getHome())
    }
}
"""
    try:
        resp = conn.api_post("/scriptText", data={"script": script})
        tools = {}
        for line in resp.text.strip().split("\n"):
            line = line.strip()
            if not line or "|" not in line:
                continue
            parts = line.split("|")
            if len(parts) >= 3:
                tool_type, name, home = parts[0], parts[1], parts[2]
                tools[name] = {"tool_type": tool_type, "home": home}
        return tools
    except Exception as e:
        output.print_warn(f"获取已注册工具失败: {e}")
        return {}


# ── CLI 命令 ──────────────────────────────────────────────

@click.group("tool")
def tool_group():
    """工具链管理（安装/列表/验证）。"""
    pass


@tool_group.command("list")
@click.pass_context
def tool_list(ctx):
    """列出已安装工具 + 版本 + 路径。"""
    conn = ctx.obj["connection"]
    filesystem_tools = _scan_tools_dir(conn)
    registered_tools = _get_registered_tools(conn)

    fmt = ctx.obj["output_format"]
    if fmt == "json":
        output.print_json({
            "filesystem": filesystem_tools,
            "registered": registered_tools,
        })
    else:
        rows = []
        # 合并文件系统扫描结果和已注册工具
        seen = set()
        for name, info in registered_tools.items():
            home = info.get("home", "")
            # 查找对应的 symlink
            for fs_name, fs_info in filesystem_tools.items():
                if fs_info["path"] == home or (fs_info["type"] == "file" and fs_info["path"] in home):
                    rows.append([info["tool_type"], name, fs_name, home])
                    seen.add(fs_name)
                    break
            else:
                rows.append([info["tool_type"], name, "-", home])

        # 未注册的文件系统工具
        for fs_name, fs_info in filesystem_tools.items():
            if fs_name not in seen and fs_info["category"] == "tool":
                rows.append(["unregistered", "-", fs_name, fs_info["path"]])

        output.print_table(["类型", "注册名", "目录名", "路径"], rows, title="Jenkins 工具链")


@tool_group.command("show")
@click.argument("name")
@click.pass_context
def tool_show(ctx, name):
    """查看工具详情。"""
    conn = ctx.obj["connection"]
    registered = _get_registered_tools(conn)
    filesystem = _scan_tools_dir(conn)

    info = registered.get(name) or filesystem.get(name)
    if info is None:
        output.print_err(f"工具 {name} 未找到")
        sys.exit(1)

    fmt = ctx.obj["output_format"]
    if fmt == "json":
        output.print_json({"name": name, **info})
    else:
        output.print_kv({"名称": name, **{k: str(v) for k, v in info.items()}}, title=f"工具: {name}")


@tool_group.command("install")
@click.option("--type", "tool_type", required=True,
              type=click.Choice(["maven", "jdk", "gradle", "ant", "nodejs"]),
              help="工具类型")
@click.option("--version", "tool_version", required=True, help="版本号")
@click.option("--vendor", default=None, help="发行商（jdk: zulu/temurin/openjdk）")
@click.option("--name", "tool_name", default=None, help="注册名称（默认自动生成）")
@click.pass_context
def tool_install(ctx, tool_type, tool_version, vendor, tool_name):
    """安装工具到 .tools_env/。

    示例:
      jenkinsctl tool install --type jdk --version 17 --vendor zulu
      jenkinsctl tool install --type maven --version 3.9.16
    """
    conn = ctx.obj["connection"]

    if not tool_name:
        tool_name = f"{tool_type}-{tool_version}"

    # 构建安装脚本
    script = _build_install_script(conn, tool_type, tool_version, vendor, tool_name)
    if script is None:
        sys.exit(1)

    click.echo(f"正在安装 {tool_type} {tool_version} ...")
    try:
        resp = conn.api_post("/scriptText", data={"script": script})
        result = resp.text.strip()
        if "SUCCESS" in result:
            output.print_ok(f"{tool_type} {tool_version} 安装完成 (注册名: {tool_name})")
            # 提取公钥（如果有）
            for line in result.split("\n"):
                if line.startswith("PUBLIC_KEY:"):
                    click.echo(f"\n公钥 (部署到目标服务器 authorized_keys):")
                    click.echo(line.replace("PUBLIC_KEY:", "").strip())
        else:
            output.print_err(f"安装失败:\n{result}")
            sys.exit(1)
    except Exception as e:
        output.print_err(f"安装失败: {e}")
        sys.exit(1)


@tool_group.command("remove")
@click.argument("name")
@click.pass_context
def tool_remove(ctx, name):
    """移除工具。"""
    conn = ctx.obj["connection"]
    registered = _get_registered_tools(conn)

    info = registered.get(name)
    if info is None:
        output.print_err(f"工具 {name} 未注册")
        sys.exit(1)

    script = f"""
import hudson.model.Jenkins
import java.io.File

def j = Jenkins.instance
def home = '{info["home"]}'
def toolType = '{info["tool_type"]}'

// 从 Jenkins 配置中移除
if (toolType == 'jdk') {{
    def jdks = j.getJDKs()
    jdks.removeAll {{ it.getName() == '{name}' }}
}} else if (toolType == 'maven') {{
    j.getExtensionList(hudson.tasks.Maven.DescriptorImpl.class).each {{ d ->
        def insts = d.getInstallations().toList()
        insts.removeAll {{ it.getName() == '{name}' }}
        d.setInstallations(insts.toArray(new hudson.tasks.Maven.MavenInstallation[0]))
    }}
}}

// 删除文件（如果是 symlink，只删除 symlink + 目标目录）
def f = new File(home)
if (f.exists()) {{
    def canonical = f.getCanonicalFile()
    if (java.nio.file.Files.isSymbolicLink(f.toPath())) {{
        f.delete()
        println("Removed symlink: " + f.getAbsolutePath())
        // 删除目标
        if (canonical.exists() && canonical.getAbsolutePath().contains('.tools_env')) {{
            canonical.deleteDir()
            println("Removed directory: " + canonical.getAbsolutePath())
        }}
    }} else if (f.isDirectory()) {{
        f.deleteDir()
        println("Removed directory: " + home)
    }}
}}

j.save()
println("SUCCESS")
"""
    try:
        resp = conn.api_post("/scriptText", data={"script": script})
        result = resp.text.strip()
        if "SUCCESS" in result:
            output.print_ok(f"工具 {name} 已移除")
        else:
            output.print_err(f"移除失败:\n{result}")
            sys.exit(1)
    except Exception as e:
        output.print_err(f"移除工具失败: {e}")
        sys.exit(1)


@tool_group.command("verify")
@click.pass_context
def tool_verify(ctx):
    """验证所有工具可用性。"""
    conn = ctx.obj["connection"]
    registered = _get_registered_tools(conn)

    if not registered:
        click.echo("未发现已注册工具")
        return

    click.echo("验证工具链可用性:\n")

    for name, info in registered.items():
        home = info.get("home", "")
        tool_type = info.get("tool_type", "")

        version_cmd = _TOOL_VERSION_CMDS.get(tool_type)
        if not version_cmd:
            output.print_warn(f"{name}: 未知类型 {tool_type}")
            continue

        script = f"""
def proc = ['{home}/{version_cmd[0]}', '{version_cmd[1]}'].execute()
proc.waitFor(30000)
def out = proc.err.text + proc.text
println(out.split('\\n').take(3).join('\\n'))
"""
        try:
            resp = conn.api_post("/scriptText", data={"script": script})
            version_line = resp.text.strip().split("\n")[0] if resp.text.strip() else ""
            if version_line and "error" not in version_line.lower():
                output.print_ok(f"{name} ({tool_type}): {version_line[:80]}")
            else:
                output.print_err(f"{name} ({tool_type}): 验证失败 - {version_line or '无输出'}")
        except Exception as e:
            output.print_err(f"{name} ({tool_type}): {e}")


# ── 内部辅助 ──────────────────────────────────────────

def _build_install_script(conn, tool_type: str, version: str, vendor: str, name: str) -> str | None:
    """构建 Groovy 安装脚本。"""
    tools_env = f"{conn.jenkins_home}/.tools_env"

    if tool_type == "jdk":
        vendor = vendor or "zulu"
        if vendor == "zulu":
            # 根据版本确定 Zulu 包名
            jdk_ver = version.split(".")[0]
            return f"""
import java.io.File

def toolsEnv = '{tools_env}'
def version = '{version}'
def vendor = '{vendor}'
def name = '{name}'

// 构建 Zulu JDK 下载 URL (需要根据实际版本调整)
def jdkMajor = version.split('\\\\.')[0] as int
def zuluUrl = "https://cdn.azul.com/zulu/bin/zulu" + version + "-ca-jdk" + version + "-linux_x64.tar.gz"

// 下载并解压
def tarFile = new File(toolsEnv, "zulu-" + version + ".tar.gz")
def extractDir = new File(toolsEnv)

def dlCmd = "wget -q -O " + tarFile.getAbsolutePath() + " " + zdkUrl
def dlProc = dlCmd.execute()
dlProc.waitFor()

if (tarFile.exists() && tarFile.length() > 1000) {{
    def tarProc = ("tar xzf " + tarFile.getAbsolutePath() + " -C " + toolsEnv).execute()
    tarProc.waitFor()
    tarFile.delete()

    // 创建 symlink
    def extractedDirs = extractDir.listFiles().findAll {{ it.name.startsWith("zulu") && it.isDirectory() && it.name.contains(version) }}
    if (extractedDirs) {{
        def target = extractedDirs.sort {{ it.name }}.last()
        def link = new File(toolsEnv, name)
        if (link.exists()) link.delete()
        java.nio.file.Files.createSymbolicLink(link.toPath(), target.toPath())

        // 注册到 Jenkins
        def j = hudson.model.Jenkins.instance
        def jdk = new hudson.model.JDK(name, link.getAbsolutePath())
        j.getJDKs().add(jdk)
        j.save()

        println("SUCCESS")
    }} else {{
        println("ERROR: extracted directory not found")
    }}
}} else {{
    println("ERROR: download failed")
}}
"""
        else:
            output.print_err(f"不支持的 JDK 发行商: {vendor}（目前仅支持 zulu）")
            return None

    elif tool_type == "maven":
        return f"""
import java.io.File

def toolsEnv = '{tools_env}'
def version = '{version}'
def name = '{name}'
def mvnUrl = "https://dlcdn.apache.org/maven/maven-3/" + version + "/binaries/apache-maven-" + version + "-bin.tar.gz"

def tarFile = new File(toolsEnv, "maven-" + version + ".tar.gz")
def dlProc = ("wget -q -O " + tarFile.getAbsolutePath() + " " + mvnUrl).execute()
dlProc.waitFor()

if (tarFile.exists() && tarFile.length() > 1000) {{
    def tarProc = ("tar xzf " + tarFile.getAbsolutePath() + " -C " + toolsEnv).execute()
    tarProc.waitFor()
    tarFile.delete()

    def mvnDir = new File(toolsEnv, "apache-maven-" + version)
    def link = new File(toolsEnv, name)
    if (link.exists()) link.delete()
    java.nio.file.Files.createSymbolicLink(link.toPath(), mvnDir.toPath())

    // 注册到 Jenkins
    def j = hudson.model.Jenkins.instance
    def installation = new hudson.tasks.Maven.MavenInstallation(name, link.getAbsolutePath(), Collections.emptyList())
    j.getExtensionList(hudson.tasks.Maven.DescriptorImpl.class).each {{ d ->
        def insts = d.getInstallations().toList()
        insts.removeAll {{ it.getName() == name }}
        insts.add(installation)
        d.setInstallations(insts.toArray(new hudson.tasks.Maven.MavenInstallation[0]))
    }}
    j.save()
    println("SUCCESS")
}} else {{
    println("ERROR: download failed")
}}
"""

    elif tool_type == "gradle":
        return f"""
import java.io.File

def toolsEnv = '{tools_env}'
def version = '{version}'
def name = '{name}'
def gradleUrl = "https://services.gradle.org/distributions/gradle-" + version + "-bin.zip"

def zipFile = new File(toolsEnv, "gradle-" + version + ".zip")
def dlProc = ("wget -q -O " + zipFile.getAbsolutePath() + " " + gradleUrl).execute()
dlProc.waitFor()

if (zipFile.exists() && zipFile.length() > 1000) {{
    def unzipProc = ("unzip -q " + zipFile.getAbsolutePath() + " -d " + toolsEnv).execute()
    unzipProc.waitFor()
    zipFile.delete()

    def gradleDir = new File(toolsEnv, "gradle-" + version)
    def link = new File(toolsEnv, name)
    if (link.exists()) link.delete()
    java.nio.file.Files.createSymbolicLink(link.toPath(), gradleDir.toPath())

    def j = hudson.model.Jenkins.instance
    j.save()
    println("SUCCESS")
}} else {{
    println("ERROR: download failed")
}}
"""

    elif tool_type == "ant":
        return f"""
import java.io.File

def toolsEnv = '{tools_env}'
def version = '{version}'
def name = '{name}'
def antUrl = "https://dlcdn.apache.org/ant/binaries/apache-ant-" + version + "-bin.tar.gz"

def tarFile = new File(toolsEnv, "ant-" + version + ".tar.gz")
def dlProc = ("wget -q -O " + tarFile.getAbsolutePath() + " " + antUrl).execute()
dlProc.waitFor()

if (tarFile.exists() && tarFile.length() > 1000) {{
    def tarProc = ("tar xzf " + tarFile.getAbsolutePath() + " -C " + toolsEnv).execute()
    tarProc.waitFor()
    tarFile.delete()

    def antDir = new File(toolsEnv, "apache-ant-" + version)
    def link = new File(toolsEnv, name)
    if (link.exists()) link.delete()
    java.nio.file.Files.createSymbolicLink(link.toPath(), antDir.toPath())

    def j = hudson.model.Jenkins.instance
    j.save()
    println("SUCCESS")
}} else {{
    println("ERROR: download failed")
}}
"""

    elif tool_type == "nodejs":
        return f"""
import java.io.File

def toolsEnv = '{tools_env}'
def version = '{version}'
def name = '{name}'
def nodeUrl = "https://nodejs.org/dist/v" + version + "/node-v" + version + "-linux-x64.tar.xz"

def tarFile = new File(toolsEnv, "node-" + version + ".tar.xz")
def dlProc = ("wget -q -O " + tarFile.getAbsolutePath() + " " + nodeUrl).execute()
dlProc.waitFor()

if (tarFile.exists() && tarFile.length() > 1000) {{
    def tarProc = ("tar xJf " + tarFile.getAbsolutePath() + " -C " + toolsEnv).execute()
    tarProc.waitFor()
    tarFile.delete()

    def nodeDir = new File(toolsEnv, "node-v" + version + "-linux-x64")
    def link = new File(toolsEnv, name)
    if (link.exists()) link.delete()
    java.nio.file.Files.createSymbolicLink(link.toPath(), nodeDir.toPath())

    def j = hudson.model.Jenkins.instance
    j.save()
    println("SUCCESS")
}} else {{
    println("ERROR: download failed")
}}
"""
    return None
