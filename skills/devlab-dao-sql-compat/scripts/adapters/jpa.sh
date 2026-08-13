#!/bin/bash
# ============================================================================
# JPA/Hibernate Adapter — @Query 注解扫描与 native SQL 提取
# 扫描 Java 源文件中的 @Query 注解，区分 JPQL 与 nativeQuery
# ============================================================================

adapter_name() { echo "jpa"; }

adapter_file_pattern() { echo "*.java"; }

# 输入: $1=scan_dir, $2=module_glob(可选)
# 输出: stdout 每行一个含 @Query 的 Java 文件路径
adapter_find_files() {
    local scan_dir="$1"
    grep -rl --include="*.java" -E "@Query|@NamedQuery|@NamedQueries" "$scan_dir" \
        --exclude-dir=target --exclude-dir=build 2>/dev/null
}

# 输入: $1=文件路径
# 输出: stdout 剥离注释后的文件内容（行号不变）
# Java: 剥离 // 单行注释和 /* */ 多行注释
adapter_strip_comments() {
    awk '{
        line=$0; out=""; i=1; n=length(line)
        while (i<=n) {
            if (inc)      { if (substr(line,i,2)=="*/") {inc=0;i+=2} else i++ }
            else if (substr(line,i,2)=="//") { break }
            else if (substr(line,i,2)=="/*") { inc=1;i+=2 }
            else { out=out substr(line,i,1); i++ }
        }
        print out
    }' "$1"
}

# 输入: $1=scan_dir, $2=module_glob(可选)
# 输出: stdout 每行一个模块根目录路径
adapter_detect_modules() {
    local scan_dir="$1" module_glob="$2"
    if [[ -n "$module_glob" ]]; then
        local d
        for d in "$scan_dir"/$module_glob; do
            [[ -d "$d" ]] && echo "$d"
        done
    else
        find "$scan_dir" -type d -path "*/src/main/java" -not -path "*/target/*" 2>/dev/null \
            | sed 's|/src/main/java$||' | sort -u
    fi
}

# 输入: $1=模块目录路径
# 输出: stdout 该模块的源码根目录
adapter_get_mapper_dir() {
    local module_dir="$1"
    local src_dir="${module_dir}/src/main/java"
    [[ -d "$src_dir" ]] && echo "$src_dir" || echo "$module_dir"
}

# 额外: 提取 @Query 注解中的 SQL（JPA 专属）
# 输入: $1=文件路径
# 输出: stdout 每行 "line:line_number\ttype:jpql|native\tSQL内容"
adapter_extract_queries() {
    local file="$1"
    awk '
    /@Query/ { in_query=1; line=NR; collect="" }
    in_query {
        collect=collect " " $0
        if (match(collect, /nativeQuery[[:space:]]*=[[:space:]]*true/)) { qtype="native" }
        else if (match(collect, /value[[:space:]]*=/) || match(collect, /[[:space:]]"/)) { qtype="native" }
        else { qtype="jpql" }
        if (match(collect, /"/)) {
            gsub(/.*"/, "", collect)
            gsub(/".*/, "", collect)
            gsub(/^\\s+/, "", collect)
            if (length(collect) > 0) {
                print "line:" line "\ttype:" qtype "\t" collect
            }
            in_query=0; collect=""; qtype=""
        }
    }
    ' "$file" 2>/dev/null
}
