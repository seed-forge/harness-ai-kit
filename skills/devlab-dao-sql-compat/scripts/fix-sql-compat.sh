#!/usr/bin/env bash
# =============================================================================
# devlab-mybatis-sql-compat: 自动修复引擎
# Version: 0.3.0
# Description: 批量修复 MyBatis Mapper XML 中的 SQL 方言兼容性问题
# =============================================================================
set -euo pipefail

SCRIPT_NAME="fix-sql-compat.sh"
SCRIPT_VERSION="0.3.0"

# ── 颜色 ──
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }
log_step()  { echo -e "${CYAN}[STEP]${NC} $*"; }

# ── 默认值 ──
FIX_TYPE=""
SCAN_DIR=""
DRY_RUN=false

# ── 帮助 ──
show_help() {
  cat <<EOF
${SCRIPT_NAME} v${SCRIPT_VERSION} — MyBatis SQL 方言自动修复引擎

用法: ${SCRIPT_NAME} --type <fix-type> --dir <directory> [options]

修复类型 (--type):
  regex-operator    PG ~ / !~ 正则运算符 → Oracle REGEXP_LIKE() / NOT REGEXP_LIKE()
  coalesce-nullstr  coalesce(col, '') → NVL(col, ' ')（Oracle 空字符串=NULL 陷阱）
  todate-concat     to_date 拼接场景格式掩码修正（含 || 拼接的日期字符串）
  todate-direct     to_date 直接参数绑定格式掩码修正（纯日期参数误用 hh24:mi:ss）
  all               执行以上所有修复类型

选项:
  --dir <dir>       扫描根目录（必须）
  --type <type>     修复类型（必须）
  --dry-run         仅显示变更，不实际修改文件
  --help            显示此帮助

示例:
  ${SCRIPT_NAME} --type all --dir ./src
  ${SCRIPT_NAME} --type regex-operator --dir . --dry-run
  ${SCRIPT_NAME} --type todate-concat --dir ./tiny-emas-service-business
EOF
}

# ── 参数解析 ──
while [[ $# -gt 0 ]]; do
  case "$1" in
    --type)        FIX_TYPE="$2"; shift 2 ;;
    --dir)         SCAN_DIR="$2"; shift 2 ;;
    --dry-run)     DRY_RUN=true; shift ;;
    --help|-h)     show_help; exit 0 ;;
    *)             log_error "未知参数: $1"; show_help; exit 1 ;;
  esac
done

# ── 校验 ──
if [[ -z "$FIX_TYPE" ]]; then
  log_error "必须指定 --type"; show_help; exit 1
fi
if [[ -z "$SCAN_DIR" ]]; then
  log_error "必须指定 --dir"; show_help; exit 1
fi
if [[ ! -d "$SCAN_DIR" ]]; then
  log_error "目录不存在: $SCAN_DIR"; exit 1
fi

VALID_TYPES="regex-operator coalesce-nullstr todate-concat todate-direct all"
if ! echo "$VALID_TYPES" | grep -qw "$FIX_TYPE"; then
  log_error "无效修复类型: $FIX_TYPE（可选: $VALID_TYPES）"; exit 1
fi

# ── 统计变量 ──
TOTAL_FILES=0
MODIFIED_FILES=0
TOTAL_CHANGES=0

# ── 查找 XML 文件 ──
find_xml_files() {
  find "$SCAN_DIR" -name "*.xml" -path "*/mapper/*" -not -path "*/target/*" -type f 2>/dev/null
}

# ── 修复类型实现 ──

fix_regex_operator() {
  log_step "修复类型 1: PG ~ / !~ 正则运算符 → REGEXP_LIKE()"

  local files_found=0
  local files_modified=0

  while IFS= read -r file; do
    [[ -z "$file" ]] && continue
    local count
    count=$(grep -cE "~'" "$file" 2>/dev/null | tail -1 || echo 0)
    count=${count//[^0-9]/}
    [[ -z "$count" ]] && count=0
    [[ "$count" -eq 0 ]] && continue

    files_found=$((files_found + 1))
    TOTAL_FILES=$((TOTAL_FILES + 1))

    if [[ "$DRY_RUN" == true ]]; then
      echo "  [DRY-RUN] regex-operator: $count 处 → $(basename "$file")"
      TOTAL_CHANGES=$((TOTAL_CHANGES + $count))
      continue
    fi

    # !~ 替换（必须在 ~ 之前执行）
    sed -i -E "s/([a-zA-Z_][a-zA-Z0-9_.]*) !~'([^']+)'/NOT REGEXP_LIKE(\1, '\2')/g" "$file" 2>/dev/null || true
    # ~ 替换（仅匹配 WHERE/AND 上下文中的 ~'pattern'，排除字符串拼接中的 '~'）
    sed -i -E "s/([a-zA-Z_][a-zA-Z0-9_.]*) ~'([^']+)'/REGEXP_LIKE(\1, '\2')/g" "$file" 2>/dev/null || true
    # = '' → is null
    sed -i -E "s/([a-zA-Z_][a-zA-Z0-9_.]*) = ''/\1 is null/g" "$file" 2>/dev/null || true
    # != '' → is not null
    sed -i -E "s/([a-zA-Z_][a-zA-Z0-9_.]*) != ''/\1 is not null/g" "$file" 2>/dev/null || true

    local after
    after=$(grep -cE "~'" "$file" 2>/dev/null || echo 0)
    local fixed=$((count - after))
    if [[ $fixed -gt 0 ]]; then
      files_modified=$((files_modified + 1))
      MODIFIED_FILES=$((MODIFIED_FILES + 1))
      TOTAL_CHANGES=$((TOTAL_CHANGES + fixed))
      echo -e "  ${GREEN}✓${NC} regex-operator: $fixed 处 → $(basename "$file")"
    fi
  done < <(find_xml_files)

  echo "  扫描文件: $files_found, 修改文件: $files_modified"
}

fix_coalesce_nullstr() {
  log_step "修复类型 2: coalesce(col, '') → NVL(col, ' ')"

  local files_found=0
  local files_modified=0

  while IFS= read -r file; do
    [[ -z "$file" ]] && continue
    local count
    count=$(grep -cE "coalesce\\([^,]+, ''\\)" "$file" 2>/dev/null | tail -1 || echo 0)
    count=${count//[^0-9]/}
    [[ -z "$count" ]] && count=0
    [[ "$count" -eq 0 ]] && continue

    files_found=$((files_found + 1))
    TOTAL_FILES=$((TOTAL_FILES + 1))

    if [[ "$DRY_RUN" == true ]]; then
      echo "  [DRY-RUN] coalesce-nullstr: $count 处 → $(basename "$file")"
      TOTAL_CHANGES=$((TOTAL_CHANGES + $count))
      continue
    fi

    sed -i -E "s/coalesce\\(([^,]+), ''\\)/NVL(\1, ' ')/g" "$file" 2>/dev/null || true

    local after
    after=$(grep -cE "coalesce\\([^,]+, ''\\)" "$file" 2>/dev/null | tail -1 || echo 0)
    after=${after//[^0-9]/}
    [[ -z "$after" ]] && after=0
    local fixed=$((count - after))
    if [[ $fixed -gt 0 ]]; then
      files_modified=$((files_modified + 1))
      MODIFIED_FILES=$((MODIFIED_FILES + 1))
      TOTAL_CHANGES=$((TOTAL_CHANGES + fixed))
      echo -e "  ${GREEN}✓${NC} coalesce-nullstr: $fixed 处 → $(basename "$file")"
    fi
  done < <(find_xml_files)

  echo "  扫描文件: $files_found, 修改文件: $files_modified"
}

fix_todate_concat() {
  log_step "修复类型 3: to_date 拼接场景格式掩码修正"

  local files_found=0
  local files_modified=0

  while IFS= read -r file; do
    [[ -z "$file" ]] && continue
    local count
    count=$(grep -cE "to_date\\([^)]*\\|\\|[^)]*,'yyyy-mm-dd hh24:mi:ss'\\)" "$file" 2>/dev/null | tail -1 || echo 0)
    count=${count//[^0-9]/}
    [[ -z "$count" ]] && count=0
    [[ "$count" -eq 0 ]] && continue

    files_found=$((files_found + 1))
    TOTAL_FILES=$((TOTAL_FILES + 1))

    if [[ "$DRY_RUN" == true ]]; then
      echo "  [DRY-RUN] todate-concat: $count 处 → $(basename "$file")"
      TOTAL_CHANGES=$((TOTAL_CHANGES + $count))
      continue
    fi

    # to_date(xxx||'...', 'yyyy-mm-dd hh24:mi:ss') → to_date(xxx||'...', 'yyyy-mm-dd')
    sed -i -E "s/to_date\\(([^)]*\\|\\|[^)]*),'yyyy-mm-dd hh24:mi:ss'\\)/to_date(\1,'yyyy-mm-dd')/g" "$file" 2>/dev/null || true

    local after
    after=$(grep -cE "to_date\\([^)]*\\|\\|[^)]*,'yyyy-mm-dd hh24:mi:ss'\\)" "$file" 2>/dev/null | tail -1 || echo 0)
    after=${after//[^0-9]/}
    [[ -z "$after" ]] && after=0
    local fixed=$((count - after))
    if [[ $fixed -gt 0 ]]; then
      files_modified=$((files_modified + 1))
      MODIFIED_FILES=$((MODIFIED_FILES + 1))
      TOTAL_CHANGES=$((TOTAL_CHANGES + fixed))
      echo -e "  ${GREEN}✓${NC} todate-concat: $fixed 处 → $(basename "$file")"
    fi
  done < <(find_xml_files)

  echo "  扫描文件: $files_found, 修改文件: $files_modified"
}

fix_todate_direct() {
  log_step "修复类型 4: to_date 直接参数绑定格式掩码标记"
  log_warn "此修复类型仅标记候选项，需 Agent 语义分析后确定正确格式"

  local candidates=0

  while IFS= read -r file; do
    [[ -z "$file" ]] && continue
    local matches
    matches=$(grep -nE "to_date\\(#\\{[a-zA-Z]+\\},'yyyy-mm-dd hh24:mi:ss'\\)" "$file" 2>/dev/null || true)
    [[ -z "$matches" ]] && continue

    local file_count
    file_count=$(echo "$matches" | wc -l)
    candidates=$((candidates + file_count))
    TOTAL_FILES=$((TOTAL_FILES + 1))

    echo "  候选项: $(basename "$file") ($file_count 处)"
    echo "$matches" | while IFS= read -r line; do
      local lineno content param
      lineno=$(echo "$line" | cut -d: -f1)
      content=$(echo "$line" | cut -d: -f2-)
      param=$(echo "$content" | grep -oE '#\\{[a-zA-Z]+' | head -1 | sed 's/#{//')
      echo "    L${lineno}: 参数=${param} — $(echo "$content" | sed 's/^[[:space:]]*//')"
    done
  done < <(find_xml_files)

  if [[ $candidates -gt 0 ]]; then
    echo ""
    log_warn "共发现 $candidates 个候选项，需要 Agent 分析参数语义后确定正确格式"
    log_info "参数名含 'Time'（如 taskTime/dataTime）→ 保留 hh24:mi:ss"
    log_info "参数名含 'Date'（如 statDate/startDate）→ 改为 yyyy-mm-dd"
    log_info "参数名不确定 → 需读取 Java 代码确认参数类型"
  else
    log_info "未发现 to_date 直接绑定的格式掩码问题"
  fi
}

# ── 主流程 ──
echo "=========================================="
echo "  ${SCRIPT_NAME} v${SCRIPT_VERSION}"
echo "  修复类型: ${FIX_TYPE}"
echo "  扫描目录: ${SCAN_DIR}"
echo "  模式: $([ "$DRY_RUN" == true ] && echo 'DRY-RUN' || echo 'LIVE')"
echo "=========================================="
echo ""

case "$FIX_TYPE" in
  regex-operator)   fix_regex_operator ;;
  coalesce-nullstr) fix_coalesce_nullstr ;;
  todate-concat)    fix_todate_concat ;;
  todate-direct)    fix_todate_direct ;;
  all)
    fix_regex_operator
    echo ""
    fix_coalesce_nullstr
    echo ""
    fix_todate_concat
    echo ""
    fix_todate_direct
    ;;
esac

echo ""
echo "=========================================="
echo "  修复统计"
echo "=========================================="
echo "  扫描文件数: $TOTAL_FILES"
echo "  修改文件数: $MODIFIED_FILES"
echo "  修复条目数: $TOTAL_CHANGES"
echo "=========================================="

if [[ "$DRY_RUN" == true ]]; then
  log_warn "DRY-RUN 模式：以上变更未实际执行"
fi

exit 0
