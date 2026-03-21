import logging
from datetime import datetime, timezone

from sqlalchemy import create_engine, select, desc, func
from sqlalchemy.orm import Session, sessionmaker

from app.celery_app import celery
from app.config import settings
from app.models.price_alert import PriceAlert
from app.models.notification import Notification
from app.models.raw_price import RawPrice
from app.models.stock import Stock

logger = logging.getLogger(__name__)

# Sync engine for Celery tasks
sync_engine = create_engine(settings.database_url_sync)
SyncSession = sessionmaker(bind=sync_engine)


@celery.task(name="app.tasks.alert_checker.check_price_alerts")
def check_price_alerts():
    """Check all active price alerts against latest closing prices."""
    with SyncSession() as session:
        # 1. Get all active, non-triggered alerts
        alerts = session.execute(
            select(PriceAlert)
            .where(PriceAlert.is_active == True, PriceAlert.is_triggered == False)
        ).scalars().all()

        if not alerts:
            logger.info("No active alerts to check")
            return

        # 2. Get unique stock_ids
        stock_ids = list(set(a.stock_id for a in alerts))

        # 3. Batch fetch latest prices using window function
        price_subq = (
            select(
                RawPrice.stock_id,
                RawPrice.close_price,
                func.row_number().over(
                    partition_by=RawPrice.stock_id,
                    order_by=desc(RawPrice.date)
                ).label("rn")
            )
            .where(RawPrice.stock_id.in_(stock_ids))
            .subquery()
        )

        price_result = session.execute(
            select(price_subq.c.stock_id, price_subq.c.close_price)
            .where(price_subq.c.rn == 1)
        )
        price_map = {r[0]: r[1] for r in price_result.all()}

        # 4. Get stock names
        stock_result = session.execute(
            select(Stock.stock_id, Stock.stock_name)
            .where(Stock.stock_id.in_(stock_ids))
        )
        name_map = {r[0]: r[1] for r in stock_result.all()}

        # 5. Check each alert
        triggered_count = 0
        for alert in alerts:
            price = price_map.get(alert.stock_id)
            if price is None:
                continue

            triggered = False
            if alert.condition_type == "above" and price >= alert.threshold:
                triggered = True
            elif alert.condition_type == "below" and price <= alert.threshold:
                triggered = True

            if triggered:
                alert.is_triggered = True
                stock_name = name_map.get(alert.stock_id, alert.stock_id)
                condition_text = "突破" if alert.condition_type == "above" else "跌破"

                notification = Notification(
                    user_id=alert.user_id,
                    alert_id=alert.id,
                    title=f"{stock_name} {condition_text} ${alert.threshold}",
                    message=f"目前收盤價 ${price}",
                )
                session.add(notification)
                triggered_count += 1

        session.commit()
        logger.info(f"Alert check complete: {triggered_count} alerts triggered out of {len(alerts)}")
