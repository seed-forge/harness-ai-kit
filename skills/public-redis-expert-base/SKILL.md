---
name: public-redis-expert-base
description: Redis 知识基座。覆盖数据结构选型、Key 命名、连接池与 Pipeline、集群与副本读取、TTL 与淘汰策略。供 devlab-redis-usage 通过 extends 继承。
---

# Redis Knowledge Base

Foundational guidance for modeling data in Redis and connecting to it efficiently.

> **Source**: Adapted from [redis/agent-skills](https://github.com/redis/agent-skills) (redis-core + redis-connections + redis-clustering). Official Redis team content.

## Workflow
1. Identify the access pattern (read/write mix, data shape, latency target).
2. Choose the matching data structure (Section 1).
3. Design key names following conventions (Section 2).
4. Configure connection pool and timeouts (Section 3).
5. Batch work with pipelining (Section 4).
6. Plan for cluster mode if scaling (Section 5).

## Data Structure Selection
Pick the type that matches the *access pattern*, not just the shape of the data.

| Use case | Recommended type | Why |
|---|---|---|
| Simple values, counters | String | Atomic `INCR`/`DECR`, `SET`/`GET` |
| Object with independently updated fields | Hash | Per-field reads/writes, no whole-object rewrite |
| Queue, recent-N items | List | O(1) push/pop at ends |
| Unique items, membership checks | Set | O(1) `SADD`/`SISMEMBER`/`SCARD` |
| Rankings, score-based ranges | Sorted Set | Score-ordered; `ZADD`/`ZRANGE`/`ZRANK` |
| Nested / hierarchical data | JSON | Path-level updates, nested arrays, RQE indexing |
| Event log, fan-out messaging | Stream | Persistent, consumer groups |
| Vector similarity | Vector Set | Native vector storage with HNSW |

**Common anti-pattern:** stuffing a flat object into a serialized string. Use a Hash instead.

References:
- [choose-data-structure](references/REFERENCE-CHOOSE-DATA-STRUCTURE.md)

## Key Naming
Use `colon-separated` segments with a stable hierarchy:

```
{entity}:{id}:{attribute}
user:1001:profile
session:abc123
article:987:likes
```

Rules:
- Lowercase, colon-separated. No spaces, no mixed casing.
- Keep keys short but readable.
- Don't use full URLs or long strings as keys.
- Prefix for multi-tenancy (`tenant:42:user:7:cart`).

References:
- [key-naming](references/REFERENCE-KEY-NAMING.md)

## Connection Management
Always use pooling or multiplexing — never one connection per request.

| Style | Used by | Note |
|---|---|---|
| Pool | redis-py, Jedis, go-redis | Each lease blocks if pool exhausted |
| Multiplex | Lettuce, NRedisStack | Single connection; cannot carry blocking commands |

Set explicit timeouts: connect timeout shorter than read/write timeout.

References:
- [pooling](references/REFERENCE-POOLING.md)
- [timeouts](references/REFERENCE-TIMEOUTS.md)

## Pipelining & Batching
For N commands that don't depend on each other's results, send as a single batch.

```python
pipe = redis.pipeline()
for user_id in user_ids:
    pipe.get(f"user:{user_id}")
results = pipe.execute()
```

Avoid commands that scan everything: use `SCAN` instead of `KEYS`, `SSCAN` instead of `SMEMBERS` on large sets.

References:
- [pipelining](references/REFERENCE-PIPELINING.md)
- [blocking-commands](references/REFERENCE-BLOCKING-COMMANDS.md)

## Clustering & Replication
In Redis Cluster, keys are distributed across 16,384 slots. Multi-key operations require all keys on the same slot — use hash tags: `{user:1001}:profile`.

For read-heavy workloads, route reads to replicas (eventually consistent).

References:
- [hash-tags](references/REFERENCE-HASH-TAGS.md)
- [read-replicas](references/REFERENCE-READ-REPLICAS.md)

## TTL & Eviction
- Always set TTL for cache keys; never rely on manual cleanup.
- Use `EXPIRE` / `PEXPIRE` for time-based eviction.
- Choose eviction policy based on workload: `allkeys-lru` for cache, `volatile-lru` for mixed.
- Monitor `evicted_keys` in `INFO stats` to detect memory pressure.

## Guardrails
- Never use `KEYS *` in production — use `SCAN`.
- Never `HGETALL` or `SMEMBERS` on large containers — use `HSCAN`/`SSCAN`.
- Prefer Hash over serialized String for objects with multiple fields.
- Set TTL on all cache keys; avoid manual cleanup patterns.

参考文档：
- references/REFERENCE-README.md
