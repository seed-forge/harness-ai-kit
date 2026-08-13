---
name: devlab-dao-sql-compat
description: "DAO 层通用 SQL 方言兼容性检查 + 系统性修复工作流。支持 MyBatis/JPA/MyBatis-Plus/SQLAlchemy 四种持久层框架，扫描源码识别 Oracle/PostgreSQL/MySQL 方言混用风险，自动修复 80% 常见陷阱，剩余 20% 由 Agent 辅助人工确认。七阶段流程 + adapter 模式框架适配。触发词：SQL 兼容性、方言混用、Oracle 转 PG、PG 转 Oracle、MyBatis 迁移、JPA 方言、Hibernate SQL、SQLAlchemy raw SQL、数据库国产化改造、DAO 层 SQL 检查。"
---

# devlab-dao-sql-compat

## 用途

面向使用任何持久层框架（MyBatis / JPA / MyBatis-Plus / SQLAlchemy）的项目，解决"同一套 DAO 代码需要运行在不同数据库（Oracle / PostgreSQL / MySQL）"或"数据库迁移"场景下的 SQL 方言兼容性问题：

- **检查**：通过 adapter 模式扫描框架专属源码文件，按模块输出三方言命中矩阵与风险分级
- **修复**：AI 按转换方向加载对应映射表（references/dialects/），逐模块修复
- **验证**：静态复扫必做，库级语法预检可选，明确降级声明
- **记录**：输出前后对比与待人工复核清单

支持三方言全对称 6 个转换方向：O→PG、PG→O、O→MySQL、MySQL→O、PG→MySQL、MySQL→PG。

## 框架探测

本技能支持 4 种 DAO 框架的 adapter，默认自动探测：

| 检测特征 | 判定框架 | 扫描目标 |
|---------|---------|---------|
| `**/mapper/**/*.xml` 含 SQL 标签 | MyBatis | Mapper XML |
| `**/*.java` 含 `@Query` / `@NamedQuery` | JPA/Hibernate | Java 源码 |
| `**/*.java` 含 `QueryWrapper` / `LambdaQueryWrapper` / `BaseMapper` | MyBatis-Plus | Java + XML |
| `**/*.py` 含 `text()` / `.execute()` / `session.execute` | SQLAlchemy | Python 源码 |
| 多个命中 | 提示用户选择 | monorepo 可能多框架 |

也可手动指定：`bash scripts/scan-sql-compat.sh --adapter mybatis`

各框架的扫描模式、提取逻辑和方言陷阱详见 `references/adapters/` 下对应文档。

## 配置上下文

本 Skill 的运行时配置遵循 ai-kit 配置治理规范的三级优先级：

> L3 对话中用户明确声明的参数 > L2 用户配置（~/.ai-kit/config.yaml → 环境变量 → ~/.ai-kit/.env.tak）> L1 本目录 config.defaults.yaml

配置项见 `config.defaults.yaml`：adapter / scan_dir / module_glob / report_path / custom_procs_file / fail_on_critical / verify_jdbc_url。
其中 verify_jdbc_url 为 sensitive：无默认值，只能经 L2/L3 注入，禁止写入任何文档或提交。

## 工作流（七阶段）

### Phase 0 环境确认

1. 确认 DAO 框架类型（auto-detect 或手动 `--adapter`）
2. 确认扫描根目录（scan_dir）；框架专属源码位置默认自动探测，非标准布局时向用户确认 module_glob
3. 向用户确认**目标方言拓扑**（二选一）：
   - **单一目标库**：整个项目最终只跑一种数据库 → 所有非目标方言都是待修复项
   - **多库路由**：不同模块路由到不同数据库 → 逐模块建立"模块 → 目标方言"映射表
4. 询问是否有自定义存储过程/函数（写入 custom_procs_file 清单）

### Phase 1 扫描

    bash <本Skill目录>/scripts/scan-sql-compat.sh \
      --adapter <auto|mybatis|jpa|mybatis-plus|sqlalchemy> \
      --dir <scan_dir> [--module-glob <glob>] [--procs <file>] --report <report_path>

产出报告含：三方言命中明细、模块级风险矩阵、自定义存储过程依赖。
风险等级：CRITICAL（同模块方言混用）/ HIGH（单方言文件数 >5）/ MEDIUM（单方言文件数 ≤5）。

### Phase 2 范围决策

向用户呈现风险矩阵，确认本次修复范围（CRITICAL 优先，或用户指定模块）。**禁止全量静默修复**。

### Phase 3 自动修复

在人工修复之前，先运行自动修复引擎处理 4 类系统性问题：

    bash <本Skill目录>/scripts/fix-sql-compat.sh \
      --adapter <adapter> --type <fix-type> --dir <scan_dir> [--dry-run]

支持的修复类型：

| --type | 问题 | 修复方式 | 自动化程度 |
|--------|------|---------|-----------|
| regex-operator | PG `~` / `!~` 正则运算符 | → Oracle `REGEXP_LIKE()` / `NOT REGEXP_LIKE()` | 100% 自动 |
| coalesce-nullstr | `coalesce(col, '')` 空字符串陷阱 | → `NVL(col, ' ')` | 100% 自动 |
| todate-concat | to_date 拼接场景格式掩码 | → 修正为 `'yyyy-mm-dd'` | 100% 自动 |
| todate-direct | to_date 直接参数绑定格式掩码 | → Agent 标记候选项，需人工确认 | 仅标记 |
| all | 以上所有 | 按顺序执行 | 80% 自动 |

建议先用 `--dry-run` 预览变更。4 类陷阱根因详见 `references/systematic-fixes/`。

### Phase 4 人工修复

逐模块执行，每个模块：

1. 由"模块目标方言"和"命中方言"确定转换方向，**只读取** `references/dialects/` 下对应方向的映射表（如消除 PG 语法、目标 Oracle → 读 postgres-to-oracle.md）
2. 修复原则：
   - **最小 diff**：只改方言函数本身，不重排 SQL、不改格式
   - **优先标准 SQL**：映射表给出多个替代时选跨库兼容写法（COALESCE、CASE WHEN）
   - **结构性重写**（映射表 ⚠ 项：CONNECT BY、MERGE INTO、ROWNUM 复杂分页、generate_series 等）：完成后标记"需人工复核"
   - **自定义存储过程/函数调用不自动改写**：仅列入报告
3. 动态分支（MyBatis `<if>`/`<choose>`、JPA 条件拼接、SQLAlchemy if/else 分支）逐分支检查

### Phase 5 验证

按 `references/REFERENCE-VERIFICATION.md` 执行：
- L1 静态复扫（必做）：重跑扫描脚本，逐模块对比前后命中数
- L2 语法预检（可选）：仅当配置了 verify_jdbc_url 时，对结构性重写项逐条 EXPLAIN/PREPARE 预检
- L2 不可用时，输出降级声明

### Phase 6 记录

输出修复记录（Markdown），必须包含：
1. 模块 × (修复前 → 修复后) 方言命中数对比表
2. 待人工复核清单（结构性重写项：文件、行号、重写类型）
3. 未处理项及原因
4. 验证方式声明（L1/L2 执行情况，含降级声明）

## 约束

- 修复前必须完成 Phase 0 的框架确认 + 目标方言拓扑确认
- 结构性重写项必须标记"需人工复核"，不得静默视为完成
- MySQL 相关 4 个转换方向的映射表未经实战验证（文件头已标注），使用时加倍复核
- 扫描为正则匹配，存在少量误报可能，修复前先确认上下文
- 不修改扫描脚本检测不到但语义不同的写法，依赖 L2 验证与人工复核兜底
- JPA/SQLAlchemy adapter 的扫描正则为通用模式，项目特殊写法可能遗漏

## 参考文档

### 框架适配器

- `references/adapters/mybatis.md` - MyBatis Mapper XML 扫描模式与动态 SQL 方言陷阱
- `references/adapters/jpa.md` - JPA/Hibernate @Query 注解扫描与 JPQL vs native SQL
- `references/adapters/mybatis-plus.md` - MyBatis-Plus QueryWrapper 模式与分页插件方言
- `references/adapters/sqlalchemy.md` - SQLAlchemy text()/execute() 扫描与 Python ORM 方言

### 方言映射表

- `references/dialects/oracle-to-postgres.md` - Oracle → PostgreSQL
- `references/dialects/oracle-to-mysql.md` - Oracle → MySQL
- `references/dialects/postgres-to-oracle.md` - PostgreSQL → Oracle
- `references/dialects/postgres-to-mysql.md` - PostgreSQL → MySQL
- `references/dialects/mysql-to-oracle.md` - MySQL → Oracle
- `references/dialects/mysql-to-postgres.md` - MySQL → PostgreSQL

### 自动修复与验证

- `references/systematic-fixes/regex-operator.sed` - PG 正则运算符自动修复
- `references/systematic-fixes/coalesce-nullstr.sed` - coalesce 空字符串自动修复
- `references/systematic-fixes/todate-concat.sed` - to_date 拼接格式自动修复
- `references/systematic-fixes/todate-format-guide.md` - to_date 参数格式判断指南
- `references/REFERENCE-VERIFICATION.md` - 验证方法论（L1 静态复扫 + L2 语法预检）

## 深入阅读（可选依赖）

若环境已安装以下知识基座（skill.json 中声明为 optional 依赖），可延伸阅读数据库深度知识：
public-oracle-expert-base、public-postgres-expert-base、public-mysql-expert-base。缺失不影响本 Skill 运行。
