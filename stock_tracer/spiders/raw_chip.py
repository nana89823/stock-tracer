"""Spider for scraping TWSE institutional investors trading data.

Source: https://www.twse.com.tw/fund/T86?response=json&date=&selectType=ALL
"""

import json

import scrapy

from stock_tracer.items import RawChipItem


class RawChipSpider(scrapy.Spider):
    """Spider to scrape three major institutional investors trading data."""

    name = "raw_chip"
    start_urls = [
        "https://www.twse.com.tw/fund/T86?response=json&date=&selectType=ALL"
    ]

    def parse(self, response):
        """Parse JSON response and yield RawChipItem.

        JSON structure:
        {
            "stat": "OK",
            "date": "20260126",
            "data": [
                [stock_id, stock_name, foreign_buy, foreign_sell, foreign_net, ...]
            ]
        }

        Data columns (0-18):
        0: 證券代號
        1: 證券名稱
        2: 外陸資買進股數(不含外資自營商)
        3: 外陸資賣出股數(不含外資自營商)
        4: 外陸資買賣超股數(不含外資自營商)
        5: 外資自營商買進股數
        6: 外資自營商賣出股數
        7: 外資自營商買賣超股數
        8: 投信買進股數
        9: 投信賣出股數
        10: 投信買賣超股數
        11: 自營商買賣超股數
        12: 自營商買進股數(自行買賣)
        13: 自營商賣出股數(自行買賣)
        14: 自營商買賣超股數(自行買賣)
        15: 自營商買進股數(避險)
        16: 自營商賣出股數(避險)
        17: 自營商買賣超股數(避險)
        18: 三大法人買賣超股數
        """
        try:
            data = json.loads(response.text)
        except json.JSONDecodeError:
            self.logger.error("Failed to parse JSON response")
            return

        if data.get("stat") != "OK":
            self.logger.warning(f"API returned non-OK status: {data.get('stat')}")
            return

        raw_date = data.get("date", "")
        iso_date = self._convert_date(raw_date)

        for row in data.get("data", []):
            if len(row) < 19:
                continue

            yield RawChipItem(
                date=iso_date,
                stock_id=row[0].strip(),
                stock_name=row[1].strip(),
                foreign_buy=self._parse_number(row[2]),
                foreign_sell=self._parse_number(row[3]),
                foreign_net=self._parse_number(row[4]),
                foreign_dealer_buy=self._parse_number(row[5]),
                foreign_dealer_sell=self._parse_number(row[6]),
                foreign_dealer_net=self._parse_number(row[7]),
                trust_buy=self._parse_number(row[8]),
                trust_sell=self._parse_number(row[9]),
                trust_net=self._parse_number(row[10]),
                dealer_net=self._parse_number(row[11]),
                dealer_self_buy=self._parse_number(row[12]),
                dealer_self_sell=self._parse_number(row[13]),
                dealer_self_net=self._parse_number(row[14]),
                dealer_hedge_buy=self._parse_number(row[15]),
                dealer_hedge_sell=self._parse_number(row[16]),
                dealer_hedge_net=self._parse_number(row[17]),
                total_net=self._parse_number(row[18]),
            )

    def _convert_date(self, date_str: str) -> str:
        """Convert date string (20260126) to ISO format (2026-01-26)."""
        if len(date_str) == 8:
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        return date_str

    def _parse_number(self, value: str) -> int:
        """Parse number string, handling commas and negative values."""
        try:
            return int(value.replace(",", "").strip())
        except (ValueError, AttributeError):
            return 0
