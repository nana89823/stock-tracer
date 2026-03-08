"""Spider for scraping TPEX (OTC) daily stock prices.

Source: https://www.tpex.org.tw/www/zh-tw/afterTrading/dailyQuotes
"""

import json
from datetime import datetime

import scrapy

from stock_tracer.items import RawPriceItem


class TpexPriceSpider(scrapy.Spider):
    """Spider to scrape daily stock prices from TPEX (OTC market)."""

    name = "tpex_price"
    market_type = "tpex"

    custom_settings = {
        "DOWNLOAD_DELAY": 3,
        "DEFAULT_REQUEST_HEADERS": {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "en-US,en;q=0.9,zh-TW;q=0.8,zh;q=0.7",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": "https://www.tpex.org.tw",
            "Referer": "https://www.tpex.org.tw/zh-tw/mainboard/trading/info/pricing.html",
            "X-Requested-With": "XMLHttpRequest",
        },
    }

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
        """Send POST request to TPEX daily quotes API."""
        # Convert YYYYMMDD to YYYY/MM/DD for the API
        formatted_date = (
            f"{self.target_date[:4]}/{self.target_date[4:6]}/{self.target_date[6:8]}"
        )

        yield scrapy.FormRequest(
            url="https://www.tpex.org.tw/www/zh-tw/afterTrading/dailyQuotes",
            formdata={
                "date": formatted_date,
                "id": "",
                "response": "json",
            },
            callback=self.parse,
        )

    def parse(self, response):
        """Parse JSON response and yield RawPriceItem.

        Expected JSON structure:
        {
            "tables": [
                {
                    "title": "...",
                    "subtitle": "114/03/06",
                    "totalCount": ...,
                    "data": [
                        [代號, 名稱, 收盤, 漲跌, 開盤, 最高, 最低, 均價,
                         成交股數, 成交金額(元), 成交筆數, ...],
                        ...
                    ]
                }
            ]
        }

        Data columns (based on TPEX daily quotes):
        0: 代號
        1: 名稱
        2: 收盤
        3: 漲跌
        4: 開盤
        5: 最高
        6: 最低
        7: 均價
        8: 成交股數
        9: 成交金額(元)
        10: 成交筆數
        11: 最後買價
        12: 最後賣價
        13: 發行股數
        14: 次日參考價
        15: 次日漲停價
        16: 次日跌停價
        """
        try:
            data = json.loads(response.text)
        except json.JSONDecodeError:
            self.logger.error("Failed to parse JSON response")
            return

        tables = data.get("tables", [])
        if not tables:
            self.logger.warning("No tables found in response")
            return

        table = tables[0]
        # Date is in top-level "date" field as YYYYMMDD, NOT in subtitle
        raw_date = data.get("date", "")
        if len(raw_date) == 8:
            iso_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
        else:
            # Fallback: try table-level "date" field (ROC format)
            iso_date = self._convert_roc_date(table.get("date", ""))

        rows = table.get("data", [])
        if not rows:
            self.logger.warning("No data rows found in response")
            return

        self.logger.info(f"Processing {len(rows)} rows for date {iso_date}")

        for row in rows:
            if len(row) < 11:
                continue

            stock_id = str(row[0]).strip()
            stock_name = str(row[1]).strip()

            # Skip non-stock entries (e.g., summary rows)
            if not stock_id or not stock_id[0].isdigit():
                continue

            yield RawPriceItem(
                date=iso_date,
                stock_id=stock_id,
                stock_name=stock_name,
                trade_volume=self._parse_number(row[8]),
                trade_value=self._parse_number(row[9]),
                open_price=self._parse_float(row[4]),
                high_price=self._parse_float(row[5]),
                low_price=self._parse_float(row[6]),
                close_price=self._parse_float(row[2]),
                price_change=self._parse_float(row[3]),
                transaction_count=self._parse_number(row[10]),
            )

    def _convert_roc_date(self, roc_date: str) -> str:
        """Convert ROC date (114/03/06) to ISO format (2025-03-06).

        ROC year = Western year - 1911
        """
        roc_date = roc_date.strip()
        parts = roc_date.split("/")
        if len(parts) == 3:
            year = int(parts[0]) + 1911
            month = parts[1].zfill(2)
            day = parts[2].zfill(2)
            return f"{year}-{month}-{day}"
        return roc_date

    def _parse_number(self, value) -> int:
        """Parse number string, removing commas and quotes."""
        try:
            return int(str(value).replace(",", "").replace('"', "").strip())
        except (ValueError, AttributeError):
            return 0

    def _parse_float(self, value) -> float:
        """Parse float string, handling +/- prefix and special chars."""
        try:
            clean_value = str(value).replace(",", "").replace('"', "").strip()
            # Handle cases like "---" or empty values (no trade)
            if not clean_value or clean_value in ("---", "--", "-"):
                return 0.0
            return float(clean_value)
        except (ValueError, AttributeError):
            return 0.0
