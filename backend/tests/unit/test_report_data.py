"""Tests for report_data — daily report data queries."""

from datetime import date
from unittest.mock import MagicMock

from app.services.report_data import (
    get_watchlist_prices,
    get_market_summary,
    get_user_alerts,
)


class TestGetWatchlistPrices:
    def test_returns_empty_list_for_no_watchlist(self):
        session = MagicMock()
        session.execute.return_value.all.return_value = []
        result = get_watchlist_prices(
            session, user_id=1, target_date=date(2026, 4, 1)
        )
        assert result == []


class TestGetMarketSummary:
    def test_returns_dict_with_required_keys(self):
        session = MagicMock()
        # Mock aggregate query result
        mock_price_row = MagicMock()
        mock_price_row.up_count = 100
        mock_price_row.down_count = 50
        mock_price_row.flat_count = 30
        mock_price_row.total_volume = 1000000000

        mock_chip_row = MagicMock()
        mock_chip_row.foreign_total = 5000000
        mock_chip_row.trust_total = -2000000
        mock_chip_row.dealer_total = 1000000
        mock_chip_row.inst_total = 4000000

        session.execute.return_value.one.side_effect = [
            mock_price_row,
            mock_chip_row,
        ]
        result = get_market_summary(session, target_date=date(2026, 4, 1))
        assert "up_count" in result
        assert "down_count" in result
        assert "flat_count" in result
        assert "total_volume" in result
        assert "foreign_total" in result
        assert "trust_total" in result
        assert result["up_count"] == 100
        assert result["foreign_total"] == 5000000


class TestGetUserAlerts:
    def test_returns_empty_list_when_no_alerts(self):
        session = MagicMock()
        session.execute.return_value.all.return_value = []
        result = get_user_alerts(
            session, user_id=1, target_date=date(2026, 4, 1)
        )
        assert result == []
