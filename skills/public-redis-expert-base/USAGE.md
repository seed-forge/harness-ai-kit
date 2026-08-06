# public-redis-expert-base 使用说明

## 一句话

Redis 知识基座，被 devlab-redis-usage 通过 extends 继承。一般不直接使用。

## 触发场景

| 你说的话 | AI 自动执行 |
|----------|-------------|
| 被 extends 继承 | devlab-redis-usage 自动合并本技能的数据结构/连接/集群等章节 |
| 直接使用 | 安装后获取 Redis 通用知识参考 |

## 可直接复制的中文 Prompt

```
我在设计 Redis 缓存方案，帮我选择合适的数据结构和 Key 命名规范。
```

```
这个项目的 Redis 连接池配置有问题，帮我用最佳实践来优化。
```

## 覆盖主题

- Data Structure Selection（String/Hash/List/Set/Sorted Set/JSON/Stream）
- Key Naming（colon-separated hierarchy）
- Connection Management（Pool/Multiplex/Timeouts）
- Pipelining & Batching
- Clustering & Replication（Hash tags/Read replicas）
- TTL & Eviction

## 与运维的分工

- **你（开发自助）**：查连接信息、生成代码、导出 .env
- **运维（infra-datasource-ops）**：建库、建用户、改密码
- **诊断（diag-*）**：性能问题排查

## 来源

借鉴自 [redis/agent-skills](https://github.com/redis/agent-skills)（Redis 官方）
