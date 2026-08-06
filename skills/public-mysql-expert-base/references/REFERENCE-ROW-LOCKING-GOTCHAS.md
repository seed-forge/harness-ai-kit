# Row Locking Gotchas

InnoDB uses row-level locking, but the actual locked range is often wider than expected.

## Next-Key Locks (REPEATABLE READ)
Locking reads, UPDATE, DELETE use next-key locks (row + gap). Plain SELECTs use MVCC (no locks).

**Exception**: unique index search with unique condition locks only the record, not the gap.

## Gap Locks on Non-Existent Rows
```sql
-- No row with id=999 exists, but this locks the gap
SELECT * FROM orders WHERE id = 999 FOR UPDATE;
```

## Index-Less UPDATE/DELETE = Full Scan and Broad Locking
```sql
-- No index on status -> locks all rows
UPDATE orders SET processed = 1 WHERE status = 'pending';
-- Fix: CREATE INDEX idx_status ON orders (status);
```

## INSERT ... ON DUPLICATE KEY UPDATE
Takes exclusive next-key lock. Concurrent sessions on nearby keys -> gap-lock deadlocks.

## Lock Escalation Misconception
InnoDB does **not** escalate row locks to table locks. Missing index causes all-row locking because InnoDB scans and locks every row individually.

## Mitigation
- Use READ COMMITTED when gap locks cause excessive blocking.
- Keep transactions short.
- Ensure WHERE columns are indexed.
