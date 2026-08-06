# Deadlocks

InnoDB auto-detects deadlocks and rolls back one transaction (the "victim").

## Common Causes
1. **Opposite row ordering** — Fix: access rows in consistent order (by PK).
2. **Next-key lock conflicts** (REPEATABLE READ) — Fix: use READ COMMITTED or narrow scope.
3. **Missing index on WHERE column** — Fix: add index to avoid full-table locking.
4. **AUTO_INCREMENT lock contention** — Fix: `innodb_autoinc_lock_mode=2` or batch inserts.

## Diagnosing
```sql
SHOW ENGINE INNODB STATUS\G  -- "LATEST DETECTED DEADLOCK"

-- Current lock waits (MySQL 8.0+)
SELECT object_name, lock_type, lock_mode, lock_status, lock_data
FROM performance_schema.data_locks WHERE lock_status = 'WAITING';
```

## Prevention
- Keep transactions short. Do I/O outside transactions.
- Ensure WHERE columns in UPDATE/DELETE are indexed.
- Access rows in consistent order across all transactions.

## Retry Pattern (Error 1213)
Ensure the operation is idempotent before adding automatic retries.

## Common Misconceptions
- Deadlocks are normal, not bugs.
- READ COMMITTED reduces but doesn't eliminate deadlocks.
- InnoDB generally chooses the transaction with lower rollback cost as victim.
