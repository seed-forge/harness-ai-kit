# MyBatis-Plus Adapter — QueryWrapper 模式与分页插件方言

## 扫描目标

- **文件类型**: `*.java` + `*.xml`（Java 源码 + Mapper XML）
- **路径探测**: `src/main/java/**/*.java`（含 QueryWrapper/BaseMapper）+ `src/main/resources/mapper/**/*.xml`
- **注释剥离**: 按文件类型选择（Java: `//` + `/* */`；XML: `<!-- -->` + `/* */`）

## SQL 提取模式

MyBatis-Plus 在 MyBatis 基础上增加了 Java API 方式的查询构建：

```java
// QueryWrapper（运行时生成 SQL，方言由 DbType 枚举决定）
QueryWrapper<User> wrapper = new QueryWrapper<>();
wrapper.eq("status", 1).ge("age", 18).orderByDesc("create_time");

// LambdaQueryWrapper（类型安全版本）
LambdaQueryWrapper<User> lambda = new LambdaQueryWrapper<>();
lambda.eq(User::getStatus, 1).ge(User::getAge, 18);

// BaseMapper 方法（框架生成 SQL）
userMapper.selectList(wrapper);
userMapper.selectPage(page, wrapper);
```

### 方言陷阱（MyBatis-Plus 专属）

1. **分页插件方言**: MyBatis-Plus 的 `PaginationInnerInterceptor` 根据 `DbType` 枚举自动生成方言分页 SQL。配置错误会导致分页 SQL 在目标库执行失败
   - `DbType.ORACLE` → `ROWNUM` 分页
   - `DbType.POSTGRE_SQL` → `LIMIT/OFFSET` 分页
   - `DbType.MYSQL` → `LIMIT offset,count` 分页
2. **`@TableName` autoResultMap**: 启用 `autoResultMap = true` 后，`@TableField(typeHandler = ...)` 的类型处理可能引入方言转换逻辑
3. **`Db.generateId()` / `IdType.ASSIGN_ID`**: 雪花算法 ID 生成在不同库的序列/自增列上有不同兼容性
4. **`@TableLogic` 逻辑删除**: 生成的 `UPDATE ... SET deleted=1 WHERE ...` 在不同库的布尔类型处理不同
5. **`@Version` 乐观锁**: 生成的 `WHERE version = #{version}` 子句在不同库的事务隔离级别下行为不同

## 配置检查

扫描前应确认项目的 MyBatis-Plus 配置：

```yaml
mybatis-plus:
  configuration:
    database-id: oracle  # 或 postgresql / mysql — 影响方言选择
  global-config:
    db-config:
      db-type: oracle
```

## 与其他 adapter 的关系

- **MyBatis adapter**: 本 adapter 是 MyBatis adapter 的超集——同时扫描 Mapper XML 和 Java QueryWrapper。如果项目只用 MyBatis（无 QueryWrapper），用 `--adapter mybatis` 更精准
- **JPA adapter**: 如果项目混合使用 MyBatis-Plus 和 JPA，应分别用两个 adapter 扫描
