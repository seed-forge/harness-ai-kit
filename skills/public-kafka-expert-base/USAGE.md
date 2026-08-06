# public-kafka-expert-base 使用说明

## 一句话

Kafka 知识基座，被 devlab-kafka-usage 通过 extends 继承。一般不直接使用。

## 触发场景

| 你说的话 | AI 自动执行 |
|----------|-------------|
| 被 extends 继承 | devlab-kafka-usage 自动合并本技能的 Topics/Consumer/Producer 等章节 |
| 直接使用 | 安装后获取 Kafka 通用知识参考 |

## 可直接复制的中文 Prompt

```
我在设计 Kafka 消息方案，帮我选择 Topic 分区策略和 Producer 配置。
```

```
Consumer Group 的 offset 管理怎么做最安全？
```

## 覆盖主题

- Topics & Partitions
- Consumer Groups
- Producer/Consumer Config
- Serialization
- Exactly-Once
- Rebalancing

## 与运维的分工

- **你（开发自助）**：查连接信息、生成代码、导出 .env
- **运维（infra-datasource-ops）**：建库、建用户、改密码
- **诊断（diag-*）**：性能问题排查

## 来源

借鉴自 [confluentinc/agent-skills](https://github.com/confluentinc/agent-skills)
