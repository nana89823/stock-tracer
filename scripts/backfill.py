#!/usr/bin/env python3
"""Backfill script to run spiders over a date range.

Usage:
    python scripts/backfill.py --spider raw_price --start 20260101 --end 20260131
    python scripts/backfill.py --spider raw_chip --start 20260301 --end 20260310
    python scripts/backfill.py --spider all --start 20260301 --end 20260305

Options:
    --spider    Spider name or 'all' to run all spiders
    --start     Start date in YYYYMMDD format
    --end       End date in YYYYMMDD format (inclusive)
    --skip-weekends  Skip Saturday and Sunday (default: True)
    --delay     Delay in seconds between each spider run (default: 5)
"""

import argparse
import subprocess
from datetime import datetime, timedelta

ALL_SPIDERS = [
    "raw_price",
    "raw_chip",
    "tpex_price",
    "tpex_chip",
    "margin_trading",
    "tpex_margin",
    "broker_trading",
    # major_holders excluded: TDCC is weekly, not daily
]


def date_range(start: str, end: str, skip_weekends: bool = True):
    """Generate dates from start to end (inclusive)."""
    start_dt = datetime.strptime(start, "%Y%m%d")
    end_dt = datetime.strptime(end, "%Y%m%d")
    current = start_dt
    while current <= end_dt:
        if skip_weekends and current.weekday() >= 5:  # 5=Sat, 6=Sun
            current += timedelta(days=1)
            continue
        yield current.strftime("%Y%m%d")
        current += timedelta(days=1)


def run_spider(spider_name: str, date_str: str, delay: int):
    """Run a single spider for a specific date."""
    cmd = [
        "scrapy",
        "crawl",
        spider_name,
        "-a",
        f"date={date_str}",
    ]
    print(f"  [{date_str}] scrapy crawl {spider_name} -a date={date_str}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  [{date_str}] ERROR: {spider_name} failed")
        stderr_lines = result.stderr.strip().split("\n")
        # Print last 3 lines of error
        for line in stderr_lines[-3:]:
            print(f"    {line}")
        return False
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Backfill spider data over a date range"
    )
    parser.add_argument("--spider", required=True, help="Spider name or 'all'")
    parser.add_argument("--start", required=True, help="Start date (YYYYMMDD)")
    parser.add_argument("--end", required=True, help="End date (YYYYMMDD)")
    parser.add_argument(
        "--skip-weekends", action="store_true", default=True, help="Skip weekends"
    )
    parser.add_argument(
        "--no-skip-weekends", action="store_true", help="Include weekends"
    )
    parser.add_argument(
        "--delay", type=int, default=5, help="Delay between runs (seconds)"
    )
    args = parser.parse_args()

    skip_weekends = not args.no_skip_weekends

    if args.spider == "all":
        spiders = ALL_SPIDERS
    else:
        spiders = [s.strip() for s in args.spider.split(",")]

    dates = list(date_range(args.start, args.end, skip_weekends))
    print(f"Backfill: {len(spiders)} spider(s) x {len(dates)} date(s)")
    print(f"Spiders: {', '.join(spiders)}")
    print(f"Date range: {args.start} ~ {args.end} (skip weekends: {skip_weekends})")
    print()

    success = 0
    fail = 0
    import time

    for spider_name in spiders:
        print(f"=== {spider_name} ===")
        for date_str in dates:
            ok = run_spider(spider_name, date_str, args.delay)
            if ok:
                success += 1
            else:
                fail += 1
            time.sleep(args.delay)
        print()

    print(f"Done! Success: {success}, Failed: {fail}")


if __name__ == "__main__":
    main()
