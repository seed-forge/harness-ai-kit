#!/bin/bash
# ============================================================================
# SQLAlchemy Adapter — text()/query()/execute() 扫描与 raw SQL 提取
# 扫描 Python 源文件中的 raw SQL（text()、execute()、raw 字符串）
# ============================================================================

adapter_name() { echo "sqlalchemy"; }

adapter_file_pattern() { echo "*.py"; }

# 输入: $1=scan_dir, $2=module_glob(可选)
# 输出: stdout 每行一个含 raw SQL 的 Python 文件路径
adapter_find_files() {
    local scan_dir="$1"
    grep -rl --include="*.py" \
        -E "text\(|\.execute\(|session\.execute|engine\.execute|\.query\(|raw\(|op\.execute|db\.engine\.execute" \
        "$scan_dir" --exclude-dir=__pycache__ --exclude-dir=.venv --exclude-dir=venv 2>/dev/null
}

# 输入: $1=文件路径
# 输出: stdout 剥离注释后的文件内容（行号不变）
# Python: 剥离 # 单行注释（保留行结构，不处理三引号 docstring 以保行号）
adapter_strip_comments() {
    awk '{
        line=$0; out=""; i=1; n=length(line)
        # 简单状态: 不处理三引号内的 # 以避免误删 SQL 字符串中的 # 
        # 只处理行首 # 和行中 "..." 后的 #
        in_str=0; prev=""
        while (i<=n) {
            ch=substr(line,i,1)
            if (ch=="\"" && prev!="\\") { in_str=!in_str }
            if (ch=="#" && !in_str) { break }
            out=out ch; prev=ch; i++
        }
        print out
    }' "$1"
}

# 输入: $1=scan_dir, $2=module_glob(可选)
# 输出: stdout 每行一个模块根目录路径（Python 包根）
adapter_detect_modules() {
    local scan_dir="$1" module_glob="$2"
    if [[ -n "$module_glob" ]]; then
        local d
        for d in "$scan_dir"/$module_glob; do
            [[ -d "$d" ]] && echo "$d"
        done
    else
        # 查找含 __init__.py 的目录作为模块边界
        find "$scan_dir" -name "__init__.py" -not -path "*/__pycache__/*" \
            -not -path "*/.venv/*" -not -path "*/venv/*" 2>/dev/null \
            | xargs -I{} dirname {} 2>/dev/null | sort -u | head -20
    fi
}

adapter_get_mapper_dir() {
    local module_dir="$1"
    echo "$module_dir"
}

# 额外: 提取 text() 和 execute() 中的 SQL（SQLAlchemy 专属）
# 输入: $1=文件路径
# 输出: stdout 每行 "line:line_number\ttype:text|execute\tSQL内容"
adapter_extract_queries() {
    local file="$1"
    grep -n -E "text\(|\.execute\(|session\.execute" "$file" 2>/dev/null \
        | while IFS= read -r line; do
            local lineno=$(echo "$line" | cut -d: -f1)
            local content=$(echo "$line" | cut -d: -f2-)
            local qtype="text"
            echo "$content" | grep -q "execute" && qtype="execute"
            # 提取引号内的 SQL
            echo "$content" | sed -n "s/.*text(\s*[\\"']\(.*\)[\\"'].*/\1/p" 2>/dev/null \
                | while IFS= read -r sql; do
                    [[ -n "$sql" ]] && echo "line:${lineno}\ttype:${qtype}\t${sql}"
                done
        done
}
