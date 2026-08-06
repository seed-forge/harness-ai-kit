---
name: public-kafka-expert-base
description: Kafka 知识基座。覆盖 Topics/Partitions、Consumer Groups、Producer/Consumer Config、Serialization、Exactly-Once、Rebalancing。供 devlab-kafka-usage 通过 extends 继承。
---

# Kafka Knowledge Base

Foundational guidance for building event streaming applications with Apache Kafka.

> **Source**: Adapted from [confluentinc/agent-skills](https://github.com/confluentinc/agent-skills) and Apache Kafka best practices.

## Topics & Partitions
- Design topics around domain events (`order.created`, `payment.completed`), not database tables.
- Partition count determines max consumer parallelism — start with 3-6, scale up as needed.
- Partitions are ordered; messages within a partition have guaranteed order.
- Use partition keys for related messages that must be ordered (e.g., `user_id` for user events).

## Consumer Groups
- All consumers in a group share the workload (each partition → one consumer).
- Multiple groups can independently consume the same topic (fan-out).
- Consumer offset tracking: committed offsets vs. current position.
- Use `auto.offset.reset=earliest` for new groups that need to process all history.

## Producer Configuration
| Setting | Default | Recommended |
|---------|---------|-------------|
| `acks` | 1 | `all` (durability) |
| `retries` | 0 | 3+ (transient failures) |
| `linger.ms` | 0 | 5-100 (batching) |
| `batch.size` | 16KB | 32-64KB (throughput) |
| `compression.type` | none | `lz4` or `zstd` |
| `enable.idempotence` | true | **always true** |

## Consumer Configuration
| Setting | Default | Recommended |
|---------|---------|-------------|
| `auto.offset.reset` | latest | `earliest` (first run) |
| `enable.auto.commit` | true | **false** (manual commit) |
| `max.poll.records` | 500 | Tune to processing capacity |
| `session.timeout.ms` | 45s | 10-30s (failure detection) |
| `heartbeat.interval.ms` | 3s | session.timeout / 3 |

## Serialization
- Use Avro/Protobuf/JSON Schema with Schema Registry for type safety.
- Never use Java serialization (not cross-language, not forward-compatible).
- StringSerializer/StringDeserializer only for simple text messages.

## Exactly-Once Semantics
- Enable `enable.idempotence=true` on producer (prevents duplicates from retries).
- Use `isolation.level=read_committed` on consumer (read only committed transactions).
- For transactional processing: `beginTransaction()` → process → `commitTransaction()`.

## Rebalancing
- Triggered when consumers join/leave a group or partitions are reassigned.
- Use cooperative rebalancing (`partition.assignment.strategy=CooperativeStickyAssignor`).
- Handle `CommitFailedException` during rebalance — retry after rebalance completes.
- Use `ConsumerRebalanceListener` for cleanup on partition revocation.

## Guardrails
- Always set `acks=all` and `enable.idempotence=true` for producers.
- Always use manual offset commits (`enable.auto.commit=false`).
- Never use Java serialization for Kafka messages.
- Monitor consumer lag (`kafka-consumer-groups --describe`).
