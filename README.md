# Stock Tracer

台灣股市資料爬蟲，用於自動選股分析的資料收集工具。

## 資料來源

| Spider | 資料 | 來源 |
|--------|------|------|
| `raw_price` | 個股成交價格 | TWSE 證交所 |
| `raw_chip` | 三大法人買賣超 | TWSE 證交所 |
| `major_holders` | 集保戶股權分散表 | TDCC 集保中心 |

## 環境需求

- Python 3.12+
- Scrapy 2.11+

## 安裝

```bash
pip install -r requirements.txt
```

## 使用方式

### 執行爬蟲

```bash
# 抓取個股成交價格
scrapy crawl raw_price

# 抓取三大法人買賣超
scrapy crawl raw_chip

# 抓取大戶持股分布
scrapy crawl major_holders

# 一次執行全部
scrapy crawl raw_price && scrapy crawl raw_chip && scrapy crawl major_holders
```

### 輸出格式

CSV 檔案輸出至 `output/` 目錄，命名格式：`{YYYYMMDD}_{spider_name}.csv`

```
output/
├── 20260127_raw_price.csv
├── 20260127_raw_chip.csv
└── 20260127_major_holders.csv
```

## 資料欄位說明

### raw_price (個股成交價格)

| 欄位 | 說明 |
|------|------|
| date | 日期 (YYYY-MM-DD) |
| stock_id | 證券代號 |
| stock_name | 證券名稱 |
| open_price | 開盤價 |
| high_price | 最高價 |
| low_price | 最低價 |
| close_price | 收盤價 |
| price_change | 漲跌價差 |
| trade_volume | 成交股數 |
| trade_value | 成交金額 |
| transaction_count | 成交筆數 |

### raw_chip (三大法人買賣超)

| 欄位 | 說明 |
|------|------|
| date | 日期 |
| stock_id | 證券代號 |
| stock_name | 證券名稱 |
| foreign_buy | 外資買進股數 |
| foreign_sell | 外資賣出股數 |
| foreign_net | 外資買賣超 |
| trust_buy | 投信買進股數 |
| trust_sell | 投信賣出股數 |
| trust_net | 投信買賣超 |
| dealer_net | 自營商買賣超 |
| total_net | 三大法人合計買賣超 |

### major_holders (大戶持股分布)

| 欄位 | 說明 |
|------|------|
| date | 資料日期 |
| stock_id | 證券代號 |
| holding_level | 持股分級 (1-17) |
| holder_count | 人數 |
| share_count | 股數 |
| holding_ratio | 占集保庫存比例 (%) |

#### 持股分級對照表

| 級距 | 持股張數 |
|------|----------|
| 1 | 1-999 股 |
| 2 | 1,000-5,000 股 |
| ... | ... |
| 11 | 200,001-400,000 股 (200-400張) |
| 12 | 400,001-600,000 股 (400張以上，大戶起始) |
| 13-17 | 600,001 股以上 |

**400張以上大戶** = `holding_level >= 12`

## 測試

```bash
# 執行所有測試
pytest tests/ -v

# 執行測試並顯示覆蓋率
pytest tests/ --cov=stock_tracer --cov-report=term-missing
```

## 專案結構

```
stock_tracer/
├── scrapy.cfg
├── pytest.ini
├── requirements.txt
├── stock_tracer/
│   ├── items.py              # 資料結構定義
│   ├── pipelines.py          # CSV 輸出處理
│   ├── settings.py           # Scrapy 設定
│   └── spiders/
│       ├── raw_price.py      # 成交價格爬蟲
│       ├── raw_chip.py       # 三大法人爬蟲
│       └── major_holders.py  # 大戶持股爬蟲
├── tests/                    # 測試案例
└── output/                   # CSV 輸出目錄
```

## License

MIT
