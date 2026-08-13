# to_date 拼接场景格式掩码修正
# 用法: sed -f todate-concat.sed <file.xml>
#
# 规则：如果 to_date() 的第一个参数包含 || 拼接（如 #{statDate}||'-01'），
# 则结果一定是纯日期字符串，格式必须为 'yyyy-mm-dd'。
#
# 典型模式：
# - to_date(#{statDate}||'-01','yyyy-mm-dd hh24:mi:ss') → to_date(#{statDate}||'-01','yyyy-mm-dd')
# - to_date(#{statDate} || '-01-01','yyyy-mm-dd hh24:mi:ss') → to_date(#{statDate} || '-01-01','yyyy-mm-dd')
#
# 不修改的场景（含时分秒拼接，语义正确）：
# - to_date(#{statDate}||' 00:00:00','yyyy-mm-dd hh24:mi:ss') — 拼接了具体时分秒
# - to_date(#{year}||'-01-01 00:00:00','yyyy-mm-dd hh24:mi:ss') — 年度边界含时间

# 修复：to_date(...||..., 'yyyy-mm-dd hh24:mi:ss') → to_date(...||..., 'yyyy-mm-dd')
s/to_date(\([^)]*||[^)]*\),'yyyy-mm-dd hh24:mi:ss')/to_date(\1,'yyyy-mm-dd')/g
