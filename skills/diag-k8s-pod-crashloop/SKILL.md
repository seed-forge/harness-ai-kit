---
name: diag-k8s-pod-crashloop
description: >
  K8s Pod CrashLoopBackOff 全链排查。从 kubectl describe → events → logs →
  restart policy → resource limits → liveness/readiness probe → image pull →
  configmap/secret 挂载，定位根因并输出修复建议。
---

# K8s Pod CrashLoopBackOff Full-Chain Diagnostics

## 用途

当 Pod 反复重启、状态显示 `CrashLoopBackOff` 或 `Error` 时触发。本技能是**自包含诊断 Runbook**。

## 输入

- kubectl 上下文（kubeconfig）
- 目标 Pod 名称 + Namespace

## 输出

- CrashLoop 根因分析报告 + 修复建议

## 诊断步骤

### Step 1: Pod 状态与事件

```bash
kubectl get pod {pod_name} -n {namespace} -o wide
kubectl describe pod {pod_name} -n {namespace}
# 关注 Events 区块：OOMKilled / Error / ImagePullBackOff / FailedMount
```

### Step 2: 容器日志

```bash
# 当前容器日志（可能在 crash 后已清空）
kubectl logs {pod_name} -n {namespace} --all-containers=true --tail=100

# 上一次崩溃的日志
kubectl logs {pod_name} -n {namespace} --all-containers=true --previous --tail=200
```

### Step 3: 重启原因分类

| 事件关键词 | 根因 | 典型修复 |
|-----------|------|---------|
| `OOMKilled` | 内存超限 | 增大 `resources.limits.memory` 或修复内存泄漏 |
| `Error` (exit code 1) | 应用启动失败 | 检查日志、配置、依赖服务连通性 |
| `ImagePullBackOff` | 镜像拉取失败 | 检查 image tag、imagePullSecrets、registry 可达 |
| `FailedMount` | ConfigMap/Secret/PVC 挂载失败 | 检查引用是否存在 |
| `Liveness probe failed` | 健康检查超时 | 调整 `initialDelaySeconds` / `timeoutSeconds` |
| `CreateContainerConfigError` | env/configMapKeyRef 缺失 | 检查引用的 ConfigMap/Secret key |
| `BackOff restarting` | 重启间隔递增 | 以上任一原因的持续重试 |

### Step 4: 资源限制与请求

```bash
kubectl get pod {pod_name} -n {namespace} -o jsonpath='{range .spec.containers[*]}{.name}: requests={.resources.requests} limits={.resources.limits}{"\n"}{end}'
```

### Step 5: 依赖检查

```bash
# ConfigMap/Secret 是否存在
kubectl get configmap -n {namespace} | grep {configmap_name}
kubectl get secret -n {namespace} | grep {secret_name}

# PVC 状态
kubectl get pvc -n {namespace} | grep {pvc_name}

# Service 端点
kubectl get endpoints {service_name} -n {namespace}
```

## 输出模板

```
K8s Pod CrashLoop Analysis Report
════════════════════════════════════════
Cluster:   {context}
Namespace: {namespace}
Pod:       {pod_name}
Node:      {node_name}
Time:      {timestamp}

Pod Status
  Phase:         {phase}
  Restart Count: {restart_count}
  Last State:    {last_state} (exit code: {exit_code})
  Reason:        {reason}

Events (last 10)
  {event_1}
  {event_2}
  ...

Container Logs (previous crash, last 20 lines)
  {log_lines}

Root Cause: {root_cause}

Recommendations
  1. {fix_1}
  2. {fix_2}
```

## 告警阈值

| 指标 | Warning | Critical |
|------|---------|----------|
| Pod restarts in 1h | > 3 | > 10 |
| CrashLoopBackOff duration | > 5min | > 30min |
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

- 只读诊断，不执行 `kubectl delete / edit / scale` 等变更操作。
- 不修改 kubeconfig 或切换 context。

## Quick Reference

| 动作 | 命令 |
|------|------|
| Pod 状态 | `kubectl get pod {name} -n {ns} -o wide` |
| Pod 详情 | `kubectl describe pod {name} -n {ns}` |
| 容器日志 | `kubectl logs {name} -n {ns} --previous --tail=200` |
| 资源限制 | `kubectl get pod {name} -n {ns} -o jsonpath='...'` |
| 节点状态 | `kubectl get nodes -o wide` |

## 专题引用

无外部 references。如需 K8s 集群运维，联动 `infra-observability-ops`。
