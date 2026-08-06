# diag-container-oom

容器 OOM 全链排查技能。当相关症状出现时调用。

自包含 Runbook：内嵌诊断命令、模式分类表、输出模板、告警阈值表。

## 可直接复制的中文 Prompt

```
请对主机 {hostname} 上的容器 {container_name} 执行 OOM 全链排查：
1. 确认 OOM 事件（dmesg + docker inspect OOMKilled）
2. 检查 cgroup 内存限制和用量
3. 检查 Compose/运行时的 memory 配置
4. 检查系统内存状态（free/swab）
5. 应用内存分析（如可进入容器）
6. 输出结构化报告，包含根因和修复建议
```
