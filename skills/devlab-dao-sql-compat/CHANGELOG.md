# Changelog — devlab-dao-sql-compat

## 0.4.2 - 2026-08-14

- frontmatter 规范化：SKILL.md 统一 LF / 无 BOM / 单一 YAML frontmatter 块，修复 AI IDE 加载告警（missing YAML frontmatter delimited by ---）。
## [0.4.1] - 2026-08-11

- config.defaults.yaml 迁移到 harness-ai-kit-config/v1 schema（$schema 头 + config 列表格式，键位不变，validate 债务清欠）。

## [0.4.0] - 2026-08-06

### Breaking Change
- **重命名**: `devlab-mybatis-sql-compat` → `devlab-dao-sql-compat`
  - skill.json 新增 `replaces: "devlab-mybatis-sql-compat"` 字段
  - 更新所有引用方：devlab-web-deep-acceptance (3处) + devlab-db-data-migration (2处) + catalog.md

### Added — Adapter 架构
- **adapter 模式**: 从 MyBatis 专属扩展为 DAO 层通用，支持 4 种持久层框架
  - `scripts/adapters/mybatis.sh`: MyBatis Mapper XML 扫描/提取（从主脚本迁移）
  - `scripts/adapters/jpa.sh`: JPA/Hibernate @Query 注解扫描 + JPQL/native SQL 区分
  - `scripts/adapters/mybatis-plus.sh`: QueryWrapper/LambdaQueryWrapper 模式 + Mapper XML
  - `scripts/adapters/sqlalchemy.sh`: text()/execute() 扫描 + Python ORM 提取
- **框架自动探测**: `--adapter auto` 检测项目使用的 DAO 框架
- `references/adapters/` 4 个框架专属参考文档（扫描模式、方言陷阱、配置检查）

### Changed
- `scan-sql-compat.sh` 泛化：接受 `--adapter` 参数，通过 `source adapters/$ADAPTER.sh` 加载框架逻辑
- 方言映射表移入 `references/dialects/`（原 `references/` 根目录）
- `examples/` 重组为 `examples/mybatis/` + `examples/jpa/` + `examples/sqlalchemy/`
- SKILL.md 新增"框架探测"章节 + 参考文档目录
- 环境约束声明：`environment.system` 改为 ExecutableRequirement 对象格式
- 关键理念从 "mybatis-compat" 扩展为 "sql-compat"（DAO 层通用）

### Migration
- 旧 ID `devlab-mybatis-sql-compat` 在 Nexus 保留，新版本只在新 ID `devlab-dao-sql-compat` 下发布
- `.agents/skills/devlab-mybatis-sql-compat/` 应删除，替换为 `devlab-dao-sql-compat/`

## [0.3.0] - 2026-07-26

### Added
- **Phase 4: 自动修复引擎**（`scripts/fix-sql-compat.sh`）
  - 支持 4 类系统性问题的批量修复：
    1. PG `~` / `!~` 正则运算符 → Oracle `REGEXP_LIKE()` / `NOT REGEXP_LIKE()`
    2. `coalesce(col, '')` → `NVL(col, ' ')`（Oracle 视空字符串为 NULL 陷阱）
    3. `to_date(#{param} || '-01', 'yyyy-mm-dd hh24:mi:ss')` → 格式修正为 `'yyyy-mm-dd'`
    4. `to_date(#{param}, 'yyyy-mm-dd hh24:mi:ss')` → Agent 分析参数语义确定正确格式
  - 80% 修复场景可脚本化（regex-operator、coalesce-nullstr、todate-concat）
  - 20% 需 Agent 辅助人工确认（todate-format 参数类型推断）
- `references/systematic-fixes/` 新增 4 个修复模板
- `references/PG-to-Oracle.md` 补充 4 类陷阱的根因、修复策略、验证方法
- 经验来源：Tiny-EMAS v2 全量迁移实战（319 个 Mapper XML，633 处修复）

### Changed
- 工作流从 6 阶段扩展为 7 阶段，Phase 4「修复」拆分为 Phase 4「自动修复」+ Phase 5「人工修复」
- Phase 5「人工修复」降级为仅处理 Agent 标记的不确定项（从 100% 人工 → 20% 人工）

## [0.2.0] - 2026-07-26

### Changed
- 扫描前剥离 `/* */` 与 `<!-- -->` 注释（行号保持不变），消除注释内关键字误报。
- `to_timestamp` 仅报告单参 epoch 形式；两参 `to_timestamp(str,fmt)` 为 Oracle/PG 双方言兼容写法，不再计入 PG-only（实战中 452 处命中绝大多数为此类误报）。

### Added
- PG-only 新增深度 PG 特征检测，修复旧版漏报：`$$` 美元引号（常伴随 dblink/自定义函数如 dquery）、聚合 `FILTER (WHERE)` 子句、`array_agg()`、`~ '^...'` 正则运算符、裸 `LIMIT n` 分页（Oracle 不支持，PG/MySQL 共有）、`now()`、`nextval('seq')`、PG 式 `interval '数字 单位'`（单位在引号内）；`null::type` 泛化为任意 `::type` 强转。
- 经验来源：Tiny-EMAS 试点批次实战（14 处命中中 6 处为误报/兼容项，同时发现 dquery 包裹型深度 PG 查询漏报）。

## [0.1.0] - 2026-07-26

### Added
- 初始版本（draft）：通用 MyBatis SQL 方言兼容性检查 + 修复工作流。
- 六阶段工作流：环境确认 → 扫描 → 范围决策 → 修复 → 验证 → 记录。
- 参数化扫描脚本 `scripts/scan-sql-compat.sh`（--dir / --module-glob / --procs / --report / --fail-on-critical）。
- 三方言全对称映射表（6 个转换方向）+ 三层验证方法 `references/`。
- 配置治理：`config.defaults.yaml` 声明 6 个配置项，verify_jdbc_url 为 sensitive。
- 素材来源：Tiny-EMAS 项目 SQL 兼容性治理实战（O↔PG 双向已实战验证；MySQL 相关 4 向未经实战验证）。
