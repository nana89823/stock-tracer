"""Item pipelines for stock_tracer."""

import csv
import logging
import os
from datetime import datetime

from itemadapter import ItemAdapter
from scrapy import signals
from scrapy.exceptions import NotConfigured
from scrapy.exporters import CsvItemExporter
from sqlalchemy import BigInteger, Column, Date, DateTime, Float, Integer, MetaData, String, Table, create_engine
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import sessionmaker

from stock_tracer.items import RawPriceItem, RawChipItem, MajorHoldersItem, MarginTradingItem, BrokerTradingItem

logger = logging.getLogger(__name__)

# Define tables using SQLAlchemy Core (no dependency on backend.app.models)
metadata = MetaData()

stocks_table = Table(
    "stocks", metadata,
    Column("stock_id", String(10), primary_key=True),
    Column("stock_name", String(50)),
    Column("market_type", String(10)),
    Column("created_at", DateTime),
    Column("updated_at", DateTime),
)

raw_prices_table = Table(
    "raw_prices", metadata,
    Column("date", Date, primary_key=True),
    Column("stock_id", String(10), primary_key=True),
    Column("stock_name", String(50)),
    Column("trade_volume", BigInteger),
    Column("trade_value", BigInteger),
    Column("open_price", Float),
    Column("high_price", Float),
    Column("low_price", Float),
    Column("close_price", Float),
    Column("price_change", Float),
    Column("transaction_count", Integer),
)

raw_chips_table = Table(
    "raw_chips", metadata,
    Column("date", Date, primary_key=True),
    Column("stock_id", String(10), primary_key=True),
    Column("stock_name", String(50)),
    Column("foreign_buy", BigInteger),
    Column("foreign_sell", BigInteger),
    Column("foreign_net", BigInteger),
    Column("foreign_dealer_buy", BigInteger),
    Column("foreign_dealer_sell", BigInteger),
    Column("foreign_dealer_net", BigInteger),
    Column("trust_buy", BigInteger),
    Column("trust_sell", BigInteger),
    Column("trust_net", BigInteger),
    Column("dealer_net", BigInteger),
    Column("dealer_self_buy", BigInteger),
    Column("dealer_self_sell", BigInteger),
    Column("dealer_self_net", BigInteger),
    Column("dealer_hedge_buy", BigInteger),
    Column("dealer_hedge_sell", BigInteger),
    Column("dealer_hedge_net", BigInteger),
    Column("total_net", BigInteger),
)

major_holders_table = Table(
    "major_holders", metadata,
    Column("date", Date, primary_key=True),
    Column("stock_id", String(10), primary_key=True),
    Column("holding_level", Integer, primary_key=True),
    Column("holder_count", Integer),
    Column("share_count", BigInteger),
    Column("holding_ratio", Float),
)

margin_trading_table = Table(
    "margin_trading", metadata,
    Column("date", Date, primary_key=True),
    Column("stock_id", String(10), primary_key=True),
    Column("margin_buy", BigInteger),
    Column("margin_sell", BigInteger),
    Column("margin_cash_repay", BigInteger),
    Column("margin_balance_prev", BigInteger),
    Column("margin_balance", BigInteger),
    Column("margin_limit", BigInteger),
    Column("short_buy", BigInteger),
    Column("short_sell", BigInteger),
    Column("short_cash_repay", BigInteger),
    Column("short_balance_prev", BigInteger),
    Column("short_balance", BigInteger),
    Column("short_limit", BigInteger),
    Column("offset", BigInteger),
    Column("note", String(20)),
)

broker_trading_table = Table(
    "broker_trading", metadata,
    Column("date", Date, primary_key=True),
    Column("stock_id", String(10), primary_key=True),
    Column("broker_id", String(10), primary_key=True),
    Column("broker_name", String(50)),
    Column("price", Float),
    Column("buy_volume", BigInteger),
    Column("sell_volume", BigInteger),
)

ITEM_TABLE_MAP = {
    "RawPriceItem": raw_prices_table,
    "RawChipItem": raw_chips_table,
    "MajorHoldersItem": major_holders_table,
    "MarginTradingItem": margin_trading_table,
    "BrokerTradingItem": broker_trading_table,
}

BATCH_SIZE = 100


class DatabasePipeline:
    """Pipeline to write items to PostgreSQL database.

    Uses synchronous SQLAlchemy since Scrapy runs in Twisted reactor.
    Implements UPSERT (INSERT ... ON CONFLICT DO UPDATE) for idempotency.
    """

    def __init__(self, db_url):
        self.db_url = db_url
        self.engine = None
        self.Session = None
        self.buffer = []
        self.stock_buffer = {}

    @classmethod
    def from_crawler(cls, crawler):
        db_url = crawler.settings.get("DATABASE_URL_SYNC")
        if not db_url:
            raise NotConfigured("DATABASE_URL_SYNC not set")
        return cls(db_url)

    def open_spider(self, spider):
        self.engine = create_engine(self.db_url)
        self.Session = sessionmaker(bind=self.engine)
        self.buffer = []
        self.stock_buffer = {}
        spider.logger.info("DatabasePipeline opened")

    def close_spider(self, spider):
        self._flush(spider)
        if self.engine:
            self.engine.dispose()
        spider.logger.info("DatabasePipeline closed")

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        data = adapter.asdict()

        # Collect stock info for upsert
        if "stock_id" in data:
            name = data.get("stock_name", "")
            if name:  # Only update if stock_name is non-empty
                self.stock_buffer[data["stock_id"]] = name

        # Determine target table
        item_class_name = type(item).__name__
        table = ITEM_TABLE_MAP.get(item_class_name)
        if table is not None:
            self.buffer.append((table, data))

        if len(self.buffer) >= BATCH_SIZE:
            self._flush(spider)

        return item

    def _flush(self, spider):
        if not self.buffer and not self.stock_buffer:
            return

        session = self.Session()
        try:
            # Upsert stocks first (FK dependency)
            if self.stock_buffer:
                now = datetime.utcnow()
                market_type = getattr(spider, "market_type", "twse")
                for stock_id, stock_name in self.stock_buffer.items():
                    stmt = insert(stocks_table).values(
                        stock_id=stock_id,
                        stock_name=stock_name,
                        market_type=market_type,
                        created_at=now,
                        updated_at=now,
                    )
                    if stock_name:
                        stmt = stmt.on_conflict_do_update(
                            index_elements=["stock_id"],
                            set_=dict(stock_name=stock_name, updated_at=now),
                        )
                    else:
                        stmt = stmt.on_conflict_do_update(
                            index_elements=["stock_id"],
                            set_=dict(updated_at=now),
                        )
                    session.execute(stmt)
                self.stock_buffer.clear()

            # Group items by table for bulk upsert
            by_table = {}
            for table, data in self.buffer:
                by_table.setdefault(table.name, (table, []))
                by_table[table.name][1].append(data)

            # For tables with FK to stocks, filter out unknown stock_ids
            valid_stock_ids = None
            for table_name, (table, rows) in by_table.items():
                if table_name in ("major_holders",) and rows:
                    if valid_stock_ids is None:
                        result = session.execute(
                            stocks_table.select().with_only_columns(stocks_table.c.stock_id)
                        )
                        valid_stock_ids = {r[0] for r in result}
                    before = len(rows)
                    rows[:] = [r for r in rows if r.get("stock_id") in valid_stock_ids]
                    skipped = before - len(rows)
                    if skipped:
                        spider.logger.debug(f"Skipped {skipped} items with unknown stock_id")

            for table_name, (table, rows) in by_table.items():
                pk_cols = [c.name for c in table.primary_key.columns]
                non_pk_cols = [c.name for c in table.columns if c.name not in pk_cols]

                table_cols = {c.name for c in table.columns}
                for row in rows:
                    # Filter row to only include columns in the table
                    filtered_row = {k: v for k, v in row.items() if k in table_cols}
                    stmt = insert(table).values(**filtered_row).on_conflict_do_update(
                        index_elements=pk_cols,
                        set_={col: filtered_row[col] for col in non_pk_cols if col in filtered_row},
                    )
                    session.execute(stmt)

            session.commit()
            spider.logger.debug(f"Flushed {len(self.buffer)} items to database")
            self.buffer.clear()
        except Exception:
            session.rollback()
            spider.logger.error("Database flush failed", exc_info=True)
            raise
        finally:
            session.close()


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
            "tpex_price": [
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
            "tpex_chip": [
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
            "margin_trading": [
                "date", "stock_id",
                "margin_buy", "margin_sell", "margin_cash_repay",
                "margin_balance_prev", "margin_balance", "margin_limit",
                "short_buy", "short_sell", "short_cash_repay",
                "short_balance_prev", "short_balance", "short_limit",
                "offset", "note"
            ],
            "broker_trading": [
                "date", "stock_id", "broker_id", "broker_name",
                "price", "buy_volume", "sell_volume"
            ],
        }
        return field_map.get(spider_name, [])
