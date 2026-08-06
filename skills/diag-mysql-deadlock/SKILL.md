---
name: diag-mysql-deadlock
description: >
  MySQL 死锁全链诊断。捕获 InnoDB 死锁状态，解析锁链（谁持有什么、谁等待什么），
  分类死锁模式（AB-BA / Gap Lock / FK cascade / Auto-Inc），查找当前锁等待和长事务，
  输出结构化报告并给出修复建议。支持 MySQL 5.7+ performance_schema 与 5.6 兼容回退。
---

# MySQL Deadlock Full-Chain Diagnostics

## 用途

当用户报告 MySQL 死锁或怀疑锁竞争时触发。覆盖：

- 应用日志出现 `Error: 1213 Deadlock found`
- 监控发现 `Innodb_deadlocks` 计数器持续增长
- 高峰期锁竞争排查
- Schema 变更后可能影响锁行为

本技能是**自包含诊断 Runbook**——所有 SQL、模式分类、输出模板、告警阈值都在本文件内，不依赖外部 references。

## 输入

- MySQL 连接信息（host / port / user / password）
- 可选：应用日志中的死锁片段
- 可选：已知的表结构和索引信息

## 输出

- 结构化死锁分析报告（填充输出模板）
- 根因判定 + 修复建议（SQL / 代码 / 配置三级）

## 前置条件

| 项 | 要求 |
|----|------|
| MySQL 权限 | `PROCESS`（查看线程和 InnoDB 状态） |
| 版本 | MySQL 5.6+（5.7+ 使用 performance_schema，5.6 回退 information_schema） |

## 诊断步骤

### Step 1: 捕获死锁计数与最近状态

```sql
-- 死锁计数与锁等待指标
SHOW GLOBAL STATUS LIKE 'Innodb_deadlocks';
SHOW GLOBAL STATUS LIKE 'Innodb_row_lock_waits';
SHOW GLOBAL STATUS LIKE 'Innodb_row_lock_time_avg';

-- 完整 InnoDB 状态（包含 LATEST DETECTED DEADLOCK 区块）
SHOW ENGINE INNODB STATUS;
```

### Step 2: 检查当前锁等待（MySQL 5.7+）

```sql
-- 谁阻塞了谁
SELECT
  waiting_trx.trx_id AS waiting_trx,
  blocking_trx.trx_id AS blocking_trx,
  waiting_trx.trx_state AS wait_state,
  waiting_trx.trx_started AS wait_started,
  LEFT(waiting_trx.trx_query, 200) AS wait_query,
  LEFT(blocking_trx.trx_query, 200) AS block_query
FROM performance_schema.data_lock_waits w
JOIN information_schema.innodb_trx waiting_trx ON w.requesting_engine_transaction_id = waiting_trx.trx_id
JOIN information_schema.innodb_trx blocking_trx ON w.blocking_engine_transaction_id = blocking_trx.trx_id;

-- MySQL 5.6 回退:
SELECT * FROM information_schema.innodb_trx ORDER BY trx_started;
```

### Step 3: 查找长事务

```sql
-- 运行超过 60 秒的事务
SELECT
  trx_id, trx_state, trx_started,
  TIMESTAMPDIFF(SECOND, trx_started, NOW()) AS duration_sec,
  trx_tables_locked, trx_rows_locked,
  LEFT(trx_query, 200) AS current_query
FROM information_schema.innodb_trx
WHERE TIMESTAMPDIFF(SECOND, trx_started, NOW()) > 60
ORDER BY trx_started;
```

### Step 4: 判定死锁模式

从 `SHOW ENGINE INNODB STATUS` 的 LATEST DETECTED DEADLOCK 区块提取并分类：

| 模式 | 特征 | 典型修复 |
|------|------|---------|
| **AB-BA** | 事务 A 锁行1→行2，B 锁行2→行1 | 统一访问顺序 |
| **Gap Lock** | Next-key lock 在索引间隙上 | 缩小扫描范围、使用 RC 隔离级别 |
| **FK Cascade** | 外键触发级联锁 | 在 FK 列上加索引 |
| **Auto-Inc** | 并发 insert 竞争自增锁 | `innodb_autoinc_lock_mode=2` |
| **Lock Upgrade** | S-lock 升级为 X-lock | 缩小事务范围 |

### Step 5: 检查配置

```sql
SHOW VARIABLES LIKE 'innodb_print_all_deadlocks';
SHOW VARIABLES LIKE 'tx_isolation';
SHOW VARIABLES LIKE 'innodb_lock_wait_timeout';
SHOW VARIABLES LIKE 'innodb_autoinc_lock_mode';
```

## 输出模板

```
MySQL Deadlock Analysis Report
════════════════════════════════════════
Instance:       {host}:{port}
Analysis Time:  {timestamp}
MySQL Version:  {version}

Deadlock Status
  Total Deadlocks:   {deadlock_count}
  Row Lock Waits:    {lock_waits_count}
  Avg Lock Wait:     {avg_lock_wait_ms}ms

Latest Deadlock (from InnoDB Status)
────────────────────────────────────────
  Transaction A (ID: {trx_a_id})
    Status:   {status_a}   Duration: {duration_a}s
    Holds:    {holds_a}
    Waits:    {waits_a}
    SQL:      {sql_a}

  Transaction B (ID: {trx_b_id})
    Status:   {status_b}   Duration: {duration_b}s
    Holds:    {holds_b}
    Waits:    {waits_b}
    SQL:      {sql_b}

  Pattern: {AB-BA / Gap Lock / FK Cascade / Auto-Inc / Lock Upgrade}

Current Lock Waits
  {blocking_trx} → {waiting_trx} | {wait_query}

Long Transactions ({long_trx_count} found)
  | Trx ID  | Duration | State    | SQL          |
  |---------|----------|----------|--------------|
  | {trx_id}| {dur}s   | {state}  | {sql_snippet}|

Root Cause
  {root_cause_analysis}

Recommendations
  1. [SQL]    {sql_level_fix}
  2. [Code]   {code_level_fix}
  3. [Config] {config_level_fix}
```

## 告警阈值

适用于 Grafana / Prometheus 监控集成：

| 指标 | Warning | Critical |
|------|---------|----------|
| Deadlocks/min | > 1 | > 5 |
| Row lock waits/min | > 100 | > 500 |
| Avg lock wait | > 100ms | > 500ms |
| Long transactions (>60s) | > 3 | > 10 |

## 推荐输出格式

执行完毕后按以下结构输出：

**状态**：✅ 成功 / ⚠️ 部分成功 / ❌ 失败

| <结论/证据/建议> | <值/状态> | 说明 |
|------|------|------|

**下一步**：<可执行动作>
MySQL Deadlock Analysis Report
════════════════════════════════════════
Instance:       db-prod-01:3306
Analysis Time:  2026-07-08 23:30:00
MySQL Version:  8.0.35

Deadlock Status
  Total Deadlocks:   12
  Row Lock Waits:    847
  Avg Lock Wait:     42ms

Latest Deadlock: Pattern = AB-BA
  Transaction A: UPDATE orders SET status='paid' WHERE id=1001
  Transaction B: UPDATE inventory SET qty=qty-1 WHERE product_id=55

Root Cause: 两个事务以不同顺序访问 orders 和 inventory 表。

Recommendations
  1. [SQL]    ALTER TABLE inventory ADD INDEX idx_product_id (product_id)
  2. [Code]   统一事务内访问顺序：先 orders 后 inventory
  3. [Config] SET GLOBAL innodb_print_all_deadlocks = ON
```

## 专题引用

无外部 references——本技能为自包含诊断 Runbook。
如需 MySQL 数据源连接管理，联动 `infra-datasource-ops`。
