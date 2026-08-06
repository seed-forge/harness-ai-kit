# Timeout Configuration

## redis-py
```python
r = redis.Redis(
    host="localhost",
    socket_connect_timeout=2.0,   # fail fast on dead nodes
    socket_timeout=5.0,           # tune to expected operation time
    retry_on_timeout=True,
)
```

## Guidelines
- Connect timeout < read/write timeout
- Tight timeouts + retry for latency-sensitive paths
- Longer timeouts for batch jobs / large pipelines
- Default values vary by client and may be too generous

## Common Issues
- `ConnectionRefusedError`: server down or wrong port → check connect timeout
- `TimeoutError` on read: slow command or network issue → check socket timeout
- `BusyLoadingError`: server loading RDB → increase connect timeout temporarily
