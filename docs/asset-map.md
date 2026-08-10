# Asset Map

23 production-tested skills included in v0.1. Install any with:

```bash
ai-kit add skill <id>
```

---

## Database Expert Bases

Deep knowledge bases for specific database technologies. Your AI agent inherits this expertise when the skill is installed.

| Skill | What your AI learns | Install |
|-------|-------------------|---------|
| `public-mysql-expert-base` | MySQL/InnoDB schema design, index strategy, query tuning, transactions, locks, partitioning | `ai-kit add skill public-mysql-expert-base` |
| `public-postgres-expert-base` | PostgreSQL B-Tree/GIN/GiST indexes, JSONB, partitioning, extensions | `ai-kit add skill public-postgres-expert-base` |
| `public-redis-expert-base` | Redis data structure selection, key naming, connection pool, TTL, eviction | `ai-kit add skill public-redis-expert-base` |
| `public-mongodb-expert-base` | MongoDB document model, aggregation pipeline, indexes, replica sets, change streams | `ai-kit add skill public-mongodb-expert-base` |
| `public-kafka-expert-base` | Kafka topics/partitions, consumer groups, serialization, exactly-once, rebalancing | `ai-kit add skill public-kafka-expert-base` |
| `public-rabbitmq-expert-base` | RabbitMQ exchange types, queue routing, durability, dead letter, confirmations | `ai-kit add skill public-rabbitmq-expert-base` |
| `public-oracle-expert-base` | Oracle connection types, JDBC driver, connection pool, LOB handling, SQL dialect | `ai-kit add skill public-oracle-expert-base` |
| `public-nl2sql-expert-base` | Natural language to SQL translation patterns | `ai-kit add skill public-nl2sql-expert-base` |
| `public-git-workflow-expert-base` | Git commit conventions, branch strategy, PR workflow | `ai-kit add skill public-git-workflow-expert-base` |

## Diagnostic Playbooks

Step-by-step troubleshooting chains for common production incidents. Each skill guides the AI through a full diagnostic flow.

| Skill | What it diagnoses | Install |
|-------|-------------------|---------|
| `diag-mysql-deadlock` | InnoDB deadlock capture, lock chain analysis (who holds what, who waits), deadlock pattern classification (AB-BA / Gap Lock / FK cascade) | `ai-kit add skill diag-mysql-deadlock` |
| `diag-mysql-slow-query` | Slow query log analysis, Top-N slow SQL identification, EXPLAIN execution plan review, missing index detection | `ai-kit add skill diag-mysql-slow-query` |
| `diag-mysql-replication` | Master-slave delay root cause (large transactions, network, slave load, binlog format, parallel replication config) | `ai-kit add skill diag-mysql-replication` |
| `diag-container-oom` | Container OOM killer → cgroup memory limits → Docker/Compose memory config → swap → application memory analysis | `ai-kit add skill diag-container-oom` |
| `diag-k8s-pod-crashloop` | CrashLoopBackOff full chain: kubectl describe → events → logs → restart policy → resource limits → probes → image pull → configmap/secret mounts | `ai-kit add skill diag-k8s-pod-crashloop` |
| `diag-k8s-node-pressure` | Node CPU/Memory/Disk/PID pressure: kubectl top → describe node → conditions → eviction events → scheduling analysis | `ai-kit add skill diag-k8s-node-pressure` |
| `diag-network-port-unreach` | Port unreachable: DNS → TCP connect → iptables/firewalld → service listen status → routing table → SELinux/AppArmor | `ai-kit add skill diag-network-port-unreach` |

## General Engineering

| Skill | Purpose | Install |
|-------|---------|---------|
| `base-cn-registry-mirror-strategy` | China mirror acceleration for Docker, Debian, Alpine, Node, Python, Maven, Gradle, Go | `ai-kit add skill base-cn-registry-mirror-strategy` |
| `base-goal-execution` | Goal-driven execution with checkpoints, verification, and rollback | `ai-kit add skill base-goal-execution` |
| `markitdown` | Convert PDF/DOCX/PPTX/XLSX/images/audio/HTML to Markdown | `ai-kit add skill markitdown` |
| `work-convert` | General document format conversion | `ai-kit add skill work-convert` |
| `work-export` | Document export with formatting | `ai-kit add skill work-export` |
| `post-task-skill-miner` | Post-task retrospective → extract reusable patterns → propose new skills | `ai-kit add skill post-task-skill-miner` |

## Infrastructure

| Skill | Purpose | Install |
|-------|---------|---------|
| `infra-system-env-ops` | Port forwarding (iptables/firewalld/portproxy/SSH tunnel) + Monit watchdog deployment + service crash self-healing + system resource monitoring | `ai-kit add skill infra-system-env-ops` |

---

## Installing External Skills

Any GitHub repo can be a skill source:

```bash
ai-kit add skill https://github.com/OWNER/REPO/tree/main/path/to/skill
ai-kit add skill OWNER/REPO --subpath path/to/skill --ref v1.0
```

## v0.2 (Planned)

- Loop automation framework (loopctl + templates)
- Hooks mechanism
- Skill authoring toolkit with validation

## v0.3 (Backlog)

- Extended infra/devlab skill library (50+ skills)
- MCP server assets
- RBAC governance pipeline
