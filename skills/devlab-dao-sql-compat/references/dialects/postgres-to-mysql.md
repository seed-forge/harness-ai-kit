# PostgreSQL → MySQL 映射表

> ⚠ 本方向未经 Tiny-EMAS 项目实战验证，使用时加倍复核。⚠ 标记 = 结构性重写。
> 以 MySQL 8.0+ 为基线。

## 字符串与数组

| PostgreSQL | MySQL | 说明 |
|---|---|---|
| `split_part(s, ',', n)` | `SUBSTRING_INDEX(SUBSTRING_INDEX(s, ',', n), ',', -1)` | 边界行为不同，人工复核 |
| `string_agg(x, ',' ORDER BY y)` | `GROUP_CONCAT(x ORDER BY y SEPARATOR ',')` | 注意 group_concat_max_len |
| ⚠ `unnest(string_to_array(s, ','))` | `JSON_TABLE` 或递归 CTE 拆分 | 结构性重写 |
| `s ILIKE p` | `s LIKE p` | MySQL 默认排序规则不区分大小写（依 collation） |

## 日期时间与类型

| PostgreSQL | MySQL | 说明 |
|---|---|---|
| `date_trunc('day', d)` | `DATE(d)` | ('month') → `DATE_FORMAT(d, '%Y-%m-01')` |
| `to_timestamp(s, 'YYYY-MM-DD HH24:MI:SS')` | `STR_TO_DATE(s, '%Y-%m-%d %H:%i:%s')` | 掩码体系不同 |
| `d + INTERVAL '1 month'` | `DATE_ADD(d, INTERVAL 1 MONTH)` | |
| `expr::numeric` | `CAST(expr AS DECIMAL)` | `::` 为 PG 专有 |
| `null::varchar` | `CAST(NULL AS CHAR)` | |

## 序列、分页与 Upsert

| PostgreSQL | MySQL | 说明 |
|---|---|---|
| ⚠ `nextval('seq')` | `AUTO_INCREMENT` 或序列表方案 | 需 schema 层配合，人工决策 |
| ⚠ `generate_series(1, n)` | 递归 CTE：`WITH RECURSIVE nums AS (SELECT 1 n UNION ALL SELECT n+1 FROM nums WHERE n < x) ...` | 结构性重写 |
| `LIMIT n OFFSET m` | `LIMIT m, n` 或 `LIMIT n OFFSET m` | MySQL 两种写法均支持 |
| ⚠ `INSERT ... ON CONFLICT (k) DO UPDATE SET v = EXCLUDED.v` | `INSERT ... ON DUPLICATE KEY UPDATE v = VALUES(v)`（8.0.20+ 用行别名） | 结构性重写 |
