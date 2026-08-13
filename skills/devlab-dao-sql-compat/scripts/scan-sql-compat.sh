#!/bin/bash
# ============================================================================
# DAO 层 SQL 方言兼容性扫描脚本（devlab-dao-sql-compat）
# 框架无关的方言检测引擎 + adapter 模式框架适配
# 支持: mybatis / jpa / mybatis-plus / sqlalchemy
# 降噪：扫描前剥离注释（行号保持不变），消除注释内误报
# ============================================================================
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ADAPTER=""
SCAN_DIR="."
MODULE_GLOB=""
PROCS_FILE=""
REPORT_FILE="./sql-compat-report.md"
FAIL_ON_CRITICAL=0

usage() {
    cat <<'EOF'
用法: scan-sql-compat.sh [选项]
  --adapter <name>        DAO 框架适配器 (mybatis|jpa|mybatis-plus|sqlalchemy|auto)
                          auto: 自动检测项目使用的框架（默认）
  --dir <path>            扫描根目录（默认 .）
  --module-glob <glob>    模块目录 glob，相对 --dir
  --procs <file>          自定义存储过程清单文件
  --report <path>         报告输出路径（默认 ./sql-compat-report.md）
  --fail-on-critical      发现 CRITICAL 模块时退出码为 1
  -h, --help              显示帮助
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --adapter) ADAPTER="$2"; shift 2 ;;
        --dir) SCAN_DIR="$2"; shift 2 ;;
        --module-glob) MODULE_GLOB="$2"; shift 2 ;;
        --procs) PROCS_FILE="$2"; shift 2 ;;
        --report) REPORT_FILE="$2"; shift 2 ;;
        --fail-on-critical) FAIL_ON_CRITICAL=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "未知参数: $1" >&2; usage; exit 2 ;;
    esac
done

[[ -d "$SCAN_DIR" ]] || { echo "扫描目录不存在: $SCAN_DIR" >&2; exit 2; }

# ---- 框架自动探测 ----
detect_adapter() {
    local d="$1"
    # MyBatis: mapper XML with SQL tags
    if find "$d" -name "*.xml" -path "*mapper*" -not -path "*/target/*" 2>/dev/null | head -1 | grep -q .; then
        echo "mybatis"
        return
    fi
    # JPA: @Query annotations
    if grep -rl --include="*.java" -E "@Query|@NamedQuery" "$d" --exclude-dir=target 2>/dev/null | head -1 | grep -q .; then
        # Check if also MyBatis-Plus
        if grep -rl --include="*.java" -E "QueryWrapper|LambdaQueryWrapper|BaseMapper" "$d" --exclude-dir=target 2>/dev/null | head -1 | grep -q .; then
            echo "mybatis-plus"
        else
            echo "jpa"
        fi
        return
    fi
    # MyBatis-Plus: QueryWrapper without mapper XML
    if grep -rl --include="*.java" -E "QueryWrapper|LambdaQueryWrapper|BaseMapper" "$d" --exclude-dir=target 2>/dev/null | head -1 | grep -q .; then
        echo "mybatis-plus"
        return
    fi
    # SQLAlchemy
    if grep -rl --include="*.py" -E "text\(|\.execute\(|session\.execute" "$d" --exclude-dir=__pycache__ --exclude-dir=.venv 2>/dev/null | head -1 | grep -q .; then
        echo "sqlalchemy"
        return
    fi
    echo ""
}

if [[ -z "$ADAPTER" || "$ADAPTER" == "auto" ]]; then
    ADAPTER=$(detect_adapter "$SCAN_DIR")
    if [[ -z "$ADAPTER" ]]; then
        echo "错误: 无法自动检测 DAO 框架。请用 --adapter <mybatis|jpa|mybatis-plus|sqlalchemy> 指定。" >&2
        exit 2
    fi
    echo "自动检测到框架: $ADAPTER" >&2
fi

ADAPTER_FILE="$SCRIPT_DIR/adapters/${ADAPTER}.sh"
if [[ ! -f "$ADAPTER_FILE" ]]; then
    echo "错误: 适配器不存在: $ADAPTER_FILE" >&2
    echo "可用适配器: mybatis, jpa, mybatis-plus, sqlalchemy" >&2
    exit 2
fi
source "$ADAPTER_FILE"
echo "使用适配器: $(adapter_name)" >&2

FILE_PATTERN=$(adapter_file_pattern)

# ---- 方言特征模式集（框架无关，操作 SQL 文本） ----
ORACLE_FILE_PATTERN='CONNECT BY|SYS_CONNECT_BY_PATH|LISTAGG|DECODE\(|[^a-zA-Z_]NVL\(|ROWNUM|MERGE[[:space:]]+INTO|\.NEXTVAL|\.nextval|KEEP[[:space:]]*\(.*DENSE_RANK|SYSDATE|ADD_MONTHS|[^a-zA-Z_]TRUNC\('
PG_FILE_PATTERN="split_part\\(|unnest\\(|string_to_array\\(|generate_series\\(|date_trunc\\(|to_timestamp[[:space:]]*\\([^,)]*\\)|::[a-zA-Z]|string_agg\\(|[$][$]|filter[[:space:]]*\\([[:space:]]*where|array_agg[[:space:]]*\\(|~[[:space:]]*'\\^|[Ll][Ii][Mm][Ii][Tt][[:space:]]+[0-9]+[[:space:]]*([^,0-9]|$)|[^a-zA-Z_][Nn][Oo][Ww][[:space:]]*\\(\\)|[Nn][Ee][Xx][Tt][Vv][Aa][Ll][[:space:]]*\\('|[Ii][Nn][Tt][Ee][Rr][Vv][Aa][Ll][[:space:]]*'[0-9]+[[:space:]]*[a-zA-Z]"
MYSQL_FILE_PATTERN='DATE_FORMAT\(|DATE_SUB\(|DATE_ADD\(|CURDATE\(|WEEKDAY\(|IFNULL\(|GROUP_CONCAT\(|SUBSTRING_INDEX\(|LIMIT[[:space:]]+[0-9]+[[:space:]]*,[[:space:]]*[0-9]+'

ORACLE_TOTAL=0
PG_TOTAL=0
MYSQL_TOTAL=0
CRITICAL_COUNT=0

TMP_COUNT=$(mktemp 2>/dev/null || echo "${SCAN_DIR}/.sqlcompat-count.tmp")
echo 0 > "$TMP_COUNT"

# ---- 注释剥离镜像：使用 adapter 的 strip 函数 ----
STRIP_ROOT=$(mktemp -d 2>/dev/null || echo "${SCAN_DIR}/.sqlcompat-strip.tmp")
while IFS= read -r f; do
    rel="${f#$SCAN_DIR/}"
    mkdir -p "$STRIP_ROOT/$(dirname "$rel")"
    adapter_strip_comments "$f" > "$STRIP_ROOT/$rel"
done < <(adapter_find_files "$SCAN_DIR" "$MODULE_GLOB")

# ---- 单模式扫描（框架无关） ----
scan_pattern() {
    local pattern="$1" label="$2" severity="$3"
    local results count prev
    # 按适配器文件模式搜索
    local include_opts=""
    for pat in $FILE_PATTERN; do
        include_opts="$include_opts --include=$pat"
    done
    results=$(grep -rn $include_opts -E "$pattern" "$STRIP_ROOT" 2>/dev/null | sed "s|^${STRIP_ROOT}/|${SCAN_DIR}/|" || true)
    count=$(echo "$results" | grep -c . || echo 0)
    [[ -z "$results" ]] && count=0
    prev=$(cat "$TMP_COUNT")
    echo $(( prev + count )) > "$TMP_COUNT"
    if [[ $count -gt 0 ]]; then
        echo ""
        echo "### ${severity} ${label}（${count} 处）"
        echo ""
        echo '```'
        echo "$results" | head -80
        [[ $count -gt 80 ]] && echo "... (truncated, ${count} total matches)"
        echo '```'
        echo ""
    fi
}

# ---- 模块级风险判定（使用 adapter 的模块探测） ----
scan_module() {
    local module_dir="$1"
    local mapper_dir
    mapper_dir=$(adapter_get_mapper_dir "$module_dir")
    [[ -d "$mapper_dir" ]] || mapper_dir="$module_dir"
    local strip_dir
    if [[ "$mapper_dir" == "$SCAN_DIR" ]]; then
        strip_dir="$STRIP_ROOT"
    else
        strip_dir="${STRIP_ROOT}/${mapper_dir#$SCAN_DIR/}"
    fi
    [[ -d "$strip_dir" ]] || return 0
    local include_opts=""
    for pat in $FILE_PATTERN; do
        include_opts="$include_opts --include=$pat"
    done
    local oc pc mc
    oc=$(grep -rl $include_opts -E "$ORACLE_FILE_PATTERN" "$strip_dir" 2>/dev/null | wc -l)
    pc=$(grep -rl $include_opts -E "$PG_FILE_PATTERN" "$strip_dir" 2>/dev/null | wc -l)
    mc=$(grep -rl $include_opts -E "$MYSQL_FILE_PATTERN" "$strip_dir" 2>/dev/null | wc -l)
    [[ $oc -eq 0 && $pc -eq 0 && $mc -eq 0 ]] && return 0

    local risk="🟢 LOW"
    if [[ $oc -gt 0 && $pc -gt 0 ]]; then
        risk="🔴 CRITICAL"; CRITICAL_COUNT=$(( CRITICAL_COUNT + 1 ))
    elif [[ $mc -gt 0 && ( $oc -gt 0 || $pc -gt 0 ) ]]; then
        risk="🔴 CRITICAL"; CRITICAL_COUNT=$(( CRITICAL_COUNT + 1 ))
    elif [[ $oc -gt 5 || $pc -gt 5 || $mc -gt 5 ]]; then
        risk="🟡 HIGH"
    else
        risk="🟡 MEDIUM"
    fi
    echo "| $(basename "$module_dir") | ${oc} 文件 | ${pc} 文件 | ${mc} 文件 | ${risk} |"
}

# ============================================================================
# 主报告
# ============================================================================
{
    echo "# SQL 方言兼容性扫描报告"
    echo ""
    echo "**扫描时间**: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "**扫描目录**: ${SCAN_DIR}"
    echo "**DAO 框架**: ${ADAPTER}"
    echo ""
    total_files=$(adapter_find_files "$SCAN_DIR" "$MODULE_GLOB" | wc -l)
    echo "**含 SQL 文件总数**: ${total_files}"
    echo ""

    # ---- Oracle-only ----
    echo "---"; echo ""
    echo "## 一、Oracle-only 语法"
    echo ""
    echo "### 🔴 CRITICAL"
    scan_pattern "CONNECT BY|SYS_CONNECT_BY_PATH" "CONNECT BY 层级查询" "🔴"
    scan_pattern "LISTAGG" "LISTAGG 聚合字符串" "🔴"
    scan_pattern "DECODE[[:space:]]*\(" "DECODE 条件函数" "🔴"
    scan_pattern "[^a-zA-Z_]NVL[[:space:]]*\(" "NVL 空值处理" "🔴"
    scan_pattern "ROWNUM" "ROWNUM 行限制" "🔴"
    scan_pattern "MERGE[[:space:]]+INTO" "MERGE INTO Upsert" "🔴"
    scan_pattern "\.NEXTVAL|\.nextval" "序列 NEXTVAL" "🔴"
    scan_pattern "KEEP[[:space:]]*\(.*DENSE_RANK" "KEEP(DENSE_RANK) 分析函数" "🔴"
    echo "### 🟡 HIGH"
    scan_pattern "SYSDATE" "SYSDATE 当前时间" "🟡"
    scan_pattern "ADD_MONTHS[[:space:]]*\(" "ADD_MONTHS 日期运算" "🟡"
    scan_pattern "[^a-zA-Z_]TRUNC[[:space:]]*\(" "TRUNC 日期截断" "🟡"
    ORACLE_TOTAL=$(cat "$TMP_COUNT")
    echo ""; echo "**Oracle-only 语法总匹配数**: ${ORACLE_TOTAL}"; echo ""

    # ---- PG-only ----
    echo 0 > "$TMP_COUNT"
    echo "---"; echo ""
    echo "## 二、PostgreSQL-only 语法"
    echo ""
    echo "### 🔴 CRITICAL"
    scan_pattern "split_part[[:space:]]*\(" "split_part() 字符串分割" "🔴"
    scan_pattern "unnest[[:space:]]*\(" "unnest() 数组展开" "🔴"
    scan_pattern "string_to_array[[:space:]]*\(" "string_to_array() 字符串转数组" "🔴"
    scan_pattern "generate_series[[:space:]]*\(" "generate_series() 序列生成" "🔴"
    scan_pattern "[$][$]" "\$\$ 美元引号" "🔴"
    scan_pattern "filter[[:space:]]*\([[:space:]]*where" "聚合 FILTER (WHERE) 子句" "🔴"
    scan_pattern "array_agg[[:space:]]*\(" "array_agg() 数组聚合" "🔴"
    scan_pattern "~[[:space:]]*'\^" "~ 正则匹配运算符" "🔴"
    scan_pattern "[Ll][Ii][Mm][Ii][Tt][[:space:]]+[0-9]+[[:space:]]*([^,0-9]|$)" "裸 LIMIT n 分页" "🔴"
    scan_pattern "[^a-zA-Z_][Nn][Oo][Ww][[:space:]]*\(\)" "now() 当前时间" "🔴"
    scan_pattern "[Nn][Ee][Xx][Tt][Vv][Aa][Ll][[:space:]]*\('" "nextval('seq') 序列调用" "🔴"
    scan_pattern "[Ii][Nn][Tt][Ee][Rr][Vv][Aa][Ll][[:space:]]*'[0-9]+[[:space:]]*[a-zA-Z]" "PG 式 interval" "🔴"
    echo "### 🟡 HIGH"
    scan_pattern "date_trunc[[:space:]]*\(" "date_trunc() 日期截断" "🟡"
    scan_pattern "to_timestamp[[:space:]]*\([^,)]*\)" "to_timestamp() 单参 epoch 形式" "🟡"
    scan_pattern "::[a-zA-Z]" "::type 类型强转" "🟡"
    scan_pattern "string_agg[[:space:]]*\(" "string_agg() 字符串聚合" "🟡"
    PG_TOTAL=$(cat "$TMP_COUNT")
    echo ""; echo "**PostgreSQL-only 语法总匹配数**: ${PG_TOTAL}"; echo ""

    # ---- MySQL ----
    echo 0 > "$TMP_COUNT"
    echo "---"; echo ""
    echo "## 三、MySQL 方言语法"
    scan_pattern "DATE_FORMAT[[:space:]]*\(" "DATE_FORMAT() 日期格式化" "🔴"
    scan_pattern "DATE_SUB[[:space:]]*\(" "DATE_SUB() 日期减法" "🔴"
    scan_pattern "DATE_ADD[[:space:]]*\(" "DATE_ADD() 日期加法" "🔴"
    scan_pattern "CURDATE[[:space:]]*\(" "CURDATE() 当前日期" "🔴"
    scan_pattern "WEEKDAY[[:space:]]*\(" "WEEKDAY() 星期几" "🔴"
    scan_pattern "IFNULL[[:space:]]*\(" "IFNULL() 空值处理" "🔴"
    scan_pattern "GROUP_CONCAT[[:space:]]*\(" "GROUP_CONCAT() 字符串聚合" "🔴"
    scan_pattern "SUBSTRING_INDEX[[:space:]]*\(" "SUBSTRING_INDEX() 字符串截取" "🔴"
    scan_pattern "LIMIT[[:space:]]+[0-9]+[[:space:]]*,[[:space:]]*[0-9]+" "LIMIT offset,count 分页" "🔴"
    MYSQL_TOTAL=$(cat "$TMP_COUNT")
    echo ""; echo "**MySQL 方言语法总匹配数**: ${MYSQL_TOTAL}"; echo ""

    # ---- 模块风险矩阵 ----
    echo "---"; echo ""
    echo "## 四、模块级风险矩阵"
    echo ""
    echo "> CRITICAL=方言混用 | HIGH=单方言文件数>5 | MEDIUM=单方言文件数<=5"
    echo ""
    echo "| 模块 | Oracle-only | PG-only | MySQL | 风险等级 |"
    echo "|------|-------------|---------|-------|---------|"
    while IFS= read -r mod; do
        [[ -n "$mod" ]] && scan_module "$mod"
    done < <(adapter_detect_modules "$SCAN_DIR" "$MODULE_GLOB")
    echo ""

    # ---- 自定义存储过程 ----
    if [[ -n "$PROCS_FILE" && -f "$PROCS_FILE" ]]; then
        echo "---"; echo ""
        echo "## 五、自定义存储过程/函数依赖"
        echo ""
        echo "| 函数 | 引用文件数 |"
        echo "|------|-----------|"
        while IFS= read -r proc; do
            proc=$(echo "$proc" | tr -d '[:space:]')
            [[ -z "$proc" || "$proc" == \#* ]] && continue
            local include_opts=""
            for pat in $FILE_PATTERN; do
                include_opts="$include_opts --include=$pat"
            done
            n=$(grep -rl $include_opts "$proc" "$STRIP_ROOT" 2>/dev/null | wc -l)
            [[ $n -gt 0 ]] && echo "| ${proc} | ${n} |"
        done < "$PROCS_FILE"
        echo ""
    fi

    echo "---"; echo ""
    echo "**汇总**: Oracle-only ${ORACLE_TOTAL} 处 | PG-only ${PG_TOTAL} 处 | MySQL ${MYSQL_TOTAL} 处 | CRITICAL 模块 ${CRITICAL_COUNT} 个"
} > "$REPORT_FILE"

rm -f "$TMP_COUNT"
rm -rf "$STRIP_ROOT"

echo "报告已生成: ${REPORT_FILE}"
echo "框架: ${ADAPTER} | Oracle-only: ${ORACLE_TOTAL} 处 | PG-only: ${PG_TOTAL} 处 | MySQL: ${MYSQL_TOTAL} 处 | CRITICAL 模块: ${CRITICAL_COUNT} 个"

if [[ $FAIL_ON_CRITICAL -eq 1 && $CRITICAL_COUNT -gt 0 ]]; then
    exit 1
fi
exit 0
