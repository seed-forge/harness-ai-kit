# MyBatis Adapter — Mapper XML 扫描模式与方言陷阱

## 扫描目标

- **文件类型**: `*.xml`（Mapper XML 文件）
- **路径探测**: `src/main/resources/mapper/**/*.xml`
- **注释剥离**: XML `<!-- -->` + SQL `/* */`

## SQL 提取模式

MyBatis Mapper XML 中的 SQL 嵌入在以下标签内：

```xml
<select id="findById" parameterType="map" resultMap="BaseResultMap">
  SELECT * FROM users WHERE id = #{id}
</select>
<!-- 同理: insert / update / delete / sql 标签 -->
```

### 动态 SQL 分支

MyBatis 的动态 SQL 是方言陷阱的重灾区：

- `<if test="...">` 分支内的方言代码，不同分支可能命中不同方言
- `<choose>/<when>/<otherwise>` 多路分支，每个 `<when>` 需独立检查
- `<foreach>` 生成的 IN 子句和批量操作，不同方言语法不同（Oracle 批量 INSERT vs PG/MySQL）
- `${param}` 字符串插值（非 `#{}`）可能引入不可控的方言代码

### 方言陷阱（MyBatis 专属）

1. **`<if>` 内的 Oracle 函数**: `SYSDATE`、`NVL()`、`DECODE()` 等 Oracle 专属函数常出现在条件分支中，需逐分支检查
2. **`<![CDATA[ ]]>` 内的 SQL**: CDATA 块中的 `<` `>` 等符号不被 XML 解析器干扰，但方言函数仍需扫描
3. **`resultMap` 中的 `typeHandler`**: 某些自定义 TypeHandler 可能在 Java 侧做方言转换，扫描器检测不到
4. **`<sql>` 片段引用**: `<include refid=""/>` 引入的 SQL 片段可能含方言代码，需追踪到片段定义处

## 与其他 adapter 的关系

- **MyBatis-Plus adapter**: MyBatis-Plus 继承 MyBatis 的 Mapper XML 机制，同时有 QueryWrapper Java API。MyBatis-Plus adapter 同时扫描 XML 和 Java 源码
- 如果项目同时使用 MyBatis XML 和 MyBatis-Plus QueryWrapper，应使用 `--adapter mybatis-plus`
