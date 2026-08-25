#!/usr/bin/env bash
# =============================================================================
# sync-service-list.sh — 从 jenkins.yml 的 pathMapping 提取服务列表
#
# 用法:
#   bash scripts/sync-service-list.sh
#   bash scripts/sync-service-list.sh .platform/jenkins.yml
#
# 输出:
#   Groovy 格式的 choice 列表，可直接粘贴到 Jenkinsfile 的 parameters 块
#
# 支持 pathMapping 两种格式:
#   字符串: emas-redis: tiny-emas-service-basic/emas-redis
#   对象:   emas-authserver:
#             compilePath: tiny-emas-service-support/emas-authserver
#             deployPath: tiny-emas-service-support/tiny-emas-authserver
# =============================================================================
set -euo pipefail

YAML_FILE="${1:-.platform/jenkins.yml}"

if [ ! -f "$YAML_FILE" ]; then
    echo "ERROR: $YAML_FILE not found" >&2
    exit 1
fi

echo "// =============================================="
echo "// Auto-generated service list from $YAML_FILE"
echo "// Generated at: $(date '+%Y-%m-%d %H:%M:%S')"
echo "// =============================================="
echo ""
echo "parameters {"
echo "    choice("
echo "        name: 'SERVICE',"
echo "        description: '选择要部署的服务',"

# 提取 pathMapping 中的服务名（支持字符串和对象两种格式）
SERVICES=$(awk '
    /^[[:space:]]*pathMapping:/ { in_mapping=1; next }
    in_mapping && /^[[:space:]]*$/ { next }
    in_mapping && /^[[:space:]]*#/ { next }
    in_mapping && /^[[:space:]]*[a-zA-Z_-]+:/ {
        # 匹配 "service-name:" 或 "service-name: value"
        gsub(/^[[:space:]]+/, "")
        gsub(/:.*$/, "")
        services[NR] = $0
        count++
    }
    in_mapping && /^[[:space:]]{2,}[a-zA-Z]/ && !/compilePath|deployPath/ {
        # 遇到 pathMapping 下的非 pathMapping 字段，退出
    }
    /^[^[:space:]]/ && !/^#/ && in_mapping { in_mapping=0 }
    END {
        for (i in services) print services[i]
    }
' "$YAML_FILE" | sort -u)

if [ -z "$SERVICES" ]; then
    echo "        choices: ['no-services-found']"
    echo "    )"
    echo "}"
    echo ""
    echo "// WARNING: No services found in pathMapping" >&2
    exit 0
fi

COUNT=$(echo "$SERVICES" | wc -l)
echo "        choices: ["

FIRST=1
while IFS= read -r service; do
    if [ "$FIRST" -eq 1 ]; then
        echo "            '${service}'"
        FIRST=0
    else
        echo "            , '${service}'"
    fi
done <<< "$SERVICES"

echo "        ]"
echo "    )"
echo "}"
echo ""
echo "// Total: ${COUNT} services"
echo "// To update: re-run this script and replace the parameters block in Jenkinsfile"
