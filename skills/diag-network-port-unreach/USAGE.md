# diag-network-port-unreach

端口不可达全链诊断技能。当相关症状出现时调用。

自包含 Runbook：内嵌诊断命令、模式分类表、输出模板、告警阈值表。

## 可直接复制的中文 Prompt

```
请对 {host}:{port} 执行端口不可达全链诊断：
1. DNS 解析检查
2. TCP 连通性测试（nc -zv）
3. 目标端服务监听状态（ss -tlnp）
4. 防火墙规则检查（iptables/firewalld）
5. 路由表和 NAT 规则
6. 输出结构化报告，包含根因和修复建议

从 {source_host} 发起测试
```
