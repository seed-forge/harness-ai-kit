# PostgreSQL → Oracle 映射表

> 来源：Tiny-EMAS 项目实战验证。⚠ 标记 = 结构性重写，修复后必须标记"需人工复核"。

## 字符串与数组

| PostgreSQL | Oracle | 说明 |
|---|---|---|
| `split_part(s, ',', n)` | `REGEXP_SUBSTR(s, '[^,]+', 1, n)` | 空段行为不同（split_part 保留空段，REGEXP_SUBSTR 跳过），需人工复核 |
| ⚠ `unnest(string_to_array(s, ','))` | `SELECT REGEXP_SUBSTR(s,'[^,]+',1,LEVEL) FROM DUAL CONNECT BY LEVEL <= REGEXP_COUNT(s,',')+1` | 结构性重写（行集展开） |
| `string_agg(x, ',' ORDER BY y)` | `LISTAGG(x, ',') WITHIN GROUP (ORDER BY y)` | Oracle 12c 前 LISTAGG 有 4000 字节上限 |
| `s ILIKE p` | `UPPER(s) LIKE UPPER(p)` | Oracle 无 ILIKE |

## 日期时间

| PostgreSQL | Oracle | 说明 |
|---|---|---|
| `date_trunc('day', d)` | `TRUNC(d)` | date_trunc('month',d) → TRUNC(d,'MM')；('year') → TRUNC(d,'YYYY') |
| `to_timestamp(s, fmt)` | `TO_TIMESTAMP(s, fmt)` | 同名但格式掩码差异：PG 'FMDay' 类修饰符 Oracle 不支持，逐个核对 |
| `NOW()` | `SYSTIMESTAMP`（或 `CURRENT_TIMESTAMP`） | NOW() 为 PG/MySQL 语法，Oracle 不支持 |
| `d + INTERVAL '1 month'` | `ADD_MONTHS(d, 1)` | Oracle 也支持 `INTERVAL '1' MONTH`（引号位置不同），但月末行为以 ADD_MONTHS 为准 |
| `CURRENT_DATE` | `TRUNC(SYSDATE)` | Oracle CURRENT_DATE 受会话时区影响，语义不同 |

## 类型与分页

| PostgreSQL | Oracle | 说明 |
|---|---|---|
| `expr::numeric` / `null::varchar` | `CAST(expr AS NUMBER)` / `CAST(NULL AS VARCHAR2(n))` | `::` 为 PG 专有 |
| `LIMIT n OFFSET m` | `OFFSET m ROWS FETCH NEXT n ROWS ONLY`（12c+）或 ROWNUM 嵌套 | 11g 及以下必须 ROWNUM 三层嵌套 |
| ⚠ `generate_series(1, n)` | `SELECT LEVEL FROM DUAL CONNECT BY LEVEL <= n` | 结构性重写；日期序列需 LEVEL 参与日期运算 |

## Upsert 与序列

| PostgreSQL | Oracle | 说明 |
|---|---|---|
| ⚠ `INSERT ... ON CONFLICT (k) DO UPDATE SET ...` | `MERGE INTO t USING (SELECT ... FROM DUAL) s ON (...) WHEN MATCHED THEN UPDATE ... WHEN NOT MATCHED THEN INSERT ...` | 结构性重写 |
| `nextval('seq')` | `seq.NEXTVAL` | 序列须在 Oracle 端存在 |
| ⚠ 动态 DDL（如项目自定义 `ddlexec(...)`） | 存储过程内 `EXECUTE IMMEDIATE` | 项目自定义函数不自动改写，列入报告人工处理 |

## 示例：ON CONFLICT → MERGE INTO

PostgreSQL：

    INSERT INTO t (id, val) VALUES (#{id}, #{val})
    ON CONFLICT (id) DO UPDATE SET val = EXCLUDED.val

Oracle：

    MERGE INTO t USING (SELECT #{id} AS id, #{val} AS val FROM DUAL) s
    ON (t.id = s.id)
    WHEN MATCHED THEN UPDATE SET t.val = s.val
    WHEN NOT MATCHED THEN INSERT (id, val) VALUES (s.id, s.val)
