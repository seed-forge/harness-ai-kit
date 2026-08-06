# CHANGELOG — public-mysql-expert-base

## 0.1.1 - 2026-08-06

- 治理清欠：结构合规修复后版本抬升（ref_link、ref_rename:README.md->REFERENCE-README.md、refs）。

## 0.1.0 - 2026-07-09

- 初始版本。借鉴自 [planetscale/database-skills](https://github.com/planetscale/database-skills) MySQL skill
- 去除 PlanetScale/Vitess 特有内容（hosting 推荐、deploy requests、vtgate 连接池）
- 保留通用 MySQL/InnoDB 知识：schema 设计、索引、查询优化、事务与锁、分区、运维操作
- 18 个参考文档适配为 team-ai-kit REFERENCE-* 命名规范
- 定位为 extends 知识基座，供 devlab-*-usage 技能继承
