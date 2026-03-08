# Nginx Reverse Proxy

## SSL 憑證申請 (Certbot)

在 GCP VM 上安裝 certbot 並申請憑證：

```bash
sudo apt update && sudo apt install -y certbot

# 申請前先暫停 nginx（釋放 80 port）
docker compose stop nginx

# 申請憑證（將 your-domain.com 替換為實際域名）
sudo certbot certonly --standalone -d your-domain.com

# 申請完成後啟動 nginx
docker compose start nginx
```

憑證會存放在 `/etc/letsencrypt/live/your-domain.com/`。

申請完成後，將 `nginx/conf.d/default.conf` 中的 `${domain}` 替換為實際域名。

自動續期：
```bash
sudo certbot renew --pre-hook "docker compose stop nginx" --post-hook "docker compose start nginx"
```

## 啟動服務

```bash
cd /Users/admin/stock-tracer
docker compose up -d
```

僅重啟 nginx（修改配置後）：
```bash
docker compose restart nginx
```

## 環境變數

在專案根目錄的 `.env` 檔案中設定：

| 變數 | 說明 |
|------|------|
| `POSTGRES_USER` | PostgreSQL 使用者名稱 |
| `POSTGRES_PASSWORD` | PostgreSQL 密碼 |
| `POSTGRES_DB` | PostgreSQL 資料庫名稱 |

## 架構

```
Client --> Nginx (80/443)
              |-- /api/*  --> Backend (FastAPI :8001)
              |-- /*      --> Frontend (Next.js :3000)
```
