# N+1 Query Detection

## What Is N+1?
Fetch N parent records, then N additional queries for related data.

## ORM Fixes (Quick Reference)
- **SQLAlchemy 2.0**: `select(User).options(joinedload(User.posts))`
- **Django**: `select_related('fk_field')` / `prefetch_related('m2m_field')`
- **ActiveRecord**: `User.includes(:orders)`
- **Prisma**: `findMany({ include: { orders: true } })`
- **Drizzle**: use `.leftJoin()` instead of loop queries

## Detecting in Production
```sql
SELECT digest_text, count_star, avg_timer_wait
FROM performance_schema.events_statements_summary_by_digest
ORDER BY count_star DESC LIMIT 20;
```

## Batch Consolidation
Replace sequential queries with `WHERE id IN (...)`.
- Up to ~1000-5000 ids: `IN (...)` is fine
- Larger: chunk or use a temporary table + join

## Joins vs Separate Queries
- Prefer JOINs when you need related data for most parent rows
- Prefer separate queries (batched) when JOINs would explode rows
