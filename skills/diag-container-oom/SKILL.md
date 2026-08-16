---
name: diag-container-oom
description: >
  容器 OOM 全链排查。从 dmesg OOM killer → cgroup memory limits →
  Docker/Compose memory 配置 → swap → 应用内存分析，定位根因并输出修复建议。
---

# Container OOM Full-Chain Diagnostics

## 用途

当容器被 OOM killed、`docker inspect` 显示 `OOMKilled: true`、或系统日志出现 OOM killer 记录时触发。

## 输入

- 目标主机 + 容器名称/ID
- 可选：Compose 文件路径

## 输出

- OOM 根因分析报告 + 修复建议

## 诊断步骤

### Step 1: 确认 OOM 事件

```bash
# 内核 OOM killer 日志
dmesg | grep -i "oom\|killed process" | tail -20
journalctl -k | grep -i oom | tail -20

# Docker 容器 OOM 状态
docker inspect {container} --format='{{.State.OOMKilled}} {{.State.ExitCode}} {{.State.Status}}'

# 最近 OOM 的容器
docker ps -a --filter "status=exited" --format '{{.Names}}: exit={{.Status}}' | head -10
```

### Step 2: Cgroup 内存限制

```bash
# 容器的内存限制
docker inspect {container} --format='Memory limit: {{.HostConfig.Memory}} Swap: {{.HostConfig.MemorySwap}}'

# cgroup v1
cat /sys/fs/cgroup/memory/docker/{container_id}/memory.limit_in_bytes
cat /sys/fs/cgroup/memory/docker/{container_id}/memory.usage_in_bytes
cat /sys/fs/cgroup/memory/docker/{container_id}/memory.max_usage_in_bytes

# cgroup v2
cat /sys/fs/cgroup/system.slice/docker-{container_id}.scope/memory.max
cat /sys/fs/cgroup/system.slice/docker-{container_id}.scope/memory.current
cat /sys/fs/cgroup/system.slice/docker-{container_id}.scope/memory.events
```

### Step 3: Compose / 运行时配置

```bash
# docker-compose.yml 中的 memory 配置
grep -A 5 "deploy\|mem_limit\|memory" docker-compose.yml

# 当前所有容器的内存限制
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.Container}}"
```

### Step 4: 系统内存状态

```bash
# 系统内存
free -h
cat /proc/meminfo | grep -E "MemTotal|MemFree|MemAvailable|SwapTotal|SwapFree|Buffers|Cached"

# Swap 使用
swapon --show

# 高内存进程
ps aux --sort=-%mem | head -15
```

### Step 5: 应用内存分析

```bash
# JVM 应用（如果是 Java 容器）
docker exec {container} jcmd 1 VM.flags | grep -i heap
docker exec {container} jmap -heap 1 2>/dev/null | head -20

# Node.js 应用
docker exec {container} node -e "console.log(process.memoryUsage())"

# Python 应用
docker exec {container} python -c "import resource; print(resource.getrusage(resource.RUSAGE_SELF))"
```

## 输出模板

```
Container OOM Analysis Report
════════════════════════════════════════
Host:      {hostname}
Container: {container_name} ({container_id_short})
Image:     {image_name}
Time:      {timestamp}

OOM Event
  OOMKilled:     {oom_killed}
  Exit Code:     {exit_code}
  dmesg:         {dmesg_oom_line}

Memory Limits
  Cgroup Limit:  {memory_limit} ({limit_human})
  Cgroup Usage:  {memory_usage} ({usage_human})
  Peak Usage:    {peak_usage}
  Swap Limit:    {swap_limit}

Compose Config
  mem_limit:     {compose_mem_limit}
  memswap_limit: {compose_memswap_limit}
  deploy.resources: {deploy_resources}

System Memory
  Total:     {sys_mem_total}
  Available: {sys_mem_available} ({sys_mem_avail_pct}%)
  Swap:      {swap_used}/{swap_total}

Top Memory Consumers
  | Container/Process | Memory | % |
  |-------------------|--------|---|
  | {consumer_1}      | {mem}  | {pct}% |

Application Memory (if accessible)
  {app_memory_details}

Root Cause: {root_cause}

Recommendations
  1. [Limit]   {increase_limit_suggestion}
  2. [App]     {app_memory_fix}
  3. [System]  {system_memory_fix}
```

## 模式分类

| 症状 | 根因 | 修复 |
|------|------|------|
| OOMKilled=true, exit 137 | 容器内存超限 | 增大 `mem_limit` 或修复内存泄漏 |
| dmesg OOM, 容器未受限 | 系统内存耗尽 | 增大系统内存 / 限制其他进程 |
| 无 OOM 但高 MemPerc | 接近限制但未触发 | 预防性增大 / 排查缓慢泄漏 |
| Swap 全满 | 系统 swap 被撑满 | 限制容器 swap / 增大物理内存 |

## 告警阈值

| 指标 | Warning | Critical |
|------|---------|----------|
| Container MemPerc | > 80% | > 95% |
| System MemAvailable | < 20% | < 5% |
| OOM kills/hour | > 1 | > 5 |
| Swap usage | > 50% | > 80% |

## 推荐输出格式

执行完毕后，按以下格式输出结果：

```markdown
### {技能名称} 执行报告

**结论**：{根因判定，如"容器内存超限"/"系统内存耗尽"/"Swap 被撑满"}

**证据**：
- OOM 状态：OOMKilled={true/false}, Exit Code={code}
- 内存限制：{limit_human} (使用率：{usage_pct}%)
- 系统状态：可用内存 {sys_mem_available}, Swap 使用 {swap_used}/{swap_total}
- 关键日志：{dmesg_oom_line}

**建议**：
1. [Limit]   {增加内存限制的具体命令}
2. [App]     {应用侧优化建议}
3. [System]  {系统级优化建议}

## 约束

- `dmesg` 和 `/sys/fs/cgroup` 为只读。
- `docker exec` 进入容器执行分析命令前确认用户同意。
- 不修改 Compose 文件或重启容器。

## Quick Reference

| 动作 | 命令 |
|------|------|
| OOM 日志 | `dmesg \| grep -i oom` |
| 容器 OOM 状态 | `docker inspect {c} --format='{{.State.OOMKilled}}'` |
| 内存限制 | `docker inspect {c} --format='{{.HostConfig.Memory}}'` |
| 实时用量 | `docker stats --no-stream` |
| 系统内存 | `free -h` |

## 专题引用

无外部 references。如需容器部署运维，联动 `compose-app-deploy`。
