# MySQL → PostgreSQL 映射表

> ⚠ 本方向未经 Tiny-EMAS 项目实战验证，使用时加倍复核。⚠ 标记 = 结构性重写。

## 空值、字符串与聚合

| MySQL | PostgreSQL | 说明 |
|---|---|---|
| `IFNULL(a, b)` | `COALESCE(a, b)` | 标准 SQL |
| `IF(cond, a, b)` | `CASE WHEN cond THEN a ELSE b END` | |
| `GROUP_CONCAT(x ORDER BY y SEPARATOR ',')` | `string_agg(x, ',' ORDER BY y)` | string_agg 要求 text 类型，数字需 ::text |
| `SUBSTRING_INDEX(s, ',', n)` | `split_part(s, ',', n)`（仅 n=1 场景等价） | n>1 语义不同（前 n 段 vs 第 n 段），人工复核 |
| `CONCAT(a, b)` | `a \|\| b` 或 `CONCAT(a, b)` | PG CONCAT 忽略 NULL，`\|\|` 遇 NULL 返回 NULL |

## 日期时间

| MySQL | PostgreSQL | 说明 |
|---|---|---|
| `NOW()` | `NOW()` / `CURRENT_TIMESTAMP` | 兼容 |
| `CURDATE()` | `CURRENT_DATE` | |
| `DATE_ADD(d, INTERVAL n DAY)` | `d + INTERVAL 'n day'` | |
| `DATE_SUB(d, INTERVAL n DAY)` | `d - INTERVAL 'n day'` | |
| `DATE_FORMAT(d, '%Y-%m-%d')` | `to_char(d, 'YYYY-MM-DD')` | 掩码逐个翻译：%H→HH24、%i→MI、%s→SS |
| `STR_TO_DATE(s, '%Y-%m-%d')` | `to_timestamp(s, 'YYYY-MM-DD')::date` | |
| `WEEKDAY(d)` | `EXTRACT(ISODOW FROM d) - 1` | 两者均周一起算，ISODOW 从 1 开始 |

## 分页、标识符与 Upsert

| MySQL | PostgreSQL | 说明 |
|---|---|---|
| `LIMIT m, n` | `LIMIT n OFFSET m` | PG 不支持逗号写法 |
| 反引号标识符 | 直接去掉或双引号 `"col"` | PG 双引号大小写敏感，优先去掉 |
| ⚠ `INSERT ... ON DUPLICATE KEY UPDATE v = VALUES(v)` | `INSERT ... ON CONFLICT (k) DO UPDATE SET v = EXCLUDED.v` | 结构性重写；需显式指定冲突键 |
