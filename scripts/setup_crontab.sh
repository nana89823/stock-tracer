#!/usr/bin/env bash
# setup_crontab.sh - 設定 Stock Tracer 爬蟲排程
set -euo pipefail

PROJECT_DIR="/Users/admin/stock-tracer"
BACKUP_DIR="${PROJECT_DIR}/backups"
CRON_TAG="# Stock Tracer Scheduler"
RUN_SCRIPT="${PROJECT_DIR}/scripts/run_spider.sh"

show_help() {
    cat <<'HELP'
Usage: setup_crontab.sh [OPTIONS]

管理 Stock Tracer 爬蟲的 crontab 排程。

排程規則（時區: Asia/Taipei）：
  週一~五 16:00  raw_price, tpex_price      收盤後日行情
  週一~五 16:15  raw_chip, tpex_chip         三大法人買賣超
  週一~五 16:30  margin_trading, tpex_margin 融資融券餘額
  週一~五 18:00  broker_trading              券商分點
  週六    10:00  major_holders               TDCC 股權分散表

Options:
  --remove    移除所有 Stock Tracer 相關排程
  -h, --help  顯示此使用說明

Examples:
  setup_crontab.sh           安裝排程
  setup_crontab.sh --remove  移除排程
HELP
}

backup_crontab() {
    mkdir -p "${BACKUP_DIR}"
    local backup_file="${BACKUP_DIR}/crontab_backup_$(date +%Y%m%d_%H%M%S).txt"
    crontab -l > "${backup_file}" 2>/dev/null || true
    echo "已備份現有 crontab 到: ${backup_file}"
}

remove_stock_tracer_crons() {
    local current
    current=$(crontab -l 2>/dev/null || true)
    if [[ -z "${current}" ]]; then
        echo "目前沒有任何 crontab 排程"
        return
    fi
    # 移除 Stock Tracer 區塊（從標記開始到下一個空行或檔案結尾）
    echo "${current}" | sed '/# Stock Tracer/d' | sed '/stock-tracer\/scripts\/run_spider.sh/d' | sed '/^$/N;/^\n$/d' | crontab -
    echo "已移除所有 Stock Tracer 相關排程"
}

install_crontab() {
    # 取得現有 crontab（排除 Stock Tracer 相關的行）
    local existing
    existing=$(crontab -l 2>/dev/null | sed '/# Stock Tracer/d' | sed '/stock-tracer\/scripts\/run_spider.sh/d' || true)

    # 組合新的 crontab
    {
        if [[ -n "${existing}" ]]; then
            echo "${existing}"
            echo ""
        fi
        cat <<CRON
${CRON_TAG}
# 時區: Asia/Taipei
# Daily spiders (Mon-Fri)
0 16 * * 1-5  ${RUN_SCRIPT} raw_price
0 16 * * 1-5  ${RUN_SCRIPT} tpex_price
15 16 * * 1-5 ${RUN_SCRIPT} raw_chip
15 16 * * 1-5 ${RUN_SCRIPT} tpex_chip
30 16 * * 1-5 ${RUN_SCRIPT} margin_trading
30 16 * * 1-5 ${RUN_SCRIPT} tpex_margin
0 18 * * 1-5  ${RUN_SCRIPT} broker_trading
# Weekly
0 10 * * 6    ${RUN_SCRIPT} major_holders
CRON
    } | crontab -

    echo "已安裝 Stock Tracer 排程："
    echo "  - raw_price + tpex_price:        週一~五 16:00"
    echo "  - raw_chip + tpex_chip:          週一~五 16:15"
    echo "  - margin_trading + tpex_margin:  週一~五 16:30"
    echo "  - broker_trading:                週一~五 18:00"
    echo "  - major_holders:                 週六    10:00"
}

# 處理參數
if [[ $# -gt 0 ]]; then
    case "$1" in
        -h|--help)
            show_help
            exit 0
            ;;
        --remove)
            backup_crontab
            remove_stock_tracer_crons
            exit 0
            ;;
        *)
            echo "錯誤: 未知參數 '$1'" >&2
            show_help
            exit 1
            ;;
    esac
fi

# 備份並安裝
backup_crontab
install_crontab
echo ""
echo "目前 crontab 內容："
crontab -l
