"""Verify celery beat schedule and queue routing are correctly configured."""


def test_beat_schedule_has_all_spiders():
    from app.celery_app import celery

    schedule = celery.conf.beat_schedule
    expected_spiders = [
        "raw_price", "tpex_price", "raw_chip", "tpex_chip",
        "margin_trading", "tpex_margin", "broker_trading", "major_holders",
    ]
    spider_tasks = [
        v["args"][0] for v in schedule.values()
        if v["task"] == "app.tasks.crawl_task.run_spider"
    ]
    for spider in expected_spiders:
        assert spider in spider_tasks, f"Spider '{spider}' not found in beat_schedule"
    assert len(spider_tasks) == 8, f"Expected 8 spiders, got {len(spider_tasks)}"


def test_beat_schedule_has_alert_checker():
    from app.celery_app import celery

    schedule = celery.conf.beat_schedule
    alert_tasks = [k for k, v in schedule.items() if "alert" in k]
    assert len(alert_tasks) == 1


def test_queue_routes_configured():
    from app.celery_app import celery

    routes = celery.conf.task_routes
    assert routes["app.tasks.crawl_task.run_spider"]["queue"] == "crawl"
    assert routes["app.tasks.alert_checker.check_price_alerts"]["queue"] == "crawl"
    assert routes["run_backtest"]["queue"] == "backtest"


def test_spiders_scheduled_on_weekdays_only():
    """Verify all scheduled tasks run only on weekdays (1-5), not every day (*)."""
    from app.celery_app import celery

    for name, entry in celery.conf.beat_schedule.items():
        schedule = entry["schedule"]
        dow = str(schedule.day_of_week)
        assert dow != "*", f"{name} should be weekdays only, got day_of_week='*'"
