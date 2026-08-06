# Composite Indexes

## Leftmost Prefix Rule
Index `(a, b, c)` is usable for:
- `WHERE a` | `WHERE a AND b` | `WHERE a AND b AND c`
- `WHERE a AND c` uses only column `a` (c can't filter without b)
- NOT usable for `WHERE b` alone or `WHERE b AND c`

## Column Order: Equality First, Then Range/Sort
```sql
-- Query: WHERE tenant_id = ? AND status = ? AND created_at > ?
CREATE INDEX idx_orders_tenant_status_created ON orders (tenant_id, status, created_at);
```

**Critical**: Range predicates stop index usage for filtering subsequent columns. However, columns after a range can still help with covering index reads or ORDER BY/GROUP BY.

## Sort Order Must Match Index
```sql
-- Index: (status, created_at)
ORDER BY status ASC, created_at ASC   -- OK
ORDER BY status DESC, created_at DESC -- OK (reverse scan)
ORDER BY status ASC, created_at DESC  -- may use filesort

-- MySQL 8.0+: descending index components
CREATE INDEX idx ON orders (status ASC, created_at DESC);
```

## Composite vs Multiple Single-Column Indexes
MySQL can merge single-column indexes (`index_merge`) but a composite index is typically faster.

## InnoDB Secondary Index Behavior
InnoDB secondary indexes implicitly store the primary key value with each index entry.
