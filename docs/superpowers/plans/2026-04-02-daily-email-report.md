# Daily Email Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Send personalized daily stock market reports via Gmail SMTP to every registered user after market close, based on their watchlist.

**Architecture:** Celery beat triggers a dispatcher task at 18:30 weekdays. The dispatcher fans out one subtask per user to the crawl queue. Each subtask queries the user's watchlist, fetches today's data (prices, chips, margin, holders, alerts), renders Jinja2 HTML+text templates, and sends via Gmail SMTP.

**Tech Stack:** Python smtplib, Jinja2, Celery, SQLAlchemy (sync), PostgreSQL

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `backend/app/config.py` | Modify | Add SMTP settings fields |
| `backend/app/models/user.py` | Modify | Add `email_report_enabled` column |
| `backend/app/services/email_service.py` | Create | SMTP connection + send logic |
| `backend/app/services/report_data.py` | Create | Query DB for all 6 report sections |
| `backend/app/tasks/email_report.py` | Create | Two Celery tasks: dispatch + per-user send |
| `backend/app/templates/daily_report.html` | Create | Jinja2 HTML email template |
| `backend/app/templates/daily_report.txt` | Create | Jinja2 plaintext email template |
| `backend/app/api/email_reports.py` | Create | Test-send API endpoint |
| `backend/app/celery_app.py` | Modify | Add beat schedule + task route |
| `backend/app/main.py` | Modify | Register email_reports router |
| `backend/requirements.txt` | Modify | Add Jinja2 |
| `.env.example` | Modify | Add SMTP vars |
| `alembic/versions/xxx_add_email_report_enabled.py` | Create | Migration |
| `backend/tests/unit/test_report_data.py` | Create | Unit tests for data queries |
| `backend/tests/unit/test_email_service.py` | Create | Unit tests for email assembly |
| `backend/tests/unit/test_email_report_task.py` | Create | Unit tests for tasks |

---

### Task 1: Add SMTP Config & Dependencies

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/requirements.txt`
- Modify: `.env.example`

- [ ] **Step 1: Add SMTP fields to Settings**

```python
# backend/app/config.py — add these fields to class Settings:
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_from_name: str = "Stock Tracer"
    email_report_enabled: bool = False
```

- [ ] **Step 2: Add Jinja2 to requirements.txt**

Append to `backend/requirements.txt`:
```
Jinja2>=3.1.0
```

- [ ] **Step 3: Add SMTP vars to .env.example**

Append to `.env.example`:
```
# Email Report (Gmail SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your-email@gmail.com
SMTP_FROM_NAME=Stock Tracer
EMAIL_REPORT_ENABLED=false
```

- [ ] **Step 4: Verify config loads**

Run: `cd backend && python3 -c "from app.config import settings; print(settings.smtp_host)"`
Expected: empty string (no .env override)

- [ ] **Step 5: Commit**

```bash
git add backend/app/config.py backend/requirements.txt .env.example
git commit -m "feat(email): add SMTP config fields and Jinja2 dependency"
```

---

### Task 2: Add email_report_enabled to User Model + Migration

**Files:**
- Modify: `backend/app/models/user.py`
- Create: Alembic migration

- [ ] **Step 1: Add column to User model**

Add to `backend/app/models/user.py`, inside class User:
```python
    email_report_enabled: Mapped[bool] = mapped_column(default=True)
```

Add `Boolean` to the sqlalchemy imports at the top of the file.

- [ ] **Step 2: Generate Alembic migration**

Run:
```bash
cd backend && alembic revision --autogenerate -m "add email_report_enabled to users"
```

- [ ] **Step 3: Run migration on local DB**

Run:
```bash
cd backend && alembic upgrade head
```

- [ ] **Step 4: Verify column exists**

Run:
```bash
PGPASSWORD=stock_tracer_dev psql -h localhost -p 5433 -U stock_tracer -d stock_tracer -c "SELECT column_name, data_type FROM information_schema.columns WHERE table_name='users' AND column_name='email_report_enabled';"
```
Expected: one row with `boolean` type

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/user.py backend/alembic/versions/
git commit -m "feat(email): add email_report_enabled column to users"
```

---

### Task 3: Email Service (SMTP Send Logic)

**Files:**
- Create: `backend/app/services/email_service.py`
- Create: `backend/tests/unit/test_email_service.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/test_email_service.py`:
```python
"""Tests for email_service — SMTP email sending."""

from email.mime.multipart import MIMEMultipart
from unittest.mock import MagicMock, patch

import pytest

from app.services.email_service import build_email, send_email


class TestBuildEmail:
    def test_builds_multipart_alternative(self):
        msg = build_email(
            to_email="user@example.com",
            subject="Test Subject",
            html_body="<h1>Hello</h1>",
            text_body="Hello",
        )
        assert msg["To"] == "user@example.com"
        assert msg["Subject"] == "Test Subject"
        assert msg.get_content_type() == "multipart/alternative"

    def test_includes_from_header(self):
        msg = build_email(
            to_email="user@example.com",
            subject="Test",
            html_body="<p>Hi</p>",
            text_body="Hi",
            from_email="sender@example.com",
            from_name="Stock Tracer",
        )
        assert "Stock Tracer" in msg["From"]
        assert "sender@example.com" in msg["From"]

    def test_contains_html_and_text_parts(self):
        msg = build_email(
            to_email="user@example.com",
            subject="Test",
            html_body="<p>HTML</p>",
            text_body="TEXT",
        )
        payloads = msg.get_payload()
        assert len(payloads) == 2
        assert payloads[0].get_content_type() == "text/plain"
        assert payloads[1].get_content_type() == "text/html"


class TestSendEmail:
    @patch("app.services.email_service.smtplib.SMTP")
    def test_send_email_calls_smtp(self, mock_smtp_class):
        mock_smtp = MagicMock()
        mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_smtp)
        mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

        msg = build_email(
            to_email="user@example.com",
            subject="Test",
            html_body="<p>Hi</p>",
            text_body="Hi",
        )
        send_email(
            msg,
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="sender@gmail.com",
            smtp_password="app-password",
        )

        mock_smtp.starttls.assert_called_once()
        mock_smtp.login.assert_called_once_with("sender@gmail.com", "app-password")
        mock_smtp.send_message.assert_called_once_with(msg)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python3 -m pytest tests/unit/test_email_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.email_service'`

- [ ] **Step 3: Implement email_service.py**

Create `backend/app/services/email_service.py`:
```python
"""Email sending service using SMTP."""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


def build_email(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str,
    from_email: str = "",
    from_name: str = "Stock Tracer",
) -> MIMEMultipart:
    """Build a multipart email with HTML and plaintext."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["To"] = to_email
    msg["From"] = f"{from_name} <{from_email}>" if from_email else from_name

    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    return msg


def send_email(
    msg: MIMEMultipart,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
) -> None:
    """Send an email via SMTP with STARTTLS."""
    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
    logger.info("Email sent to %s", msg["To"])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python3 -m pytest tests/unit/test_email_service.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/email_service.py backend/tests/unit/test_email_service.py
git commit -m "feat(email): add email service with SMTP send logic"
```

---

### Task 4: Report Data Queries

**Files:**
- Create: `backend/app/services/report_data.py`
- Create: `backend/tests/unit/test_report_data.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/test_report_data.py`:
```python
"""Tests for report_data — daily report data queries."""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from app.services.report_data import (
    get_watchlist_prices,
    get_watchlist_chips,
    get_watchlist_margin,
    get_watchlist_holders,
    get_market_summary,
    get_user_alerts,
)


class TestGetWatchlistPrices:
    def test_returns_empty_list_for_no_watchlist(self):
        session = MagicMock()
        session.execute.return_value.all.return_value = []
        result = get_watchlist_prices(session, user_id=1, target_date=date(2026, 4, 1))
        assert result == []


class TestGetMarketSummary:
    def test_returns_dict_with_required_keys(self):
        session = MagicMock()
        # Mock aggregate query result
        session.execute.return_value.one.return_value = (100, 50, 30, 1000000000)
        result = get_market_summary(session, target_date=date(2026, 4, 1))
        assert "up_count" in result
        assert "down_count" in result
        assert "flat_count" in result
        assert "total_volume" in result


class TestGetUserAlerts:
    def test_returns_empty_list_when_no_alerts(self):
        session = MagicMock()
        session.execute.return_value.all.return_value = []
        result = get_user_alerts(session, user_id=1, target_date=date(2026, 4, 1))
        assert result == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python3 -m pytest tests/unit/test_report_data.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement report_data.py**

Create `backend/app/services/report_data.py`:
```python
"""Data queries for daily email report sections."""

import logging
from datetime import date, datetime, timedelta

from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session

from app.models import (
    MajorHolders,
    MarginTrading,
    Notification,
    RawChip,
    RawPrice,
    Stock,
    Watchlist,
)

logger = logging.getLogger(__name__)


def get_watchlist_prices(
    session: Session, user_id: int, target_date: date
) -> list[dict]:
    """Get closing prices for user's watchlist stocks."""
    stmt = (
        select(
            RawPrice.stock_id,
            RawPrice.stock_name,
            RawPrice.open_price,
            RawPrice.high_price,
            RawPrice.low_price,
            RawPrice.close_price,
            RawPrice.price_change,
            RawPrice.trade_volume,
        )
        .join(Watchlist, Watchlist.stock_id == RawPrice.stock_id)
        .where(Watchlist.user_id == user_id, RawPrice.date == target_date)
        .order_by(Watchlist.sort_order)
    )
    return [row._asdict() for row in session.execute(stmt).all()]


def get_watchlist_chips(
    session: Session, user_id: int, target_date: date
) -> list[dict]:
    """Get institutional investor data for user's watchlist stocks."""
    stmt = (
        select(
            RawChip.stock_id,
            RawChip.stock_name,
            RawChip.foreign_net,
            RawChip.trust_net,
            RawChip.dealer_net,
            RawChip.total_net,
        )
        .join(Watchlist, Watchlist.stock_id == RawChip.stock_id)
        .where(Watchlist.user_id == user_id, RawChip.date == target_date)
        .order_by(Watchlist.sort_order)
    )
    return [row._asdict() for row in session.execute(stmt).all()]


def get_watchlist_margin(
    session: Session, user_id: int, target_date: date
) -> list[dict]:
    """Get margin trading data for user's watchlist stocks."""
    stmt = (
        select(
            MarginTrading.stock_id,
            MarginTrading.margin_balance,
            MarginTrading.margin_balance_prev,
            MarginTrading.short_balance,
            MarginTrading.short_balance_prev,
            MarginTrading.offset,
        )
        .join(Watchlist, Watchlist.stock_id == MarginTrading.stock_id)
        .where(Watchlist.user_id == user_id, MarginTrading.date == target_date)
        .order_by(Watchlist.sort_order)
    )
    rows = session.execute(stmt).all()
    result = []
    for row in rows:
        d = row._asdict()
        d["margin_change"] = d["margin_balance"] - d["margin_balance_prev"]
        d["short_change"] = d["short_balance"] - d["short_balance_prev"]
        result.append(d)
    return result


def get_watchlist_holders(
    session: Session, user_id: int, target_date: date
) -> list[dict]:
    """Get major holders (>=400 shares) for user's watchlist.

    Uses the latest available date on or before target_date.
    """
    # Find latest major_holders date
    latest_date_stmt = (
        select(func.max(MajorHolders.date))
        .where(MajorHolders.date <= target_date)
    )
    latest_date = session.execute(latest_date_stmt).scalar()
    if not latest_date:
        return []

    # Find previous week's date for comparison
    prev_date_stmt = (
        select(func.max(MajorHolders.date))
        .where(MajorHolders.date < latest_date)
    )
    prev_date = session.execute(prev_date_stmt).scalar()

    # Get watchlist stock_ids
    wl_stmt = select(Watchlist.stock_id).where(Watchlist.user_id == user_id)
    watchlist_ids = [r[0] for r in session.execute(wl_stmt).all()]
    if not watchlist_ids:
        return []

    # Current week: sum ratio and count for level >= 12
    curr_stmt = (
        select(
            MajorHolders.stock_id,
            func.sum(MajorHolders.holding_ratio).label("ratio"),
            func.sum(MajorHolders.holder_count).label("count"),
        )
        .where(
            MajorHolders.date == latest_date,
            MajorHolders.stock_id.in_(watchlist_ids),
            MajorHolders.holding_level >= 12,
        )
        .group_by(MajorHolders.stock_id)
    )
    current = {r.stock_id: {"ratio": r.ratio, "count": r.count}
               for r in session.execute(curr_stmt).all()}

    # Previous week for delta
    prev = {}
    if prev_date:
        prev_stmt = (
            select(
                MajorHolders.stock_id,
                func.sum(MajorHolders.holding_ratio).label("ratio"),
                func.sum(MajorHolders.holder_count).label("count"),
            )
            .where(
                MajorHolders.date == prev_date,
                MajorHolders.stock_id.in_(watchlist_ids),
                MajorHolders.holding_level >= 12,
            )
            .group_by(MajorHolders.stock_id)
        )
        prev = {r.stock_id: {"ratio": r.ratio, "count": r.count}
                for r in session.execute(prev_stmt).all()}

    result = []
    for sid in watchlist_ids:
        if sid not in current:
            continue
        c = current[sid]
        p = prev.get(sid, {"ratio": 0, "count": 0})
        result.append({
            "stock_id": sid,
            "holder_ratio": round(c["ratio"], 2),
            "holder_count": c["count"],
            "ratio_delta": round(c["ratio"] - p["ratio"], 2),
            "count_delta": c["count"] - p["count"],
            "data_date": latest_date.isoformat(),
        })
    return result


def get_market_summary(session: Session, target_date: date) -> dict:
    """Get overall market statistics for the day."""
    # Price stats
    price_stmt = select(
        func.sum(case((RawPrice.price_change > 0, 1), else_=0)).label("up_count"),
        func.sum(case((RawPrice.price_change < 0, 1), else_=0)).label("down_count"),
        func.sum(case((RawPrice.price_change == 0, 1), else_=0)).label("flat_count"),
        func.sum(RawPrice.trade_volume).label("total_volume"),
    ).where(RawPrice.date == target_date)
    price_row = session.execute(price_stmt).one()

    # Institutional net totals
    chip_stmt = select(
        func.sum(RawChip.foreign_net).label("foreign_total"),
        func.sum(RawChip.trust_net).label("trust_total"),
        func.sum(RawChip.dealer_net).label("dealer_total"),
        func.sum(RawChip.total_net).label("inst_total"),
    ).where(RawChip.date == target_date)
    chip_row = session.execute(chip_stmt).one()

    return {
        "up_count": price_row.up_count or 0,
        "down_count": price_row.down_count or 0,
        "flat_count": price_row.flat_count or 0,
        "total_volume": price_row.total_volume or 0,
        "foreign_total": chip_row.foreign_total or 0,
        "trust_total": chip_row.trust_total or 0,
        "dealer_total": chip_row.dealer_total or 0,
        "inst_total": chip_row.inst_total or 0,
    }


def get_user_alerts(
    session: Session, user_id: int, target_date: date
) -> list[dict]:
    """Get alert notifications triggered today for the user."""
    stmt = (
        select(
            Notification.title,
            Notification.message,
            Notification.created_at,
        )
        .where(
            Notification.user_id == user_id,
            func.date(Notification.created_at) == target_date,
        )
        .order_by(Notification.created_at)
    )
    return [row._asdict() for row in session.execute(stmt).all()]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python3 -m pytest tests/unit/test_report_data.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/report_data.py backend/tests/unit/test_report_data.py
git commit -m "feat(email): add report data query service"
```

---

### Task 5: Jinja2 Email Templates

**Files:**
- Create: `backend/app/templates/daily_report.html`
- Create: `backend/app/templates/daily_report.txt`

- [ ] **Step 1: Create templates directory**

```bash
mkdir -p backend/app/templates
```

- [ ] **Step 2: Create HTML template**

Create `backend/app/templates/daily_report.html`:
```html
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
body { font-family: -apple-system, 'Microsoft JhengHei', sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
.container { max-width: 680px; margin: 0 auto; background: #fff; border-radius: 8px; overflow: hidden; }
.header { background: #1a1a2e; color: #fff; padding: 20px 24px; }
.header h1 { margin: 0; font-size: 20px; }
.header .date { color: #a0a0c0; font-size: 14px; margin-top: 4px; }
.summary-bar { display: flex; gap: 16px; padding: 12px 24px; background: #f8f9fa; border-bottom: 1px solid #eee; font-size: 14px; }
.summary-bar .up { color: #d32f2f; }
.summary-bar .down { color: #2e7d32; }
.section { padding: 16px 24px; border-bottom: 1px solid #eee; }
.section h2 { font-size: 16px; margin: 0 0 12px 0; color: #333; border-left: 4px solid #1a1a2e; padding-left: 8px; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th { background: #f8f9fa; text-align: left; padding: 8px; border-bottom: 2px solid #ddd; }
td { padding: 8px; border-bottom: 1px solid #eee; }
tr:nth-child(even) { background: #fafafa; }
.num { text-align: right; font-variant-numeric: tabular-nums; }
.up-color { color: #d32f2f; }
.down-color { color: #2e7d32; }
.neutral { color: #666; }
.empty-msg { color: #999; font-style: italic; padding: 12px 0; }
.footer { padding: 16px 24px; text-align: center; font-size: 12px; color: #999; }
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>Stock Tracer Daily Report</h1>
    <div class="date">{{ report_date }}</div>
  </div>

  {# === E. Market Summary === #}
  <div class="summary-bar">
    <span class="up">&#9650; {{ market.up_count }}</span>
    <span class="down">&#9660; {{ market.down_count }}</span>
    <span>&#9644; {{ market.flat_count }}</span>
    <span>Volume: {{ "{:,.0f}".format(market.total_volume) }}</span>
  </div>
  <div class="section">
    <h2>E. Market Summary</h2>
    <table>
      <tr><td>Foreign Net</td><td class="num {{ 'up-color' if market.foreign_total > 0 else 'down-color' if market.foreign_total < 0 else 'neutral' }}">{{ "{:+,.0f}".format(market.foreign_total) }}</td></tr>
      <tr><td>Trust Net</td><td class="num {{ 'up-color' if market.trust_total > 0 else 'down-color' if market.trust_total < 0 else 'neutral' }}">{{ "{:+,.0f}".format(market.trust_total) }}</td></tr>
      <tr><td>Dealer Net</td><td class="num {{ 'up-color' if market.dealer_total > 0 else 'down-color' if market.dealer_total < 0 else 'neutral' }}">{{ "{:+,.0f}".format(market.dealer_total) }}</td></tr>
      <tr><td><strong>Total</strong></td><td class="num {{ 'up-color' if market.inst_total > 0 else 'down-color' if market.inst_total < 0 else 'neutral' }}"><strong>{{ "{:+,.0f}".format(market.inst_total) }}</strong></td></tr>
    </table>
  </div>

  {% if prices %}
  {# === A. Watchlist Prices === #}
  <div class="section">
    <h2>A. Watchlist Prices</h2>
    <table>
      <tr><th>Stock</th><th class="num">Close</th><th class="num">Change</th><th class="num">Volume</th></tr>
      {% for p in prices %}
      <tr>
        <td>{{ p.stock_id }} {{ p.stock_name }}</td>
        <td class="num">{{ "%.2f"|format(p.close_price) }}</td>
        <td class="num {{ 'up-color' if p.price_change > 0 else 'down-color' if p.price_change < 0 else 'neutral' }}">{{ "{:+.2f}".format(p.price_change) }}</td>
        <td class="num">{{ "{:,.0f}".format(p.trade_volume) }}</td>
      </tr>
      {% endfor %}
    </table>
  </div>
  {% endif %}

  {% if chips %}
  {# === B. Institutional Investors === #}
  <div class="section">
    <h2>B. Institutional Investors</h2>
    <table>
      <tr><th>Stock</th><th class="num">Foreign</th><th class="num">Trust</th><th class="num">Dealer</th><th class="num">Total</th></tr>
      {% for c in chips %}
      <tr>
        <td>{{ c.stock_id }} {{ c.stock_name }}</td>
        <td class="num {{ 'up-color' if c.foreign_net > 0 else 'down-color' if c.foreign_net < 0 else 'neutral' }}">{{ "{:+,.0f}".format(c.foreign_net) }}</td>
        <td class="num {{ 'up-color' if c.trust_net > 0 else 'down-color' if c.trust_net < 0 else 'neutral' }}">{{ "{:+,.0f}".format(c.trust_net) }}</td>
        <td class="num {{ 'up-color' if c.dealer_net > 0 else 'down-color' if c.dealer_net < 0 else 'neutral' }}">{{ "{:+,.0f}".format(c.dealer_net) }}</td>
        <td class="num {{ 'up-color' if c.total_net > 0 else 'down-color' if c.total_net < 0 else 'neutral' }}"><strong>{{ "{:+,.0f}".format(c.total_net) }}</strong></td>
      </tr>
      {% endfor %}
    </table>
  </div>
  {% endif %}

  {% if margin %}
  {# === C. Margin Trading === #}
  <div class="section">
    <h2>C. Margin Trading</h2>
    <table>
      <tr><th>Stock</th><th class="num">Margin Bal</th><th class="num">Chg</th><th class="num">Short Bal</th><th class="num">Chg</th><th class="num">Offset</th></tr>
      {% for m in margin %}
      <tr>
        <td>{{ m.stock_id }}</td>
        <td class="num">{{ "{:,.0f}".format(m.margin_balance) }}</td>
        <td class="num {{ 'up-color' if m.margin_change > 0 else 'down-color' if m.margin_change < 0 else 'neutral' }}">{{ "{:+,.0f}".format(m.margin_change) }}</td>
        <td class="num">{{ "{:,.0f}".format(m.short_balance) }}</td>
        <td class="num {{ 'up-color' if m.short_change > 0 else 'down-color' if m.short_change < 0 else 'neutral' }}">{{ "{:+,.0f}".format(m.short_change) }}</td>
        <td class="num">{{ "{:,.0f}".format(m.offset) }}</td>
      </tr>
      {% endfor %}
    </table>
  </div>
  {% endif %}

  {% if holders %}
  {# === D. Major Holders === #}
  <div class="section">
    <h2>D. Major Holders (400+)</h2>
    <p style="font-size:12px;color:#999;">Data: {{ holders[0].data_date }}</p>
    <table>
      <tr><th>Stock</th><th class="num">Ratio %</th><th class="num">Delta</th><th class="num">Count</th><th class="num">Delta</th></tr>
      {% for h in holders %}
      <tr>
        <td>{{ h.stock_id }}</td>
        <td class="num">{{ "%.2f"|format(h.holder_ratio) }}%</td>
        <td class="num {{ 'up-color' if h.ratio_delta > 0 else 'down-color' if h.ratio_delta < 0 else 'neutral' }}">{{ "{:+.2f}".format(h.ratio_delta) }}</td>
        <td class="num">{{ "{:,}".format(h.holder_count) }}</td>
        <td class="num {{ 'up-color' if h.count_delta > 0 else 'down-color' if h.count_delta < 0 else 'neutral' }}">{{ "{:+,}".format(h.count_delta) }}</td>
      </tr>
      {% endfor %}
    </table>
  </div>
  {% endif %}

  {# === F. Alert Triggers === #}
  <div class="section">
    <h2>F. Alert Triggers</h2>
    {% if alerts %}
    <table>
      <tr><th>Alert</th><th>Detail</th><th>Time</th></tr>
      {% for a in alerts %}
      <tr>
        <td>{{ a.title }}</td>
        <td>{{ a.message }}</td>
        <td>{{ a.created_at.strftime('%H:%M') }}</td>
      </tr>
      {% endfor %}
    </table>
    {% else %}
    <p class="empty-msg">No alerts triggered today.</p>
    {% endif %}
  </div>

  <div class="footer">
    Stock Tracer &mdash; Auto-generated report. Do not reply.
  </div>
</div>
</body>
</html>
```

- [ ] **Step 3: Create plaintext template**

Create `backend/app/templates/daily_report.txt`:
```
Stock Tracer Daily Report — {{ report_date }}
================================================

== E. Market Summary ==
Up: {{ market.up_count }} | Down: {{ market.down_count }} | Flat: {{ market.flat_count }}
Total Volume: {{ "{:,.0f}".format(market.total_volume) }}
Foreign Net: {{ "{:+,.0f}".format(market.foreign_total) }}
Trust Net: {{ "{:+,.0f}".format(market.trust_total) }}
Dealer Net: {{ "{:+,.0f}".format(market.dealer_total) }}
Inst Total: {{ "{:+,.0f}".format(market.inst_total) }}

{% if prices %}
== A. Watchlist Prices ==
{% for p in prices %}
{{ p.stock_id }} {{ p.stock_name }}  Close: {{ "%.2f"|format(p.close_price) }}  Chg: {{ "{:+.2f}".format(p.price_change) }}  Vol: {{ "{:,.0f}".format(p.trade_volume) }}
{% endfor %}
{% endif %}

{% if chips %}
== B. Institutional Investors ==
{% for c in chips %}
{{ c.stock_id }} {{ c.stock_name }}  Foreign: {{ "{:+,.0f}".format(c.foreign_net) }}  Trust: {{ "{:+,.0f}".format(c.trust_net) }}  Dealer: {{ "{:+,.0f}".format(c.dealer_net) }}  Total: {{ "{:+,.0f}".format(c.total_net) }}
{% endfor %}
{% endif %}

{% if margin %}
== C. Margin Trading ==
{% for m in margin %}
{{ m.stock_id }}  Margin: {{ "{:,.0f}".format(m.margin_balance) }} ({{ "{:+,.0f}".format(m.margin_change) }})  Short: {{ "{:,.0f}".format(m.short_balance) }} ({{ "{:+,.0f}".format(m.short_change) }})  Offset: {{ "{:,.0f}".format(m.offset) }}
{% endfor %}
{% endif %}

{% if holders %}
== D. Major Holders (400+) — Data: {{ holders[0].data_date }} ==
{% for h in holders %}
{{ h.stock_id }}  Ratio: {{ "%.2f"|format(h.holder_ratio) }}% ({{ "{:+.2f}".format(h.ratio_delta) }})  Count: {{ h.holder_count }} ({{ "{:+,}".format(h.count_delta) }})
{% endfor %}
{% endif %}

== F. Alert Triggers ==
{% if alerts %}
{% for a in alerts %}
[{{ a.created_at.strftime('%H:%M') }}] {{ a.title }} — {{ a.message }}
{% endfor %}
{% else %}
No alerts triggered today.
{% endif %}

---
Stock Tracer — Auto-generated report.
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/templates/
git commit -m "feat(email): add HTML and plaintext email templates"
```

---

### Task 6: Celery Tasks (Dispatch + Per-User Send)

**Files:**
- Create: `backend/app/tasks/email_report.py`
- Create: `backend/tests/unit/test_email_report_task.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/test_email_report_task.py`:
```python
"""Tests for email_report Celery tasks."""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest


class TestDispatchDailyReports:
    @patch("app.tasks.email_report.SyncSession")
    @patch("app.tasks.email_report.send_user_report")
    def test_dispatches_for_enabled_users(self, mock_send, mock_session_cls):
        from app.tasks.email_report import dispatch_daily_reports

        mock_session = MagicMock()
        mock_session_cls.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)

        # Mock 2 users with email_report_enabled=True
        mock_user1 = MagicMock(id=1, email="a@test.com")
        mock_user2 = MagicMock(id=2, email="b@test.com")
        mock_session.execute.return_value.scalars.return_value.all.return_value = [
            mock_user1, mock_user2
        ]

        result = dispatch_daily_reports()

        assert mock_send.delay.call_count == 2
        assert result["dispatched"] == 2


class TestSendUserReport:
    @patch("app.tasks.email_report.send_email")
    @patch("app.tasks.email_report.SyncSession")
    @patch("app.tasks.email_report.settings")
    def test_sends_email_for_user(self, mock_settings, mock_session_cls, mock_send):
        from app.tasks.email_report import send_user_report

        mock_settings.smtp_host = "smtp.gmail.com"
        mock_settings.smtp_port = 587
        mock_settings.smtp_user = "test@gmail.com"
        mock_settings.smtp_password = "password"
        mock_settings.smtp_from_email = "test@gmail.com"
        mock_settings.smtp_from_name = "Stock Tracer"
        mock_settings.email_report_enabled = True

        mock_session = MagicMock()
        mock_session_cls.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)

        # Mock user
        mock_user = MagicMock(id=1, email="user@test.com")
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_user

        # Mock all data queries to return empty
        with patch("app.tasks.email_report.get_watchlist_prices", return_value=[]), \
             patch("app.tasks.email_report.get_watchlist_chips", return_value=[]), \
             patch("app.tasks.email_report.get_watchlist_margin", return_value=[]), \
             patch("app.tasks.email_report.get_watchlist_holders", return_value=[]), \
             patch("app.tasks.email_report.get_market_summary", return_value={
                 "up_count": 500, "down_count": 300, "flat_count": 100,
                 "total_volume": 100000000,
                 "foreign_total": 1000000, "trust_total": -500000,
                 "dealer_total": 200000, "inst_total": 700000,
             }), \
             patch("app.tasks.email_report.get_user_alerts", return_value=[]):

            result = send_user_report(user_id=1)

        assert result["status"] == "sent"
        mock_send.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python3 -m pytest tests/unit/test_email_report_task.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement email_report.py**

Create `backend/app/tasks/email_report.py`:
```python
"""Celery tasks for daily email reports."""

import logging
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.celery_app import celery
from app.config import settings
from app.models.user import User
from app.services.email_service import build_email, send_email
from app.services.report_data import (
    get_market_summary,
    get_user_alerts,
    get_watchlist_chips,
    get_watchlist_holders,
    get_watchlist_margin,
    get_watchlist_prices,
)

logger = logging.getLogger(__name__)

sync_engine = create_engine(settings.database_url_sync)
SyncSession = sessionmaker(bind=sync_engine)

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
jinja_env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))


@celery.task(name="app.tasks.email_report.dispatch_daily_reports")
def dispatch_daily_reports() -> dict:
    """Fan out one send_user_report task per enabled user."""
    if not settings.email_report_enabled:
        logger.info("Email reports disabled, skipping")
        return {"status": "disabled"}

    today = date.today()

    with SyncSession() as session:
        stmt = select(User).where(
            User.is_active == True,  # noqa: E712
            User.email_report_enabled == True,  # noqa: E712
        )
        users = session.execute(stmt).scalars().all()

    dispatched = 0
    for user in users:
        if not user.email:
            logger.warning("User %d has no email, skipping", user.id)
            continue
        send_user_report.delay(user_id=user.id, target_date=today.isoformat())
        dispatched += 1

    logger.info("Dispatched %d email report tasks", dispatched)
    return {"status": "dispatched", "dispatched": dispatched}


@celery.task(
    name="app.tasks.email_report.send_user_report",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_user_report(self, user_id: int, target_date: str = None) -> dict:
    """Generate and send daily report for a single user."""
    if not settings.email_report_enabled:
        return {"status": "disabled"}

    target = date.fromisoformat(target_date) if target_date else date.today()

    try:
        with SyncSession() as session:
            user = session.execute(
                select(User).where(User.id == user_id)
            ).scalar_one_or_none()

            if not user or not user.email:
                logger.warning("User %d not found or no email", user_id)
                return {"status": "skipped", "reason": "no user/email"}

            # Gather all report data
            data = {
                "report_date": target.strftime("%Y/%m/%d"),
                "prices": get_watchlist_prices(session, user_id, target),
                "chips": get_watchlist_chips(session, user_id, target),
                "margin": get_watchlist_margin(session, user_id, target),
                "holders": get_watchlist_holders(session, user_id, target),
                "market": get_market_summary(session, target),
                "alerts": get_user_alerts(session, user_id, target),
            }

        # Render templates
        html_template = jinja_env.get_template("daily_report.html")
        text_template = jinja_env.get_template("daily_report.txt")
        html_body = html_template.render(**data)
        text_body = text_template.render(**data)

        # Build and send email
        subject = f"Stock Tracer Daily Report - {data['report_date']}"
        msg = build_email(
            to_email=user.email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            from_email=settings.smtp_from_email,
            from_name=settings.smtp_from_name,
        )
        send_email(
            msg,
            smtp_host=settings.smtp_host,
            smtp_port=settings.smtp_port,
            smtp_user=settings.smtp_user,
            smtp_password=settings.smtp_password,
        )

        logger.info("Report sent to user %d (%s)", user_id, user.email)
        return {"status": "sent", "user_id": user_id, "email": user.email}

    except Exception as exc:
        logger.exception("Failed to send report to user %d", user_id)
        raise self.retry(exc=exc)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python3 -m pytest tests/unit/test_email_report_task.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/tasks/email_report.py backend/tests/unit/test_email_report_task.py
git commit -m "feat(email): add dispatch and per-user report Celery tasks"
```

---

### Task 7: Celery Beat Schedule + Task Routing

**Files:**
- Modify: `backend/app/celery_app.py`

- [ ] **Step 1: Add task route for email tasks**

In `backend/app/celery_app.py`, add to `celery.conf.task_routes`:
```python
    "app.tasks.email_report.dispatch_daily_reports": {"queue": "crawl"},
    "app.tasks.email_report.send_user_report": {"queue": "crawl"},
```

- [ ] **Step 2: Add beat schedule entry**

In `backend/app/celery_app.py`, add to `celery.conf.beat_schedule`:
```python
    # --- Daily email report (18:30, after all crawls complete) ---
    "send-daily-reports": {
        "task": "app.tasks.email_report.dispatch_daily_reports",
        "schedule": crontab(hour=18, minute=30, day_of_week="1-5"),
    },
```

- [ ] **Step 3: Add task import**

At the bottom of `celery_app.py`, add:
```python
import app.tasks.email_report  # noqa: F401, E402
```

- [ ] **Step 4: Verify celery loads**

Run: `cd backend && python3 -c "from app.celery_app import celery; print([t for t in celery.conf.beat_schedule if 'report' in t])"`
Expected: `['send-daily-reports']`

- [ ] **Step 5: Commit**

```bash
git add backend/app/celery_app.py
git commit -m "feat(email): add daily report to celery beat schedule"
```

---

### Task 8: Test-Send API Endpoint

**Files:**
- Create: `backend/app/api/email_reports.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create the router**

Create `backend/app/api/email_reports.py`:
```python
"""API endpoint for testing email report delivery."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.tasks.email_report import send_user_report

router = APIRouter()


@router.post("/test-send")
async def test_send_report(current_user: User = Depends(get_current_user)):
    """Send a test daily report to the current user immediately."""
    send_user_report.delay(user_id=current_user.id)
    return {"status": "queued", "email": current_user.email}
```

- [ ] **Step 2: Register the router in main.py**

In `backend/app/main.py`, add import and registration:
```python
from app.api.email_reports import router as email_reports_router
```

Add with other `app.include_router` calls:
```python
app.include_router(email_reports_router, prefix="/api/v1/email-reports", tags=["email-reports"])
```

- [ ] **Step 3: Verify endpoint registers**

Run: `cd backend && python3 -c "from app.main import app; routes = [r.path for r in app.routes]; print('/api/v1/email-reports/test-send' in routes)"`
Expected: `True`

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/email_reports.py backend/app/main.py
git commit -m "feat(email): add test-send API endpoint"
```

---

### Task 9: Integration Test + Final Verification

**Files:**
- All files from previous tasks

- [ ] **Step 1: Run all unit tests**

Run: `cd backend && python3 -m pytest tests/unit/ -v`
Expected: All tests pass

- [ ] **Step 2: Run black formatter**

Run: `python3 -m black backend/app/services/email_service.py backend/app/services/report_data.py backend/app/tasks/email_report.py backend/app/api/email_reports.py backend/tests/unit/test_email_service.py backend/tests/unit/test_report_data.py backend/tests/unit/test_email_report_task.py`

- [ ] **Step 3: Run flake8**

Run: `python3 -m flake8 backend/app/services/email_service.py backend/app/services/report_data.py backend/app/tasks/email_report.py backend/app/api/email_reports.py`
Fix any issues found.

- [ ] **Step 4: Run Alembic migration check**

Run: `cd backend && alembic check`
Expected: No pending migrations

- [ ] **Step 5: Manual smoke test (optional)**

Set up `.env` with real Gmail SMTP credentials and run:
```bash
curl -X POST http://localhost:8001/api/v1/email-reports/test-send \
  -H "Authorization: Bearer <your-jwt-token>"
```
Check email inbox for the report.

- [ ] **Step 6: Final commit if any fixes**

```bash
git add -u
git commit -m "fix(email): lint and formatting fixes"
```
