# public-mongodb-expert-base 使用说明

## 一句话

MongoDB 知识基座，被 devlab-mongodb-usage 通过 extends 继承。一般不直接使用。

## 触发场景

| 你说的话 | AI 自动执行 |
|----------|-------------|
| 被 extends 继承 | devlab-mongodb-usage 自动合并本技能的文档模型/索引/聚合等章节 |

## 可直接复制的中文 Prompt

```
帮我设计 MongoDB 文档模型
```

```
这个查询很慢，帮我用 explain 分析
```

## 覆盖主题

- Document Model
- Schema Design Patterns
- Indexing
- Aggregation Pipeline
- Connection & Configuration
- Replica Sets & Sharding

## 与运维的分工

- **你（开发自助）**：查连接信息、生成代码、导出 .env
- **运维（infra-datasource-ops）**：建库、建用户、改密码
- **诊断（diag-*）**：性能问题排查

## 来源

借鉴自 [mongodb/agent-skills](https://github.com/mongodb/agent-skills)
