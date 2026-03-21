"""Yahoo Finance 1-minute candle scraper for intraday data."""

import asyncio
import logging
from datetime import datetime

import httpx
from sqlalchemy.dialects.postgresql import insert

from app.database import AsyncSessionLocal
from app.models.intraday_minute import IntradayMinute
from app.scrapers.base import (
    TW_TZ,
    get_tracked_stocks,
    parse_args,
    run_loop,
)

logger = logging.getLogger(__name__)

YAHOO_CHART_URL = (
    "https://query2.finance.yahoo.com/v8/finance/chart/"
    "{stock_id}.TW?interval=1m&range=1d&crumb={crumb}"
)
TABLE = IntradayMinute.__table__

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
}


async def _get_crumb(client: httpx.AsyncClient, retries: int = 3) -> str:
    """Obtain a Yahoo Finance crumb token (requires cookie from fc.yahoo.com).

    Retries with exponential backoff on 429 responses.
    """
    # Step 1: hit a Yahoo endpoint to obtain consent cookies
    await client.get("https://fc.yahoo.com/", follow_redirects=True)
    # Step 2: fetch crumb with retry
    for attempt in range(retries):
        resp = await client.get(
            "https://query2.finance.yahoo.com/v1/test/getcrumb",
            follow_redirects=True,
        )
        if resp.status_code == 200:
            return resp.text.strip()
        if resp.status_code == 429 and attempt < retries - 1:
            wait = 2 ** (attempt + 1)
            logger.warning("Crumb 429, retrying in %ds (attempt %d/%d)", wait, attempt + 1, retries)
            await asyncio.sleep(wait)
            continue
        resp.raise_for_status()
    return ""  # unreachable


async def fetch_and_save(
    client: httpx.AsyncClient,
    stock_id: str,
    crumb: str,
    db_session,
) -> int:
    """Fetch 1-minute candle data for a single stock and upsert to DB.

    Returns number of rows upserted.
    """
    url = YAHOO_CHART_URL.format(stock_id=stock_id, crumb=crumb)
    resp = await client.get(url)
    if resp.status_code != 200:
        logger.warning("HTTP %d for %s", resp.status_code, stock_id)
        return 0
    data = resp.json()

    results = data.get("chart", {}).get("result")
    if not results:
        logger.warning("No chart result for %s", stock_id)
        return 0

    result = results[0]
    timestamps = result.get("timestamp") or []
    quote = (result.get("indicators", {}).get("quote") or [{}])[0]
    opens = quote.get("open") or []
    highs = quote.get("high") or []
    lows = quote.get("low") or []
    closes = quote.get("close") or []
    volumes = quote.get("volume") or []

    rows_written = 0
    pk_cols = ["stock_id", "date", "minute_time"]
    non_pk_cols = ["open_price", "high_price", "low_price", "close_price", "volume"]

    for i, ts in enumerate(timestamps):
        o = opens[i] if i < len(opens) else None
        h = highs[i] if i < len(highs) else None
        lo = lows[i] if i < len(lows) else None
        c = closes[i] if i < len(closes) else None
        v = volumes[i] if i < len(volumes) else None

        # Skip data points with None values
        if any(x is None for x in (o, h, lo, c, v)):
            continue

        dt = datetime.fromtimestamp(ts, tz=TW_TZ)
        row = {
            "stock_id": stock_id,
            "date": dt.date(),
            "minute_time": dt.time().replace(microsecond=0),
            "open_price": float(o),
            "high_price": float(h),
            "low_price": float(lo),
            "close_price": float(c),
            "volume": int(v),
        }

        stmt = insert(TABLE).values(**row).on_conflict_do_update(
            index_elements=pk_cols,
            set_={col: row[col] for col in non_pk_cols},
        )
        await db_session.execute(stmt)
        rows_written += 1

    await db_session.commit()
    return rows_written


async def scrape(stock_ids: list[str]) -> None:
    """Scrape 1-minute candles for all tracked stocks."""
    semaphore = asyncio.Semaphore(10)
    total_rows = 0

    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True) as client:
        crumb = await _get_crumb(client)
        logger.info("Obtained Yahoo crumb")

        async def _task(sid: str) -> int:
            async with semaphore:
                async with AsyncSessionLocal() as db_session:
                    return await fetch_and_save(client, sid, crumb, db_session)

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
        "intraday_minute: scraped %d stocks, wrote %d rows",
        len(stock_ids),
        total_rows,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    args = parse_args(default_interval=60)
    stock_ids_arg = args.stocks.split(",") if args.stocks else None

    async def main():
        ids = await get_tracked_stocks(stock_ids_arg)
        await run_loop(scrape, args.interval, "intraday_minute", ids)

    asyncio.run(main())
