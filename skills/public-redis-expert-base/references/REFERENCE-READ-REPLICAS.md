# Reading from Replicas

## When to Use
- Read-heavy workloads (caches, analytics, dashboards)
- Replicas are eventually consistent
- Don't read your own writes from a replica

## Redis Cluster
```python
from redis.cluster import RedisCluster
rc = RedisCluster(host="localhost", port=6379, read_from_replicas=True)
```

## Standalone
```python
primary = Redis(host="primary-host", port=6379)
replica = Redis(host="replica-host", port=6379)
primary.set("key", "value")
value = replica.get("key")  # eventually consistent
```

## Good Fits
Cache layers, analytics queries, dashboard data, recommendation feeds.

## Bad Fits
Financial balances, idempotency state, anything requiring strict freshness.
