---
name: diag-mysql-slow-query
description: >
  MySQL 慢查询全链诊断。开启/分析 slow query log，定位 Top-N 慢 SQL，
  用 EXPLAIN 检查执行计划，识别缺失索引、全表扫描、大结果集、锁等待，
  输出结构化报告与优化建议。支持 MySQL 5.7+ 与 8.0 performance_schema。
---

# MySQL Slow Query Full-Chain Diagnostics

## 用途

当用户报告查询慢、接口超时、或怀疑 SQL 性能问题时触发。覆盖：

- 接口响应变慢，怀疑数据库层
- `SHOW PROCESSLIST` 看到大量 `Sending data` / `Waiting for table metadata lock`
- 慢查询日志告警
- 定期慢 SQL 巡检

本技能是**自包含诊断 Runbook**。

## 输入

- MySQL 连接信息（host / port / user / password）
- 可选：已知慢 SQL 片段或时间段

## 输出

- 慢查询分析报告（填充输出模板）
- Top-N 慢 SQL + EXPLAIN 结果 + 优化建议

## 前置条件

| 项 | 要求 |
|----|------|
| MySQL 权限 | `PROCESS`, `SELECT`（performance_schema） |
| 版本 | MySQL 5.7+（8.0 优先用 performance_schema） |

## 诊断步骤

### Step 1: 检查慢查询日志配置

```sql
SHOW VARIABLES LIKE 'slow_query_log';        -- 是否开启
SHOW VARIABLES LIKE 'slow_query_log_file';   -- 日志路径
SHOW VARIABLES LIKE 'long_query_time';       -- 阈值（秒）
SHOW VARIABLES LIKE 'log_queries_not_using_indexes';  -- 是否记录无索引查询
SHOW VARIABLES LIKE 'min_examined_row_limit';
```

如果未开启，建议临时开启（需 SUPER 权限）：

```sql
SET GLOBAL slow_query_log = ON;
SET GLOBAL long_query_time = 1;
SET GLOBAL log_queries_not_using_indexes = ON;
```

### Step 2: 从 performance_schema 获取 Top-N 慢 SQL（MySQL 8.0+）

```sql
SELECT
  DIGEST_TEXT AS query_pattern,
  COUNT_STAR AS exec_count,
  ROUND(SUM_TIMER_WAIT / 1000000000000, 2) AS total_time_s,
  ROUND(AVG_TIMER_WAIT / 1000000000000, 4) AS avg_time_s,
  SUM_ROWS_EXAMINED AS rows_examined,
  SUM_ROWS_SENT AS rows_sent,
  SUM_NO_INDEX_USED AS no_index_count,
  FIRST_SEEN, LAST_SEEN
FROM performance_schema.events_statements_summary_by_digest
WHERE SCHEMA_NAME IS NOT NULL
  AND DIGEST_TEXT NOT LIKE 'SHOW%'
  AND DIGEST_TEXT NOT LIKE 'SET%'
ORDER BY SUM_TIMER_WAIT DESC
LIMIT 20;
```

### Step 3: EXPLAIN 可疑 SQL

```sql
EXPLAIN FORMAT=JSON {slow_query};
-- 或
EXPLAIN ANALYZE {slow_query};  -- MySQL 8.0.18+
```

关注：
| 字段 | 问题信号 |
|------|---------|
| `type` = ALL | 全表扫描 |
| `rows` >> 实际返回行数 | 扫描过多 |
| `Extra` = Using filesort | 排序未用索引 |
| `Extra` = Using temporary | 临时表 |
| `possible_keys` = NULL | 无可用索引 |

### Step 4: 检查缺失索引

```sql
-- 未使用索引的查询统计（8.0+）
SELECT
  OBJECT_SCHEMA, OBJECT_NAME, INDEX_NAME,
  COUNT_STAR, COUNT_READ, COUNT_WRITE
FROM performance_schema.table_io_waits_summary_by_index_usage
WHERE INDEX_NAME IS NULL
  AND OBJECT_SCHEMA NOT IN ('mysql', 'performance_schema', 'information_schema')
ORDER BY COUNT_STAR DESC
LIMIT 20;
```

### Step 5: 检查表统计信息是否过期

```sql
-- 统计信息最后更新时间（8.0+）
SELECT
  TABLE_SCHEMA, TABLE_NAME,
  TABLE_ROWS, AVG_ROW_LENGTH, DATA_LENGTH, INDEX_LENGTH,
  UPDATE_TIME
FROM information_schema.TABLES
WHERE TABLE_SCHEMA NOT IN ('mysql', 'performance_schema', 'information_schema', 'sys')
ORDER BY TABLE_ROWS DESC
LIMIT 20;

-- 手动刷新统计信息
ANALYZE TABLE {schema}.{table};
```

## 输出模板

```
MySQL Slow Query Analysis Report
════════════════════════════════════════
Instance:        {host}:{port}
Analysis Time:   {timestamp}
Slow Query Log:  {enabled/disabled} (threshold: {long_query_time}s)

Top-10 Slow Queries (by total time)
────────────────────────────────────────
  #1  {query_pattern_1}
      Exec: {exec_count}x | Avg: {avg_time}s | Rows examined: {rows_examined}
      No index used: {no_index_count}x
      Last seen: {last_seen}

  #2  {query_pattern_2}
      ...

EXPLAIN Summary
────────────────────────────────────────
  Query #1: type={type} | rows={rows} | Extra={extra}
  Issue: {full_scan / filesort / temporary / no_index}

Missing Indexes
  | Table           | Column(s)      | Impact        |
  |-----------------|----------------|---------------|
  | {table_1}       | {columns}      | {exec_count}x |

Stale Statistics
  {tables with UPDATE_TIME > 7 days ago}

Root Cause
  {root_cause_analysis}

Recommendations
  1. [Index]  {add_index_suggestion}
  2. [Query]  {rewrite_suggestion}
  3. [Config] {config_suggestion}
```

## 告警阈值

| 指标 | Warning | Critical |
|------|---------|----------|
| Avg query time | > 1s | > 5s |
| Queries without index/min | > 10 | > 50 |
| Full table scans/min | > 100 | > 500 |
| Rows examined/rows sent ratio | > 100:1 | > 1000:1 |

## 推荐输出格式

执行完毕后输出诊断报告：

**结论**：<正常 / 发现问题>

| 排查环节 | 发现 | 证据 |
|---------|------|------|
| ... | {...} | {...} |

**根因**：<定位>
**修复建议**：<可执行步骤>

## 约束

- 所有 SQL 均为**只读查询**。`SET GLOBAL` 仅用于临时开启慢查询日志，诊断完成后建议恢复。
- 不猜测密码；连接信息缺失时提示用户补充。
- `EXPLAIN ANALYZE` 会实际执行查询，确认用户同意后再运行。

## Quick Reference

| 动作 | 查询 |
|------|------|
| 慢查询日志状态 | `SHOW VARIABLES LIKE 'slow_query_log%'` |
| Top 慢 SQL (8.0) | `SELECT ... FROM performance_schema.events_statements_summary_by_digest ORDER BY SUM_TIMER_WAIT DESC` |
| EXPLAIN | `EXPLAIN FORMAT=JSON {sql}` |
| 缺失索引 | `performance_schema.table_io_waits_summary_by_index_usage WHERE INDEX_NAME IS NULL` |
| 刷新统计 | `ANALYZE TABLE {schema}.{table}` |

## 示例

用户说：「db-prod-01 最近接口变慢了，帮忙看看 SQL」

Agent 执行 Step 1-5，输出 Top-10 慢 SQL、EXPLAIN 分析、缺失索引建议。

## 专题引用

无外部 references——本技能为自包含诊断 Runbook。
如需 MySQL 数据源连接管理，联动 `infra-datasource-ops`。
