#!/usr/bin/env bash
# clear_cache.sh - 清除 Redis 中 Stock Tracer 相關的 cache
set -euo pipefail

REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"

show_help() {
    cat <<'HELP'
Usage: clear_cache.sh [OPTIONS]

清除 Redis 中 Stock Tracer 相關的快取資料。

預設清除 pattern: stocks:*

Options:
  -p, --pattern PATTERN  自訂要清除的 Redis key pattern (預設: stocks:*)
  -h, --help             顯示此使用說明

Environment Variables:
  REDIS_HOST    Redis 主機位址 (預設: localhost)
  REDIS_PORT    Redis 連接埠 (預設: 6379)

Examples:
  clear_cache.sh
  clear_cache.sh --pattern "stocks:price:*"
  REDIS_HOST=redis-server clear_cache.sh
HELP
}

PATTERN="stocks:*"

# 處理參數
while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)
            show_help
            exit 0
            ;;
        -p|--pattern)
            PATTERN="$2"
            shift 2
            ;;
        *)
            echo "錯誤: 未知參數 '$1'" >&2
            show_help
            exit 1
            ;;
    esac
done

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 清除 Redis cache (pattern: ${PATTERN})..."

# 檢查 redis-cli 是否可用
if ! command -v redis-cli &>/dev/null; then
    echo "警告: redis-cli 未安裝，跳過 cache 清除" >&2
    exit 0
fi

# 檢查 Redis 是否可連線
if ! redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" ping &>/dev/null; then
    echo "警告: 無法連線到 Redis (${REDIS_HOST}:${REDIS_PORT})，跳過 cache 清除" >&2
    exit 0
fi

# 使用 SCAN 安全地找出並刪除匹配的 keys
KEYS=$(redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" --scan --pattern "${PATTERN}" 2>/dev/null)

if [[ -z "${KEYS}" ]]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 沒有找到匹配的 cache keys"
else
    COUNT=$(echo "${KEYS}" | wc -l | tr -d ' ')
    echo "${KEYS}" | xargs redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" DEL >/dev/null 2>&1
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 已清除 ${COUNT} 個 cache keys"
fi
