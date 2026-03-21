"""Shared utilities for intraday scrapers."""

import argparse
import asyncio
import logging
import signal
from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.stock import Stock

logger = logging.getLogger(__name__)

TW_TZ = ZoneInfo("Asia/Taipei")
MARKET_OPEN = dtime(9, 0)
MARKET_CLOSE = dtime(13, 30)


def is_trading_hours() -> bool:
    """Check if current time is within Taiwan stock market trading hours."""
    now = datetime.now(TW_TZ)
    return now.weekday() < 5 and MARKET_OPEN <= now.time() <= MARKET_CLOSE


async def get_tracked_stocks(stock_ids: list[str] | None) -> list[str]:
    """Return provided stock IDs or load all from DB."""
    if stock_ids:
        return stock_ids
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Stock.stock_id))
        ids = [row[0] for row in result.fetchall()]
    logger.info("Loaded %d stocks from DB", len(ids))
    return ids


async def run_loop(
    scrape_fn,
    interval: int,
    name: str,
    stock_ids: list[str],
) -> None:
    """Main event loop: call scrape_fn periodically during trading hours."""
    running = True

    def _shutdown(sig, frame):
        nonlocal running
        logger.info("%s received signal %s, shutting down …", name, sig)
        running = False

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    logger.info("%s started — tracking %d stocks, interval=%ds", name, len(stock_ids), interval)

    while running:
        if not is_trading_hours():
            await asyncio.sleep(60)
            continue
        try:
            await scrape_fn(stock_ids)
        except Exception:
            logger.error("%s scrape error", name, exc_info=True)
        await asyncio.sleep(interval)

    logger.info("%s stopped", name)


def parse_args(default_interval: int) -> argparse.Namespace:
    """Parse CLI arguments for intraday scrapers."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stocks",
        type=str,
        default=None,
        help="Comma-separated stock IDs, e.g. 2330,2317",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Load all stocks from DB",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=default_interval,
        help=f"Polling interval in seconds (default: {default_interval})",
    )
    args = parser.parse_args()
    return args
