"""Spider for scraping TWSE margin trading (融資融券) data.

Source: https://www.twse.com.tw/exchangeReport/MI_MARGN?response=open_data&selectType=ALL
"""

import csv
from datetime import datetime
from io import StringIO

import scrapy

from stock_tracer.items import MarginTradingItem


class MarginTradingSpider(scrapy.Spider):
    """Spider to scrape margin trading balances from TWSE."""

    name = "margin_trading"
    market_type = "twse"

    def __init__(self, date=None, *args, **kwargs):
        """Initialize spider with optional date argument.

        Args:
            date: Date in YYYYMMDD format. Defaults to today.
        """
        super().__init__(*args, **kwargs)
        if date:
            self.target_date = date
        else:
            self.target_date = datetime.now().strftime("%Y%m%d")

    def start_requests(self):
        url = f"https://www.twse.com.tw/exchangeReport/MI_MARGN?response=open_data&selectType=ALL&date={self.target_date}"
        yield scrapy.Request(url, callback=self.parse)

    def parse(self, response):
        """Parse CSV response and yield MarginTradingItem.

        CSV columns:
        0: 股票代號
        1: 股票名稱
        2: 融資買進
        3: 融資賣出
        4: 融資現金償還
        5: 融資前日餘額
        6: 融資今日餘額
        7: 融資限額
        8: 融券買進
        9: 融券賣出
        10: 融券現券償還
        11: 融券前日餘額
        12: 融券今日餘額
        13: 融券限額
        14: 資券互抵
        15: 註記
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

        # Use date from target_date parameter
        iso_date = (
            f"{self.target_date[:4]}-{self.target_date[4:6]}-{self.target_date[6:8]}"
        )

        for row in reader:
            if len(row) < 16:
                continue

            yield MarginTradingItem(
                date=iso_date,
                stock_id=row[0].strip(),
                stock_name=row[1].strip(),
                margin_buy=self._parse_number(row[2]),
                margin_sell=self._parse_number(row[3]),
                margin_cash_repay=self._parse_number(row[4]),
                margin_balance_prev=self._parse_number(row[5]),
                margin_balance=self._parse_number(row[6]),
                margin_limit=self._parse_number(row[7]),
                short_buy=self._parse_number(row[8]),
                short_sell=self._parse_number(row[9]),
                short_cash_repay=self._parse_number(row[10]),
                short_balance_prev=self._parse_number(row[11]),
                short_balance=self._parse_number(row[12]),
                short_limit=self._parse_number(row[13]),
                offset=self._parse_number(row[14]),
                note=row[15].strip(),
            )

    def _parse_number(self, value: str) -> int:
        """Parse number string, removing commas and handling empty values."""
        try:
            cleaned = value.replace(",", "").strip()
            if not cleaned:
                return 0
            return int(cleaned)
        except (ValueError, AttributeError):
            return 0
