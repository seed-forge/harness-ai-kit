"""credential 子命令组：凭据管理（credentials.xml 操作）。"""
import subprocess
import sys
import tempfile
import uuid
from typing import Optional

import click

from jenkinsctl import output


# ── XML 操作辅助 ──────────────────────────────────────────

_CRED_CLASSES = {
    "ssh-key": "com.cloudbees.jenkins.plugins.sshcredentials.impl.BasicSSHUserPrivateKey",
    "username-password": "com.cloudbees.plugins.credentials.impl.UsernamePasswordCredentialsImpl",
    "secret-text": "org.jenkinsci.plugins.plaincredentials.impl.StringCredentialsImpl",
}


def _get_cred_list(conn) -> list[dict]:
    """通过 REST API 获取凭据列表（脱敏）。"""
    try:
        data = conn.api_get(
            "/credentials/store/system/domain/_/api/json"
            "?tree=credentials[id,description,typeName]"
        )
        return data.get("credentials", [])
    except Exception as e:
        output.print_err(f"获取凭据列表失败: {e}")
        return []


def _get_cred_detail(conn, cred_id: str) -> Optional[dict]:
    """通过 REST API 获取单个凭据详情。"""
    try:
        data = conn.api_get(
            f"/credentials/store/system/domain/_/credential/{cred_id}/api/json"
            "?tree=id,description,typeName,displayName"
        )
        return data
    except Exception as e:
        output.print_err(f"获取凭据详情失败: {e}")
        return None


# ── CLI 命令 ──────────────────────────────────────────────

@click.group("credential")
def credential_group():
    """凭据管理（增删改查）。"""
    pass


@credential_group.command("list")
@click.pass_context
def credential_list(ctx):
    """列出所有凭据（脱敏显示）。"""
    conn = ctx.obj["connection"]
    creds = _get_cred_list(conn)

    fmt = ctx.obj["output_format"]
    if fmt == "json":
        output.print_json(creds)
    else:
        rows = [[c.get("id", "?"), c.get("typeName", "?"), c.get("description", "")] for c in creds]
        output.print_table(["ID", "类型", "描述"], rows, title="Jenkins 凭据")


@credential_group.command("show")
@click.argument("cred_id")
@click.pass_context
def credential_show(ctx, cred_id):
    """查看凭据详情。"""
    conn = ctx.obj["connection"]
    detail = _get_cred_detail(conn, cred_id)
    if detail is None:
        sys.exit(1)

    fmt = ctx.obj["output_format"]
    if fmt == "json":
        output.print_json(detail)
    else:
        output.print_kv({
            "ID": detail.get("id", ""),
            "类型": detail.get("typeName", ""),
            "描述": detail.get("description", ""),
            "显示名": detail.get("displayName", ""),
        }, title=f"凭据: {cred_id}")


@credential_group.command("add")
@click.option("--type", "cred_type", required=True,
              type=click.Choice(["ssh-key", "username-password", "secret-text"]),
              help="凭据类型")
@click.option("--id", "cred_id", required=True, help="凭据 ID")
@click.option("--description", default="", help="凭据描述")
@click.option("--username", default="root", help="用户名（ssh-key/username-password 类型）")
@click.option("--password", default=None, help="密码（username-password 类型）")
@click.option("--secret", default=None, help="Secret 值（secret-text 类型）")
@click.option("--private-key", default=None, help="私钥内容（ssh-key 类型）")
@click.option("--private-key-file", default=None, help="私钥文件路径（ssh-key 类型）")
@click.option("--generate", is_flag=True, default=False,
              help="自动生成 Ed25519 SSH 密钥对（ssh-key 类型）")
@click.pass_context
def credential_add(ctx, cred_type, cred_id, description, username, password, secret,
                   private_key, private_key_file, generate):
    """添加凭据。

    注意: 此命令需要在 Jenkins 容器内执行（直接操作 credentials.xml），
    或通过 Jenkins REST API（Groovy 脚本）。
    """
    conn = ctx.obj["connection"]

    # 检查凭据是否已存在
    existing = _get_cred_detail(conn, cred_id)
    if existing is not None:
        output.print_err(f"凭据 {cred_id} 已存在")
        sys.exit(1)

    if cred_type == "ssh-key":
        if generate:
            private_key = _generate_ssh_keypair()
            if private_key is None:
                sys.exit(1)
            click.echo(f"已生成 Ed25519 密钥对")
        elif private_key_file:
            from pathlib import Path
            pk_path = Path(private_key_file)
            if not pk_path.exists():
                output.print_err(f"私钥文件不存在: {private_key_file}")
                sys.exit(1)
            private_key = pk_path.read_text(encoding="utf-8")
        elif not private_key:
            output.print_err("ssh-key 类型需要提供 --private-key、--private-key-file 或 --generate")
            sys.exit(1)

        _add_ssh_key_via_groovy(conn, cred_id, description, username, private_key)

    elif cred_type == "username-password":
        if not password:
            output.print_err("username-password 类型需要提供 --password")
            sys.exit(1)
        _add_username_password_via_groovy(conn, cred_id, description, username, password)

    elif cred_type == "secret-text":
        if not secret:
            output.print_err("secret-text 类型需要提供 --secret")
            sys.exit(1)
        _add_secret_text_via_groovy(conn, cred_id, description, secret)

    output.print_ok(f"凭据 {cred_id} ({cred_type}) 已添加")


@credential_group.command("remove")
@click.argument("cred_id")
@click.pass_context
def credential_remove(ctx, cred_id):
    """删除凭据。"""
    conn = ctx.obj["connection"]

    # 检查是否存在
    existing = _get_cred_detail(conn, cred_id)
    if existing is None:
        output.print_err(f"凭据 {cred_id} 不存在")
        sys.exit(1)

    script = f"""
import com.cloudbees.plugins.credentials.*
import com.cloudbees.plugins.credentials.domains.*

def store = Jenkins.instance.getExtensionList(SystemCredentialsProvider.class)[0].getStore()
def domain = Domain.global()
def cred = store.getCredentials(domain).find {{ it.id == '{cred_id}' }}
if (cred) {{
    store.removeCredentials(domain, cred)
    println("DELETED")
}} else {{
    println("NOT_FOUND")
}}
"""
    try:
        resp = conn.api_post("/scriptText", data={"script": script})
        result = resp.text.strip()
        if "DELETED" in result:
            output.print_ok(f"凭据 {cred_id} 已删除")
        else:
            output.print_err(f"删除失败: {result}")
            sys.exit(1)
    except Exception as e:
        output.print_err(f"删除凭据失败: {e}")
        sys.exit(1)


@credential_group.command("rename")
@click.argument("old_id")
@click.argument("new_id")
@click.pass_context
def credential_rename(ctx, old_id, new_id):
    """重命名凭据 ID。

    注意: Jenkins 不直接支持重命名，此命令通过
    读取旧凭据 → 创建新凭据 → 删除旧凭据实现。
    """
    conn = ctx.obj["connection"]

    # 检查旧凭据存在、新 ID 不存在
    old_cred = _get_cred_detail(conn, old_id)
    if old_cred is None:
        output.print_err(f"凭据 {old_id} 不存在")
        sys.exit(1)
    new_cred = _get_cred_detail(conn, new_id)
    if new_cred is not None:
        output.print_err(f"凭据 {new_id} 已存在")
        sys.exit(1)

    script = f"""
import com.cloudbees.plugins.credentials.*
import com.cloudbees.plugins.credentials.domains.*
import com.cloudbees.plugins.credentials.impl.*
import com.cloudbees.jenkins.plugins.sshcredentials.impl.*
import org.jenkinsci.plugins.plaincredentials.impl.*
import hudson.util.Secret

def store = Jenkins.instance.getExtensionList(SystemCredentialsProvider.class)[0].getStore()
def domain = Domain.global()
def oldCred = store.getCredentials(domain).find {{ it.id == '{old_id}' }}
if (!oldCred) {{
    println("ERROR: old credential not found")
    return
}}

Credentials newCred = null
if (oldCred instanceof BasicSSHUserPrivateKey) {{
    newCred = new BasicSSHUserPrivateKey(
        oldCred.getScope(), '{new_id}', oldCred.getUsername(),
        oldCred.getPrivateKeySource(), null, oldCred.getDescription())
}} else if (oldCred instanceof UsernamePasswordCredentialsImpl) {{
    newCred = new UsernamePasswordCredentialsImpl(
        oldCred.getScope(), '{new_id}', oldCred.getDescription(),
        oldCred.getUsername(), oldCred.getPassword().getPlainText())
}} else if (oldCred instanceof StringCredentialsImpl) {{
    newCred = new StringCredentialsImpl(
        oldCred.getScope(), '{new_id}', oldCred.getDescription(),
        oldCred.getSecret())
}} else {{
    println("ERROR: unsupported credential type: " + oldCred.getClass().getName())
    return
}}

store.addCredentials(domain, newCred)
store.removeCredentials(domain, oldCred)
println("RENAMED")
"""
    try:
        resp = conn.api_post("/scriptText", data={"script": script})
        result = resp.text.strip()
        if "RENAMED" in result:
            output.print_ok(f"凭据 {old_id} → {new_id} 重命名成功")
        else:
            output.print_err(f"重命名失败: {result}")
            sys.exit(1)
    except Exception as e:
        output.print_err(f"重命名失败: {e}")
        sys.exit(1)


@credential_group.command("distribute")
@click.argument("cred_id")
@click.option("--target", multiple=True, help="目标服务器 (user@host)，可指定多个")
@click.pass_context
def credential_distribute(ctx, cred_id, target):
    """提取 SSH 公钥并输出分发指引。

    从 Jenkins 凭据中提取 SSH 公钥，显示公钥内容和手动分发步骤。
    不会自动 SSH 到目标服务器（首次需要手动操作）。

    示例:
      jenkinsctl credential distribute 207-deploy-ssh-key
      jenkinsctl credential distribute 207-deploy-ssh-key --target root@203.0.113.207
    """
    conn = ctx.obj["connection"]

    # 提取公钥
    script = f"""
import com.cloudbees.plugins.credentials.*
import com.cloudbees.plugins.credentials.domains.*
import com.cloudbees.jenkins.plugins.sshcredentials.impl.*

import java.security.KeyFactory
import java.security.interfaces.RSAPublicKey
import java.security.spec.RSAPublicKeySpec
import java.util.Base64

def store = Jenkins.instance.getExtensionList(SystemCredentialsProvider.class)[0].getStore()
def domain = Domain.global()
def cred = store.getCredentials(domain).find {{ it.id == '{cred_id}' }}

if (!cred) {{
    println("ERROR: credential not found")
    return
}}

if (!(cred instanceof BasicSSHUserPrivateKey)) {{
    println("ERROR: not an SSH key credential")
    return
}}

// 从私钥推导公钥
import java.io.StringReader
import java.security.PrivateKey
import org.bouncycastle.openssl.PEMParser
import org.bouncycastle.openssl.jcajce.JcaPEMKeyConverter

def privateKeyStr = cred.getPrivateKey()
def pemParser = new PEMParser(new StringReader(privateKeyStr))
def keyPair = pemParser.readObject()

// 尝试多种解析方式
def publicKey = null
try {{
    // Ed25519 / EC key pair
    if (keyPair instanceof java.security.KeyPair) {{
        publicKey = keyPair.getPublic()
    }} else {{
        def converter = new JcaPEMKeyConverter()
        def kp = converter.getKeyPair(keyPair)
        publicKey = kp.getPublic()
    }}
}} catch (Exception e) {{
    // fallback: 直接输出私钥让用户用 ssh-keygen 提取
    println("FALLBACK")
    println(privateKeyStr)
    return
}}

if (publicKey != null) {{
    def encoded = Base64.getEncoder().encodeToString(publicKey.getEncoded())
    def algo = publicKey.getAlgorithm()
    println("PUBLIC_KEY:" + algo + " " + encoded)
}} else {{
    println("FALLBACK")
    println(cred.getPrivateKey())
}}
"""
    try:
        resp = conn.api_post("/scriptText", data={"script": script})
        result = resp.text.strip()

        if "ERROR:" in result:
            error_msg = result.split("ERROR:")[1].strip()
            output.print_err(f"{error_msg}")
            sys.exit(1)

        # 解析公钥
        public_key_line = None
        private_key_fallback = None

        for line in result.split("\n"):
            if line.startswith("PUBLIC_KEY:"):
                public_key_line = line.replace("PUBLIC_KEY:", "").strip()
            elif "FALLBACK" in line:
                private_key_fallback = True

        click.echo()
        click.echo("=" * 60)
        click.echo(f"  SSH 公钥分发指引 — 凭据: {cred_id}")
        click.echo("=" * 60)
        click.echo()

        if public_key_line:
            click.echo("【公钥内容】")
            click.echo(f"  {public_key_line}")
            click.echo()
        elif private_key_fallback:
            click.echo("  [!] 无法自动提取公钥，请手动操作:")
            click.echo("  1. 在 Jenkins 容器内执行:")
            click.echo(f"     docker exec {conn.container} bash")
            click.echo(f"     echo '<私钥内容>' > /tmp/id_key")
            click.echo(f"     ssh-keygen -y -f /tmp/id_key")
            click.echo("  2. 将输出的公钥添加到目标服务器")
            click.echo()

        # 分发指引
        click.echo("【目标服务器操作】")
        if target:
            for t in target:
                click.echo(f"  {t}:")
                click.echo(f"    ssh {t} 'mkdir -p ~/.ssh && echo '{public_key_line or '<公钥内容>'}' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys'")
        else:
            click.echo("  未指定 --target，请手动将公钥添加到目标服务器:")
            click.echo("    ssh <user>@<host> 'mkdir -p ~/.ssh && echo '<公钥>' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys'")

        click.echo()
        click.echo("【验证】")
        if target:
            for t in target:
                click.echo(f"  ssh -o BatchMode=yes {t} 'echo 连接成功'")
        else:
            click.echo("  ssh -o BatchMode=yes <user>@<host> 'echo 连接成功'")

        click.echo()
        click.echo("【警告】")
        click.echo("  - 此命令不会自动 SSH 到目标服务器")
        click.echo("  - 首次配置必须手动完成公钥分发")
        click.echo("  - 分发完成后，deployViaSsh 将自动使用免密登录")
        click.echo("  - 确保目标服务器的 ~/.ssh 目录权限为 700")
        click.echo("  - 确保 authorized_keys 文件权限为 600")
        click.echo()

    except Exception as e:
        output.print_err(f"提取公钥失败: {e}")
        sys.exit(1)


# ── 内部辅助函数 ──────────────────────────────────────────

def _generate_ssh_keypair() -> Optional[str]:
    """生成 Ed25519 SSH 密钥对，返回私钥内容。"""
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            key_path = f"{tmpdir}/id_ed25519"
            subprocess.run(
                ["ssh-keygen", "-t", "ed25519", "-f", key_path, "-N", "", "-q"],
                check=True, capture_output=True,
                encoding="utf-8", errors="replace",
            )
            from pathlib import Path
            return Path(key_path).read_text(encoding="utf-8")
    except Exception as e:
        output.print_err(f"生成 SSH 密钥对失败: {e}")
        return None


def _add_ssh_key_via_groovy(conn, cred_id: str, description: str, username: str, private_key: str):
    """通过 Groovy 脚本添加 SSH 密钥凭据。"""
    # 转义单引号
    pk_escaped = private_key.replace("'", "\\'").replace("\n", "\\n")
    desc_escaped = description.replace("'", "\\'")
    script = f"""
import com.cloudbees.plugins.credentials.*
import com.cloudbees.plugins.credentials.domains.*
import com.cloudbees.jenkins.plugins.sshcredentials.impl.*

def store = Jenkins.instance.getExtensionList(SystemCredentialsProvider.class)[0].getStore()
def domain = Domain.global()
def cred = new BasicSSHUserPrivateKey(
    CredentialsScope.GLOBAL, '{cred_id}', '{username}',
    new BasicSSHUserPrivateKey.DirectEntryPrivateKeySource('{pk_escaped}'),
    null, '{desc_escaped}')
store.addCredentials(domain, cred)
println("ADDED")
"""
    try:
        resp = conn.api_post("/scriptText", data={"script": script})
        result = resp.text.strip()
        if "ADDED" not in result:
            output.print_err(f"添加失败: {result}")
            sys.exit(1)
    except Exception as e:
        output.print_err(f"添加 SSH 密钥失败: {e}")
        sys.exit(1)


def _add_username_password_via_groovy(conn, cred_id: str, description: str, username: str, password: str):
    """通过 Groovy 脚本添加用户名密码凭据。"""
    desc_escaped = description.replace("'", "\\'")
    pw_escaped = password.replace("'", "\\'")
    script = f"""
import com.cloudbees.plugins.credentials.*
import com.cloudbees.plugins.credentials.domains.*
import com.cloudbees.plugins.credentials.impl.*

def store = Jenkins.instance.getExtensionList(SystemCredentialsProvider.class)[0].getStore()
def domain = Domain.global()
def cred = new UsernamePasswordCredentialsImpl(
    CredentialsScope.GLOBAL, '{cred_id}', '{desc_escaped}',
    '{username}', '{pw_escaped}')
store.addCredentials(domain, cred)
println("ADDED")
"""
    try:
        resp = conn.api_post("/scriptText", data={"script": script})
        result = resp.text.strip()
        if "ADDED" not in result:
            output.print_err(f"添加失败: {result}")
            sys.exit(1)
    except Exception as e:
        output.print_err(f"添加凭据失败: {e}")
        sys.exit(1)


def _add_secret_text_via_groovy(conn, cred_id: str, description: str, secret: str):
    """通过 Groovy 脚本添加 Secret Text 凭据。"""
    desc_escaped = description.replace("'", "\\'")
    secret_escaped = secret.replace("'", "\\'")
    script = f"""
import com.cloudbees.plugins.credentials.*
import com.cloudbees.plugins.credentials.domains.*
import org.jenkinsci.plugins.plaincredentials.impl.*
import hudson.util.Secret

def store = Jenkins.instance.getExtensionList(SystemCredentialsProvider.class)[0].getStore()
def domain = Domain.global()
def cred = new StringCredentialsImpl(
    CredentialsScope.GLOBAL, '{cred_id}', '{desc_escaped}',
    Secret.fromString('{secret_escaped}'))
store.addCredentials(domain, cred)
println("ADDED")
"""
    try:
        resp = conn.api_post("/scriptText", data={"script": script})
        result = resp.text.strip()
        if "ADDED" not in result:
            output.print_err(f"添加失败: {result}")
            sys.exit(1)
    except Exception as e:
        output.print_err(f"添加 Secret Text 失败: {e}")
        sys.exit(1)
