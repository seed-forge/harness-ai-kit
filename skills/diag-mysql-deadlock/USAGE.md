# diag-mysql-deadlock

MySQL 死锁全链诊断技能。当应用报 `Error: 1213 Deadlock found` 或监控发现 `Innodb_deadlocks` 增长时调用。

自包含 Runbook：内嵌 5 步诊断 SQL、模式分类表（AB-BA / Gap Lock / FK / Auto-Inc / Lock Upgrade）、结构化报告模板、告警阈值表。

## 可直接复制的中文 Prompt

```
请对 MySQL 实例 {host}:{port} 执行死锁全链诊断：
1. 捕获死锁计数和 InnoDB 状态
2. 检查当前锁等待（谁阻塞谁）
3. 查找运行超过 60 秒的长事务
4. 从 InnoDB 状态中判定死锁模式（AB-BA / Gap Lock / FK / Auto-Inc）
5. 输出结构化分析报告，包含根因和 SQL/代码/配置三级修复建议

连接信息：
- Host: {host}
- Port: {port}
- User: {user}
- Password: {password}
```

## 与 infra-datasource-ops 的关系

`infra-datasource-ops` 是 umbrella：管连接、建库、授权、回填。
`diag-mysql-deadlock` 是专项诊断：当 umbrella 发现死锁症状时委派到本技能。
