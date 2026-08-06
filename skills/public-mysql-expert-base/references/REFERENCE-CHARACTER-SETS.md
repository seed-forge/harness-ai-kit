# Character Sets and Collations

## Always Use utf8mb4
MySQL's `utf8` = `utf8mb3` (3-byte only, no emoji/many CJK). Always `utf8mb4`.

```sql
CREATE DATABASE myapp DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
```

## Collation Quick Reference
| Collation | Behavior | Use for |
|---|---|---|
| `utf8mb4_0900_ai_ci` | Case-insensitive, accent-insensitive | Default |
| `utf8mb4_0900_as_cs` | Case/accent sensitive | Exact matching |
| `utf8mb4_bin` | Byte-by-byte comparison | Tokens, hashes |

`_0900_` = Unicode 9.0 (preferred over older `_unicode_` variants).

## Collation Behavior
- **Case-insensitive (`_ci`)**: `'A' = 'a'` true, `LIKE 'a%'` matches 'Apple'
- **Case-sensitive (`_cs`)**: `'A' = 'a'` false
- **Binary (`_bin`)**: strict byte-by-byte comparison

Override per query: `WHERE name COLLATE utf8mb4_0900_as_cs = 'José';`

## Migrating from utf8/utf8mb3
```sql
SELECT table_name, column_name FROM information_schema.columns
WHERE table_schema = 'mydb' AND character_set_name = 'utf8';

ALTER TABLE users CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
```

**Warning**: index key length limits depend on InnoDB row format:
- DYNAMIC/COMPRESSED: 3072 bytes max (≈768 chars with utf8mb4)
- REDUNDANT/COMPACT: 767 bytes max (≈191 chars with utf8mb4)

## Connection
Ensure client uses `utf8mb4`: `SET NAMES utf8mb4;` (most modern drivers default to this).
