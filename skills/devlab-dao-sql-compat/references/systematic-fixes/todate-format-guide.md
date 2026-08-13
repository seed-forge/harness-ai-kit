# to_date 格式掩码判断指南

## 问题背景

PostgreSQL 中 `::timestamp` / `::date` 自动处理格式，迁移至 Oracle 后需要显式指定 `to_date(str, format)`。
常见错误是统一使用 `'yyyy-mm-dd hh24:mi:ss'` 格式掩码，但当输入是纯日期字符串时会导致 ORA-01830。

## 判断规则

### 规则 1：拼接场景（100% 自动修复）

如果 `to_date()` 的第一个参数包含 `||` 拼接，结果一定是纯日期：

```sql
-- 输入: '2024-01' || '-01' = '2024-01-01' → 纯日期
to_date(#{statDate}||'-01','yyyy-mm-dd')         -- ✅ 正确
to_date(#{statDate}||'-01','yyyy-mm-dd hh24:mi:ss')  -- ❌ 错误

-- 例外：拼接了时分秒 → 保留 hh24:mi:ss
to_date(#{statDate}||' 00:00:00','yyyy-mm-dd hh24:mi:ss')  -- ✅ 正确
```

### 规则 2：参数名语义推断（需 Agent 分析）

| 参数名模式 | 推断 | 格式掩码 | 置信度 |
|-----------|------|---------|--------|
| `statDate`, `startDate`, `endDate`, `queryDate` | 纯日期 | `'yyyy-mm-dd'` | 90% |
| `beginDate`, `dataDate`, `reportDate` | 纯日期 | `'yyyy-mm-dd'` | 85% |
| `taskTime`, `dataTime`, `createTime`, `updateTime` | 日期时间 | `'yyyy-mm-dd hh24:mi:ss'` | 95% |
| `abnorRecovTime`, `powerOffTime`, `hndlTime` | 日期时间 | `'yyyy-mm-dd hh24:mi:ss'` | 90% |
| 不确定 | 需查 Java 代码 | 待确认 | — |

### 规则 3：Java 代码确认（最终判定）

```java
// 纯日期 → 'yyyy-mm-dd'
@Param("statDate") String statDate   // String 类型 + 名含 Date → 纯日期
@Param("startDate") LocalDate start  // LocalDate → 纯日期

// 日期时间 → 'yyyy-mm-dd hh24:mi:ss'
@Param("taskTime") Date taskTime     // Date/Timestamp → 日期时间
@Param("dataTime") LocalDateTime dt  // LocalDateTime → 日期时间
```

## 修复优先级

1. **自动修复**（脚本可完成）：拼接场景（规则 1）
2. **Agent 辅助**（需读 Java 代码）：直接参数绑定（规则 2+3）
3. **人工确认**（Agent 无法确定时）：参数名歧义或无 Java 代码可读

## 验证方法

修复后执行：
```bash
# 检查是否还有 hh24:mi:ss 用于纯日期的场景
grep -rn "to_date.*'yyyy-mm-dd hh24:mi:ss'" --include='*.xml' . | grep -v target
```

对照结果逐条确认：
- 含 `||` 拼接且无时分秒 → 应已修复
- 参数名含 Time → 保留
- 其他 → 需确认
