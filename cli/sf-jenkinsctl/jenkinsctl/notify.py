"""notify 子命令组：通知管理（测试 webhook）。"""
import sys

import click
import requests

from jenkinsctl import output


@click.group("notify")
def notify_group():
    """通知管理（测试 webhook）。"""
    pass


@notify_group.command("test")
@click.option("--type", "notify_type", required=True,
              type=click.Choice(["mattermost", "slack", "email"]),
              help="通知类型")
@click.option("--webhook-url", default=None, help="Webhook URL（mattermost/slack）")
@click.option("--channel", default=None, help="目标频道（mattermost/slack）")
@click.option("--message", default="jenkinsctl 测试通知", help="测试消息内容")
@click.option("--smtp-host", default=None, help="SMTP 主机（email 类型）")
@click.option("--smtp-port", default=587, help="SMTP 端口（email 类型）")
@click.pass_context
def notify_test(ctx, notify_type, webhook_url, channel, message, smtp_host, smtp_port):
    """测试通知渠道。"""
    if notify_type == "mattermost":
        _test_mattermost(webhook_url, channel, message)
    elif notify_type == "slack":
        _test_slack(webhook_url, channel, message)
    elif notify_type == "email":
        _test_email(smtp_host, smtp_port, message)


def _test_mattermost(webhook_url, channel, message):
    """测试 Mattermost webhook。"""
    if not webhook_url:
        output.print_err("需要提供 --webhook-url")
        sys.exit(1)

    payload = {"text": message}
    if channel:
        payload["channel"] = channel

    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        if resp.status_code == 200:
            output.print_ok(f"Mattermost 通知发送成功")
            if channel:
                click.echo(f"  频道: {channel}")
        else:
            output.print_err(f"Mattermost 返回 {resp.status_code}: {resp.text}")
            sys.exit(1)
    except Exception as e:
        output.print_err(f"Mattermost 通知失败: {e}")
        sys.exit(1)


def _test_slack(webhook_url, channel, message):
    """测试 Slack webhook。"""
    if not webhook_url:
        output.print_err("需要提供 --webhook-url")
        sys.exit(1)

    payload = {"text": message}
    if channel:
        payload["channel"] = channel

    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        if resp.status_code == 200 and resp.text == "ok":
            output.print_ok("Slack 通知发送成功")
        else:
            output.print_err(f"Slack 返回 {resp.status_code}: {resp.text}")
            sys.exit(1)
    except Exception as e:
        output.print_err(f"Slack 通知失败: {e}")
        sys.exit(1)


def _test_email(smtp_host, smtp_port, message):
    """测试邮件通知（SMTP 连接测试）。"""
    if not smtp_host:
        output.print_err("需要提供 --smtp-host")
        sys.exit(1)

    import smtplib
    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as smtp:
            smtp.ehlo()
            output.print_ok(f"SMTP 连接成功 ({smtp_host}:{smtp_port})")
    except Exception as e:
        output.print_err(f"SMTP 连接失败: {e}")
        sys.exit(1)
