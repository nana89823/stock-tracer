"""Tests for email_report Celery tasks."""

from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(user_id=1, email="user@test.com", is_active=True, report=True):
    user = MagicMock()
    user.id = user_id
    user.email = email
    user.is_active = is_active
    user.email_report_enabled = report
    return user


# ---------------------------------------------------------------------------
# dispatch_daily_reports
# ---------------------------------------------------------------------------


class TestDispatchDailyReports:
    @patch("app.tasks.email_report.send_user_report")
    @patch("app.tasks.email_report.SyncSession")
    def test_dispatches_for_enabled_users(self, mock_session_cls, mock_send):
        """Should call send_user_report.delay for each enabled user."""
        mock_session = MagicMock()
        mock_session_cls.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_session.execute.return_value.scalars.return_value.all.return_value = [
            1,
            2,
            3,
        ]

        from app.tasks.email_report import dispatch_daily_reports

        dispatch_daily_reports("2026-04-02")

        assert mock_send.delay.call_count == 3
        mock_send.delay.assert_any_call(user_id=1, target_date="2026-04-02")
        mock_send.delay.assert_any_call(user_id=2, target_date="2026-04-02")
        mock_send.delay.assert_any_call(user_id=3, target_date="2026-04-02")

    @patch("app.tasks.email_report.send_user_report")
    @patch("app.tasks.email_report.SyncSession")
    def test_no_users(self, mock_session_cls, mock_send):
        """Should not call send_user_report when no users are subscribed."""
        mock_session = MagicMock()
        mock_session_cls.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_session.execute.return_value.scalars.return_value.all.return_value = []

        from app.tasks.email_report import dispatch_daily_reports

        dispatch_daily_reports("2026-04-02")

        mock_send.delay.assert_not_called()


# ---------------------------------------------------------------------------
# send_user_report
# ---------------------------------------------------------------------------


class TestSendUserReport:
    @patch("app.tasks.email_report.send_email")
    @patch("app.tasks.email_report.build_email")
    @patch("app.tasks.email_report.get_user_alerts", return_value=[])
    @patch("app.tasks.email_report.get_watchlist_holders", return_value=[])
    @patch("app.tasks.email_report.get_watchlist_margin", return_value=[])
    @patch("app.tasks.email_report.get_watchlist_chips", return_value=[])
    @patch("app.tasks.email_report.get_watchlist_prices", return_value=[])
    @patch(
        "app.tasks.email_report.get_market_summary",
        return_value={
            "up_count": 100,
            "down_count": 50,
            "flat_count": 30,
            "total_volume": 1000000,
            "foreign_total": 5000,
            "trust_total": -2000,
            "dealer_total": 1000,
            "inst_total": 4000,
        },
    )
    @patch("app.tasks.email_report.SyncSession")
    def test_sends_email_for_user(
        self,
        mock_session_cls,
        mock_market,
        mock_prices,
        mock_chips,
        mock_margin,
        mock_holders,
        mock_alerts,
        mock_build,
        mock_send,
    ):
        """Should query data, render templates, and send email."""
        user = _make_user()
        mock_session = MagicMock()
        mock_session_cls.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_session.execute.return_value.scalar_one_or_none.return_value = user

        mock_msg = MagicMock()
        mock_build.return_value = mock_msg

        from app.tasks.email_report import send_user_report

        send_user_report(user_id=1, target_date="2026-04-02")

        mock_build.assert_called_once()
        build_kwargs = mock_build.call_args
        assert build_kwargs[1]["to_email"] == "user@test.com"
        assert "2026/04/02" in build_kwargs[1]["subject"]

        mock_send.assert_called_once()

    @patch("app.tasks.email_report.send_email")
    @patch("app.tasks.email_report.SyncSession")
    def test_skips_missing_user(self, mock_session_cls, mock_send):
        """Should not send email if user is not found."""
        mock_session = MagicMock()
        mock_session_cls.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_session.execute.return_value.scalar_one_or_none.return_value = None

        from app.tasks.email_report import send_user_report

        send_user_report(user_id=999, target_date="2026-04-02")

        mock_send.assert_not_called()
