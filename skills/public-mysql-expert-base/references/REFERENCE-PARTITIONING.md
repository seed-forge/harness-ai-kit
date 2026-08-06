# Partitioning

All columns used in the partitioning expression must be part of every UNIQUE/PRIMARY KEY.

## Types
| Need | Type |
|---|---|
| Time-ordered / data retention | RANGE |
| Discrete categories | LIST |
| Even distribution | HASH / KEY |

```sql
-- RANGE COLUMNS (direct date comparisons)
PARTITION BY RANGE COLUMNS (created_at) (
  PARTITION p2025_q1 VALUES LESS THAN ('2025-04-01'),
  PARTITION p_future VALUES LESS THAN (MAXVALUE)
);

-- LIST
PARTITION BY LIST COLUMNS (region) (
  PARTITION p_americas VALUES IN ('us', 'ca', 'br'),
  PARTITION p_europe  VALUES IN ('uk', 'de', 'fr')
);

-- HASH/KEY
PARTITION BY HASH (user_id) PARTITIONS 8;
```

## Foreign Key Restrictions
Partitioned InnoDB tables do not support foreign keys.

## Management Operations
```sql
-- Add partition
ALTER TABLE events REORGANIZE PARTITION p_future INTO (
  PARTITION p2026_01 VALUES LESS THAN (TO_DAYS('2026-02-01')),
  PARTITION p_future VALUES LESS THAN MAXVALUE
);
-- Drop aged-out data (much faster than DELETE)
ALTER TABLE events DROP PARTITION p2025_q1;
```

Always ask for human approval before dropping or archiving data.
