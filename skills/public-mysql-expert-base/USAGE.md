# public-mysql-expert-base 使用说明

## 一句话

MySQL/InnoDB 知识基座，被 devlab-*-usage 技能通过 extends 继承。一般不直接使用。

## 触发场景

| 场景 | 说明 |
|------|------|
| 被 extends 继承 | devlab-middleware-expert 通过 extends 自动合并本技能的 Schema/Indexing/Query 等章节 |
| 直接使用 | 安装后获取 MySQL/InnoDB 通用知识参考 |

## 可直接复制的中文 Prompt

```
我在设计一个新的 MySQL 表，数据量预计千万级，帮我用 MySQL 最佳实践来设计 schema、主键和索引。
```

```
这个查询很慢，帮我用 EXPLAIN 分析一下执行计划，看看是不是索引设计有问题。
```

## 覆盖主题

- Schema Design（主键、数据类型、字符集、JSON）
- Indexing（复合索引、覆盖索引、全文索引、索引维护）
- Partitioning（RANGE/LIST/HASH）
- Query Optimization（EXPLAIN、反模式、N+1）
- Transactions & Locking（隔离级别、死锁、行锁陷阱）
- Operations（Online DDL、连接管理、复制延迟）

## 来源

借鉴自 [planetscale/database-skills](https://github.com/planetscale/database-skills) MySQL skill，去除 PlanetScale 特有内容。
