"""scan 子命令组：安全扫描集成（透传 Trivy / SonarQube）。"""
import subprocess
import sys

import click

from jenkinsctl import output


@click.group("scan")
def scan_group():
    """安全扫描（透传 Trivy / SonarQube）。"""
    pass


@scan_group.command("image")
@click.argument("image")
@click.option("--severity", default="HIGH,CRITICAL", help="严重级别过滤（默认 HIGH,CRITICAL）")
@click.option("--format", "output_format", default="table",
              type=click.Choice(["table", "json", "sarif"]),
              help="输出格式")
@click.pass_context
def scan_image(ctx, image, severity, output_format):
    """扫描 Docker 镜像漏洞（需要本地安装 trivy）。

    示例: jenkinsctl scan image my-app:latest
    """
    cmd = [
        "trivy", "image",
        "--severity", severity,
        "--format", output_format,
        "--no-progress",
        image,
    ]

    try:
        result = subprocess.run(cmd, capture_output=False)
        if result.returncode != 0:
            output.print_err(f"Trivy 扫描返回非零退出码: {result.returncode}")
            sys.exit(result.returncode)
    except FileNotFoundError:
        output.print_err("trivy 未安装，请先安装: https://aquasecurity.github.io/trivy/")
        sys.exit(1)


@scan_group.command("deps")
@click.argument("path", default=".")
@click.option("--severity", default="HIGH,CRITICAL", help="严重级别过滤")
@click.option("--format", "output_format", default="table",
              type=click.Choice(["table", "json", "sarif"]),
              help="输出格式")
@click.pass_context
def scan_deps(ctx, path, severity, output_format):
    """扫描依赖漏洞（需要本地安装 trivy）。

    示例: jenkinsctl scan deps ./pom.xml
    """
    cmd = [
        "trivy", "fs",
        "--severity", severity,
        "--format", output_format,
        "--scanners", "vuln",
        path,
    ]

    try:
        result = subprocess.run(cmd, capture_output=False)
        if result.returncode != 0:
            output.print_err(f"Trivy 扫描返回非零退出码: {result.returncode}")
            sys.exit(result.returncode)
    except FileNotFoundError:
        output.print_err("trivy 未安装，请先安装: https://aquasecurity.github.io/trivy/")
        sys.exit(1)


@scan_group.command("config")
@click.argument("path", default=".")
@click.option("--format", "output_format", default="table",
              type=click.Choice(["table", "json"]),
              help="输出格式")
@click.pass_context
def scan_config(ctx, path, output_format):
    """扫描配置文件安全问题（IaC misconfiguration）。

    示例: jenkinsctl scan config ./terraform/
    """
    cmd = [
        "trivy", "config",
        "--format", output_format,
        path,
    ]

    try:
        result = subprocess.run(cmd, capture_output=False)
        if result.returncode != 0:
            output.print_err(f"Trivy 扫描返回非零退出码: {result.returncode}")
            sys.exit(result.returncode)
    except FileNotFoundError:
        output.print_err("trivy 未安装，请先安装: https://aquasecurity.github.io/trivy/")
        sys.exit(1)
