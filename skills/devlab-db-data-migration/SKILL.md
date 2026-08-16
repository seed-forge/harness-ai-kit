---
name: devlab-db-data-migration
description: "数据库数据层安全迁移专家技能。覆盖 schema 演进（加列/改约束/建索引）与数据搬迁的完整安全流程：备份→幂等检测→迁移→验证→失败回滚。当项目需要变更已有表结构、生产报 no such column / 唯一约束冲突、或需编写独立迁移脚本时使用。与 devlab-dao-sql-compat 互补：本技能管数据层面，后者管 SQL 语法层面。Triggers on \"数据迁移\", \"表结构变更\", \"schema 演进\", \"no such column\", \"唯一约束冲突\", \"迁移脚本\", \"db migration\"."
---

# devlab-db-data-migration

## 用途

数据库**数据层**安全迁移：当已有表需要加列、改约束、建索引或搬迁数据时，提供一条"绝不留半迁移状态"的安全流程。源自真实生产修复（33/33 测试通过 + 生产库迁移成功）。

**定位**：与 `devlab-dao-sql-compat`（SQL 语法兼容层）正交互补——一个管"语法怎么写才兼容"，一个管"数据怎么迁才安全"。

## 适用场景

- 已有表结构演进：加列、改唯一约束、补索引。
- 生产环境报 `no such column` / 唯一约束冲突。
- 需要编写可重复执行、可回滚的独立迁移脚本。
- 跨库数据搬迁需要行数对账。

## 不适用场景

- SQL 语法跨方言兼容问题（用 `devlab-dao-sql-compat`）。
- 组织内部集群 应用级迁移（用 `组织内部集群-app-migration`，非数据层）。
- 全新建表（无历史数据，直接建即可）。

## 通用五步流程（所有数据库通用）

1. **备份**：迁移前备份（文件库复制 .bak；服务端库 dump 或快照），记录备份位置。
2. **幂等检测**：先探测目标结构是否已存在（列/索引/约束），已迁移则退出 0——保证脚本可重复执行。
3. **迁移执行**（顺序硬约束）：
   - 加列必须先于任何引用新列的 CREATE INDEX / 回填 UPDATE。
   - 约束变更评估该方言是否支持在线 ALTER，不支持则走重建表路径。
   - 索引对齐/去重必须在改名、补列、回填、legacy 合并全部完成之后。
4. **迁移后验证**：schema 断言（结构符合预期）+ 行数对账（旧表 == 新表）+ 全量测试回归。
5. **失败自动恢复**：任一步异常 → 从备份恢复 → 退出非 0，**绝不留半迁移状态**。

## 方言分支

### SQLite

- `ALTER TABLE` 仅支持加列/改名；**UNIQUE 约束不可 ALTER**，只能四步重建：
  `CREATE TABLE new_x` → `INSERT INTO new_x SELECT ...` → `DROP TABLE x` → `RENAME TO x`（重建后补全部索引）。
- 探测用 `PRAGMA table_info` / `PRAGMA index_list`。
- 陷阱：`CREATE TABLE IF NOT EXISTS` 不会更新已存在表的列与约束。

### MySQL（Flyway/Liquibase 场景）

- 版本化脚本内做幂等：information_schema 探测 + 动态 SQL 条件执行。
- 大表 DDL 评估 online DDL / pt-osc；重建表路径同样适用约束不兼容场景。

## 工程约定

- 开发环境可用代码内自动迁移（嵌入 init）；**生产必须独立迁移脚本**（有备份/dry-run/回滚/审计）。
- CLI 约定：`--db <path>` / `--dry-run` / `--rollback`。
- 验收标准：迁移后全量测试绿 + 实际库 schema 验证通过。

## 附带 tool

- `scripts/sqlite_safe_migration.py` — Python 单文件模板（备份/幂等/重建/验证/回滚骨架已固化，按具体迁移填充 MIGRATION 区）。

## Notes：迁移脚本编辑纪律

编辑顺序敏感的迁移脚本时：**连续 2 次 patch 失败/overlap 即熔断**——停止增量修改，
全量重读文件 + grep 关键锚点定位，单次精准 patch 后 grep 校验锚点唯一且位置正确。

根因：多次改动后锚点漂移，基于"记忆中的旧版本"继续 patch 必然错位。

## 与其他 Skill 的关系

| Skill | 关系 |
|-------|------|
| `devlab-dao-sql-compat` | 正交互补：语法层 vs 数据层 |
| `public-mysql-expert-base` | 知识库上游（schema 设计知识） |
| `devlab-srv-reliability-ops` / `infra-reliability-ops` | 迁移失败根因诊断（研发服务/基础设施） |
| `组织内部集群-app-migration` | 无关（应用级迁移，非数据层） |

## 推荐触发方式

```text
用 devlab-db-data-migration 帮我给这张表加唯一约束，SQLite 的，要安全可回滚
```

```text
生产报 no such column，帮我按安全迁移流程排查修复
```
