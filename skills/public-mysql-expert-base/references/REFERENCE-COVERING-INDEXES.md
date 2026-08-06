# Covering Indexes

A covering index contains all columns a query needs — InnoDB satisfies it from the index alone (`Using index` in EXPLAIN Extra).

```sql
-- Query: SELECT user_id, status, total FROM orders WHERE user_id = 42
CREATE INDEX idx_orders_cover ON orders (user_id, status, total);
```

## InnoDB Implicit Covering
InnoDB secondary indexes store the PK value, so `INDEX(status)` already covers `SELECT id FROM t WHERE status = ?`.

## EXPLAIN Signals
Look for `Using index` in the Extra column. `Using index condition` means ICP is helping but not covering.

## When to Use
- High-frequency reads selecting few columns from wide tables.
- Not worth it for: wide result sets (TEXT/BLOB), write-heavy tables, low-frequency queries.

## Tradeoffs
- Write amplification: every INSERT/UPDATE/DELETE must update all indexes.
- Index size: wide indexes consume more disk and buffer pool.
- `SELECT *` defeats covering indexes — select only needed columns.
