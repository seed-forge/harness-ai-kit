# Fulltext Indexes

Fulltext indexes are useful for keyword text search in MySQL. For advanced ranking or fuzzy matching, prefer a dedicated search engine.

```sql
ALTER TABLE articles ADD FULLTEXT INDEX ft_title_body (title, body);

-- Natural language (default, sorted by relevance)
SELECT *, MATCH(title, body) AGAINST('database performance') AS score
FROM articles WHERE MATCH(title, body) AGAINST('database performance');

-- Boolean mode: + required, - excluded, * suffix wildcard
WHERE MATCH(title, body) AGAINST('+mysql -postgres +optim*' IN BOOLEAN MODE);
```

## Key Gotchas
- **Min word length**: default 3 chars (`innodb_ft_min_token_size`).
- **Stopwords**: common words excluded from index.
- **No partial matching**: requires whole tokens (except `*` in boolean mode).
- **MATCH() columns must correspond to an index definition**.
- Fulltext adds write overhead — consider Elasticsearch/Meilisearch for complex search.
