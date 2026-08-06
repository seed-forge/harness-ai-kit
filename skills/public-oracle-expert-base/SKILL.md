---
name: public-oracle-expert-base
description: Oracle 知识基座。覆盖 Connection Types、JDBC Driver、Connection Pool、LOB Handling、Character Set、SQL Dialect。供 devlab-oracle-usage 通过 extends 继承。
---

# Oracle Database Knowledge Base

> **Source**: Compiled from Oracle official documentation, JDBC best practices, and common integration patterns.

## Connection Types
| Format | Example | Status |
|--------|---------|--------|
| Service Name | `jdbc:oracle:thin:@//host:port/service_name` | **Recommended** |
| SID (legacy) | `jdbc:oracle:thin:@host:port:SID` | Legacy, avoid |
| TNS | `jdbc:oracle:thin:@tns_alias` | Enterprise with tnsnames.ora |
| EZConnect | `jdbc:oracle:thin:@host:port/service_name` | Simple, no config file |

- **Always prefer Service Name** over SID for new projects.
- Easy Connect Plus (19c+): `jdbc:oracle:thin:@tcp://host:port/service_name?wallet_location=/path`.

## JDBC Driver
| Type | Description | When to use |
|------|-------------|-------------|
| Thin (Type 4) | Pure Java, no Oracle client | **Default choice** |
| Thick (OCI, Type 2) | Requires Oracle Client | Advanced features (TAF, Advanced Queuing) |
| UCP | Universal Connection Pool | Production pooling |

- Thin driver is sufficient for 95% of use cases.
- Use `ojdbc8.jar` for JDK 8+, `ojdbc11.jar` for JDK 11+.
- Add `orai18n.jar` for internationalization support.

## Connection Pool
| Pool | Recommended for |
|------|----------------|
| UCP (Oracle) | Oracle-specific features, best performance |
| HikariCP | Spring Boot, general-purpose, simpler config |

HikariCP config for Oracle:
```properties
spring.datasource.driver-class-name=oracle.jdbc.OracleDriver
spring.datasource.url=jdbc:oracle:thin:@//host:1521/service_name
spring.datasource.hikari.maximum-pool-size=20
spring.datasource.hikari.connection-timeout=5000
spring.datasource.hikari.idle-timeout=300000
spring.datasource.hikari.connection-test-query=SELECT 1 FROM DUAL
```

## LOB Handling
- `CLOB` for large text (>4000 chars); `BLOB` for binary data.
- Use `setStringForClob()` / `setBinaryStream()` for inserts.
- For reads, use `getCharacterStream()` / `getBinaryStream()` — avoid `getString()` on large CLOBs.
- LOB locator vs data: `oracle.jdbc.useStreamForLobOutput=true` for streaming writes.

## Character Set
- **AL32UTF8** is the recommended database character set (Unicode).
- JDBC driver auto-detects charset from database; no client-side config needed.
- Verify: `SELECT value FROM nls_database_parameters WHERE parameter='NLS_CHARACTERSET';`

## SQL Dialect Differences (vs MySQL/PostgreSQL)
| Feature | Oracle | MySQL/PostgreSQL |
|---------|--------|-----------------|
| Auto-increment | `SEQUENCE` + `TRIGGER` or `IDENTITY` (12c+) | `AUTO_INCREMENT` / `SERIAL` |
| LIMIT | `FETCH FIRST n ROWS ONLY` (12c+) or `ROWNUM` | `LIMIT n` |
| String concat | `||` operator | `CONCAT()` / `||` |
| Date functions | `SYSDATE`, `ADD_MONTHS()`, `MONTHS_BETWEEN()` | `NOW()`, `DATE_ADD()` |
| Boolean | No native BOOLEAN in SQL (use NUMBER(1)) | Native `BOOLEAN` |
| Outer join syntax | `(+)` legacy or ANSI `LEFT JOIN` | ANSI `LEFT JOIN` |

## Oracle Wallet
- Wallet stores credentials for mutual TLS authentication.
- Location: set `oracle.net.wallet_location` in connection properties.
- For Autonomous Database: download wallet zip, extract to directory, reference in connection string.

## Guardrails
- Use Service Name format, not SID.
- Always use connection pooling (UCP or HikariCP).
- Use bind variables (prepared statements) — never string concatenation for SQL.
- Set `oracle.jdbc.ReadTimeout` and `oracle.net.CONNECT_TIMEOUT`.
- For LOBs >4KB, always use streaming API.
