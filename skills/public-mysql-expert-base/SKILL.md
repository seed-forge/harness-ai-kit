---
name: public-mysql-expert-base
description: MySQL/InnoDB 知识基座。覆盖 schema 设计、索引策略、查询调优、事务与锁、分区、运维操作。供 devlab-middleware-expert 通过 extends 继承。
---

# MySQL/InnoDB Knowledge Base

Use this skill to make safe, measurable MySQL/InnoDB changes.

> **Source**: Adapted from [planetscale/database-skills](https://github.com/planetscale/database-skills) (MySQL skill). PlanetScale-specific content removed; only general MySQL/InnoDB knowledge retained.

## Workflow
1. Define workload and constraints (read/write mix, latency target, data volume, MySQL version).
2. Read only the relevant reference files linked in each section below.
3. Propose the smallest change that can solve the problem, including trade-offs.
4. Validate with evidence (`EXPLAIN`, `EXPLAIN ANALYZE`, lock/connection metrics).
5. For production changes, include rollback and post-deploy verification.

## Schema Design
- Prefer narrow, monotonic PKs (`BIGINT UNSIGNED AUTO_INCREMENT`) for write-heavy OLTP tables.
- Avoid random UUID values as clustered PKs; if external IDs are required, keep UUID in a secondary unique column.
- Always `utf8mb4` / `utf8mb4_0900_ai_ci`. Prefer `NOT NULL`, `DATETIME` over `TIMESTAMP`.
- Lookup tables over `ENUM`. Normalize to 3NF; denormalize only for measured hot paths.

References:
- [primary-keys](references/REFERENCE-PRIMARY-KEYS.md)
- [data-types](references/REFERENCE-DATA-TYPES.md)
- [character-sets](references/REFERENCE-CHARACTER-SETS.md)
- [json-column-patterns](references/REFERENCE-JSON-COLUMN-PATTERNS.md)

## Indexing
- Composite order: equality first, then range/sort (leftmost prefix rule).
- Range predicates stop index usage for subsequent columns.
- Secondary indexes include PK implicitly. Prefix indexes for long strings.
- Audit via `performance_schema` — drop indexes with `count_read = 0`.

References:
- [composite-indexes](references/REFERENCE-COMPOSITE-INDEXES.md)
- [covering-indexes](references/REFERENCE-COVERING-INDEXES.md)
- [fulltext-indexes](references/REFERENCE-FULLTEXT-INDEXES.md)
- [index-maintenance](references/REFERENCE-INDEX-MAINTENANCE.md)

## Partitioning
- Partition time-series (>50M rows) or large tables (>100M rows). Plan early — retrofit = full rebuild.
- Include partition column in every unique/PK. Always add a `MAXVALUE` catch-all.

References:
- [partitioning](references/REFERENCE-PARTITIONING.md)

## Query Optimization
- Check `EXPLAIN` — red flags: `type: ALL`, `Using filesort`, `Using temporary`.
- Cursor pagination, not `OFFSET`. Avoid functions on indexed columns in `WHERE`.
- Batch inserts (500–5000 rows). `UNION ALL` over `UNION` when dedup unnecessary.

References:
- [explain-analysis](references/REFERENCE-EXPLAIN-ANALYSIS.md)
- [query-optimization-pitfalls](references/REFERENCE-QUERY-OPTIMIZATION-PITFALLS.md)
- [n-plus-one](references/REFERENCE-N-PLUS-ONE.md)

## Transactions & Locking
- Default: `REPEATABLE READ` (gap locks). Use `READ COMMITTED` for high contention.
- Consistent row access order prevents deadlocks. Retry error 1213 with backoff.
- Do I/O outside transactions. Use `SELECT ... FOR UPDATE` sparingly.

References:
- [isolation-levels](references/REFERENCE-ISOLATION-LEVELS.md)
- [deadlocks](references/REFERENCE-DEADLOCKS.md)
- [row-locking-gotchas](references/REFERENCE-ROW-LOCKING-GOTCHAS.md)

## Operations
- Use online DDL (`ALGORITHM=INPLACE`) when possible; test on replicas first.
- Tune connection pooling — avoid `max_connections` exhaustion under load.
- Monitor replication lag; avoid stale reads from replicas during writes.

References:
- [online-ddl](references/REFERENCE-ONLINE-DDL.md)
- [connection-management](references/REFERENCE-CONNECTION-MANAGEMENT.md)
- [replication-lag](references/REFERENCE-REPLICATION-LAG.md)

## Guardrails
- Prefer measured evidence over blanket rules of thumb.
- Note MySQL-version-specific behavior when giving advice.
- Ask for explicit human approval before destructive data operations (drops/deletes/truncates).

参考文档：
- references/REFERENCE-README.md
