"""Yahoo TW 5-second tick scraper for intraday data."""

import asyncio
import logging
import random
import re
from datetime import datetime

import aiohttp
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert

from app.database import AsyncSessionLocal
from app.models.intraday_tick import IntradayTick
from app.scrapers.base import (
    TW_TZ,
    get_tracked_stocks,
    parse_args,
    run_loop,
)

logger = logging.getLogger(__name__)

YAHOO_URL = "https://tw.stock.yahoo.com/quote/{stock_id}.TW/time-sales"
TABLE = IntradayTick.__table__

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
}

# Regex to parse tick rows from Yahoo TW HTML.
# Each row has 4 columns: time, price, change (with arrow span), volume.
#   time   — inside <div ...W(72px)">HH:MM:SS</div>
#   price  — inside <span ...Fw(600)...c-trend-{dir}...>N,NNN</span>
#   change — inside <span ...Fw(600)...c-trend-{dir}...>(<span arrow/>)NN</span>
#   volume — inside <span ...Jc(fe)">N,NNN</span>  (no Fw(600))
TICK_RE = re.compile(
    r'W\(72px\)">(\d{2}:\d{2}:\d{2})</div>'           # (1) time
    r'.*?Fw\(600\).*?c-trend-(\w+).*?>([\d,]+)</span>' # (2) trend dir, (3) price
    r'.*?Fw\(600\).*?c-trend-\w+[^>]*>(.*?)</span>'    # (4) change (may contain arrow <span>)
    r'.*?Jc\(fe\)">([\d,]+)</span>',                   # (5) volume
    re.DOTALL,
)

# Sub-pattern to strip inner HTML from change field, leaving only the number.
CHANGE_NUM_RE = re.compile(r'[\d,.]+$')


def _parse_change(raw: str, direction: str) -> float:
    """Extract numeric change value and apply sign based on trend direction."""
    m = CHANGE_NUM_RE.search(raw.strip())
    if not m:
        return 0.0
    val = float(m.group().replace(",", ""))
    if direction == "down":
        return -val
    return val


async def fetch_and_save(
    http_session: aiohttp.ClientSession,
    stock_id: str,
    db_session,
) -> int:
    """Fetch tick data for a single stock and upsert to DB.

    Returns number of rows upserted.
    """
    url = YAHOO_URL.format(stock_id=stock_id)
    async with http_session.get(url, headers=HEADERS) as resp:
        if resp.status != 200:
            logger.warning("HTTP %d for %s", resp.status, stock_id)
            return 0
        html = await resp.text()

    matches = TICK_RE.findall(html)
    if not matches:
        logger.warning("No tick data found for %s", stock_id)
        return 0

    today = datetime.now(TW_TZ).date()
    rows_written = 0
    pk_cols = ["stock_id", "date", "tick_time"]

    for time_str, direction, price_str, change_raw, volume_str in matches:
        price = float(price_str.replace(",", ""))
        change = _parse_change(change_raw, direction)
        volume = int(volume_str.replace(",", ""))

        hour, minute, second = (int(x) for x in time_str.split(":"))
        tick_time = datetime(
            today.year, today.month, today.day,
            hour, minute, second,
            tzinfo=TW_TZ,
        ).time()

        row = {
            "stock_id": stock_id,
            "date": today,
            "tick_time": tick_time,
            "price": price,
            "price_change": change,
            "volume": volume,
        }

        # ON CONFLICT: update price, keep the larger volume
        excluded = insert(TABLE).values(**row).excluded
        stmt = insert(TABLE).values(**row).on_conflict_do_update(
            index_elements=pk_cols,
            set_={
                "price": price,
                "price_change": change,
                "volume": func.greatest(TABLE.c.volume, excluded.volume),
            },
        )
        await db_session.execute(stmt)
        rows_written += 1

    await db_session.commit()
    return rows_written


async def scrape(stock_ids: list[str]) -> None:
    """Scrape tick data for all tracked stocks."""
    semaphore = asyncio.Semaphore(5)
    total_rows = 0

    async with aiohttp.ClientSession() as http_session:

        async def _task(sid: str) -> int:
            async with semaphore:
                # Random delay between stocks to avoid rate limiting
                await asyncio.sleep(random.uniform(0, 0.5))
                async with AsyncSessionLocal() as db_session:
                    return await fetch_and_save(http_session, sid, db_session)

        results = await asyncio.gather(
            *[_task(sid) for sid in stock_ids],
            return_exceptions=True,
        )

    for r in results:
        if isinstance(r, Exception):
            logger.error("fetch error: %s", r)
        else:
            total_rows += r

    logger.info(
        "intraday_tick: scraped %d stocks, wrote %d rows",
        len(stock_ids),
        total_rows,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    args = parse_args(default_interval=15)
    stock_ids_arg = args.stocks.split(",") if args.stocks else None

    async def main():
        ids = await get_tracked_stocks(stock_ids_arg)
        await run_loop(scrape, args.interval, "intraday_tick", ids)

    asyncio.run(main())
