#!/bin/bash
# ============================================================================
# MyBatis-Plus Adapter — QueryWrapper 模式检测 + Mapper XML 扫描
# 兼容 MyBatis Mapper XML + QueryWrapper/LambdaQueryWrapper Java 源码
# ============================================================================

adapter_name() { echo "mybatis-plus"; }

adapter_file_pattern() { echo "*.java *.xml"; }

# 输入: $1=scan_dir, $2=module_glob(可选)
# 输出: stdout 每行一个含 SQL 的文件路径（Mapper XML + QueryWrapper Java）
adapter_find_files() {
    local scan_dir="$1"
    # Mapper XML files
    find "$scan_dir" -name "*.xml" -path "*mapper*" -not -path "*/target/*" 2>/dev/null
    # Java files with QueryWrapper/LambdaQueryWrapper
    grep -rl --include="*.java" -E "QueryWrapper|LambdaQueryWrapper|BaseMapper" "$scan_dir" \
        --exclude-dir=target --exclude-dir=build 2>/dev/null
}

# 输入: $1=文件路径
# 输出: stdout 剥离注释后的文件内容（行号不变）
# 按文件类型选择注释剥离策略
adapter_strip_comments() {
    local file="$1"
    case "$file" in
        *.xml)
            # XML: /* */ 与 <!-- -->
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
            ;;
        *.java)
            # Java: // 单行 + /* */ 多行
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
            ;;
        *)
            cat "$1"
            ;;
    esac
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
        # 合并 mapper 目录和 java 源码目录
        find "$scan_dir" -type d -path "*/src/main/resources/mapper" -not -path "*/target/*" 2>/dev/null \
            | sed 's|/src/main/resources/mapper$||' | sort -u
        find "$scan_dir" -type d -path "*/src/main/java" -not -path "*/target/*" 2>/dev/null \
            | sed 's|/src/main/java$||' | sort -u | while read -r d; do
            # 只输出含 BaseMapper 的模块（避免全量）
            grep -rl --include="*.java" "BaseMapper" "$d/src/main/java" 2>/dev/null | head -1 | grep -q . && echo "$d"
        done
    fi
}

adapter_get_mapper_dir() {
    local module_dir="$1"
    local mapper_dir="${module_dir}/src/main/resources/mapper"
    [[ -d "$mapper_dir" ]] && echo "$mapper_dir" || echo "$module_dir"
}
