# EXPLAIN Analysis

```sql
EXPLAIN SELECT ...;                    -- estimated plan
EXPLAIN FORMAT=JSON SELECT ...;        -- detailed with cost estimates
EXPLAIN FORMAT=TREE SELECT ...;        -- tree format (8.0+)
EXPLAIN ANALYZE SELECT ...;            -- actual execution (8.0.18+)
```

## Access Types (Best to Worst)
`system` > `const` > `eq_ref` > `ref` > `range` > `index` > `ALL`

Target `ref` or better. `ALL` on >1000 rows almost always needs an index.

## Key Extra Flags
| Flag | Meaning | Action |
|---|---|---|
| `Using index` | Covering index (optimal) | None |
| `Using filesort` | Sort not via index | Index the ORDER BY columns |
| `Using temporary` | Temp table for GROUP BY | Index the grouped columns |
| `Using join buffer` | No index on join column | Add index on join column |
| `Using index condition` | ICP at index level | Generally good |

## rows vs filtered
- `rows`: estimated rows examined after index access
- `filtered`: percent passing full WHERE conditions
- Rough estimate: `rows * filtered / 100`

## EXPLAIN ANALYZE (8.0.18+)
Actually executes the query. Metrics: `actual time` (ms), `rows`, `loops`. Compare estimated vs actual to find optimizer misestimates. Refresh stats with `ANALYZE TABLE`.
