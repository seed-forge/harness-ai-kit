# Isolation Levels (InnoDB Best Practices)

**Default to REPEATABLE READ.** Most tested, prevents phantom reads.

```sql
SELECT @@transaction_isolation;
SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED;  -- per-session only
```

## REPEATABLE READ (Default)
- Consistent reads: snapshot at first read (MVCC). Plain SELECTs are non-locking.
- Locking reads/writes use **next-key locks** (row + gap).
- **Use for**: OLTP, check-then-insert, financial logic.

## READ COMMITTED (Per-Session, When Needed)
- Fresh snapshot per SELECT; record locks only (no gap locks).
- **Switch only when**: gap-lock deadlocks confirmed, bulk imports with contention.
- **Never switch globally.** Check-then-insert patterns break.

## SERIALIZABLE — Avoid
Converts plain SELECTs to locking reads when autocommit is disabled. Prefer explicit `FOR UPDATE` at REPEATABLE READ.

## READ UNCOMMITTED — Never Use

## Decision Guide
| Scenario | Recommendation |
|---|---|
| General OLTP | **REPEATABLE READ** |
| Gap-lock deadlocks | **READ COMMITTED** (per-session) |
| Need serializability | Explicit `FOR UPDATE` at RR |
