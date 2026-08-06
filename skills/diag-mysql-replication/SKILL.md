---
name: diag-mysql-replication
description: >
  MySQL 主从延迟全链诊断。检查 replication 状态、定位延迟根因（大事务/网络/从库负载/
  binlog 格式/并行复制配置），输出结构化报告与修复建议。支持异步/半同步/GTID 复制。
---

# MySQL Replication Lag Full-Chain Diagnostics

## 用途

当用户报告主从延迟、读写分离数据不一致、或定期复制健康巡检时触发。

本技能是**自包含诊断 Runbook**。

## 输入

- 主库和从库的 MySQL 连接信息
- 可选：已知延迟时间段或特定大事务

## 输出

- 复制延迟分析报告（填充输出模板）
- 延迟根因 + 修复建议

## 前置条件

| 项 | 要求 |
|----|------|
| 权限 | `REPLICATION CLIENT`, `PROCESS` |
| 版本 | MySQL 5.7+（8.0+ 优先用 performance_schema replication 表） |

## 诊断步骤

### Step 1: 检查复制状态

```sql
-- 从库上执行
SHOW REPLICA STATUS\G          -- MySQL 8.0.22+
SHOW SLAVE STATUS\G            -- MySQL 5.7 / 8.0 < 8.0.22

-- 关键字段
-- Seconds_Behind_Source: 延迟秒数（NULL 表示复制中断）
-- Replica_IO_Running / Replica_SQL_Running: 线程是否正常
-- Last_Error / Last_SQL_Error: 最近的错误信息
-- Retrieved_Gtid_Set / Executed_Gtid_Set: GTID 进度
```

### Step 2: 对比主从 GTID / Position

```sql
-- 主库
SHOW MASTER STATUS;
-- 或 MySQL 8.0+
SHOW BINARY LOG STATUS;

-- 从库
SHOW REPLICA STATUS\G
-- 比较 Master_Log_File/Read_Master_Log_Pos 与 Executed_Gtid_Set
```

### Step 3: 检查从库 SQL 线程瓶颈

```sql
-- 从库当前执行的 SQL
SHOW PROCESSLIST;

-- 大事务检测（从库 relay log 中的大事务）
SELECT * FROM performance_schema.events_transactions_summary_by_thread_by_event_name
WHERE EVENT_NAME LIKE 'transaction%'
ORDER BY COUNT_STAR DESC LIMIT 10;

-- 从库并行复制状态（8.0+）
SELECT * FROM performance_schema.replication_applier_status_by_worker;
```

### Step 4: 检查复制配置

```sql
-- 复制模式
SHOW VARIABLES LIKE 'rpl_semi_sync%';
SHOW VARIABLES LIKE 'slave_parallel_type';      -- LOGICAL_CLOCK / WRITESET
SHOW VARIABLES LIKE 'slave_parallel_workers';
SHOW VARIABLES LIKE 'binlog_format';            -- ROW / MIXED / STATEMENT
SHOW VARIABLES LIKE 'sync_binlog';
SHOW VARIABLES LIKE 'innodb_flush_log_at_trx_commit';
```

### Step 5: 检查网络与 IO 延迟

```sql
-- 从库 IO 线程状态
SHOW REPLICA STATUS\G
-- 关注 Slave_IO_State: "Waiting for source to send event" 可能表示网络问题
-- 关注 Slave_SQL_State: "Reading event relay log" vs "Waiting for dependent transaction"
```

## 输出模板

```
MySQL Replication Lag Analysis Report
════════════════════════════════════════
Master:        {master_host}:{master_port}
Replica:       {replica_host}:{replica_port}
Analysis Time: {timestamp}

Replication Status
  IO Thread:    {io_running} (state: {io_state})
  SQL Thread:   {sql_running} (state: {sql_state})
  Lag:          {seconds_behind}s
  Last Error:   {last_error}

GTID Progress
  Master:   {master_gtid_set}
  Replica:  {replica_gtid_set}
  Gap:      {gtid_gap_description}

Configuration
  Binlog Format:    {binlog_format}
  Parallel Workers: {parallel_workers} ({parallel_type})
  Semi-Sync:        {semi_sync_status}
  sync_binlog:      {sync_binlog}
  flush_log_at_trx: {flush_log_at_trx}

Bottleneck Analysis
  {bottleneck_analysis}

Root Cause
  {root_cause}

Recommendations
  1. [Config] {config_fix}
  2. [SQL]    {sql_fix}
  3. [Infra]  {infra_fix}
```

## 告警阈值

| 指标 | Warning | Critical |
|------|---------|----------|
| Seconds_Behind_Source | > 10s | > 60s |
| IO/SQL Thread stopped | 任一 No | 均 No |
| GTID gap (events) | > 1000 | > 10000 |
| Parallel worker busy | > 80% | 100% |

## 推荐输出格式

执行完毕后输出诊断报告：

**结论**：<正常 / 发现问题>

| 排查环节 | 发现 | 证据 |
|---------|------|------|
| ... | {...} | {...} |

**根因**：<定位>
**修复建议**：<可执行步骤>

## 约束

- 所有 SQL 均为只读查询。`STOP REPLICA / START REPLICA` 等变更操作需明确告知用户。
- 不猜测密码；连接信息缺失时提示用户补充。

## Quick Reference

| 动作 | 查询 |
|------|------|
| 复制状态 | `SHOW REPLICA STATUS\G` |
| 主库位点 | `SHOW MASTER STATUS` / `SHOW BINARY LOG STATUS` |
| 并行复制 | `SELECT * FROM performance_schema.replication_applier_status_by_worker` |
| 半同步状态 | `SHOW STATUS LIKE 'Rpl_semi_sync%'` |
| 当前线程 | `SHOW PROCESSLIST` |

## 专题引用

无外部 references——本技能为自包含诊断 Runbook。
如需 MySQL 数据源连接管理，联动 `infra-datasource-ops`。
