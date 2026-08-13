# coalesce(col, '') → NVL(col, ' ')
# 用法: sed -f coalesce-nullstr.sed <file.xml>
#
# 陷阱：Oracle 将 '' 视为 NULL，因此 coalesce(col, '') 等价于 coalesce(col, NULL)，
# 回退值永远不会生效。改为 NVL(col, ' ') 确保非 NULL 回退。
#
# 适用场景：
# 1. 字符串拼接：col1 || '~' || coalesce(col2, '') → NVL(col2, ' ')
# 2. 比较过滤：coalesce(col, '') = '' → col is null（需额外处理）

# coalesce(col, '') → NVL(col, ' ')
s/coalesce(\([^,]*\), '')/NVL(\1, ' ')/g
