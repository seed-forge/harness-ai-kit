# Skill Catalog

A categorized index of all skills shipped with harness-ai-kit. Install any with:

```bash
ai-kit add skill <id>
```

> **How are these used day-to-day?** See [docs/usage-scenarios.md](docs/usage-scenarios.md).
> In short: **skills** are best driven by an SDD framework (e.g. Trellis) that decomposes your
> task and pulls in the relevant skill; **loops** are bound to a specific agent runtime
> (Codex / Claude Code / Qoder / OpenClaw).

**Total: 34 skills** across 7 categories.

---

## 1. Database Expert Bases (9)

Deep knowledge bases for a specific database technology. Your AI agent inherits this expertise once the skill is installed. Meant to be *extended* by downstream usage skills via the `extends` mechanism.

| ID | Domain |
|----|--------|
| [`public-mysql-expert-base`](skills/public-mysql-expert-base) | MySQL/InnoDB — schema, indexes, locks, tuning, partitioning |
| [`public-postgres-expert-base`](skills/public-postgres-expert-base) | PostgreSQL — B-Tree/GIN/GiST, JSONB, partitioning, extensions |
| [`public-redis-expert-base`](skills/public-redis-expert-base) | Redis — data structures, connection pool, TTL, eviction |
| [`public-mongodb-expert-base`](skills/public-mongodb-expert-base) | MongoDB — document model, aggregation, indexes, replica sets |
| [`public-kafka-expert-base`](skills/public-kafka-expert-base) | Kafka — topics, consumer groups, serialization, exactly-once |
| [`public-rabbitmq-expert-base`](skills/public-rabbitmq-expert-base) | RabbitMQ — exchanges, routing, durability, dead letter |
| [`public-oracle-expert-base`](skills/public-oracle-expert-base) | Oracle — JDBC, connection pool, LOB, character set |
| [`public-nl2sql-expert-base`](skills/public-nl2sql-expert-base) | NL2SQL — natural language to SQL translation patterns |
| [`public-git-workflow-expert-base`](skills/public-git-workflow-expert-base) | Git — commit conventions, branch strategy, PR workflow |

## 2. Diagnostic Playbooks (7)

Step-by-step troubleshooting chains for production incidents. Each guides the AI through a full diagnostic flow with a structured report.

| ID | Scenario |
|----|----------|
| [`diag-mysql-deadlock`](skills/diag-mysql-deadlock) | InnoDB deadlock capture + lock chain analysis |
| [`diag-mysql-slow-query`](skills/diag-mysql-slow-query) | Slow query log + EXPLAIN + missing index detection |
| [`diag-mysql-replication`](skills/diag-mysql-replication) | Master-slave delay root cause |
| [`diag-container-oom`](skills/diag-container-oom) | OOM killer → cgroup → Docker memory analysis |
| [`diag-k8s-pod-crashloop`](skills/diag-k8s-pod-crashloop) | CrashLoopBackOff full-chain diagnosis |
| [`diag-k8s-node-pressure`](skills/diag-k8s-node-pressure) | Node CPU/Memory/Disk/PID pressure |
| [`diag-network-port-unreach`](skills/diag-network-port-unreach) | DNS → TCP → iptables → service → route |

## 3. AI Engineering Methodology (5)

Methodology-layer skills for building AI/LLM applications. Best paired with an SDD framework — see [usage scenarios](docs/usage-scenarios.md).

| ID | Purpose |
|----|---------|
| [`devlab-spec-driven-dev`](skills/devlab-spec-driven-dev) | Spec-driven AI collaboration (requirements → design → tasks) |
| [`devlab-ai-agent-engineering`](skills/devlab-ai-agent-engineering) | AI agent app architecture (layering, rule+LLM, prompt governance) |
| [`devlab-eval-driven-agent`](skills/devlab-eval-driven-agent) | Eval-driven agent quality system (eval sets, regression gates) |
| [`devlab-ai-kit-miner`](skills/devlab-ai-kit-miner) | Post-session retrospective → reusable asset extraction |
| [`devlab-tech-debt-ops`](skills/devlab-tech-debt-ops) | Tech debt lifecycle (audit → plan → safe refactor → verify) |

## 4. Patent & Document Authoring (6)

Structured drafting and review workflows for patents, software copyright, and reusable document SOPs.

| ID | Purpose |
|----|---------|
| [`patent-specification-writer`](skills/patent-specification-writer) | Patent specification drafting |
| [`patent-review`](skills/patent-review) | Patent quality review with a dimensions checklist |
| [`patent-disclosure-workflow`](skills/patent-disclosure-workflow) | Patent disclosure end-to-end workflow |
| [`work-sc-patent-specification-writer`](skills/work-sc-patent-specification-writer) | Patent spec drafting (work-sc namespace) |
| [`work-sc-software-copyright-writer`](skills/work-sc-software-copyright-writer) | Software copyright application materials |
| [`document-reference-sop-builder`](skills/document-reference-sop-builder) | Turn an exemplar document into a reusable drafting SOP |

## 5. General & Base (4)

| ID | Purpose |
|----|---------|
| [`base-cn-registry-mirror-strategy`](skills/base-cn-registry-mirror-strategy) | China mirror acceleration (Docker/Debian/Python/Maven/Go) |
| [`base-goal-execution`](skills/base-goal-execution) | Goal-driven execution with checkpoints and verification |
| [`markitdown`](skills/markitdown) | Convert PDF/DOCX/PPTX/XLSX/images/audio/HTML to Markdown |
| [`post-task-skill-miner`](skills/post-task-skill-miner) | Post-task retrospective → skill extraction |

## 6. Document Conversion (2)

| ID | Purpose |
|----|---------|
| [`work-convert`](skills/work-convert) | General document format conversion |
| [`work-export`](skills/work-export) | Document export with formatting |

## 7. Infrastructure (1)

| ID | Purpose |
|----|---------|
| [`infra-system-env-ops`](skills/infra-system-env-ops) | Port forwarding + Monit watchdog + service self-healing |

---

## Naming Conventions

Skill IDs use a category prefix so you can tell purpose at a glance:

| Prefix | Meaning |
|--------|---------|
| `public-*-expert-base` | Reusable knowledge base (extended by usage skills) |
| `diag-*` | Diagnostic playbook for a specific failure scenario |
| `devlab-*` | Development-lab methodology / engineering practice |
| `patent-*` / `work-sc-*` | Document authoring (patent, copyright, spec) |
| `base-*` | Domain-neutral foundational skill |
| `infra-*` | Infrastructure / ops skill |
| `work-*` | Document conversion / export utility |

## Roadmap

More skills ship on a rolling basis. See [ROADMAP.md](ROADMAP.md) for upcoming batches
(loop automation framework, extended infra/devlab library, MCP assets).
