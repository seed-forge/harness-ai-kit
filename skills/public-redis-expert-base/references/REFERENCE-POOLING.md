# Connection Pooling

## redis-py
```python
pool = redis.ConnectionPool(host="localhost", port=6379, max_connections=50)
r = redis.Redis(connection_pool=pool)
```

## Jedis (Java)
```java
JedisPoolConfig config = new JedisPoolConfig();
config.setMaxTotal(50);
config.setMaxIdle(10);
JedisPool pool = new JedisPool(config, "localhost", 6379);
try (Jedis jedis = pool.getResource()) {
    jedis.get("key");
}
```

## Lettuce (Java) — Multiplex
```java
RedisClient client = RedisClient.create("redis://localhost");
StatefulRedisConnection<String, String> conn = client.connect();
// Single connection, shared across threads (thread-safe)
conn.sync().get("key");
```

## Pool Sizing
- Start with pool_size = (CPU cores * 2) for OLTP
- Monitor pool exhaustion (timeouts waiting for connection)
- Don't oversize: each idle connection costs memory on both client and server
