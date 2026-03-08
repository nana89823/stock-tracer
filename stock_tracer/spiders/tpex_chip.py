"""Spider for scraping TPEX (OTC) institutional investors trading data.

Source: https://www.tpex.org.tw/www/zh-tw/insti/dailyTrade
"""

import json
from datetime import datetime

import scrapy

from stock_tracer.items import RawChipItem


class TpexChipSpider(scrapy.Spider):
    """Spider to scrape three major institutional investors trading data from TPEX."""

    name = "tpex_chip"

    custom_settings = {
        "DOWNLOAD_DELAY": 3,
    }

    def __init__(self, date=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.market_type = "tpex"

        if date:
            # Accept YYYYMMDD format, convert to YYYY/MM/DD for API
            self.query_date = f"{date[:4]}/{date[4:6]}/{date[6:8]}"
        else:
            today = datetime.now()
            self.query_date = today.strftime("%Y/%m/%d")

    def start_requests(self):
        """Send POST request to TPEX institutional investors API."""
        headers = {
            "accept": "application/json, text/javascript, */*; q=0.01",
            "accept-language": "en-US,en;q=0.9,zh-TW;q=0.8,zh;q=0.7",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "origin": "https://www.tpex.org.tw",
            "referer": "https://www.tpex.org.tw/zh-tw/mainboard/trading/info/pricing.html",
            "user-agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/143.0.0.0 Safari/537.36"
            ),
            "x-requested-with": "XMLHttpRequest",
        }

        formdata = {
            "type": "Daily",
            "sect": "AL",
            "date": self.query_date,
            "id": "",
            "response": "json",
        }

        yield scrapy.FormRequest(
            url="https://www.tpex.org.tw/www/zh-tw/insti/dailyTrade",
            headers=headers,
            formdata=formdata,
            callback=self.parse,
        )

    def parse(self, response):
        """Parse JSON response and yield RawChipItem.

        JSON structure:
        {
            "stat": "ok",
            "date": "20260306",
            "tables": [
                {
                    "title": "三大法人買賣明細資訊",
                    "date": "115/03/06",  (ROC date)
                    "fields": [...],
                    "data": [
                        [stock_id, stock_name, ...]
                    ]
                }
            ]
        }

        Data columns (0-23):
        0:  代號
        1:  名稱
        2:  外資及陸資(不含外資自營商) 買進股數
        3:  外資及陸資(不含外資自營商) 賣出股數
        4:  外資及陸資(不含外資自營商) 買賣超股數
        5:  外資自營商 買進股數
        6:  外資自營商 賣出股數
        7:  外資自營商 買賣超股數
        8:  外資及陸資合計 買進股數
        9:  外資及陸資合計 賣出股數
        10: 外資及陸資合計 買賣超股數
        11: 投信 買進股數
        12: 投信 賣出股數
        13: 投信 買賣超股數
        14: 自營商(自行買賣) 買進股數
        15: 自營商(自行買賣) 賣出股數
        16: 自營商(自行買賣) 買賣超股數
        17: 自營商(避險) 買進股數
        18: 自營商(避險) 賣出股數
        19: 自營商(避險) 買賣超股數
        20: 自營商合計 買進股數
        21: 自營商合計 賣出股數
        22: 自營商合計 買賣超股數
        23: 三大法人買賣超股數合計
        """
        try:
            data = json.loads(response.text)
        except json.JSONDecodeError:
            self.logger.error("Failed to parse JSON response")
            return

        if data.get("stat") != "ok":
            self.logger.warning(f"API returned non-ok status: {data.get('stat')}")
            return

        tables = data.get("tables", [])
        if not tables:
            self.logger.warning("No tables found in response")
            return

        table = tables[0]
        roc_date = table.get("date", "")
        iso_date = self._convert_roc_date(roc_date)

        rows = table.get("data", [])
        if not rows:
            self.logger.warning("No data rows found in table")
            return

        self.logger.info(f"Processing {len(rows)} rows for date {iso_date}")

        for row in rows:
            if len(row) < 24:
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
                trust_buy=self._parse_number(row[11]),
                trust_sell=self._parse_number(row[12]),
                trust_net=self._parse_number(row[13]),
                dealer_net=self._parse_number(row[22]),
                dealer_self_buy=self._parse_number(row[14]),
                dealer_self_sell=self._parse_number(row[15]),
                dealer_self_net=self._parse_number(row[16]),
                dealer_hedge_buy=self._parse_number(row[17]),
                dealer_hedge_sell=self._parse_number(row[18]),
                dealer_hedge_net=self._parse_number(row[19]),
                total_net=self._parse_number(row[23]),
            )

    def _convert_roc_date(self, roc_date: str) -> str:
        """Convert ROC date (115/03/06) to ISO format (2026-03-06).

        ROC year = Western year - 1911
        """
        roc_date = roc_date.strip()
        parts = roc_date.split("/")
        if len(parts) == 3:
            year = int(parts[0]) + 1911
            return f"{year}-{parts[1]}-{parts[2]}"
        return roc_date

    def _parse_number(self, value: str) -> int:
        """Parse number string, handling commas and negative values."""
        try:
            return int(value.replace(",", "").strip())
        except (ValueError, AttributeError):
            return 0
