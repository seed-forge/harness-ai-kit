# JPA/Hibernate Adapter — @Query 注解扫描与方言陷阱

## 扫描目标

- **文件类型**: `*.java`（Java 源文件）
- **路径探测**: `src/main/java/**/*.java`（含 `@Query` / `@NamedQuery` 的文件）
- **注释剥离**: Java `//` 单行 + `/* */` 多行

## SQL 提取模式

JPA/Hibernate 中的 SQL 通过注解嵌入：

```java
// JPQL（框架生成 SQL，方言由 Hibernate dialect 处理）
@Query("SELECT u FROM User u WHERE u.status = :status")

// Native SQL（直接方言相关）
@Query(value = "SELECT * FROM users WHERE REGEXP_LIKE(name, :pattern)", nativeQuery = true)
```

### JPQL vs Native SQL 的方言风险

- **JPQL**: 方言风险低——Hibernate 根据 `hibernate.dialect` 自动转换函数。但部分 JPQL 函数在跨方言时有差异
- **Native SQL**: 方言风险高——直接写入方言语法，与 MyBatis Mapper XML 等价

### 方言陷阱（JPA 专属）

1. **Hibernate 函数差异**: `DATE()` 在 Oracle dialect 下映射为 `TO_DATE()`，在 PG dialect 下映射为 `DATE()`。JPQL 中使用 `DATE()` 是安全的，但 native query 中需注意
2. **`@Modifying` + nativeQuery**: 批量 UPDATE/DELETE 的 native query 常含方言 DDL（`MERGE INTO`、`RETURNING`）
3. **Hibernate `dialect` 配置**: `spring.jpa.database-platform` 指定方言类，影响生成的 SQL。扫描时需确认项目使用的 dialect
4. **`@OrderBy` vs `ORDER BY`**: `@OrderBy` 在 JPQL 中安全，但 native query 中的 `ORDER BY` 可能含方言分页语法
5. **Hibernate `@Formula`**: `@Formula` 注解中的 SQL 是 native 的，方言风险等同 `nativeQuery=true`

## 与其他 adapter 的关系

- **MyBatis adapter**: 如果项目同时使用 MyBatis 和 JPA（混合持久层），应分别用两个 adapter 扫描，或使用 `--adapter mybatis-plus`（覆盖更广）
- **SQLAlchemy adapter**: Python 项目的等价物，扫描 `text()` 而非 `@Query`
