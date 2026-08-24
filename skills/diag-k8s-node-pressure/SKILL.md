---
name: diag-k8s-node-pressure
description: >
  K8s 节点资源压力排查。CPU/Memory/Disk/PID Pressure 全链诊断：
  kubectl top → describe node → conditions → eviction events → 调度分析，
  输出结构化报告与缓解建议。
---

# K8s Node Pressure Full-Chain Diagnostics

## 用途

当节点出现 `NotReady`、Pod 被驱逐、或监控报节点资源告警时触发。

## 输入

- kubectl 上下文、目标节点名称（可选，默认排查所有）

## 输出

- 节点资源压力报告 + 缓解建议

## 诊断步骤

### Step 1: 节点状态总览

```bash
kubectl get nodes -o wide
kubectl describe node {node_name}
# 关注 Conditions: MemoryPressure / DiskPressure / PIDPressure / Ready
```

### Step 2: 资源用量

```bash
kubectl top nodes
kubectl top pods --all-namespaces --sort-by=memory | head -20
kubectl top pods --all-namespaces --sort-by=cpu | head -20
```

### Step 3: 驱逐事件

```bash
# 最近被驱逐的 Pod
kubectl get events --all-namespaces --field-selector reason=Evicted --sort-by='.lastTimestamp' | tail -20

# 节点上的驱逐历史
kubectl get events --field-selector involvedObject.name={node_name} | grep -i evict
```

### Step 4: Allocatable vs Allocated

```bash
kubectl describe node {node_name} | grep -A 20 "Allocated resources"
# 关注 CPU/ memory requests 占 Allocatable 的百分比
```

### Step 5: 系统级排查

```bash
# 在目标节点上（SSH 或通过 kubectl debug）
df -h                          # 磁盘使用
free -h                        # 内存使用
ps aux --sort=-%mem | head -10 # 高内存进程
dmesg | grep -i oom            # OOM killer
journalctl -u kubelet --since "1 hour ago" | tail -50
```

## 输出模板

```
K8s Node Pressure Analysis Report
════════════════════════════════════════
Cluster: {context}
Node:    {node_name}
Time:    {timestamp}

Node Conditions
  Ready:            {ready}
  MemoryPressure:   {mem_pressure}
  DiskPressure:     {disk_pressure}
  PIDPressure:      {pid_pressure}

Resource Usage
  CPU:     {cpu_used}/{cpu_allocatable} ({cpu_pct}%)
  Memory:  {mem_used}/{mem_allocatable} ({mem_pct}%)
  Disk:    {disk_used}/{disk_total} ({disk_pct}%)
  Pods:    {pod_count}/{pod_max}

Top Consumers (by memory)
  | Pod | Namespace | Memory | CPU |
  |-----|-----------|--------|-----|
  | {pod_1} | {ns_1} | {mem_1} | {cpu_1} |

Evicted Pods (last 10)
  {evicted_pod_1} at {time_1}: {reason_1}

Allocated Resources
  CPU Requests:    {cpu_req_pct}% of allocatable
  Memory Requests: {mem_req_pct}% of allocatable

Root Cause: {root_cause}

Recommendations
  1. {immediate_action}
  2. {scaling_action}
  3. {long_term_fix}
```

## 告警阈值

| 指标 | Warning | Critical |
|------|---------|----------|
| CPU usage | > 80% | > 95% |
| Memory usage | > 80% | > 95% |
| Disk usage | > 85% | > 95% |
| Evictions/hour | > 3 | > 10 |
| Node NotReady | - | 任一 |

## 推荐输出格式

执行完毕后输出诊断报告：

**结论**：<正常 / 发现问题>

| 排查环节 | 发现 | 证据 |
|---------|------|------|
| ... | {...} | {...} |

**根因**：<定位>
**修复建议**：<可执行步骤>

## 约束

- 只读诊断。节点级操作（cordon/drain/reboot）需明确告知用户。
- SSH 到节点属于受控操作，优先通过 `kubectl debug node/` 替代。

## Quick Reference

| 动作 | 命令 |
|------|------|
| 节点状态 | `kubectl get nodes -o wide` |
| 节点详情 | `kubectl describe node {name}` |
| 资源用量 | `kubectl top nodes` |
| Top Pod | `kubectl top pods -A --sort-by=memory` |
| 驱逐事件 | `kubectl get events --field-selector reason=Evicted` |

## 专题引用

无外部 references。如需节点运维，联动 `组织内部集群-ansible-control` 或 `infra-observability-ops`。
