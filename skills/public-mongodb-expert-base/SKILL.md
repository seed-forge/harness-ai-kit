---
name: public-mongodb-expert-base
description: MongoDB 知识基座。覆盖 Document Model、Aggregation Pipeline、Indexes、Replica Sets、Change Streams。供 devlab-mongodb-usage 通过 extends 继承。
---

# MongoDB Knowledge Base

Foundational guidance for building applications with MongoDB.

> **Source**: Adapted from [mongodb/agent-skills](https://github.com/mongodb/agent-skills) (schema-design + query-optimizer + connection).

## Document Model
- Design documents around access patterns, not normalization.
- Embed related data that's always read together (1:1, 1:few).
- Reference (DBRef or manual ID) for data that grows unbounded or is accessed independently.
- Use arrays for ordered collections; use sub-documents for named fields.
- Avoid anti-patterns: unbounded arrays, massive documents (>16MB), excessive nesting.

## Schema Design Patterns
| Pattern | Use for |
|---------|---------|
| Embedding | 1:1, 1:few relationships, always-read-together data |
| Referencing | 1:many (unbounded), independent access |
| Bucket | Time-series data (group by time window) |
| Tree | Hierarchical data (materialized paths, nested sets) |
| Outlier | Handle occasional large documents separately |
| Extended Reference | Embed frequently accessed fields, reference the rest |

## Indexing
- Index fields used in queries, sorts, and aggregation `$match`/`$sort` stages.
- Compound index order matters: equality first, then range, then sort.
- Use `explain()` to verify index usage (look for `IXSCAN`, avoid `COLLSCAN`).
- Text indexes for full-text search; 2dsphere for geospatial queries.
- TTL indexes for auto-expiring documents.
- Monitor with `$indexStats` — drop unused indexes.

## Aggregation Pipeline
- Order stages for efficiency: `$match` and `$sort` first (use indexes).
- `$lookup` for joins (prefer embedding when possible).
- `$group` for aggregation; `$unwind` to flatten arrays before grouping.
- Use `$project` early to reduce document size through the pipeline.
- `$facet` for multiple aggregations in one query.

## Connection & Configuration
- Connection string: `mongodb://host:port/db?options`
- Use connection pooling (built into all official drivers).
- Set `w=majority` for write concern (durability).
- Set `readPreference=secondaryPreferred` for read scaling.
- Use `retryWrites=true` and `retryReads=true`.

## Replica Sets & Sharding
- Replica sets: 3 members minimum (primary + 2 secondaries).
- Read from secondaries for analytics/reporting (eventual consistency).
- Sharding: shard key choice is critical — high cardinality, frequently in queries.
- Never change shard key after collection is sharded (pre-6.0).

## Change Streams
- Real-time event processing from oplog.
- Use `watch()` on collection or database level.
- Resume with `resumeAfter` or `startAfter` token.
- Filter with aggregation pipeline match.

## Guardrails
- Never store unbounded arrays in a single document.
- Always index fields used in queries — verify with `explain()`.
- Use `w=majority` for critical writes.
- Set document TTL for temporary data.
- Monitor slow queries with profiler (`db.setProfilingLevel(1, {slowms: 100})`).
