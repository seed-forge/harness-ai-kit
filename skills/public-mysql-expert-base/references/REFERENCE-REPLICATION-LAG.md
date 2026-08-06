# Replication Lag

MySQL replication is asynchronous by default. Reads from a replica may return stale data.

## Detecting Lag
```sql
SHOW REPLICA STATUS\G
-- Key: Seconds_Behind_Source (0 = caught up, NULL = not replicating)
```

**Warning**: measures relay-log lag, not true wall-clock staleness. Can underreport during long transactions.

## Mitigation Strategies
| Strategy | Trade-off |
|---|---|
| Read from primary after writes | Increases primary load |
| Sticky sessions | Adds complexity |
| GTID wait (`WAIT_FOR_EXECUTED_GTID_SET`) | Adds latency |
| Semi-sync replication | Higher write latency |

## Common Pitfalls
- **Large transactions cause lag spikes**: break into batches.
- **DDL blocks replication**: COPY-like rebuilds block relay-log on replicas.
- **Long queries on replica**: can block relay-log application.

## Guidelines
- Assume replicas are always slightly behind.
- Use GTID-based replication for reliable failover.
- Monitor `Seconds_Behind_Source` with alerting (>5s warrants investigation).
