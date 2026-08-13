# SQLAlchemy Adapter — text()/execute() 扫描与方言陷阱

## 扫描目标

- **文件类型**: `*.py`（Python 源文件）
- **路径探测**: 含 `text()` / `.execute()` / `session.execute` / `engine.execute` 的 Python 文件
- **注释剥离**: Python `#` 单行注释（保留字符串内的 `#`）

## SQL 提取模式

SQLAlchemy 中的 raw SQL 通过以下方式嵌入：

```python
# text() 构造（最常见，方言风险最高）
result = session.execute(text("SELECT * FROM users WHERE name ~ :pattern"))

# execute() 直接执行 raw SQL
conn.execute("SELECT * FROM users WHERE status = 'active'")

# f-string 拼接（危险，可能含方言代码）
query = f"SELECT * FROM users WHERE created_at > '{date}'"
session.execute(text(query))

# ORM query() API（框架生成 SQL，方言风险低）
session.query(User).filter(User.status == 'active').all()
```

### ORM API vs Raw SQL 的方言风险

- **ORM query() / select()**: 方言风险低——SQLAlchemy Core 根据绑定的 dialect 自动转换类型和函数
- **text() / execute()**: 方言风险高——直接写入方言语法，需逐行扫描
- **f-string 拼接**: 最危险——可能引入不可控的方言代码，且无法被 SQL 解析器验证

### 方言陷阱（SQLAlchemy 专属）

1. **`::type` 类型转换**: PostgreSQL 专有（`col::text`），Oracle 需 `CAST(col AS VARCHAR)`
2. **`||` 字符串拼接**: Oracle 和 PG 支持 `||`，MySQL 需 `CONCAT()` 函数
3. **`LIMIT/OFFSET`**: PG 和 MySQL 支持，Oracle 需 `ROWNUM` 或 `FETCH FIRST`
4. **`RETURNING`**: PG 支持 `RETURNING`，Oracle 支持 `RETURNING ... INTO`，MySQL 不支持
5. **布尔字面量**: PG 支持 `TRUE`/`FALSE`，Oracle 用 `1`/`0`，MySQL 用 `1`/`0`
6. **`EXTRACT(field FROM ...)`**: 跨库支持但参数格式不同
7. **`||` vs `CONCAT()`**: 在 `text()` 中直接写的 `||` 在 MySQL 上会失败
8. **SQLAlchemy `dialect` 配置**: 连接字符串中的 `dialect://` 决定生成 SQL 的方言语法。扫描前应确认 `engine = create_engine("postgresql://...")` 的 dialect

## 配置检查

扫描前应确认项目的 SQLAlchemy 配置：

```python
# 连接字符串中的 dialect
engine = create_engine("postgresql://user:pass@host/db")  # PG
engine = create_engine("oracle+cx_oracle://user:pass@host/db")  # Oracle
engine = create_engine("mysql+pymysql://user:pass@host/db")  # MySQL
```

## 与其他 adapter 的关系

- **JPA adapter**: Java 项目的等价物。JPA 扫描 `@Query`，本 adapter 扫描 `text()` / `execute()`
- **MyBatis adapter**: 不相关——Python 和 Java 项目使用不同的持久层框架
