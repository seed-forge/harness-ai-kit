# devlab-mybatis-sql-compat

通用 MyBatis SQL 方言兼容性检查 + 系统性修复工作流。

## 功能

- **扫描检测**：正则扫描全部 Mapper XML，输出三方言命中矩阵与风险分级
- **自动修复**：批量修复 4 类常见陷阱（80% 场景自动化）
- **人工辅助**：Agent 标记不确定项，需读取 Java 代码确认参数语义
- **验证**：静态复扫对比前后命中数，结构性重写项标记"需人工复核"

## 快速开始

### 1. 只做检查（CI 可用）

```bash
bash scripts/scan-sql-compat.sh --dir . --report ./sql-compat-report.md --fail-on-critical
```

### 2. 自动修复（推荐）

```bash
# 先预览变更（dry-run 模式）
bash scripts/fix-sql-compat.sh --type all --dir ./src --dry-run

# 确认后执行
bash scripts/fix-sql-compat.sh --type all --dir ./src
```

### 3. 单类型修复

```bash
# 只修复 PG 正则运算符
bash scripts/fix-sql-compat.sh --type regex-operator --dir ./src

# 只修复 coalesce 空字符串
bash scripts/fix-sql-compat.sh --type coalesce-nullstr --dir ./src

# 只修复 to_date 拼接格式
bash scripts/fix-sql-compat.sh --type todate-concat --dir ./src

# 标记 to_date 直接绑定候选项（需 Agent 确认）
bash scripts/fix-sql-compat.sh --type todate-direct --dir ./src
```

## 修复类型详解

| --type | 问题描述 | 修复方式 | 自动化程度 |
|--------|---------|---------|-----------|
| `regex-operator` | PG `~` / `!~` 正则运算符 | → Oracle `REGEXP_LIKE()` / `NOT REGEXP_LIKE()` | 100% 自动 |
| `coalesce-nullstr` | `coalesce(col, '')` 空字符串陷阱 | → `NVL(col, ' ')` | 100% 自动 |
| `todate-concat` | `to_date` 拼接场景格式掩码 | → 修正为 `'yyyy-mm-dd'` | 100% 自动 |
| `todate-direct` | `to_date` 直接参数绑定格式掩码 | → Agent 标记候选项，需人工确认 | 仅标记 |
| `all` | 以上所有 | 按顺序执行 | 80% 自动 |

## 使用示例

### 示例 1：PG→Oracle 迁移（Tiny-EMAS 实战）

```bash
# 1. 扫描检测
bash scripts/scan-sql-compat.sh \
  --dir ./tiny-emas-service-business \
  --report ./sql-compat-report.md

# 2. 预览修复
bash scripts/fix-sql-compat.sh \
  --type all \
  --dir ./tiny-emas-service-business \
  --dry-run

# 3. 执行修复
bash scripts/fix-sql-compat.sh \
  --type all \
  --dir ./tiny-emas-service-business

# 4. 验证（重跑扫描对比）
bash scripts/scan-sql-compat.sh \
  --dir ./tiny-emas-service-business \
  --report ./sql-compat-report-after.md
```

### 示例 2：AI 辅助完整工作流

直接对 AI 说：

```
使用 devlab-mybatis-sql-compat 技能，自动修复本项目 Mapper XML 中的 SQL 方言陷阱。
目标方言：Oracle（消除 PostgreSQL 语法）。
先运行 fix-sql-compat.sh --dry-run 预览，确认后执行。
to_date 格式掩码问题需要分析参数语义，不确定的列出来让我确认。
```

## 4 类陷阱根因

### 1. PG 正则运算符

```sql
-- PostgreSQL
WHERE col ~ '^[0-9]+$'
WHERE col !~ '[^0-9]+'

-- Oracle（修复后）
WHERE REGEXP_LIKE(col, '^[0-9]+$')
WHERE NOT REGEXP_LIKE(col, '[^0-9]+')
```

### 2. coalesce 空字符串

```sql
-- PostgreSQL（正常工作）
SELECT coalesce(col, '') FROM dual  -- NULL → ''

-- Oracle（陷阱！'' 被视为 NULL）
SELECT coalesce(col, '') FROM dual  -- NULL → NULL（回退值不生效）
SELECT NVL(col, ' ') FROM dual     -- NULL → ' '（修复后）
```

### 3. to_date 拼接格式

```sql
-- 错误（拼接结果是纯日期，但用了 datetime 格式）
to_date(#{statDate}||'-01','yyyy-mm-dd hh24:mi:ss')

-- 正确
to_date(#{statDate}||'-01','yyyy-mm-dd')

-- 例外：拼接了时分秒 → 保留 hh24:mi:ss
to_date(#{statDate}||' 00:00:00','yyyy-mm-dd hh24:mi:ss')  -- ✅ 正确
```

### 4. to_date 参数格式

```sql
-- 纯日期参数（如 statDate/startDate）
to_date(#{statDate},'yyyy-mm-dd')

-- 日期时间参数（如 taskTime/dataTime）
to_date(#{taskTime},'yyyy-mm-dd hh24:mi:ss')

-- 判断依据：Java 参数类型
-- String + 名含 Date → 纯日期
-- Date/Timestamp + 名含 Time → 日期时间
```

## 配置

配置项声明见 `config.defaults.yaml`，按 L3（对话参数）> L2（环境变量）> L1（默认值）解析：

| key | 默认 | 说明 |
|-----|------|------|
| scan_dir | `.` | 扫描根目录 |
| module_glob | 自动探测 | 模块目录 glob |
| report_path | `./sql-compat-report.md` | 报告输出路径 |
| custom_procs_file | 无 | 自定义存储过程清单 |
| fail_on_critical | false | CI 模式退出码 |
| verify_jdbc_url | 无（sensitive） | 可选库验证连接串 |

## 文件结构

```
.agents/skills/devlab-mybatis-sql-compat/
├── SKILL.md                    # 技能说明
├── USAGE.md                    # 使用指南
├── README.md                   # 本文件
├── CHANGELOG.md                # 版本历史
├── skill.json                  # 技能元数据
├── config.defaults.yaml        # 配置声明
├── scripts/
│   ├── scan-sql-compat.sh      # 扫描检测脚本
│   └── fix-sql-compat.sh       # 自动修复引擎
├── references/
│   ├── postgres-to-oracle.md   # PG→Oracle 映射表
│   ├── oracle-to-postgres.md   # Oracle→PG 映射表
│   ├── ...                     # 其他方向映射表
│   ├── verification.md         # 验证方法
│   └── systematic-fixes/       # 系统性修复模板
│       ├── regex-operator.sed
│       ├── coalesce-nullstr.sed
│       ├── todate-concat.sed
│       └── todate-format-guide.md
└── examples/
    ├── before/                 # 修复前示例
    └── after/                  # 修复后示例
```

## 版本历史

| 版本 | 日期 | 主要变更 |
|------|------|---------|
| v0.3.0 | 2026-07-27 | 新增自动修复引擎（4 类系统性问题） |
| v0.2.0 | 2026-07-26 | 深度 PG 特征检测（$$、FILTER、array_agg 等） |
| v0.1.0 | 2026-07-26 | 初始版本（六阶段工作流） |

## 经验来源

- Tiny-EMAS v2 全量迁移实战：319 个 Mapper XML，633 处修复
- 12 个并行 Agent 审查，784K tokens 验证
- 4 类系统性陷阱的根因分析与修复策略

## License

内部团队工具，遵循 ai-kit 规范。
