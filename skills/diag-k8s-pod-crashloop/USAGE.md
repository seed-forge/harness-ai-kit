# diag-k8s-pod-crashloop

K8s Pod CrashLoopBackOff 全链排查技能。当相关症状出现时调用。

自包含 Runbook：内嵌诊断命令、模式分类表、输出模板、告警阈值表。

## 可直接复制的中文 Prompt

```
请对 K8s Pod {pod_name} (namespace: {namespace}) 执行 CrashLoopBackOff 全链排查：
1. 获取 Pod 状态和事件（kubectl describe）
2. 获取上一次崩溃的容器日志（kubectl logs --previous）
3. 根据事件关键词分类根因（OOMKilled/ImagePull/FailedMount/Liveness probe）
4. 检查资源限制（requests/limits）
5. 检查依赖（ConfigMap/Secret/PVC）
6. 输出结构化报告

集群 context: {context}
```
