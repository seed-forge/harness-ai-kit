# Online DDL

Not all `ALTER TABLE` is equal — some block writes for the entire duration.

## Algorithm Spectrum
| Algorithm | What Happens | DML During? |
|---|---|---|
| `INSTANT` | Metadata-only | Yes |
| `INPLACE` | Rebuilds in background | Usually yes |
| `COPY` | Full table copy | **Blocked** |

```sql
ALTER TABLE orders ADD COLUMN note VARCHAR(255) DEFAULT NULL, ALGORITHM=INSTANT;
-- Fails loudly if INSTANT isn't possible, rather than falling back to COPY.
```

## What Supports INSTANT (MySQL 8.0+)
- Adding a column (at any position as of 8.0.29)
- Dropping a column (8.0.29+)
- Renaming a column (8.0.28+)

## Large Tables
Even INPLACE holds brief metadata locks at start/end. Long-running transactions can block DDL completion.

For very large tables, consider:
- **pt-online-schema-change**: shadow table + triggers
- **gh-ost**: triggerless, binlog stream. Preferred for high-write tables.

## Key Rule
Never run `ALTER TABLE` on production without checking the algorithm. A COPY on a 100M-row table can lock writes for hours.
