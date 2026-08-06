# public-postgres-expert-base 使用说明

## 一句话

PostgreSQL 知识基座，被 devlab-postgres-usage 通过 extends 继承。

## 触发场景

| 你说的话 | AI 自动执行 |
|----------|-------------|
| 被 extends 继承 | devlab-postgres-usage 自动合并 Schema/Indexing/JSONB 等章节 |

## 可直接复制的中文 Prompt

```
帮我设计 PostgreSQL 表结构
```

```
PostgreSQL 索引怎么选
```

## 覆盖主题

- Schema Design
- Indexing (B-Tree/GIN/GiST/BRIN)
- JSONB
- Partitioning
- Extensions
- Connection Management

## 与运维的分工

- **你（开发自助）**：查连接信息、生成代码、导出 .env
- **运维（infra-datasource-ops）**：建库、建用户、改密码
- **诊断（diag-*）**：性能问题排查

## 来源

借鉴自 [planetscale/database-skills](https://github.com/planetscale/database-skills)
