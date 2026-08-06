# diag-k8s-node-pressure

K8s 节点资源压力排查技能。当相关症状出现时调用。

自包含 Runbook：内嵌诊断命令、模式分类表、输出模板、告警阈值表。

## 可直接复制的中文 Prompt

```
请对 K8s 节点 {node_name} 执行资源压力全链排查：
1. 获取节点状态和 Conditions（MemoryPressure/DiskPressure/PIDPressure）
2. 获取资源用量（kubectl top nodes/pods）
3. 检查驱逐事件
4. 对比 Allocatable vs Allocated
5. 输出结构化报告，包含 Top 消费者和缓解建议

集群 context: {context}
```
