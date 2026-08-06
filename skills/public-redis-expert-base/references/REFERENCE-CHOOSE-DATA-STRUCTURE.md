# Choosing the Right Data Structure

## Decision Guide

### String
Best for: simple values, counters (`INCR`/`DECR`), serialized JSON blobs (when the whole object is read/written together), distributed locks.

### Hash
Best for: objects with named fields (user profiles, settings). Update individual fields without rewriting the whole object. Memory-efficient for objects with many fields (ziplist encoding).

### List
Best for: queues (LPUSH/BRPOP), recent-N items (LTRIM), timeline feeds. O(1) push/pop at both ends. Not ideal for random access.

### Set
Best for: unique membership (tags, user groups), set operations (intersection, union, difference). O(1) add/remove/check membership.

### Sorted Set
Best for: leaderboards, priority queues, time-based ranges. Score-ordered access. O(log(N)) add, O(1) score lookup.

### JSON (RedisJSON)
Best for: nested/hierarchical data, partial updates. Path-level reads/writes. RQE indexing for secondary queries.

### Stream
Best for: event logs, fan-out messaging, CDC. Persistent, consumer groups, acknowledgment model. Like Kafka but in-memory.

## Common Mistakes
- Using String with JSON serialization when Hash would be more efficient
- Using List as a queue without LTRIM (unbounded growth)
- Using SET for small membership checks when SISMEMBER overhead matters
