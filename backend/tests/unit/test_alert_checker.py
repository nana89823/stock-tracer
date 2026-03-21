"""Unit tests for the alert_checker Celery task.

Uses a sync SQLite engine to test check_price_alerts() with real SQL queries,
patching SyncSession in the alert_checker module to use the test database.
"""

from datetime import date, datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.base import Base
from app.models.notification import Notification
from app.models.price_alert import PriceAlert
from app.models.raw_price import RawPrice
from app.models.stock import Stock
from app.models.user import User


# Sync SQLite test engine
_test_engine = create_engine("sqlite:///:memory:")
_TestSyncSession = sessionmaker(bind=_test_engine)


@pytest.fixture(autouse=True)
def setup_sync_db():
    """Create only the tables needed for alert_checker tests.

    We cannot use Base.metadata.create_all because the Strategy model uses
    JSONB which is not supported by SQLite.
    """
    tables = [
        User.__table__,
        Stock.__table__,
        RawPrice.__table__,
        PriceAlert.__table__,
        Notification.__table__,
    ]
    Base.metadata.create_all(_test_engine, tables=tables)
    yield
    Base.metadata.drop_all(_test_engine, tables=tables)


@pytest.fixture
def sync_session():
    """Provide a sync test session."""
    with _TestSyncSession() as session:
        yield session


def _seed_user(session: Session, user_id: int = 1) -> User:
    user = User(
        id=user_id,
        username=f"user{user_id}",
        email=f"user{user_id}@test.com",
        hashed_password="fakehash",
    )
    session.add(user)
    session.flush()
    return user


def _seed_stock(session: Session, stock_id: str, stock_name: str) -> Stock:
    stock = Stock(stock_id=stock_id, stock_name=stock_name, market_type="twse")
    session.add(stock)
    session.flush()
    return stock


def _seed_price(
    session: Session, stock_id: str, close_price: float, d: date | None = None
) -> RawPrice:
    d = d or date(2026, 3, 14)
    price = RawPrice(
        date=d,
        stock_id=stock_id,
        stock_name="",
        trade_volume=1000,
        trade_value=1000000,
        open_price=close_price,
        high_price=close_price,
        low_price=close_price,
        close_price=close_price,
        price_change=0.0,
        transaction_count=100,
    )
    session.add(price)
    session.flush()
    return price


def _seed_alert(
    session: Session,
    user_id: int,
    stock_id: str,
    condition_type: str,
    threshold: float,
    is_active: bool = True,
    is_triggered: bool = False,
) -> PriceAlert:
    alert = PriceAlert(
        user_id=user_id,
        stock_id=stock_id,
        condition_type=condition_type,
        threshold=threshold,
        is_active=is_active,
        is_triggered=is_triggered,
    )
    session.add(alert)
    session.flush()
    return alert


def _run_check():
    """Import and run the task function with patched SyncSession."""
    with patch("app.tasks.alert_checker.SyncSession", _TestSyncSession):
        from app.tasks.alert_checker import check_price_alerts
        check_price_alerts()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCheckPriceAlerts:
    """Tests for the check_price_alerts Celery task."""

    def test_no_active_alerts(self, sync_session):
        """No active alerts -> no notifications created, no errors."""
        _run_check()

        notifications = sync_session.query(Notification).all()
        assert notifications == []

    def test_above_condition_triggers(self, sync_session):
        """Alert with condition 'above' triggers when price >= threshold."""
        _seed_user(sync_session)
        _seed_stock(sync_session, "2330", "台積電")
        _seed_price(sync_session, "2330", 850.0)
        _seed_alert(sync_session, 1, "2330", "above", 800.0)
        sync_session.commit()

        _run_check()

        sync_session.expire_all()
        notifications = sync_session.query(Notification).all()
        assert len(notifications) == 1
        assert "台積電" in notifications[0].title
        assert "突破" in notifications[0].title
        assert "$800.0" in notifications[0].title
        assert "$850.0" in notifications[0].message

        # Alert should be marked as triggered
        alert = sync_session.query(PriceAlert).first()
        assert alert.is_triggered is True

    def test_above_condition_exact_threshold(self, sync_session):
        """Alert with condition 'above' triggers when price == threshold (>=)."""
        _seed_user(sync_session)
        _seed_stock(sync_session, "2330", "台積電")
        _seed_price(sync_session, "2330", 800.0)
        _seed_alert(sync_session, 1, "2330", "above", 800.0)
        sync_session.commit()

        _run_check()

        sync_session.expire_all()
        notifications = sync_session.query(Notification).all()
        assert len(notifications) == 1

    def test_below_condition_triggers(self, sync_session):
        """Alert with condition 'below' triggers when price <= threshold."""
        _seed_user(sync_session)
        _seed_stock(sync_session, "2317", "鴻海")
        _seed_price(sync_session, "2317", 90.0)
        _seed_alert(sync_session, 1, "2317", "below", 100.0)
        sync_session.commit()

        _run_check()

        sync_session.expire_all()
        notifications = sync_session.query(Notification).all()
        assert len(notifications) == 1
        assert "鴻海" in notifications[0].title
        assert "跌破" in notifications[0].title
        assert "$100.0" in notifications[0].title
        assert "$90.0" in notifications[0].message

    def test_below_condition_exact_threshold(self, sync_session):
        """Alert with condition 'below' triggers when price == threshold (<=)."""
        _seed_user(sync_session)
        _seed_stock(sync_session, "2317", "鴻海")
        _seed_price(sync_session, "2317", 100.0)
        _seed_alert(sync_session, 1, "2317", "below", 100.0)
        sync_session.commit()

        _run_check()

        sync_session.expire_all()
        notifications = sync_session.query(Notification).all()
        assert len(notifications) == 1

    def test_above_condition_not_met(self, sync_session):
        """Alert with condition 'above' does NOT trigger when price < threshold."""
        _seed_user(sync_session)
        _seed_stock(sync_session, "2330", "台積電")
        _seed_price(sync_session, "2330", 790.0)
        _seed_alert(sync_session, 1, "2330", "above", 800.0)
        sync_session.commit()

        _run_check()

        sync_session.expire_all()
        notifications = sync_session.query(Notification).all()
        assert notifications == []

        alert = sync_session.query(PriceAlert).first()
        assert alert.is_triggered is False

    def test_below_condition_not_met(self, sync_session):
        """Alert with condition 'below' does NOT trigger when price > threshold."""
        _seed_user(sync_session)
        _seed_stock(sync_session, "2317", "鴻海")
        _seed_price(sync_session, "2317", 110.0)
        _seed_alert(sync_session, 1, "2317", "below", 100.0)
        sync_session.commit()

        _run_check()

        sync_session.expire_all()
        notifications = sync_session.query(Notification).all()
        assert notifications == []

    def test_already_triggered_alert_skipped(self, sync_session):
        """Alerts that were already triggered are not checked again."""
        _seed_user(sync_session)
        _seed_stock(sync_session, "2330", "台積電")
        _seed_price(sync_session, "2330", 900.0)
        _seed_alert(sync_session, 1, "2330", "above", 800.0, is_triggered=True)
        sync_session.commit()

        _run_check()

        sync_session.expire_all()
        notifications = sync_session.query(Notification).all()
        assert notifications == []

    def test_inactive_alert_skipped(self, sync_session):
        """Inactive alerts are not checked."""
        _seed_user(sync_session)
        _seed_stock(sync_session, "2330", "台積電")
        _seed_price(sync_session, "2330", 900.0)
        _seed_alert(sync_session, 1, "2330", "above", 800.0, is_active=False)
        sync_session.commit()

        _run_check()

        sync_session.expire_all()
        notifications = sync_session.query(Notification).all()
        assert notifications == []

    def test_multiple_alerts_only_matching_trigger(self, sync_session):
        """Multiple alerts for different stocks; only matching ones trigger."""
        _seed_user(sync_session)
        _seed_stock(sync_session, "2330", "台積電")
        _seed_stock(sync_session, "2317", "鴻海")
        _seed_stock(sync_session, "2454", "聯發科")
        _seed_price(sync_session, "2330", 850.0)  # above 800 -> triggers
        _seed_price(sync_session, "2317", 110.0)  # below 100 -> NOT triggered
        _seed_price(sync_session, "2454", 500.0)  # below 600 -> triggers
        _seed_alert(sync_session, 1, "2330", "above", 800.0)
        _seed_alert(sync_session, 1, "2317", "below", 100.0)
        _seed_alert(sync_session, 1, "2454", "below", 600.0)
        sync_session.commit()

        _run_check()

        sync_session.expire_all()
        notifications = sync_session.query(Notification).all()
        assert len(notifications) == 2

        triggered_titles = {n.title for n in notifications}
        assert any("台積電" in t for t in triggered_titles)
        assert any("聯發科" in t for t in triggered_titles)
        assert not any("鴻海" in t for t in triggered_titles)

    def test_stock_with_no_price_data(self, sync_session):
        """Alert for a stock with no price records -> not triggered."""
        _seed_user(sync_session)
        _seed_stock(sync_session, "2330", "台積電")
        # No price record inserted
        _seed_alert(sync_session, 1, "2330", "above", 800.0)
        sync_session.commit()

        _run_check()

        sync_session.expire_all()
        notifications = sync_session.query(Notification).all()
        assert notifications == []

        alert = sync_session.query(PriceAlert).first()
        assert alert.is_triggered is False

    def test_uses_latest_price(self, sync_session):
        """When multiple price records exist, the latest (by date) is used."""
        _seed_user(sync_session)
        _seed_stock(sync_session, "2330", "台積電")
        # Older price: above threshold
        _seed_price(sync_session, "2330", 900.0, d=date(2026, 3, 10))
        # Latest price: below threshold
        _seed_price(sync_session, "2330", 750.0, d=date(2026, 3, 14))
        _seed_alert(sync_session, 1, "2330", "above", 800.0)
        sync_session.commit()

        _run_check()

        sync_session.expire_all()
        notifications = sync_session.query(Notification).all()
        # Should use 750.0 (latest), which is below 800 -> NOT triggered
        assert notifications == []

    def test_notification_fields(self, sync_session):
        """Verify notification has correct user_id, alert_id, and content."""
        user = _seed_user(sync_session)
        _seed_stock(sync_session, "2330", "台積電")
        _seed_price(sync_session, "2330", 860.0)
        alert = _seed_alert(sync_session, user.id, "2330", "above", 850.0)
        sync_session.commit()

        _run_check()

        sync_session.expire_all()
        notification = sync_session.query(Notification).first()
        assert notification is not None
        assert notification.user_id == user.id
        assert notification.alert_id == alert.id
        assert notification.title == "台積電 突破 $850.0"
        assert notification.message == "目前收盤價 $860.0"

    def test_stock_name_fallback_to_stock_id(self, sync_session):
        """When stock name is not found, stock_id is used as fallback."""
        _seed_user(sync_session)
        # Insert price but no stock record -> name_map won't have this stock_id
        _seed_price(sync_session, "9999", 100.0)
        # We need the alert to reference a stock_id. Since SQLite doesn't enforce
        # FK by default, we can create an alert without a stocks row.
        alert = PriceAlert(
            user_id=1,
            stock_id="9999",
            condition_type="above",
            threshold=50.0,
            is_active=True,
            is_triggered=False,
        )
        sync_session.add(alert)
        # Also need a RawPrice without FK. SQLite allows this.
        sync_session.commit()

        _run_check()

        sync_session.expire_all()
        notification = sync_session.query(Notification).first()
        assert notification is not None
        # Falls back to stock_id "9999"
        assert "9999" in notification.title

    def test_multiple_users_separate_notifications(self, sync_session):
        """Different users' alerts create separate notifications."""
        _seed_user(sync_session, user_id=1)
        _seed_user(sync_session, user_id=2)
        _seed_stock(sync_session, "2330", "台積電")
        _seed_price(sync_session, "2330", 900.0)
        _seed_alert(sync_session, 1, "2330", "above", 800.0)
        _seed_alert(sync_session, 2, "2330", "above", 850.0)
        sync_session.commit()

        _run_check()

        sync_session.expire_all()
        notifications = sync_session.query(Notification).all()
        assert len(notifications) == 2
        user_ids = {n.user_id for n in notifications}
        assert user_ids == {1, 2}
