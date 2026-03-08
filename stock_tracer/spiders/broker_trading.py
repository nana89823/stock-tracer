"""Spider for scraping TWSE broker trading data (分點券商進出).

Source: https://bsr.twse.com.tw/bshtm/bsContent.aspx?StkNo={stock_id}
Format: CSV (Big5 encoded)
"""

from datetime import date

import scrapy

from stock_tracer.items import BrokerTradingItem

# 台灣前 20 大市值熱門股票（預設清單），可透過 -a stock_ids=... 覆蓋
DEFAULT_STOCK_IDS = (
    "2330,2317,2454,2881,2882,"
    "2412,3711,2308,2303,2891,"
    "1301,1303,2886,2884,3034,"
    "2357,2382,6505,1326,2002"
)


class BrokerTradingSpider(scrapy.Spider):
    """Spider to scrape broker-level trading data from TWSE."""

    name = "broker_trading"
    market_type = "twse"

    custom_settings = {
        "DOWNLOAD_DELAY": 2,
        "CONCURRENT_REQUESTS": 1,
    }

    def __init__(self, stock_ids=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if stock_ids:
            self.stock_ids = [s.strip() for s in stock_ids.split(",")]
        else:
            self.stock_ids = [s.strip() for s in DEFAULT_STOCK_IDS.split(",")]

    def start_requests(self):
        for stock_id in self.stock_ids:
            url = f"https://bsr.twse.com.tw/bshtm/bsContent.aspx?StkNo={stock_id}&RecCount=63"
            yield scrapy.Request(
                url,
                callback=self.parse,
                cb_kwargs={"stock_id": stock_id},
            )

    def parse(self, response, stock_id):
        """Parse Big5-encoded CSV response and yield aggregated BrokerTradingItem."""
        try:
            text = response.body.decode("big5", errors="ignore")
        except Exception:
            self.logger.error(f"Failed to decode response for stock {stock_id}")
            return

        if not text.strip():
            self.logger.warning(f"Empty response for stock {stock_id}")
            return

        today = date.today().isoformat()
        lines = text.strip().splitlines()

        # Skip first 3 lines (title, stock code, column headers)
        data_lines = lines[3:]

        # Collect raw entries: {(broker_id, stock_id): {buy_vol, sell_vol, buy_value, sell_value, broker_name}}
        aggregated = {}

        for line in data_lines:
            cols = line.split(",")
            # Each line has two groups separated by ,,
            # Left: cols[0:5] = seq, broker, price, buy_vol, sell_vol
            # Right: cols[6:11] = seq, broker, price, buy_vol, sell_vol
            groups = []
            if len(cols) >= 5:
                groups.append(cols[0:5])
            if len(cols) >= 11:
                groups.append(cols[6:11])

            for group in groups:
                try:
                    broker_raw = group[1].strip()
                    price_str = group[2].strip()
                    buy_str = group[3].strip()
                    sell_str = group[4].strip()
                except (IndexError, AttributeError):
                    continue

                if not broker_raw or not price_str:
                    continue

                broker_id = broker_raw[:4]
                broker_name = broker_raw[4:].replace("\u3000", "").strip()

                try:
                    price = float(price_str.replace(",", ""))
                    buy_volume = int(buy_str.replace(",", "")) if buy_str else 0
                    sell_volume = int(sell_str.replace(",", "")) if sell_str else 0
                except (ValueError, AttributeError):
                    continue

                key = (broker_id, stock_id)
                if key not in aggregated:
                    aggregated[key] = {
                        "broker_name": broker_name,
                        "buy_vol": 0,
                        "sell_vol": 0,
                        "buy_value": 0.0,
                        "sell_value": 0.0,
                    }

                aggregated[key]["buy_vol"] += buy_volume
                aggregated[key]["sell_vol"] += sell_volume
                aggregated[key]["buy_value"] += price * buy_volume
                aggregated[key]["sell_value"] += price * sell_volume

        # Yield aggregated items
        for (broker_id, sid), data in aggregated.items():
            total_volume = data["buy_vol"] + data["sell_vol"]
            total_value = data["buy_value"] + data["sell_value"]
            avg_price = round(total_value / total_volume, 2) if total_volume > 0 else 0.0

            yield BrokerTradingItem(
                date=today,
                stock_id=sid,
                broker_id=broker_id,
                broker_name=data["broker_name"],
                price=avg_price,
                buy_volume=data["buy_vol"],
                sell_volume=data["sell_vol"],
            )
