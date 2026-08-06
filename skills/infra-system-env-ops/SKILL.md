---
name: infra-system-env-ops
description: 基础设施系统环境运维技能。覆盖端口映射/转发/iptables/firewalld/portproxy/SSH tunnel（原 net-ops 能力），以及 Monit 统一看门狗部署、服务崩溃自愈、系统资源监控等企业级系统可靠性实践。当用户提到端口转发、网络连通、看门狗、Monit、服务崩溃恢复、系统可靠性、watchdog 时触发。
---

# infra-system-env-ops

系统环境运维统一入口。v1 聚焦端口联通与转发（iptables/firewalld/portproxy/SSH tunnel），v2 扩展 Monit 统一看门狗、服务崩溃自愈和系统资源监控。

## 你要完成的事

1. 先在当前笔记库中查找已有端口转发笔记、历史命令或同网段案例。
2. 把用户需求整理成结构化信息：
   - 转发机 IP
   - 对外端口
   - 目标内网 IP
   - 目标端口
   - 协议 TCP / UDP / both
   - 操作系统与网络层：Linux、Windows、SSH tunnel、云安全组 / ACL
3. 输出四段式结果：
   - 执行命令
   - 校验命令
   - 持久化方式
   - 回滚命令
4. 若用户明确要求代执行，再根据当前工具链决定是给命令、SSH 执行，还是只做变更方案。

专项诊断技能（`diag-*` namespace，自包含全链 Runbook；本 skill 发现端口不通症状时委派）：

- `diag-network-port-unreach`：端口不可达全链诊断——DNS → TCP → 防火墙 → 监听 → 路由。

## 默认判断

- 用户未说明协议时，默认按 `TCP` 处理，但要显式写出“若业务还需 UDP，再补规则”。
- 用户只给了公网机和目标机端口，默认理解为同端口转发。
- 若目标服务不是本机而是内网地址，优先考虑 `DNAT + FORWARD + POSTROUTING(MASQUERADE)`。
- 若系统是 Ubuntu 且明确使用 `ufw`，补 `ufw route allow` 思路；若是 CentOS/RHEL 且明确使用 `firewalld`，补 `firewall-cmd` 或 direct 规则思路。
- 若系统类型未知，先要求确认 OS；只需要临时联通时，优先给 SSH tunnel 方案；明确是 Linux 才给 `iptables` / `firewalld`；明确是 Windows 才给 `portproxy` / WinNAT。

## 工作流程

### 第一步：复用现有知识

优先搜索这些关键词：

- `端口转发`
- `iptables`
- `DNAT`
- `MASQUERADE`
- `firewall-cmd`
- `portproxy`
- `WinNAT`
- `ssh -L`
- `ssh -R`
- 目标 IP 或端口

如果笔记库已有近似案例，优先沿用原有命令风格。

## 第二步：组装最小可用方案

对典型公网机 A 转发到内网机 B 的 TCP 端口，默认输出这几类命令：

1. 开启 IP 转发
2. `PREROUTING` 的 `DNAT`
3. `FORWARD` 正向放行
4. `FORWARD` 回程放行，优先使用 `conntrack --ctstate ESTABLISHED,RELATED`
5. `POSTROUTING` 的 `MASQUERADE`
6. 必要时补 `INPUT` 放行入口端口

若需 UDP，单独追加 UDP 版本，不与 TCP 混写成含糊描述。

Windows 场景默认区分两类：

1. 本机监听并转发到目标地址：优先说明 `netsh interface portproxy` 只适合 TCP。
2. NAT/容器/虚拟网络转发：优先说明 WinNAT / Hyper-V / Docker 网络的适用条件。

临时联通场景优先输出 SSH tunnel：

1. 本地访问远端内网服务：`ssh -L <local_port>:<target_host>:<target_port> <jump_host>`。
2. 远端反向暴露本地服务：`ssh -R <remote_port>:<target_host>:<target_port> <jump_host>`。

## 第三步：始终附带校验

至少给出：

- `sysctl net.ipv4.ip_forward`
- `iptables -t nat -vnL`
- `iptables -vnL FORWARD`
- `ss -lntp | grep <port>` 或目标服务连通性检查
- 从转发机测试 `telnet` / `nc` 到目标 IP:port 的建议
- Windows 场景补 `netsh interface portproxy show all`、`Get-NetNat` 或 `Test-NetConnection`
- SSH tunnel 场景补本地端口监听、目标端口探测和 tunnel 进程确认

## 第四步：持久化与回滚

默认不要假设规则会自动持久化，必须补一句：

- Debian / Ubuntu 常见为 `iptables-persistent`
- CentOS / RHEL 常见为 `service iptables save`、`iptables-save`、或转为 `firewalld --permanent`
- Windows `portproxy` 规则本身持久化，但要同步检查防火墙放行；WinNAT 需要记录 NAT 名称和映射
- SSH tunnel 默认是临时方案；若用户要求长期运行，应改为 systemd / Windows 服务 / 受控代理方案，而不是后台裸跑

同时给出按本次规则一一对应的删除命令，使用 `-D` 而不是笼统建议“清空规则”。

## 输出格式约定

每次回复尽量按下面顺序：

1. 需求确认
   - `A:外部端口 -> B:内部端口`
   - 协议

2. 执行命令

3. 校验命令

4. 持久化方式

5. 回滚命令

6. 风险提醒
   - 是否影响现有同端口规则
   - 是否还需要云厂商安全组放行
   - 是否需要目标机本身放行防火墙

## 风险边界

- 不要在未确认现状前建议清空整个 `iptables`。
- 不要假设云安全组、机房 ACL、目标机防火墙已经开放。
- 若用户要求“直接执行到生产机”，先确认访问方式和回滚窗口。
- 若发现已有相同端口规则，优先提示冲突，再给替换或删除再添加的方案。

## 参考资料

- 端口转发命令模板见 `references/REFERENCE-IPTABLES-PORT-FORWARD-RECIPES.md`
- Monit 看门狗部署方案见 `references/REFERENCE-MONIT-WATCHDOG.md`

### Playbook 资产（位于 ansible-control 仓库）

| Playbook | 路径 | 说明 |
|----------|------|------|
| `deploy_monit_watchdog` | `Homelab/ansible-control/playbooks/infrastructure/deploy_monit_watchdog.yml` | Monit 统一看门狗一键部署 |
| 模板目录 | `Homelab/ansible-control/playbooks/infrastructure/monit-templates/` | Jinja2 模板（monitrc、服务配置、告警脚本） |

调用方式：
```powershell
.\Homelab\run-ansible-action.ps1 -Action deploy_monit_watchdog -Target <host> -ExtraArgs @('mm_token=<TOKEN>', 'mm_channel_id=<CHANNEL_ID>')
```

---

## v2: Monit 统一看门狗（系统可靠性）

### 背景

服务器关键服务（NetworkManager、SSH、ZeroTier、Docker 等）可能因 OOM、BUG、资源竞争等原因意外崩溃。Monit 作为统一的轻量级看门狗，提供进程监控、自动重启、资源阈值告警和 Mattermost 通知。

### Monit vs systemd-only

| 维度 | systemd-only | Monit |
|------|-------------|-------|
| 进程监控 | 基础（存活检测） | 高级（CPU/内存/负载/端口） |
| 网络端口检测 | ❌ | ✅ |
| 文件系统监控 | ❌ | ✅ |
| 告警通知 | ❌ | ✅ (exec/webhook) |
| 自动重启 | ✅ | ✅ |
| 配置复杂度 | 中等 | 低（单 monitrc） |

### 部署流程

1. 安装 Monit: `apt install -y monit`
2. 配置主文件 `/etc/monit/monitrc`（检查周期、日志、事件队列、系统资源阈值）
3. 配置服务文件 `/etc/monit/conf.d/<service>.conf`（PID 文件 + 自动重启 + 资源阈值）
4. 配置告警脚本 `/usr/local/bin/monit-mattermost-alert.sh`（Mattermost webhook）
5. 测试配置 `monit -t -c /etc/monit/monitrc`
6. 启动 `systemctl enable --now monit`

### Monit 5.31 语法注意

- `if not running` 不被支持，必须用 `if does not exist`
- `set alert script` 不被支持，改用每个 service 中的 `exec` 动作
- ZeroTier 等无 PID 文件的服务需通过 wrapper 脚本创建 PID
- Docker 使用 unix socket 而非 TCP 端口，不需要 port check

### 告警脚本示例

```python
#!/usr/bin/env python3
import json, subprocess, os

payload = {
    "channel_id": "<CHANNEL_ID>",
    "message": f":rotating_light: **{os.environ.get('MONIT_SERVICE','?')}** {os.environ.get('MONIT_EVENT','?')}",
    "props": {"attachments": [{"color": "#FF0000", "text": os.environ.get('MONIT_DESCRIPTION','')}]}
}
subprocess.run(["curl", "-s", "-X", "POST", "-H", "Content-Type: application/json",
    "-H", "Authorization: Bearer <TOKEN>", "-d", json.dumps(payload),
    "https://mattermost.example.com/api/v4/posts"], capture_output=True)
```

### 服务配置模板

```
check process <name> with pidfile /var/run/<name>.pid
    start program = "/bin/systemctl start <name>"
    stop program  = "/bin/systemctl stop <name>"
    if does not exist then restart
    if does not exist then exec "/usr/local/bin/monit-mattermost-alert.sh"
    if cpu usage > 80% for 3 cycles then alert
    if memory usage > 500 MB for 3 cycles then alert
```

### 验证清单

- `monit -t -c /etc/monit/monitrc` → 语法检查通过
- `systemctl is-active monit` → active
- `tail -20 /var/log/monit.log` → 看到服务监控启动
- 手动 `systemctl stop <service>` → Monit 自动重启并发送告警

参考文档：
- references/REFERENCE-README.md
