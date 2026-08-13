# devlab-dao-sql-compat — Usage

DAO 层通用 SQL 方言兼容性检查 + 系统性修复。支持 MyBatis/JPA/MyBatis-Plus/SQLAlchemy 四种持久层框架，通过 adapter 模式自动适配。

## 可直接复制的中文 Prompt

### 场景 1: MyBatis 项目扫描（auto-detect）

```
使用 devlab-dao-sql-compat 技能，检查本项目的 SQL 方言兼容性问题。
项目使用 MyBatis + Oracle，需评估迁移到 PostgreSQL 的影响。
```

### 场景 2: JPA 项目扫描（手动指定 adapter）

```
使用 devlab-dao-sql-compat 技能，扫描 JPA @Query 注解中的 native SQL 方言风险。
--adapter jpa --dir src/main/java
```

### 场景 3: SQLAlchemy 项目扫描

```
使用 devlab-dao-sql-compat 技能，检查 Python 项目中 text() 和 execute() 的 SQL 方言兼容性。
--adapter sqlalchemy --dir .
```

### 场景 4: 自动修复（全量）

```
使用 devlab-dao-sql-compat 技能，自动修复本项目 Mapper XML 中的 SQL 方言陷阱。
先 --dry-run 预览变更，确认后实际执行。
```

## 何时使用

- 项目需要跨数据库运行（Oracle/PostgreSQL/MySQL）
- 数据库迁移（国产化改造、云数据库切换）
- MyBatis Mapper XML / JPA @Query / SQLAlchemy text() 中混用方言语法
- 新项目初始化时检查 DAO 层 SQL 兼容性

## 输出

```
sql-compat-report.md
├── Oracle-only 语法命中明细（CRITICAL/HIGH 分级）
├── PostgreSQL-only 语法命中明细
├── MySQL 方言语法命中明细
├── 模块级风险矩阵（CRITICAL/HIGH/MEDIUM/LOW）
└── 自定义存储过程依赖统计
```

## 命令示例

```bash
# 自动检测框架并扫描
bash scripts/scan-sql-compat.sh --dir . --report ./sql-compat-report.md

# 指定 adapter 扫描
bash scripts/scan-sql-compat.sh --adapter mybatis --dir . --report ./report.md
bash scripts/scan-sql-compat.sh --adapter jpa --dir src/main/java
bash scripts/scan-sql-compat.sh --adapter sqlalchemy --dir .

# 自动修复（先预览）
bash scripts/fix-sql-compat.sh --adapter mybatis --type all --dir . --dry-run
bash scripts/fix-sql-compat.sh --adapter mybatis --type all --dir .

# CI 集成（CRITICAL 模块导致非零退出码）
bash scripts/scan-sql-compat.sh --dir . --fail-on-critical
```

## 与现有 Skill 的关系

| 现有 Skill | 关系 |
|------------|------|
| `devlab-db-data-migration` | 正交互补：本技能管 SQL 语法层面，后者管数据迁移层面 |
| `devlab-web-deep-acceptance` | 条件性集成：后端-SQL 类 FAIL 可路由到本技能做方言扫描 |
| `devlab-project-bootstrap` | Phase 4 场景化：检测持久层后询问用户是否需要 SQL 兼容性检查 |
