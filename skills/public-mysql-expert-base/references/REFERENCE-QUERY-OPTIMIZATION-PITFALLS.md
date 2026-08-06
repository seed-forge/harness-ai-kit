# Query Optimization Pitfalls

## Non-Sargable Predicates
```sql
-- BAD: function prevents index use
WHERE YEAR(created_at) = 2024
-- GOOD: sargable range
WHERE created_at >= '2024-01-01' AND created_at < '2025-01-01'
```

MySQL 8.0+ supports expression (functional) indexes:
```sql
CREATE INDEX idx ON users ((UPPER(name)));
```

## Implicit Type Conversions
```sql
-- If phone is VARCHAR, this may force CAST and scan
WHERE phone = 1234567890
-- Better: match the column type
WHERE phone = '1234567890'
```

## LIKE Patterns
```sql
WHERE name LIKE '%smith'   -- BAD: leading wildcard
WHERE name LIKE 'smith%'   -- GOOD: prefix match uses index
```

## ORDER BY + LIMIT Without an Index
```sql
-- Needs index on created_at or it will filesort
SELECT * FROM orders ORDER BY created_at DESC LIMIT 10;
```

## Other Quick Rules
- **OFFSET pagination**: use cursor-based pagination instead
- **SELECT *** defeats covering indexes
- **NOT IN with NULLs**: use NOT EXISTS instead
- **Arithmetic on indexed columns**: `WHERE price * 1.1 > 100` prevents index use; rewrite to `WHERE price > 100 / 1.1`
