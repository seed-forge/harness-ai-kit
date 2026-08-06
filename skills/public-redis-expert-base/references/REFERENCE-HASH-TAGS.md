# Hash Tags for Cluster Mode

## Purpose
Force multiple keys to the same hash slot for multi-key operations.

## Syntax
The part between `{` and `}` is hashed for slot assignment:
```python
redis.set("{user:1001}:profile",  "...")
redis.set("{user:1001}:settings", "...")
# Both land on the same slot → MGET works in cluster
```

## Rules
- Scope tags to meaningful entities: `{user:1001}`, not bare `{1001}`
- Only tag where you need multi-key ops (tagging everything creates hotspots)
- Plan tagging upfront — renaming keys in production is painful
