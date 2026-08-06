# public-rabbitmq-expert-base 使用说明

## 一句话

RabbitMQ 知识基座，被 devlab-rabbitmq-usage 通过 extends 继承。

## 触发场景

| 你说的话 | AI 自动执行 |
|----------|-------------|
| 被 extends 继承 | devlab-rabbitmq-usage 自动合并 Exchange/Queue/DLX 等章节 |

## 可直接复制的中文 Prompt

```
帮我设计 RabbitMQ 消息方案
```

```
RabbitMQ Exchange 类型怎么选
```

## 覆盖主题

- Exchange Types
- Queue & Routing
- Durability & Reliability
- Dead Letter Exchange
- Connection & Channel
- Common Patterns

## 与运维的分工

- **你（开发自助）**：查连接信息、生成代码、导出 .env
- **运维（infra-datasource-ops）**：建库、建用户、改密码
- **诊断（diag-*）**：性能问题排查

## 来源

借鉴自 [mindrally/skills](https://github.com/mindrally/skills) (rabbitmq-development)
