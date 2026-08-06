# public-oracle-expert-base 使用说明

## 一句话

Oracle 知识基座，被 devlab-oracle-usage 通过 extends 继承。

## 触发场景

| 你说的话 | AI 自动执行 |
|----------|-------------|
| 被 extends 继承 | devlab-oracle-usage 自动合并 Connection/JDBC/Pool 等章节 |

## 可直接复制的中文 Prompt

```
帮我配 Oracle JDBC 连接
```

```
Oracle 和 MySQL SQL 语法有什么区别
```

## 覆盖主题

- Connection Types (SID/ServiceName/TNS)
- JDBC Driver (Thin/Thick/UCP)
- Connection Pool (UCP/HikariCP)
- LOB Handling
- Character Set
- SQL Dialect Differences

## 与运维的分工

- **你（开发自助）**：查连接信息、生成代码、导出 .env
- **运维（infra-datasource-ops）**：建库、建用户、改密码
- **诊断（diag-*）**：性能问题排查

## 来源

综合 Oracle 官方文档与 JDBC 最佳实践
