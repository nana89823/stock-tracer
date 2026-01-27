"""Item pipelines for stock_tracer."""

import csv
import os
from datetime import datetime

from itemadapter import ItemAdapter
from scrapy import signals
from scrapy.exporters import CsvItemExporter

from stock_tracer.items import RawPriceItem, RawChipItem, MajorHoldersItem


class CsvExportPipeline:
    """Pipeline to export items to CSV files.

    Each spider's data is exported to a separate CSV file with date prefix.
    Output format: output/{date}_{spider_name}.csv
    """

    def __init__(self):
        self.files = {}
        self.exporters = {}

    @classmethod
    def from_crawler(cls, crawler):
        pipeline = cls()
        pipeline.output_dir = crawler.settings.get("OUTPUT_DIR", "output")
        crawler.signals.connect(pipeline.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(pipeline.spider_closed, signal=signals.spider_closed)
        return pipeline

    def spider_opened(self, spider):
        """Open CSV file for writing when spider starts."""
        os.makedirs(self.output_dir, exist_ok=True)

        today = datetime.now().strftime("%Y%m%d")
        filename = os.path.join(self.output_dir, f"{today}_{spider.name}.csv")

        self.files[spider.name] = open(filename, "wb")
        self.exporters[spider.name] = CsvItemExporter(
            self.files[spider.name],
            include_headers_line=True,
            encoding="utf-8",
        )
        self.exporters[spider.name].fields_to_export = self._get_fields(spider.name)
        self.exporters[spider.name].start_exporting()

        spider.logger.info(f"CSV export started: {filename}")

    def spider_closed(self, spider):
        """Close CSV file when spider finishes."""
        if spider.name in self.exporters:
            self.exporters[spider.name].finish_exporting()
            self.files[spider.name].close()

    def process_item(self, item, spider):
        """Export item to CSV."""
        if spider.name in self.exporters:
            self.exporters[spider.name].export_item(item)
        return item

    def _get_fields(self, spider_name: str) -> list:
        """Get field order for each spider type."""
        field_map = {
            "raw_price": [
                "date", "stock_id", "stock_name", "trade_volume", "trade_value",
                "open_price", "high_price", "low_price", "close_price",
                "price_change", "transaction_count"
            ],
            "raw_chip": [
                "date", "stock_id", "stock_name",
                "foreign_buy", "foreign_sell", "foreign_net",
                "foreign_dealer_buy", "foreign_dealer_sell", "foreign_dealer_net",
                "trust_buy", "trust_sell", "trust_net",
                "dealer_net", "dealer_self_buy", "dealer_self_sell", "dealer_self_net",
                "dealer_hedge_buy", "dealer_hedge_sell", "dealer_hedge_net",
                "total_net"
            ],
            "major_holders": [
                "date", "stock_id", "holding_level",
                "holder_count", "share_count", "holding_ratio"
            ],
        }
        return field_map.get(spider_name, [])
