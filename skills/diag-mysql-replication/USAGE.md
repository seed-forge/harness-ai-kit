# diag-mysql-replication

MySQL 主从延迟全链诊断技能。当主从延迟告警、读写分离数据不一致、或定期复制健康巡检时调用。

自包含 Runbook：内嵌 5 步诊断 SQL、复制配置检查、输出模板、告警阈值表。

## 可直接复制的中文 Prompt

```
请对 MySQL 主从实例执行复制延迟全链诊断：
1. 检查从库复制状态（IO/SQL 线程、延迟秒数、最近错误）
2. 对比主从 GTID / Position 进度
3. 检查从库 SQL 线程瓶颈（大事务、并行复制 worker 状态）
4. 检查复制配置（binlog 格式、并行模式、半同步）
5. 输出结构化报告，包含延迟根因和修复建议

主库连接：{master_host}:{master_port} user={user} password={password}
从库连接：{replica_host}:{replica_port} user={user} password={password}
```
