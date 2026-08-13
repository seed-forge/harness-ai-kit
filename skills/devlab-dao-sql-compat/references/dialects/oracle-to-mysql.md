# Oracle → MySQL 映射表

> ⚠ 本方向未经 Tiny-EMAS 项目实战验证，使用时加倍复核。⚠ 标记 = 结构性重写。
> 以 MySQL 8.0+ 为基线（支持 CTE 与窗口函数）。

## 空值与条件

| Oracle | MySQL | 说明 |
|---|---|---|
| `NVL(a, b)` | `IFNULL(a, b)` 或 `COALESCE(a, b)` | 推荐 COALESCE（标准 SQL） |
| `DECODE(x, v1, r1, d)` | `CASE x WHEN v1 THEN r1 ELSE d END` | 标准 SQL |

## 字符串

| Oracle | MySQL | 说明 |
|---|---|---|
| `LISTAGG(x, ',') WITHIN GROUP (ORDER BY y)` | `GROUP_CONCAT(x ORDER BY y SEPARATOR ',')` | 受 group_concat_max_len（默认 1024）限制 |
| `s1 \|\| s2` | `CONCAT(s1, s2)` | MySQL 默认 `\|\|` 是逻辑或（除非 PIPES_AS_CONCAT 模式） |
| `SUBSTR(s, -3)` | `SUBSTRING(s, -3)` | 兼容 |

## 日期时间

| Oracle | MySQL | 说明 |
|---|---|---|
| `SYSDATE` | `NOW()` | MySQL 也有 SYSDATE() 但语义为语句内实时值，勿混用 |
| `ADD_MONTHS(d, n)` | `DATE_ADD(d, INTERVAL n MONTH)` | 月末行为不同，需人工复核 |
| `TRUNC(d)` | `DATE(d)` | TRUNC(d,'MM') → `DATE_FORMAT(d, '%Y-%m-01')` |
| `TO_CHAR(d, 'YYYY-MM-DD')` | `DATE_FORMAT(d, '%Y-%m-%d')` | 掩码体系完全不同，逐个翻译 |
| `TO_DATE(s, 'YYYY-MM-DD')` | `STR_TO_DATE(s, '%Y-%m-%d')` | 同上 |

## 分页、序列与 Upsert

| Oracle | MySQL | 说明 |
|---|---|---|
| `WHERE ROWNUM <= n` | `LIMIT n` | |
| ⚠ `seq.NEXTVAL` | `AUTO_INCREMENT` 列或序列表方案 | MySQL 无原生序列，需 schema 层配合，人工决策 |
| ⚠ `MERGE INTO ...` | `INSERT ... ON DUPLICATE KEY UPDATE ...` | 结构性重写；需唯一键支撑 |
| ⚠ `CONNECT BY` | `WITH RECURSIVE`（8.0+） | 结构性重写，写法同 PG 方向 |
