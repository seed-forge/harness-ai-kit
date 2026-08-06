# Index Maintenance

## Find Unused Indexes
```sql
SELECT object_schema, object_name, index_name, COUNT_READ, COUNT_WRITE
FROM performance_schema.table_io_waits_summary_by_index_usage
WHERE object_schema = 'mydb'
  AND index_name IS NOT NULL AND index_name != 'PRIMARY'
  AND COUNT_READ = 0 AND COUNT_WRITE = 0
ORDER BY COUNT_WRITE DESC;
```
Counters reset on restart — ensure 1+ full business cycle of uptime before dropping.

## Find Redundant Indexes
```sql
SELECT table_schema, table_name,
  redundant_index_name, redundant_index_columns,
  dominant_index_name, dominant_index_columns
FROM sys.schema_redundant_indexes WHERE table_schema = 'mydb';
```

## Check Index Sizes
```sql
SELECT database_name, table_name, index_name,
  ROUND(stat_value * @@innodb_page_size / 1024 / 1024, 2) AS size_mb
FROM mysql.innodb_index_stats
WHERE stat_name = 'size' AND database_name = 'mydb'
ORDER BY stat_value DESC;
```

## Invisible Indexes (MySQL 8.0+)
```sql
ALTER TABLE orders ALTER INDEX idx_status INVISIBLE;  -- test without dropping
ALTER TABLE orders ALTER INDEX idx_status VISIBLE;
```

## Guidelines
- 1-5 indexes per table is normal. 6+: audit for redundancy.
- Combine `performance_schema` data with `EXPLAIN` of frequent queries monthly.
