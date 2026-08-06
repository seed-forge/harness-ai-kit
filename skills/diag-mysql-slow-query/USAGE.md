# diag-mysql-slow-query

MySQL 慢查询全链诊断技能。当接口变慢、怀疑 SQL 性能问题、或定期慢 SQL 巡检时调用。

自包含 Runbook：内嵌 5 步诊断 SQL、EXPLAIN 分析要点、输出模板、告警阈值表。

## 可直接复制的中文 Prompt

```
请对 MySQL 实例 {host}:{port} 执行慢查询全链诊断：
1. 检查慢查询日志配置（是否开启、阈值、日志路径）
2. 从 performance_schema 获取 Top-20 慢 SQL（按总耗时排序）
3. 对 Top-3 慢 SQL 执行 EXPLAIN 分析
4. 检查缺失索引（table_io_waits_summary_by_index_usage）
5. 输出结构化报告，包含 Top-N 慢 SQL、EXPLAIN 结果、索引建议

连接信息：
- Host: {host}
- Port: {port}
- User: {user}
- Password: {password}
```
