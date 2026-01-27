"""Spider for scraping TWSE daily stock prices.

Source: https://www.twse.com.tw/exchangeReport/STOCK_DAY_ALL?response=open_data
"""

import csv
from io import StringIO

import scrapy

from stock_tracer.items import RawPriceItem


class RawPriceSpider(scrapy.Spider):
    """Spider to scrape daily stock prices from TWSE."""

    name = "raw_price"
    start_urls = [
        "https://www.twse.com.tw/exchangeReport/STOCK_DAY_ALL?response=open_data"
    ]

    def parse(self, response):
        """Parse CSV response and yield RawPriceItem.

        CSV columns:
        0: 日期 (ROC date format: 1150126)
        1: 證券代號
        2: 證券名稱
        3: 成交股數
        4: 成交金額
        5: 開盤價
        6: 最高價
        7: 最低價
        8: 收盤價
        9: 漲跌價差
        10: 成交筆數
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
            if len(row) < 11:
                continue

            yield RawPriceItem(
                date=self._convert_roc_date(row[0]),
                stock_id=row[1].strip(),
                stock_name=row[2].strip(),
                trade_volume=self._parse_number(row[3]),
                trade_value=self._parse_number(row[4]),
                open_price=self._parse_float(row[5]),
                high_price=self._parse_float(row[6]),
                low_price=self._parse_float(row[7]),
                close_price=self._parse_float(row[8]),
                price_change=self._parse_float(row[9]),
                transaction_count=self._parse_number(row[10]),
            )

    def _convert_roc_date(self, roc_date: str) -> str:
        """Convert ROC date (1150126) to ISO format (2026-01-26).

        ROC year = Western year - 1911
        """
        roc_date = roc_date.strip()
        if len(roc_date) == 7:
            year = int(roc_date[:3]) + 1911
            month = roc_date[3:5]
            day = roc_date[5:7]
            return f"{year}-{month}-{day}"
        return roc_date

    def _parse_number(self, value: str) -> int:
        """Parse number string, removing commas and quotes."""
        try:
            return int(value.replace(",", "").replace('"', "").strip())
        except (ValueError, AttributeError):
            return 0

    def _parse_float(self, value: str) -> float:
        """Parse float string, handling +/- prefix."""
        try:
            clean_value = value.replace(",", "").replace('"', "").strip()
            return float(clean_value)
        except (ValueError, AttributeError):
            return 0.0
