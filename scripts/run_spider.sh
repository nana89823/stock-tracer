#!/usr/bin/env bash
# run_spider.sh - 執行 Scrapy 爬蟲並記錄日誌
set -euo pipefail

PROJECT_DIR="/Users/admin/stock-tracer"
LOG_DIR="${PROJECT_DIR}/logs"
CLEAR_CACHE_SCRIPT="${PROJECT_DIR}/scripts/clear_cache.sh"
DATE=$(date +"%Y%m%d")

show_help() {
    cat <<'HELP'
Usage: run_spider.sh [OPTIONS] <spider_name>

執行指定的 Scrapy 爬蟲，並將日誌輸出到 logs/ 目錄。

Arguments:
  spider_name    爬蟲名稱，例如: raw_price, raw_chip, major_holders,
                 margin_trading, broker_trading, tpex_price, tpex_chip, tpex_margin

Options:
  -h, --help     顯示此使用說明

Examples:
  run_spider.sh raw_price
  run_spider.sh major_holders

日誌檔案位置: /Users/admin/stock-tracer/logs/{spider_name}_{YYYYMMDD}.log
HELP
}

# 處理參數
if [[ $# -eq 0 ]]; then
    echo "錯誤: 請提供爬蟲名稱" >&2
    show_help
    exit 1
fi

if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    show_help
    exit 0
fi

SPIDER_NAME="$1"
LOG_FILE="${LOG_DIR}/${SPIDER_NAME}_${DATE}.log"

# 確保 logs 目錄存在
mkdir -p "${LOG_DIR}"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 開始執行爬蟲: ${SPIDER_NAME}" | tee -a "${LOG_FILE}"

# 執行爬蟲
cd "${PROJECT_DIR}"
if scrapy crawl "${SPIDER_NAME}" >> "${LOG_FILE}" 2>&1; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 爬蟲 ${SPIDER_NAME} 執行成功" | tee -a "${LOG_FILE}"

    # 爬蟲成功後清除 Redis cache
    if [[ -x "${CLEAR_CACHE_SCRIPT}" ]]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] 清除 Redis cache..." | tee -a "${LOG_FILE}"
        "${CLEAR_CACHE_SCRIPT}" >> "${LOG_FILE}" 2>&1 || true
    fi
else
    EXIT_CODE=$?
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 錯誤: 爬蟲 ${SPIDER_NAME} 執行失敗 (exit code: ${EXIT_CODE})" | tee -a "${LOG_FILE}"
    exit ${EXIT_CODE}
fi
