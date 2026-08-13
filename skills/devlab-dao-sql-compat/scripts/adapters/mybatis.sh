#!/bin/bash
# ============================================================================
# MyBatis Adapter — Mapper XML 扫描/提取/模块探测
# 适配器接口契约: adapter_name / adapter_file_pattern / adapter_find_files
#   / adapter_strip_comments / adapter_detect_modules
# ============================================================================

adapter_name() { echo "mybatis"; }

adapter_file_pattern() { echo "*.xml"; }

# 输入: $1=scan_dir, $2=module_glob(可选)
# 输出: stdout 每行一个含 SQL 的 Mapper XML 文件路径
adapter_find_files() {
    local scan_dir="$1" module_glob="$2"
    find "$scan_dir" -name "*.xml" -path "*mapper*" -not -path "*/target/*" 2>/dev/null
}

# 输入: $1=文件路径
# 输出: stdout 剥离注释后的文件内容（行号不变）
# MyBatis Mapper XML: 剥离 /* */ 与 <!-- -->
adapter_strip_comments() {
    awk '{
        line=$0; out=""; i=1; n=length(line)
        while (i<=n) {
            if (inc)      { if (substr(line,i,2)=="*/")   {inc=0;i+=2} else i++ }
            else if (inx) { if (substr(line,i,3)=="-->")  {inx=0;i+=3} else i++ }
            else if (substr(line,i,2)=="/*")   {inc=1;i+=2}
            else if (substr(line,i,4)=="<!--") {inx=1;i+=4}
            else {out=out substr(line,i,1); i++}
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
        find "$scan_dir" -type d -path "*/src/main/resources/mapper" -not -path "*/target/*" 2>/dev/null \
            | sed 's|/src/main/resources/mapper$||' | sort -u
    fi
}

# 输入: $1=模块目录路径
# 输出: stdout 该模块的 Mapper 根目录路径
adapter_get_mapper_dir() {
    local module_dir="$1"
    local mapper_dir="${module_dir}/src/main/resources/mapper"
    [[ -d "$mapper_dir" ]] && echo "$mapper_dir" || echo "$module_dir"
}
