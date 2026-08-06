# Pipelining

## Basic Pattern
```python
pipe = redis.pipeline()
for user_id in user_ids:
    pipe.get(f"user:{user_id}")
results = pipe.execute()  # one round-trip
```

## Transactional Pipeline
```python
pipe = redis.pipeline(transaction=True)  # MULTI/EXEC
pipe.set("key1", "val1")
pipe.set("key2", "val2")
pipe.execute()  # atomic
```

Use non-transactional for performance; transactional only when you need atomicity.

## In Cluster Mode
All keys in a pipeline must map to the same slot (use hash tags).
Otherwise you get CROSSSLOT errors.
