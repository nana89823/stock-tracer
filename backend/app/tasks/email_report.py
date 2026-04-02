"""Celery tasks for daily email report dispatch and delivery."""

import logging
from datetime import date, timedelta
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

# Sync engine for Celery tasks
sync_engine = create_engine(settings.database_url_sync)
SyncSession = sessionmaker(bind=sync_engine)

# Jinja2 template environment
_template_dir = Path(__file__).resolve().parent.parent / "templates"
_jinja_env = Environment(
    loader=FileSystemLoader(str(_template_dir)),
    autoescape=True,
)


@celery.task(name="app.tasks.email_report.dispatch_daily_reports")
def dispatch_daily_reports(target_date: str | None = None):
    """Dispatch individual report tasks for all subscribed users.

    Parameters
    ----------
    target_date : str, optional
        ISO-format date string (e.g. "2026-04-02"). Defaults to the
        previous weekday.
    """
    if target_date is None:
        today = date.today()
        offset = max(1, (today.weekday() - 4) % 7) if today.weekday() == 0 else 1
        target_date = (today - timedelta(days=offset)).isoformat()

    with SyncSession() as session:
        users = (
            session.execute(
                select(User.id).where(
                    User.is_active == True,  # noqa: E712
                    User.email_report_enabled == True,  # noqa: E712
                )
            )
            .scalars()
            .all()
        )

    logger.info(
        "Dispatching daily reports for %d users (date=%s)", len(users), target_date
    )
    for user_id in users:
        send_user_report.delay(user_id=user_id, target_date=target_date)


@celery.task(
    name="app.tasks.email_report.send_user_report",
    bind=True,
    max_retries=3,
)
def send_user_report(self, user_id: int, target_date: str | None = None):
    """Build and send a daily report email for a single user.

    Parameters
    ----------
    user_id : int
        The user's primary key.
    target_date : str, optional
        ISO-format date string. Defaults to yesterday.
    """
    if target_date is None:
        d = date.today() - timedelta(days=1)
    else:
        d = date.fromisoformat(target_date)

    try:
        with SyncSession() as session:
            user = session.execute(
                select(User).where(User.id == user_id)
            ).scalar_one_or_none()

            if user is None:
                logger.warning("User %d not found, skipping report", user_id)
                return

            if not user.email:
                logger.warning("User %d has no email, skipping report", user_id)
                return

            # Gather report data
            market = get_market_summary(session, target_date=d)
            prices = get_watchlist_prices(session, user_id=user_id, target_date=d)
            chips = get_watchlist_chips(session, user_id=user_id, target_date=d)
            margin = get_watchlist_margin(session, user_id=user_id, target_date=d)
            holders = get_watchlist_holders(session, user_id=user_id, target_date=d)
            alerts = get_user_alerts(session, user_id=user_id, target_date=d)

        # Render templates
        report_date = d.strftime("%Y/%m/%d")
        context = {
            "report_date": report_date,
            "market": market,
            "prices": prices,
            "chips": chips,
            "margin": margin,
            "holders": holders,
            "alerts": alerts,
        }

        html_body = _jinja_env.get_template("daily_report.html").render(**context)
        text_body = _jinja_env.get_template("daily_report.txt").render(**context)

        subject = f"Stock Tracer 每日報告 — {report_date}"
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
        logger.info("Daily report sent to user %d (%s)", user_id, user.email)

    except Exception as exc:
        logger.error("Failed to send report to user %d: %s", user_id, exc)
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))
