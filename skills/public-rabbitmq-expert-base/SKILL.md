---
name: public-rabbitmq-expert-base
description: RabbitMQ 知识基座。覆盖 Exchange Types、Queue & Routing、Durability、Dead Letter、Confirmations。供 devlab-rabbitmq-usage 通过 extends 继承。
---

# RabbitMQ Knowledge Base

> **Source**: Adapted from [mindrally/skills](https://github.com/mindrally/skills) (rabbitmq-development) and RabbitMQ official documentation.

## Exchange Types
| Type | Routing | Use for |
|------|---------|---------|
| Direct | Exact routing key match | Point-to-point, RPC |
| Topic | Wildcard pattern (`*.info`, `#`) | Flexible pub/sub |
| Fanout | Ignore routing key, broadcast to all bound queues | Broadcast notifications |
| Headers | Match on message headers (not routing key) | Complex routing rules |

- Default exchange (empty name): direct routing by queue name. Convenient but not recommended for production.
- Always declare exchanges explicitly; don't rely on auto-created exchanges.

## Queue & Routing
- Declare queues with `durable=true` for persistence across broker restarts.
- Bind queues to exchanges with routing keys.
- Use `x-message-ttl` for message expiration.
- Use `x-max-length` to cap queue size (drop or dead-letter oldest).
- Prefetch count (`basic_qos`): limit unacknowledged messages per consumer.

## Durability & Reliability
- `durable=true` on queue + `persistent` delivery mode on message = survive broker restart.
- Publisher confirms: `confirm_select()` → broker acknowledges message receipt.
- Consumer acknowledgments: `basic_ack` (success) / `basic_nack` (failure, requeue or dead-letter).
- Never use `auto_ack=true` in production (message loss on consumer crash).

## Dead Letter Exchange (DLX)
- Messages are dead-lettered when: rejected (`basic_nack` with requeue=false), TTL expired, or queue length exceeded.
- Configure with `x-dead-letter-exchange` and `x-dead-letter-routing-key` on the source queue.
- Use DLX for retry queues, error handling, and audit trails.
- Pattern: main queue → DLX → retry queue (with TTL) → main queue.

## Connection & Channel
- One connection per application; multiple channels per connection.
- Channels are lightweight; connections are expensive (TCP + AMQP handshake).
- Use connection pooling for multi-threaded applications.
- Set `heartbeat` interval (default 60s) to detect dead connections.

## Common Patterns
- **Work queue**: multiple consumers, round-robin dispatch, prefetch=1 for fair dispatch.
- **Pub/Sub**: fanout exchange, each subscriber has own queue.
- **RPC**: direct exchange, correlation_id + reply_to for request/response.
- **Delay/Retry**: DLX + TTL queue for delayed message processing.

## Guardrails
- Always use publisher confirms and consumer acknowledgments.
- Never use `auto_ack=true` in production.
- Always declare queues and exchanges explicitly.
- Set prefetch count to prevent consumer overload.
- Monitor queue depth and consumer lag.
