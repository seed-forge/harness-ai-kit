# 修复前后对比示例

本目录包含 4 类系统性问题的修复前后对比示例，来源：Tiny-EMAS v2 真实案例。

## 文件说明

| 文件 | 说明 |
|------|------|
| `before/sample-mapper.xml` | 修复前：PostgreSQL 方言混用的 Mapper XML |
| `after/sample-mapper.xml` | 修复后：Oracle 兼容的 Mapper XML |

## 示例 1: PG 正则运算符

**问题**：PostgreSQL 使用 `~` 作为正则匹配运算符，Oracle 没有此运算符。

```xml
<!-- 修复前 -->
WHERE tt.carr_chip_manuf ~ '^[0-9]+$'
WHERE tt.carr_chip_manuf !~ '[^0-9]+'

<!-- 修复后 -->
WHERE REGEXP_LIKE(tt.carr_chip_manuf, '^[0-9]+$')
WHERE NOT REGEXP_LIKE(tt.carr_chip_manuf, '[^0-9]+')
```

## 示例 2: coalesce 空字符串陷阱

**问题**：Oracle 将 `''` 视为 NULL，`coalesce(col, '')` 的回退值永远不会生效。

```xml
<!-- 修复前 -->
'pap_r' || '~' || coalesce(tt.pap_r, '')

<!-- 修复后 -->
'pap_r' || '~' || NVL(tt.pap_r, ' ')
```

## 示例 3: to_date 拼接场景格式掩码

**问题**：`#{param}||'-01'` 产生纯日期字符串，但使用了 `hh24:mi:ss` 格式掩码，导致 ORA-01830。

```xml
<!-- 修复前 -->
to_date(#{statDate} || '-01', 'yyyy-mm-dd hh24:mi:ss')

<!-- 修复后 -->
to_date(#{statDate} || '-01', 'yyyy-mm-dd')
```

## 示例 4: to_date 直接参数绑定格式掩码

**问题**：`statDate` 是纯日期参数，但使用了 `hh24:mi:ss` 格式掩码。

```xml
<!-- 修复前 -->
to_date(#{statDate}, 'yyyy-mm-dd hh24:mi:ss')

<!-- 修复后 -->
to_date(#{statDate}, 'yyyy-mm-dd')
```

## 使用方法

```bash
# 对比修复前后差异
diff examples/before/sample-mapper.xml examples/after/sample-mapper.xml
```
