"""Spider for scraping TPEX (OTC) margin trading (融資融券) data.

Source: https://www.tpex.org.tw/web/stock/margin_trading/margin_balance/margin_bal_result.php?l=zh-tw&o=data
"""

import csv
from io import StringIO

import scrapy

from stock_tracer.items import MarginTradingItem


class TpexMarginSpider(scrapy.Spider):
    """Spider to scrape margin trading balances from TPEX (OTC market)."""

    name = "tpex_margin"
    market_type = "tpex"
    start_urls = [
        "https://www.tpex.org.tw/web/stock/margin_trading/margin_balance/margin_bal_result.php?l=zh-tw&o=data"
    ]

    def parse(self, response):
        """Parse CSV response and yield MarginTradingItem.

        CSV columns:
        0: 資料日期 (ROC date: "1150306")
        1: 代號
        2: 名稱
        3: 前資餘額
        4: 資買
        5: 資賣
        6: 現償
        7: 資餘額
        8: 資屬證金 (skip)
        9: 資使用率 (skip)
        10: 資限額
        11: 前券餘額
        12: 券賣
        13: 券買
        14: 券償
        15: 券餘額
        16: 券屬證金 (skip)
        17: 券使用率 (skip)
        18: 券限額
        19: 資券相抵
        20: 備註
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
            if len(row) < 21:
                continue

            stock_id = row[1].strip().replace('"', "")
            stock_name = row[2].strip().replace('"', "")

            # Skip non-stock entries
            if not stock_id or not stock_id[0].isdigit():
                continue

            yield MarginTradingItem(
                date=self._convert_roc_date(row[0]),
                stock_id=stock_id,
                stock_name=stock_name,
                margin_balance_prev=self._parse_number(row[3]),
                margin_buy=self._parse_number(row[4]),
                margin_sell=self._parse_number(row[5]),
                margin_cash_repay=self._parse_number(row[6]),
                margin_balance=self._parse_number(row[7]),
                margin_limit=self._parse_number(row[10]),
                short_balance_prev=self._parse_number(row[11]),
                short_sell=self._parse_number(row[12]),
                short_buy=self._parse_number(row[13]),
                short_cash_repay=self._parse_number(row[14]),
                short_balance=self._parse_number(row[15]),
                short_limit=self._parse_number(row[18]),
                offset=self._parse_number(row[19]),
                note=row[20].strip().replace('"', ""),
            )

    def _convert_roc_date(self, roc_date: str) -> str:
        """Convert ROC date ("1150306") to ISO format ("2026-03-06").

        ROC year = Western year - 1911
        """
        cleaned = roc_date.strip().replace('"', "")
        if len(cleaned) == 7:
            year = int(cleaned[:3]) + 1911
            month = cleaned[3:5]
            day = cleaned[5:7]
            return f"{year}-{month}-{day}"
        return cleaned

    def _parse_number(self, value: str) -> int:
        """Parse number string, removing commas, quotes, and handling empty values."""
        try:
            cleaned = value.replace(",", "").replace('"', "").strip()
            if not cleaned:
                return 0
            return int(cleaned)
        except (ValueError, AttributeError):
            return 0
