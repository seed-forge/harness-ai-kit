# Oracle → PostgreSQL 映射表

> 来源：Tiny-EMAS 项目实战验证。⚠ 标记 = 结构性重写，修复后必须标记"需人工复核"。

## 空值与条件

| Oracle | PostgreSQL | 说明 |
|---|---|---|
| `NVL(a, b)` | `COALESCE(a, b)` | 标准 SQL，直接替换 |
| `NVL2(a, b, c)` | `CASE WHEN a IS NOT NULL THEN b ELSE c END` | 无对应函数 |
| `DECODE(x, v1, r1, v2, r2, d)` | `CASE x WHEN v1 THEN r1 WHEN v2 THEN r2 ELSE d END` | 标准 SQL；注意 DECODE 中 NULL=NULL 为真，CASE 不是 |

## 字符串

| Oracle | PostgreSQL | 说明 |
|---|---|---|
| `LISTAGG(x, ',') WITHIN GROUP (ORDER BY y)` | `string_agg(x, ',' ORDER BY y)` | 参数位置不同 |
| `INSTR(s, sub)` | `POSITION(sub IN s)` 或 `strpos(s, sub)` | 参数顺序相反 |
| `SUBSTR(s, 1, 3)` | `substr(s, 1, 3)` | 兼容；负起始位行为不同需人工确认 |
| ⚠ `SYS_CONNECT_BY_PATH(col, '/')` | `WITH RECURSIVE` + `path \|\| '/' \|\| col` 拼接 | 结构性重写 |

## 日期时间

| Oracle | PostgreSQL | 说明 |
|---|---|---|
| `SYSDATE` | `CURRENT_TIMESTAMP`（或 `LOCALTIMESTAMP`） | SYSDATE 无时区，注意会话时区差异 |
| `ADD_MONTHS(d, n)` | `d + INTERVAL 'n month'`（n 为字面量）或 `d + (n \|\| ' month')::interval`（n 为参数） | 月末行为不同：ADD_MONTHS 保持月末，PG 不 |
| `TRUNC(d)` | `date_trunc('day', d)` | TRUNC(d,'MM') → date_trunc('month', d) |
| `MONTHS_BETWEEN(d1, d2)` | `(EXTRACT(YEAR FROM age(d1,d2))*12 + EXTRACT(MONTH FROM age(d1,d2)))` | 小数部分语义不同，需人工复核 |
| `TO_DATE(s, 'YYYY-MM-DD HH24:MI:SS')` | `to_timestamp(s, 'YYYY-MM-DD HH24:MI:SS')` | 掩码大部分兼容；Oracle 'RR'、'J' 等 PG 不支持 |

## 分页与序列

| Oracle | PostgreSQL | 说明 |
|---|---|---|
| `WHERE ROWNUM <= n` | `LIMIT n` | LIMIT 放语句尾 |
| ⚠ `ROWNUM` 伪列参与计算/嵌套分页 | `ROW_NUMBER() OVER (ORDER BY ...)` | 结构性重写，需明确排序键 |
| `seq_name.NEXTVAL` | `nextval('seq_name')` | 序列须在 PG 端存在 |
| `seq_name.CURRVAL` | `currval('seq_name')` | 同上 |

## Upsert 与层级查询

| Oracle | PostgreSQL | 说明 |
|---|---|---|
| ⚠ `MERGE INTO t USING s ON (...) WHEN MATCHED THEN UPDATE ... WHEN NOT MATCHED THEN INSERT ...` | `INSERT INTO t (...) VALUES (...) ON CONFLICT (key) DO UPDATE SET ...` | 结构性重写；ON CONFLICT 需唯一约束支撑 |
| ⚠ `SELECT ... START WITH x CONNECT BY PRIOR id = pid` | `WITH RECURSIVE cte AS (SELECT ... WHERE x UNION ALL SELECT c.* FROM t c JOIN cte ON c.pid = cte.id) SELECT * FROM cte` | 结构性重写；LEVEL → 递归深度列自行维护 |
| ⚠ `MAX(col) KEEP (DENSE_RANK FIRST ORDER BY y)` | `DISTINCT ON (grp) ... ORDER BY grp, y` 或 ROW_NUMBER 子查询取第一行 | 结构性重写 |

## 示例：CONNECT BY → WITH RECURSIVE

Oracle：

    SELECT id, name, LEVEL FROM org
    START WITH parent_id IS NULL
    CONNECT BY PRIOR id = parent_id

PostgreSQL：

    WITH RECURSIVE cte AS (
      SELECT id, name, 1 AS lvl FROM org WHERE parent_id IS NULL
      UNION ALL
      SELECT o.id, o.name, cte.lvl + 1 FROM org o JOIN cte ON o.parent_id = cte.id
    )
    SELECT id, name, lvl FROM cte
