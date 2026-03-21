from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery = Celery("stock_tracer")

celery.conf.update(
    broker_url=settings.redis_url,
    result_backend=settings.redis_url,
    task_serializer="json",
    result_serializer="json",
    task_track_started=True,
    task_time_limit=600,
    task_soft_time_limit=540,
    timezone="Asia/Taipei",
)

# ── Queue routing (single source of truth) ─────────────────
celery.conf.task_default_queue = "default"
celery.conf.task_routes = {
    "app.tasks.crawl_task.run_spider": {"queue": "crawl"},
    "app.tasks.alert_checker.check_price_alerts": {"queue": "crawl"},
    "run_backtest": {"queue": "backtest"},
}

# ── Beat schedule (weekdays only, Asia/Taipei) ─────────────
# 台股收盤 13:30，資料約 14:00 後陸續更新
celery.conf.beat_schedule = {
    # --- 收盤行情（14:00~14:15，錯開 2 分鐘避免被封 IP）---
    "crawl-raw-price": {
        "task": "app.tasks.crawl_task.run_spider",
        "schedule": crontab(hour=14, minute=0, day_of_week="1-5"),
        "args": ("raw_price",),
    },
    "crawl-tpex-price": {
        "task": "app.tasks.crawl_task.run_spider",
        "schedule": crontab(hour=14, minute=2, day_of_week="1-5"),
        "args": ("tpex_price",),
    },
    "crawl-raw-chip": {
        "task": "app.tasks.crawl_task.run_spider",
        "schedule": crontab(hour=14, minute=5, day_of_week="1-5"),
        "args": ("raw_chip",),
    },
    "crawl-tpex-chip": {
        "task": "app.tasks.crawl_task.run_spider",
        "schedule": crontab(hour=14, minute=7, day_of_week="1-5"),
        "args": ("tpex_chip",),
    },
    "crawl-margin-trading": {
        "task": "app.tasks.crawl_task.run_spider",
        "schedule": crontab(hour=14, minute=10, day_of_week="1-5"),
        "args": ("margin_trading",),
    },
    "crawl-tpex-margin": {
        "task": "app.tasks.crawl_task.run_spider",
        "schedule": crontab(hour=14, minute=12, day_of_week="1-5"),
        "args": ("tpex_margin",),
    },
    "crawl-broker-trading": {
        "task": "app.tasks.crawl_task.run_spider",
        "schedule": crontab(hour=14, minute=15, day_of_week="1-5"),
        "args": ("broker_trading",),
    },
    # --- 大戶持股（18:00，資料更新較晚）---
    "crawl-major-holders": {
        "task": "app.tasks.crawl_task.run_spider",
        "schedule": crontab(hour=18, minute=0, day_of_week="1-5"),
        "args": ("major_holders",),
    },
    # --- 到價提醒（14:20，等行情爬完再檢查）---
    "check-price-alerts": {
        "task": "app.tasks.alert_checker.check_price_alerts",
        "schedule": crontab(hour=14, minute=20, day_of_week="1-5"),
    },
}

# Explicitly import tasks (autodiscover unreliable with Docker volume mounts)
import app.tasks.crawl_task  # noqa: F401, E402
import app.tasks.backtest_task  # noqa: F401, E402
import app.tasks.alert_checker  # noqa: F401, E402
