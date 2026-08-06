# Connection Management

Every MySQL connection costs memory (~1-10 MB). Unbounded connections cause OOM or `Too many connections`.

## Sizing max_connections
Default is 151. Don't blindly raise it.
```sql
SHOW VARIABLES LIKE 'max_connections';
SHOW STATUS LIKE 'Max_used_connections';
SHOW STATUS LIKE 'Threads_connected';
```

## Pool Sizing Formula
OLTP starting point: **pool size = (CPU cores * N)** where N is typically 2-10.

## Timeout Tuning
```sql
SET GLOBAL wait_timeout = 300;         -- Non-interactive (apps)
SET GLOBAL interactive_timeout = 300;  -- Interactive (CLI)
```

## Common Pitfalls
- **ORM default pools too large**: multiply per-process pool by app server count.
- **No pool at all**: PHP/CGI opens new connection per request. Use persistent connections or ProxySQL.
- **Connection storms on deploy**: stagger deployments, use pool warm-up.
- **Idle transactions**: connections with open transactions are NOT closed by wait_timeout and hold locks.

## When to Use a Proxy
Use **ProxySQL** when: multiple app services share a DB, you need read/write split, or total connections exceed safe max_connections.
