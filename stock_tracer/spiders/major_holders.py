"""Spider for scraping TDCC shareholder distribution data.

Source: https://opendata.tdcc.com.tw/getOD.ashx?id=1-5

持股分級說明:
1: 1-999股
2: 1,000-5,000股
3: 5,001-10,000股
4: 10,001-15,000股
5: 15,001-20,000股
6: 20,001-30,000股
7: 30,001-40,000股
8: 40,001-50,000股
9: 50,001-100,000股
10: 100,001-200,000股
11: 200,001-400,000股 (200-400張)
12: 400,001-600,000股 (400-600張) <- 大戶起始
13: 600,001-800,000股
14: 800,001-1,000,000股
15: 1,000,001股以上
16: (部分股票有額外級距)
17: (部分股票有額外級距)

400張以上大戶 = 級距 >= 12
"""

import csv
from io import StringIO

import scrapy

from stock_tracer.items import MajorHoldersItem


class MajorHoldersSpider(scrapy.Spider):
    """Spider to scrape shareholder distribution from TDCC."""

    name = "major_holders"
    start_urls = [
        "https://opendata.tdcc.com.tw/getOD.ashx?id=1-5"
    ]

    def parse(self, response):
        """Parse CSV response and yield MajorHoldersItem.

        CSV columns:
        0: 資料日期 (YYYYMMDD)
        1: 證券代號
        2: 持股/單位數分級
        3: 人數
        4: 股數/單位數
        5: 占集保庫存數比例 (%)
        """
        text = response.text
        if not text.strip():
            return

        reader = csv.reader(StringIO(text))

        # Skip header row
        try:
            next(reader)
        except StopIteration:
            return

        for row in reader:
            if len(row) < 6:
                continue

            yield MajorHoldersItem(
                date=self._convert_date(row[0]),
                stock_id=row[1].strip(),
                holding_level=self._parse_int(row[2]),
                holder_count=self._parse_int(row[3]),
                share_count=self._parse_int(row[4]),
                holding_ratio=self._parse_float(row[5]),
            )

    def _convert_date(self, date_str: str) -> str:
        """Convert date string (20260123) to ISO format (2026-01-23)."""
        date_str = date_str.strip()
        if len(date_str) == 8:
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        return date_str

    def _parse_int(self, value: str) -> int:
        """Parse integer string."""
        try:
            return int(value.replace(",", "").strip())
        except (ValueError, AttributeError):
            return 0

    def _parse_float(self, value: str) -> float:
        """Parse float string."""
        try:
            return float(value.strip())
        except (ValueError, AttributeError):
            return 0.0
