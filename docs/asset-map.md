# Asset Map

## v0.1 — Curated Skill Library

### Knowledge Bases (extends inheritance pattern)

| ID | Domain | Status |
|----|--------|--------|
| `public-mysql-expert-base` | MySQL/InnoDB (schema, indexes, locks, tuning) | ✅ |
| `public-postgres-expert-base` | PostgreSQL (B-Tree/GIN/GiST, JSONB, partitioning) | ✅ |
| `public-redis-expert-base` | Redis (data structures, connection pool, TTL) | ✅ |
| `public-mongodb-expert-base` | MongoDB (aggregation pipeline, indexes, replica sets) | ✅ |
| `public-kafka-expert-base` | Kafka (topics, consumer groups, exactly-once) | ✅ |
| `public-rabbitmq-expert-base` | RabbitMQ (exchanges, durability, dead letter) | ✅ |
| `public-oracle-expert-base` | Oracle (JDBC, LOB, character set) | ✅ |
| `public-nl2sql-expert-base` | NL2SQL (natural language to SQL) | ✅ |
| `public-git-workflow-expert-base` | Git workflow (commit, branch, PR conventions) | ✅ |

### Diagnostic Skills (enterprise troubleshooting chains)

| ID | Scenario | Status |
|----|----------|--------|
| `diag-mysql-deadlock` | InnoDB deadlock capture + lock chain analysis | ✅ |
| `diag-mysql-slow-query` | Slow query log + EXPLAIN + index analysis | ✅ |
| `diag-mysql-replication` | Master-slave delay root cause | ✅ |
| `diag-container-oom` | dmesg OOM killer → cgroup → Docker memory | ✅ |
| `diag-k8s-pod-crashloop` | CrashLoopBackOff full-chain diagnosis | ✅ |
| `diag-k8s-node-pressure` | CPU/Memory/Disk/PID pressure | ✅ |
| `diag-network-port-unreach` | DNS → TCP → iptables → service → route | ✅ |

### General Engineering Skills

| ID | Description | Status |
|----|-------------|--------|
| `base-cn-registry-mirror-strategy` | China mirror acceleration (Docker/Debian/Python/Maven) | ✅ |
| `base-goal-execution` | Goal-driven execution with checkpoints | ✅ |
| `markitdown` | Document-to-Markdown conversion | ✅ |
| `work-convert` / `work-export` | General document conversion/export | ✅ |
| `post-task-skill-miner` | Post-task retrospective and skill extraction | ✅ |

### Infra Flagship Samples

| ID | Description | Status |
|----|-------------|--------|
| `infra-system-net-ops` | Port forwarding / connectivity troubleshooting | ✅ |
| `infra-system-env-ops` | Monit watchdog / service self-healing | ✅ |

## v0.2 (Planned)

- Loop automation framework (loopctl + templates)
- Hooks mechanism
- "From zero to skill" authoring toolkit

## v0.3 (Backlog)

- Expanded infra/devlab skill library
- MCP server assets (playwright, gemini)
- RBAC governance and audit pipeline
