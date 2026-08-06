# JSON Column Patterns

MySQL 5.7+ supports native JSON columns. Useful, but with important caveats.

## When JSON Is Appropriate
- Truly schema-less data (user preferences, metadata bags, webhook payloads).
- Rarely filtered/joined — if you query a JSON path frequently, extract it to a real column.

## Indexing JSON: Use Generated Columns
You **cannot** index a JSON column directly. Create a virtual generated column and index that:
```sql
ALTER TABLE events
  ADD COLUMN event_type VARCHAR(50) GENERATED ALWAYS AS (data->>'$.type') VIRTUAL,
  ADD INDEX idx_event_type (event_type);
```

## Extraction Operators
| Syntax | Returns | Use for |
|---|---|---|
| `JSON_EXTRACT(col, '$.key')` | JSON type value | When you need JSON type semantics |
| `col->'$.key'` | Same as JSON_EXTRACT | Shorthand |
| `col->>'$.key'` | Unquoted scalar | WHERE comparisons, display |

Always use `->>` (unquote) in WHERE clauses.

## Multi-Valued Indexes (MySQL 8.0.17+)
```sql
ALTER TABLE products
  ADD INDEX idx_tags ((CAST(tags AS CHAR(50) ARRAY)));

SELECT * FROM products WHERE 'electronics' MEMBER OF (tags);
```

## Common Pitfalls
- **Type mismatches**: `JSON_EXTRACT` returns JSON type. Use `->>` or `JSON_UNQUOTE`.
- **Heavy update cost**: `JSON_SET`/`JSON_REPLACE` on large blobs generates significant redo/undo.
- **Large documents hurt**: JSON >8 KB spills to overflow pages.
- **VIRTUAL vs STORED**: VIRTUAL computes on read; STORED materializes on write. Both can be indexed.
