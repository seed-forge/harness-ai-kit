---
name: diag-network-port-unreach
description: >
  端口不可达全链诊断。从 DNS 解析 → TCP connect → iptables/firewalld 规则 →
  服务监听状态 → 路由表 → SELinux/AppArmor，逐层排查并输出结构化报告。
---

# Network Port Unreachable Full-Chain Diagnostics

## 用途

当用户报告某个端口/服务不可达、连接超时或被拒绝时触发。

## 输入

- 目标 host:port
- 可选：源机器、协议（TCP/UDP）

## 输出

- 端口连通性诊断报告 + 修复建议

## 诊断步骤

### Step 1: DNS 解析

```bash
# 确认目标地址能解析
dig +short {hostname}
nslookup {hostname}
getent hosts {hostname}
# 如果是 IP 则跳过 DNS
```

### Step 2: TCP 连通性测试

```bash
# 基础连通
nc -zv {host} {port} -w 5
# 或
timeout 5 bash -c "echo > /dev/tcp/{host}/{port}" 2>&1

# 多端口批量测试
for p in {port_list}; do nc -zv {host} $p -w 3 2>&1; done

# 路由追踪
traceroute -T -p {port} {host}
```

### Step 3: 目标端服务监听

```bash
# 服务是否在监听
ss -tlnp | grep :{port}
# 或
netstat -tlnp | grep :{port}

# 绑定地址（127.0.0.1 vs 0.0.0.0）
ss -tlnp | grep :{port} | awk '{print $4}'
```

### Step 4: 防火墙规则

```bash
# iptables
iptables -L INPUT -n --line-numbers | grep {port}
iptables -L FORWARD -n --line-numbers | grep {port}

# firewalld
firewall-cmd --list-all
firewall-cmd --query-port={port}/tcp

# nftables
nft list ruleset | grep {port}

# ufw
ufw status numbered | grep {port}
```

### Step 5: 路由与 NAT

```bash
# 路由表
ip route get {target_ip}
ip route show table all | grep {subnet}

# NAT 规则（端口转发场景）
iptables -t nat -L PREROUTING -n --line-numbers
iptables -t nat -L DNAT -n --line-numbers

# Windows portproxy（如果涉及 Windows 转发）
netsh interface portproxy show all
```

## 输出模板

```
Port Connectivity Diagnosis Report
════════════════════════════════════════
Target:    {host}:{port}
Protocol:  {tcp/udp}
Source:    {source_host}
Time:      {timestamp}

DNS Resolution
  {hostname} → {resolved_ip} (or N/A for IP)

TCP Connect Test
  {host}:{port} → {open/closed/timeout/refused}

Service Listening (target side)
  Port {port}: {listening/not_listening}
  Bind Address: {bind_addr} (127.0.0.1 = local only!)
  Process: {process_name} (PID: {pid})

Firewall Rules
  iptables INPUT:  {rule_or_none}
  firewalld:       {port_status}
  nftables:        {rule_or_none}

Routing
  Path: {source} → {next_hop} → ... → {destination}
  NAT:  {nat_rules_or_none}

Root Cause: {root_cause}

Recommendations
  1. {fix_1}
  2. {fix_2}
```

## 模式分类

| 症状 | 根因 | 修复 |
|------|------|------|
| Connection refused | 服务未监听 | 启动服务 / 检查端口配置 |
| Connection refused + 127.0.0.1 | 只绑定 localhost | 改 bind 为 0.0.0.0 |
| Connection timeout | 防火墙丢弃 / 路由不通 | 开放防火墙 / 检查路由 |
| No route to host | 网络不可达 | 检查路由表和网关 |
| DNS resolution failed | 域名无法解析 | 检查 DNS 配置 |

## 告警阈值

| 指标 | Warning | Critical |
|------|---------|----------|
| Port unreachable | 单端口 | 多端口同时 |
| Response time | > 2s | > 5s |

## 推荐输出格式

执行完毕后，按以下格式输出结果：

```markdown
### {技能名称} 执行报告

**结论**：{根因判定，如"服务未监听"/"防火墙阻断"/"只绑定 localhost"}

**证据**：
- DNS 解析：{hostname} → {resolved_ip} ({status})
- TCP 连通：{host}:{port} → {open/closed/timeout/refused}
- 监听状态：端口={listening/not_listening}, Bind Address={bind_addr}, Process={process_name} (PID:{pid})
- 防火墙规则：iptables={has_rule/no_rule}, firewalld={status}, nftables={status}
- 路由检查：path={route_description}, NAT={nat_status}

**建议**：
1. [Service]  {启动服务或调整 bind 地址为 0.0.0.0}
2. [Firewall] {开放防火墙端口或修正 iptables 规则}
3. [Network]  {修正路由表或 NAT 转发配置}

## 约束

- 诊断命令均为只读。`iptables -A` 等变更操作需明确告知用户并获得确认。
- 不安装额外工具（如 nmap），优先用系统自带的 ss/nc/iptables。

## Quick Reference

| 动作 | 命令 |
|------|------|
| DNS | `dig +short {host}` |
| TCP 测试 | `nc -zv {host} {port} -w 5` |
| 监听状态 | `ss -tlnp \| grep :{port}` |
| iptables | `iptables -L INPUT -n --line-numbers` |
| 路由 | `ip route get {target_ip}` |
| NAT | `iptables -t nat -L PREROUTING -n` |

## 专题引用

无外部 references。如需端口转发运维，联动 `infra-system-env-ops`。
