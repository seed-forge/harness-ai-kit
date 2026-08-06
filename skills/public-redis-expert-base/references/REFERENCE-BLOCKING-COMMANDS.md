# Blocking Commands & Safe Iteration

## Commands to Avoid in Production
| Don't | Use Instead |
|---|---|
| `KEYS pattern` | `SCAN` cursor loop |
| `SMEMBERS large_set` | `SSCAN` |
| `HGETALL large_hash` | `HSCAN` |
| `LRANGE 0 -1` on huge list | Paginate |

## Blocking Commands (OK for Queue Consumers)
`BLPOP`, `BRPOP`, `BLMOVE` intentionally wait. Always pass a timeout.
Don't use on multiplexed connections (Lettuce, NRedisStack).

## SCAN Pattern
```python
cursor = 0
while True:
    cursor, keys = redis.scan(cursor, match="user:*", count=100)
    for key in keys:
        process(key)
    if cursor == 0:
        break
```
