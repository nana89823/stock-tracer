# Stock Tracer

台灣股市追蹤分析平台 — 整合爬蟲資料收集、籌碼分析、技術圖表與回測系統。

## 技術架構

| 層級 | 技術 |
|------|------|
| 前端 | Next.js 15 (App Router) + TypeScript + Tailwind CSS + shadcn/ui |
| 後端 | FastAPI + SQLAlchemy (async) + Pydantic |
| 資料庫 | TimescaleDB (PostgreSQL 16) |
| 快取 | Redis 7 |
| 任務佇列 | Celery + Redis Broker |
| 爬蟲 | Scrapy 2.11+ |
| 反向代理 | Nginx (SSL/TLS) |
| CI/CD | GitHub Actions |
| 容器化 | Docker Compose |

## 功能特色

- 股票搜尋（代號/名稱模糊搜尋，支援分頁）
- K 線圖（日 K 技術圖表）
- 籌碼分析（三大法人買賣超、大戶持股分布）
- 融資融券數據
- 券商分點進出
- 回測系統（Celery 非同步執行，支援多策略）
- Dark mode 主題切換
- JWT 認證 + 登入頻率限制
- Loading Skeleton 骨架屏

## 環境需求

- Python 3.12+
- Node.js 18+
- PostgreSQL 16+ (或 TimescaleDB)
- Redis 7+

## 快速開始

### 1. 環境設定

```bash
cp .env.example .env
# 編輯 .env 設定資料庫和 Redis 連線
```

### 2. Docker Compose 啟動（推薦）

```bash
docker compose up -d
```

服務會在以下埠啟動：
- 前端：http://localhost:3000
- 後端 API：http://localhost:8001
- Nginx：http://localhost:80

### 3. 本地開發

```bash
# 後端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# 前端
cd frontend
npm install
npm run dev

# Celery Worker（回測任務）
cd backend
celery -A app.celery_app worker --loglevel=info --concurrency=2
```

## API 版本

API 路徑格式：`/api/v1/{resource}`

| 方法 | 路徑 | 說明 |
|------|------|------|
| POST | `/api/v1/auth/register` | 註冊 |
| POST | `/api/v1/auth/login` | 登入（取得 JWT） |
| GET | `/api/v1/auth/me` | 當前使用者 |
| GET | `/api/v1/stocks/?q=&skip=&limit=` | 搜尋股票 |
| GET | `/api/v1/stocks/{id}` | 股票詳情 |
| GET | `/api/v1/stocks/{id}/prices` | 價格資料 |
| GET | `/api/v1/stocks/{id}/chips` | 三大法人籌碼 |
| GET | `/api/v1/stocks/{id}/holders` | 大戶持股分布 |
| GET | `/api/v1/stocks/{id}/margin` | 融資融券 |
| GET | `/api/v1/stocks/{id}/brokers` | 券商分點 |
| GET | `/api/v1/backtests/` | 回測列表 |
| POST | `/api/v1/backtests/` | 建立回測 |
| GET | `/api/v1/backtests/{id}` | 回測詳情 |
| GET | `/health` | 健康檢查（DB + Redis） |

前端透過 Next.js rewrite 代理：`/api/*` → `/api/v1/*`，前端程式碼中使用 `/api/` 即可。

## 爬蟲

### 資料來源

| Spider | 資料 | 來源 | 市場 |
|--------|------|------|------|
| `raw_price` | 個股成交價格 | TWSE 證交所 | 上市 |
| `raw_chip` | 三大法人買賣超 | TWSE 證交所 | 上市 |
| `major_holders` | 集保戶股權分散表 | TDCC 集保中心 | 全部 |
| `margin_trading` | 融資融券餘額 | TWSE 證交所 | 上市 |
| `broker_trading` | 券商分點進出 | TWSE 證交所 | 上市 |
| `tpex_price` | 個股成交價格 | TPEx 櫃買中心 | 上櫃 |
| `tpex_chip` | 三大法人買賣超 | TPEx 櫃買中心 | 上櫃 |
| `tpex_margin` | 融資融券餘額 | TPEx 櫃買中心 | 上櫃 |

### 手動執行

```bash
scrapy crawl raw_price
scrapy crawl raw_chip
scrapy crawl major_holders
```

### 排程（Crontab）

```bash
# 安裝排程
bash scripts/setup_crontab.sh install

# 預設排程：
# 週一~五 18:00 — raw_price, raw_chip, margin_trading, broker_trading
# 週六 10:00 — major_holders

# 移除排程
bash scripts/setup_crontab.sh remove
```

## 測試

```bash
# 後端測試
cd backend
python -m pytest tests/ -v

# 前端 TypeScript 檢查
cd frontend
npx tsc --noEmit
```

## 專案結構

```
stock-tracer/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI 入口
│   │   ├── config.py               # 設定（環境變數）
│   │   ├── database.py             # SQLAlchemy async engine
│   │   ├── cache.py                # Redis 快取
│   │   ├── celery_app.py           # Celery 設定
│   │   ├── logging_config.py       # 結構化日誌
│   │   ├── api/
│   │   │   ├── stocks.py           # 股票 API
│   │   │   └── backtests.py        # 回測 API
│   │   ├── auth/
│   │   │   ├── router.py           # 認證路由
│   │   │   ├── security.py         # JWT + 密碼雜湊
│   │   │   └── rate_limit.py       # 登入頻率限制
│   │   ├── engine/
│   │   │   ├── backtest_runner.py   # 回測引擎
│   │   │   └── strategies.py       # 回測策略
│   │   ├── models/                  # SQLAlchemy ORM
│   │   ├── schemas/                 # Pydantic schemas
│   │   ├── tasks/
│   │   │   └── backtest_task.py     # Celery 回測任務
│   │   └── middleware/
│   │       └── logging.py           # 請求日誌中介層
│   ├── alembic/                     # DB migrations
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx           # Root layout (ThemeProvider)
│   │   │   ├── login/page.tsx       # 登入頁
│   │   │   ├── register/page.tsx    # 註冊頁
│   │   │   └── (dashboard)/
│   │   │       ├── layout.tsx       # Dashboard layout (AuthGuard)
│   │   │       ├── page.tsx         # 首頁（股票搜尋）
│   │   │       ├── stocks/[stockId] # 股票詳情頁
│   │   │       └── backtests/       # 回測頁面
│   │   ├── components/
│   │   │   ├── charts/              # K線、籌碼、融資券圖表
│   │   │   ├── skeletons/           # Loading 骨架屏
│   │   │   └── ui/                  # shadcn/ui 元件
│   │   ├── contexts/AuthContext.tsx  # 認證 Context
│   │   ├── lib/
│   │   │   ├── api.ts               # Axios 實例
│   │   │   ├── auth.ts              # Token 管理
│   │   │   └── schemas.ts           # Zod 驗證
│   │   └── hooks/useDebounce.ts
│   ├── next.config.ts               # API rewrite 代理
│   └── Dockerfile
├── stock_tracer/                     # Scrapy 爬蟲
│   └── spiders/
├── nginx/                            # Nginx 反向代理設定
├── scripts/                          # 排程、備份、快取清理
├── tests/                            # 測試
├── .github/workflows/ci.yml          # CI/CD
├── docker-compose.yml
└── .env.example
```

## 維運腳本

| 腳本 | 說明 |
|------|------|
| `scripts/run_spider.sh` | 執行爬蟲 + 清除快取 |
| `scripts/setup_crontab.sh` | 安裝/移除排程 |
| `scripts/clear_cache.sh` | 清除 Redis 股票快取 |
| `scripts/backup_db.sh` | 資料庫備份（7 天保留） |
| `scripts/restore_db.sh` | 資料庫還原 |

## License

MIT
