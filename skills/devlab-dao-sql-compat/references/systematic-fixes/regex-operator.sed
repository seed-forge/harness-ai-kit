# PostgreSQL ~ / !~ 正则运算符 → Oracle REGEXP_LIKE()
# 用法: sed -f regex-operator.sed <file.xml>
#
# 陷阱：
# 1. 字符串拼接中的 '~' 是字面量分隔符，不是正则运算符（如 'pap_r' || '~' || col）
# 2. 仅替换 WHERE/AND 子句中的 ~'pattern' 形式
# 3. 同时修复 = '' → is null 和 != '' → is not null（Oracle 空字符串陷阱）

# !~ 替换（必须在 ~ 之前执行）
s/\([a-zA-Z_][a-zA-Z0-9_.]*\) !~'\([^']*\)'/NOT REGEXP_LIKE(\1, '\2')/g

# ~ 替换
s/\([a-zA-Z_][a-zA-Z0-9_.]*\) ~'\([^']*\)'/REGEXP_LIKE(\1, '\2')/g

# = '' → is null（Oracle 将空字符串视为 NULL）
s/\([a-zA-Z_][a-zA-Z0-9_.]*\) = ''/\1 is null/g

# != '' → is not null
s/\([a-zA-Z_][a-zA-Z0-9_.]*\) != ''/\1 is not null/g
