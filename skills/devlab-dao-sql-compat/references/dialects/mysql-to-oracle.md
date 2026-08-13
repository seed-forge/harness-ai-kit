# MySQL → Oracle 映射表

> ⚠ 本方向未经 Tiny-EMAS 项目实战验证，使用时加倍复核。⚠ 标记 = 结构性重写。

## 空值、字符串与聚合

| MySQL | Oracle | 说明 |
|---|---|---|
| `IFNULL(a, b)` | `NVL(a, b)` 或 `COALESCE(a, b)` | 推荐 COALESCE |
| `IF(cond, a, b)` | `CASE WHEN cond THEN a ELSE b END` | Oracle 无 IF 函数 |
| `GROUP_CONCAT(x ORDER BY y SEPARATOR ',')` | `LISTAGG(x, ',') WITHIN GROUP (ORDER BY y)` | 12c 前注意 4000 字节上限 |
| `SUBSTRING_INDEX(s, ',', n)` | n>0: `SUBSTR(s, 1, INSTR(s, ',', 1, n) - 1)` | 需处理分隔符不足 n 个的边界，人工复核 |
| `CONCAT(a, b, c)` | `a \|\| b \|\| c` | Oracle CONCAT 仅两参数 |

## 日期时间

| MySQL | Oracle | 说明 |
|---|---|---|
| `NOW()` | `SYSDATE`（秒级）/ `SYSTIMESTAMP` | |
| `CURDATE()` | `TRUNC(SYSDATE)` | |
| `DATE_ADD(d, INTERVAL n DAY)` | `d + n` | 月：`ADD_MONTHS(d, n)` |
| `DATE_SUB(d, INTERVAL n DAY)` | `d - n` | 月：`ADD_MONTHS(d, -n)` |
| `DATE_FORMAT(d, '%Y-%m-%d')` | `TO_CHAR(d, 'YYYY-MM-DD')` | 掩码逐个翻译：%H→HH24、%i→MI、%s→SS |
| `STR_TO_DATE(s, '%Y-%m-%d')` | `TO_DATE(s, 'YYYY-MM-DD')` | 同上 |
| `WEEKDAY(d)` | `TO_CHAR(d, 'D')` 换算 | WEEKDAY 周一=0；TO_CHAR 'D' 受 NLS_TERRITORY 影响，需人工复核 |

## 分页与 Upsert

| MySQL | Oracle | 说明 |
|---|---|---|
| `LIMIT n` | `FETCH FIRST n ROWS ONLY`（12c+）或 `WHERE ROWNUM <= n` | |
| ⚠ `LIMIT m, n` | `OFFSET m ROWS FETCH NEXT n ROWS ONLY`（12c+）或 ROWNUM 三层嵌套 | 结构性重写（11g 及以下） |
| ⚠ `INSERT ... ON DUPLICATE KEY UPDATE` | `MERGE INTO ... USING DUAL` | 结构性重写 |
| 反引号标识符 | 双引号 `"COL"` 或直接去掉 | Oracle 双引号标识符大小写敏感，优先去掉 |
