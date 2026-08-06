---
name: public-postgres-expert-base
description: PostgreSQL 知识基座。覆盖 Schema Design、Indexing（B-Tree/GIN/GiST/BRIN）、JSONB、Partitioning、Extensions。供 devlab-postgres-usage 通过 extends 继承。
---

# PostgreSQL Knowledge Base

> **Source**: Adapted from [planetscale/database-skills](https://github.com/planetscale/database-skills) (PostgreSQL skill).

## Schema Design
- Prefer `BIGSERIAL` or `BIGINT GENERATED ALWAYS AS IDENTITY` for PKs.
- Use `TIMESTAMPTZ` (with timezone) over `TIMESTAMP`.
- `TEXT` and `VARCHAR` have similar performance in PostgreSQL — prefer `TEXT` unless length constraint is meaningful.
- Use `NUMERIC` for money, never `FLOAT`/`REAL`.
- `JSONB` (binary) over `JSON` (text) for structured data.

## Indexing
| Type | Use for |
|------|---------|
| B-Tree (default) | Equality, range, sorting |
| GIN | JSONB, fulltext, arrays, containment |
| GiST | Geometry, range types, nearest-neighbor |
| BRIN | Sequential data (timestamps, IDs) on large tables |
| Hash | Equality only (rarely needed) |

- Partial indexes: `CREATE INDEX ... WHERE condition` — index only relevant rows.
- Expression indexes: `CREATE INDEX ... ON t (lower(name))`.
- Covering indexes: `INCLUDE (col1, col2)` for index-only scans.
- `CONCURRENTLY` for creating indexes without blocking writes.

## JSONB
- Store structured, semi-structured, or variable-schema data.
- Index with GIN: `CREATE INDEX ... USING GIN (data jsonb_path_ops)`.
- Query: `data->>'key'` (text), `data->'key'` (jsonb), `data @> '{"key": "val"}'` (containment).
- Generated columns for frequently queried JSONB paths.

## Partitioning
- Declarative partitioning (range, list, hash) for large tables.
- Partition key must be part of every unique/PK constraint.
- `ATTACH PARTITION` / `DETACH PARTITION` for maintenance.
- Partition pruning: queries automatically skip irrelevant partitions.

## Extensions
- `pg_trgm`: trigram similarity for fuzzy search.
- `pgvector`: vector similarity search (AI/embeddings).
- `pg_stat_statements`: query performance analysis.
- `uuid-ossp`: UUID generation.
- `postgis`: geospatial data.

## Connection Management
- Use connection pooling (PgBouncer) — PostgreSQL connections are expensive (~5-10 MB each).
- Pool sizing: start with `2 * CPU cores + 1`.
- Use `prepared_statements` for parameterized queries.
- Set `statement_timeout` to prevent runaway queries.

## Guardrails
- Always use `TIMESTAMPTZ`, not `TIMESTAMP`.
- Prefer `TEXT` over `VARCHAR(N)` unless length limit is meaningful.
- Use `CONCURRENTLY` when creating indexes on production tables.
- Set `statement_timeout` at connection or session level.
- Use PgBouncer for connection pooling in production.
