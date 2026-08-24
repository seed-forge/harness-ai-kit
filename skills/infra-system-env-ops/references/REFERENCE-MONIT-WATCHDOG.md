# REFERENCE-MONIT-WATCHDOG.md

> Monit 统一看门狗部署参考。适用于 Linux 服务器关键服务崩溃自愈、资源监控和 Mattermost 告警集成。

## 适用场景

- 远程开发服务器（如 <host>）需要防止 NetworkManager/SSH/ZeroTier 等基础设施服务意外挂掉
- 需要将服务崩溃告警推送到 Mattermost #alerts 频道
- 需要统一替代 systemd-only 的 Restart=always（Monit 提供更丰富的资源阈值检测）

## 前置条件

| 项 | 要求 |
|---|------|
| OS | Ubuntu 20.04+ / Debian 11+ |
| Monit | 5.31+ (`apt install monit`) |
| Python3 | 用于告警脚本 JSON 生成 |
| curl | 用于 Mattermost API 调用 |
| Mattermost | Bot Token + alerts channel ID |

## 部署架构

```
Monit (daemon, 30s cycle)
  ├── System checks
  │   ├── CPU / Memory / Load Average / Swap
  │   └── Filesystem (space + inode usage)
  │
  ├── Service checks (pidfile / matching)
  │   ├── NetworkManager    → systemctl start/stop
  │   ├── SSH (sshd)        → systemctl start/stop + port 10022
  │   ├── ZeroTier          → wrapper script (no native pidfile)
  │   ├── 1Panel            → systemctl start/stop + port 20443
  │   ├── OpenResty         → docker start/stop + port 80/443
  │   ├── Filebeat          → docker start/stop
  │   ├── systemd-timesyncd → systemctl start/stop
  │   └── systemd-resolved  → systemctl start/stop
  │
  └── Alert pipeline
      └── /usr/local/bin/monit-mattermost-alert.sh → Mattermost #alerts
```

## 关键配置文件

### /etc/monit/monitrc（主配置）

```
set daemon 30 with start delay 60
set logfile /var/log/monit.log
set statefile /var/lib/monit/state
set idfile /var/lib/monit/id
set eventqueue
    basedir /var/lib/monit/events
    slots 100

check system $HOST
    if loadavg (1min) > 4 then alert
    if loadavg (5min) > 2 then alert
    if cpu usage > 80% for 5 cycles then alert
    if memory usage > 80% for 5 cycles then alert
    if swap usage > 25% then alert

check filesystem rootfs with path /
    if space usage > 85% then alert
    if inode usage > 85% then alert

include /etc/monit/conf.d/*.conf
```

### /etc/monit/conf.d/<service>.conf（服务模板）

**systemd 原生服务（有 pidfile）：**

```
check process <name> with pidfile /var/run/<name>.pid
    start program = "/bin/systemctl start <name>"
    stop program  = "/bin/systemctl stop <name>"
    if does not exist then restart
    if does not exist then exec "/usr/local/bin/monit-mattermost-alert.sh"
    if cpu usage > 80% for 3 cycles then alert
    if memory usage > 500 MB for 3 cycles then alert
```

**systemd 原生服务（无 pidfile，用 matching）：**

```
check process <name> matching "<name>"
    start program = "/bin/systemctl start <name>"
    stop program  = "/bin/systemctl stop <name>"
    if does not exist then restart
    if does not exist then exec "/usr/local/bin/monit-mattermost-alert.sh"
```

**Docker 容器服务（需 wrapper 脚本）：**

```
check process <name> with pidfile /var/run/monit-<name>.pid
    start program = "/bin/bash -c '/bin/docker start <container> && sleep 2 && /usr/local/bin/monit-<name>-pid.sh'"
    stop program  = "/bin/docker stop <container>"
    if does not exist then restart
    if does not exist then exec "/usr/local/bin/monit-mattermost-alert.sh"
```

### /usr/local/bin/monit-<container>-pid.sh（Docker PID wrapper）

```bash
#!/bin/bash
PID=$(docker inspect -f '{{.State.Pid}}' <container-name> 2>/dev/null)
if [ -n "$PID" ] && [ "$PID" != "0" ]; then
  echo "$PID" > /var/run/monit-<name>.pid
  exit 0
fi
exit 1
```

需配合 cron 每 5 分钟刷新 PID（容器可能 restart 导致 PID 变化）：

```
*/5 * * * * /usr/local/bin/monit-openresty-pid.sh; /usr/local/bin/monit-filebeat-pid.sh
```

### /usr/local/bin/monit-mattermost-alert.sh（告警脚本）

```python
#!/usr/bin/env python3
import json, subprocess, os

MM_URL = "https://mattermost.example.com"
MM_TOKEN = "<BOT_TOKEN>"
CHANNEL_ID = "<CHANNEL_ID>"

service = os.environ.get("MONIT_SERVICE", "unknown")
event = os.environ.get("MONIT_EVENT", "unknown")
description = os.environ.get("MONIT_DESCRIPTION", "")
date = os.environ.get("MONIT_DATE", "")
host = os.environ.get("MONIT_HOST", os.uname().nodename)

color = "#FF0000" if any(k in event.lower() for k in ["fail", "stop"]) else "#FFA500"

payload = {
    "channel_id": CHANNEL_ID,
    "message": f":rotating_light: **Watchdog** | {host} | {service} | {event}",
    "props": {"attachments": [{"color": color, "title": f"{service} - {event}",
        "text": description, "fields": [
            {"short": True, "title": "Host", "value": host},
            {"short": True, "title": "Event", "value": event},
            {"short": True, "title": "Service", "value": service},
            {"short": True, "title": "Time", "value": date}
        ]}]}
}

subprocess.run(["curl", "-s", "-X", "POST",
    "-H", "Content-Type: application/json",
    "-H", f"Authorization: Bearer {MM_TOKEN}",
    "-d", json.dumps(payload),
    f"{MM_URL}/api/v4/posts"], capture_output=True)
```

## Monit 5.31 语法陷阱

| 错误写法 | 正确写法 | 说明 |
|---------|---------|------|
| `if not running then restart` | `if does not exist then restart` | 5.31 不支持 `not running` |
| `set alert script "/path"` | 每个 service 中用 `exec` | 全局 alert script 不被支持 |
| `if failed port 2376 protocol tcp` (Docker) | 移除（Docker 用 unix socket） | Docker 不监听 TCP |
| `with pidfile /var/run/zerotier-one.pid` | `matching "zerotier"` 或 wrapper | ZeroTier 无原生 pidfile |

## 服务准入标准

纳入 Monit 看门狗的服务必须满足：

1. **基础设施级**：挂掉影响多个应用或整个运维链路
2. **非 Docker self-healing**：没有 `restart: unless-stopped` 或 `--restart` 策略
3. **可检测**：有 PID 文件、进程名匹配、或端口可探测

排除标准：

- Docker daemon（有自己的 restart 策略）
- 业务容器（通过 Compose restart policy 自愈）
- 低频崩溃的辅助服务（成本 > 收益）

## 验证清单

```bash
# 1. 语法检查
monit -t -c /etc/monit/monitrc

# 2. 服务状态
systemctl is-active monit

# 3. 日志确认
tail -20 /var/log/monit.log

# 4. 模拟崩溃测试
sudo systemctl stop <service>
# 等待 30s，Monit 应自动重启并发送告警

# 5. PID 文件验证
ls -la /var/run/monit-*.pid
cat /var/run/monit-openresty.pid  # 应为有效 PID
```

## Ansible 部署

参见 `playbooks/monit-watchdog-deploy.yml`。

## 新机器部署 SOP

1. SSH 到目标机器
2. `apt install -y monit`
3. 执行 Ansible playbook 或手动复制配置文件
4. 修改 `/usr/local/bin/monit-mattermost-alert.sh` 中的 MM_TOKEN 和 CHANNEL_ID
5. `monit -t && systemctl restart monit`
6. 手动 `systemctl stop ssh` 测试自愈 + 告警
