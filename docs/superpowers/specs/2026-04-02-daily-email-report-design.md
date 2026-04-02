# Daily Email Report Design

## Overview

每日收盤後自動寄送個人化股市報表給每位註冊用戶，內容根據用戶的 watchlist 產生，涵蓋股價、法人、融資券、大戶持股、全市場摘要及到價提醒。

## Architecture

### Trigger Flow

```
celery-beat 18:30 (weekdays)
  → dispatch_daily_reports task
    → query all users WHERE email_report_enabled=True
    → for each user: dispatch send_user_report subtask to crawl queue
      → query user's watchlist
      → query today's data (prices, chips, margin, holders, alerts)
      → render Jinja2 HTML + plaintext templates
      → send via Gmail SMTP (smtplib + STARTTLS)
```

### New Files

| File | Purpose |
|------|---------|
| `backend/app/tasks/email_report.py` | Two Celery tasks: `dispatch_daily_reports` + `send_user_report` |
| `backend/app/services/email_service.py` | SMTP connection, email assembly, sending logic |
| `backend/app/templates/daily_report.html` | Jinja2 HTML email template |
| `backend/app/templates/daily_report.txt` | Jinja2 plaintext email template |

### Modified Files

| File | Change |
|------|--------|
| `backend/app/celery_app.py` | Add beat schedule entry at 18:30 |
| `backend/app/models.py` | Add `email_report_enabled` field to User model |
| `backend/requirements.txt` | Add `Jinja2` |
| `.env.example` | Add SMTP config vars |
| Alembic migration | Add `email_report_enabled` column |

## Report Content (6 Sections)

### A. Watchlist Price Summary

- Source: `watchlist` JOIN `raw_prices` WHERE date = today
- Columns: stock_id, stock_name, open, high, low, close, price_change (%), trade_volume
- Sort: by watchlist sort_order

### B. Institutional Investors (Three Major)

- Source: `watchlist` JOIN `raw_chips` WHERE date = today
- Columns: stock_id, stock_name, foreign_net, trust_net, dealer_net, total_net
- Unit: shares (股)

### C. Margin Trading Changes

- Source: `watchlist` JOIN `margin_trading` WHERE date = today
- Columns: stock_id, margin_balance, margin_balance - margin_balance_prev (增減), short_balance, short_balance - short_balance_prev (增減), offset

### D. Major Holders Changes

- Source: `watchlist` JOIN `major_holders` WHERE date = latest Friday
- Columns: stock_id, 400+ share holders ratio (level >= 12 sum), holder_count
- Compare with previous week if data available (ratio delta, count delta)
- Note: TDCC data updates weekly (Fridays only)

### E. Market Summary (no watchlist dependency)

- Source: `raw_prices` WHERE date = today, aggregate stats
- Content:
  - Total stocks up / down / flat count
  - Total market volume
  - Foreign/trust/dealer net buy/sell totals from `raw_chips`

### F. Alert Trigger Records

- Source: `notifications` WHERE user_id = user AND created_at::date = today
- Columns: title, message, created_at
- If no alerts triggered, show "today no alerts triggered"

### Empty Watchlist Handling

If user has no watchlist items, skip sections A~D. Only send E (market summary) + F (alerts).

## Email Service

### SMTP Configuration (.env)

```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=your-email@gmail.com
EMAIL_REPORT_ENABLED=true
```

Gmail requires an "App Password" (not login password). User must enable 2FA and generate one at https://myaccount.google.com/apppasswords.

### Email Assembly

- Format: `MIMEMultipart("alternative")` with plaintext + HTML parts
- Subject: `Stock Tracer Daily Report - 2026/04/02`
- From: SMTP_FROM config value
- To: user.email

### Error Handling

| Scenario | Action |
|----------|--------|
| Single email SMTP failure | Log error, Celery auto-retry (max 3, interval 60s) |
| SMTP connection failure | Log error, no retry (avoid account lockout) |
| User has no email | Skip user, log warning |
| EMAIL_REPORT_ENABLED=false | Entire feature disabled, beat task is no-op |
| No trading data for today | Skip report (holiday/weekend guard in dispatch task) |

## Database Changes

### User Model Addition

```python
email_report_enabled = Column(Boolean, default=True, nullable=False)
```

Single Alembic migration to add the column with default=True.

## HTML Template Design

- Color scheme: red = up, green = down (Taiwan stock market convention)
- Responsive tables for mobile reading
- Each section (A~F) as independent block with header
- Zebra-striped rows, right-aligned numbers
- Top summary bar: date + market up/down/flat counts

## Celery Integration

### Beat Schedule Addition

```python
"send-daily-reports": {
    "task": "app.tasks.email_report.dispatch_daily_reports",
    "schedule": crontab(hour=18, minute=30, day_of_week="1-5"),
}
```

### Task Routing

Both email tasks route to `crawl` queue, sharing existing `celery-worker-crawl` workers.

```python
"app.tasks.email_report.dispatch_daily_reports": {"queue": "crawl"},
"app.tasks.email_report.send_user_report": {"queue": "crawl"},
```

## API Endpoints

### Test Send (for development/debugging)

```
POST /api/v1/email-reports/test-send
Auth: required (JWT)
Response: { "status": "sent", "email": "user@example.com" }
```

Triggers `send_user_report` for the authenticated user immediately.

### Email Preferences (MVP optional, implement if time allows)

```
PUT /api/v1/users/me/email-preferences
Body: { "email_report_enabled": true/false }
Auth: required (JWT)
```

## Testing Strategy

- **Unit tests**: template rendering with mock data, data aggregation queries
- **Integration tests**: mock SMTP, verify email content and structure
- **Manual test**: POST /api/v1/email-reports/test-send endpoint

## Dependencies

### New Python Packages

- `Jinja2` — template engine for HTML/plaintext email rendering

### Existing (no changes needed)

- `smtplib` — Python stdlib, Gmail SMTP sending
- `email.mime` — Python stdlib, email assembly
- Celery + Redis — task scheduling and execution
