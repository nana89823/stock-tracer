"""Tests for RawPriceSpider - 個股成交價格爬蟲。"""

import json
from io import StringIO
from unittest.mock import MagicMock

import pytest
from scrapy.http import TextResponse, Request

from stock_tracer.items import RawPriceItem
from stock_tracer.spiders.raw_price import RawPriceSpider


class TestRawPriceSpider:
    """Test suite for RawPriceSpider."""

    def test_spider_name(self):
        """Spider should have correct name."""
        spider = RawPriceSpider()
        assert spider.name == "raw_price"

    def test_start_requests_default(self):
        """Spider should generate correct start URL with today's date."""
        spider = RawPriceSpider()
        requests = list(spider.start_requests())
        assert len(requests) == 1
        assert "STOCK_DAY_ALL" in requests[0].url
        assert "response=open_data" in requests[0].url

    def test_start_requests_with_date(self):
        """Spider should accept date argument for backfill."""
        spider = RawPriceSpider(date="20260301")
        requests = list(spider.start_requests())
        assert len(requests) == 1
        assert "date=20260301" in requests[0].url

    def test_parse_csv_returns_items(self, raw_price_csv):
        """Parse should return RawPriceItem from CSV response."""
        spider = RawPriceSpider()
        request = Request(url="https://www.twse.com.tw/test")
        response = TextResponse(
            url="https://www.twse.com.tw/test",
            body=raw_price_csv.encode("utf-8"),
            request=request,
        )

        items = list(spider.parse(response))

        assert len(items) == 3
        assert all(isinstance(item, RawPriceItem) for item in items)

    def test_parse_extracts_stock_id(self, raw_price_csv):
        """Parse should extract stock_id correctly."""
        spider = RawPriceSpider()
        request = Request(url="https://www.twse.com.tw/test")
        response = TextResponse(
            url="https://www.twse.com.tw/test",
            body=raw_price_csv.encode("utf-8"),
            request=request,
        )

        items = list(spider.parse(response))

        assert items[0]["stock_id"] == "0050"
        assert items[1]["stock_id"] == "2330"
        assert items[2]["stock_id"] == "2317"

    def test_parse_extracts_stock_name(self, raw_price_csv):
        """Parse should extract stock_name correctly."""
        spider = RawPriceSpider()
        request = Request(url="https://www.twse.com.tw/test")
        response = TextResponse(
            url="https://www.twse.com.tw/test",
            body=raw_price_csv.encode("utf-8"),
            request=request,
        )

        items = list(spider.parse(response))

        assert items[0]["stock_name"] == "元大台灣50"
        assert items[1]["stock_name"] == "台積電"

    def test_parse_extracts_prices(self, raw_price_csv):
        """Parse should extract price fields correctly."""
        spider = RawPriceSpider()
        request = Request(url="https://www.twse.com.tw/test")
        response = TextResponse(
            url="https://www.twse.com.tw/test",
            body=raw_price_csv.encode("utf-8"),
            request=request,
        )

        items = list(spider.parse(response))
        tsmc = items[1]  # 2330 台積電

        assert tsmc["open_price"] == 1000.0
        assert tsmc["high_price"] == 1010.0
        assert tsmc["low_price"] == 995.0
        assert tsmc["close_price"] == 1005.0
        assert tsmc["price_change"] == 5.0

    def test_parse_extracts_volume(self, raw_price_csv):
        """Parse should extract trade volume correctly (removing commas)."""
        spider = RawPriceSpider()
        request = Request(url="https://www.twse.com.tw/test")
        response = TextResponse(
            url="https://www.twse.com.tw/test",
            body=raw_price_csv.encode("utf-8"),
            request=request,
        )

        items = list(spider.parse(response))

        assert items[0]["trade_volume"] == 87992466
        assert items[1]["trade_volume"] == 25000000

    def test_parse_converts_date_format(self, raw_price_csv):
        """Parse should convert ROC date (1150126) to ISO format (2026-01-26)."""
        spider = RawPriceSpider()
        request = Request(url="https://www.twse.com.tw/test")
        response = TextResponse(
            url="https://www.twse.com.tw/test",
            body=raw_price_csv.encode("utf-8"),
            request=request,
        )

        items = list(spider.parse(response))

        assert items[0]["date"] == "2026-01-26"

    def test_parse_handles_empty_response(self):
        """Parse should handle empty CSV gracefully."""
        spider = RawPriceSpider()
        request = Request(url="https://www.twse.com.tw/test")
        response = TextResponse(
            url="https://www.twse.com.tw/test",
            body=b"",
            request=request,
        )

        items = list(spider.parse(response))

        assert len(items) == 0

    def test_parse_handles_header_only(self):
        """Parse should handle CSV with only header."""
        spider = RawPriceSpider()
        header_only = "日期,證券代號,證券名稱,成交股數,成交金額,開盤價,最高價,最低價,收盤價,漲跌價差,成交筆數\n"
        request = Request(url="https://www.twse.com.tw/test")
        response = TextResponse(
            url="https://www.twse.com.tw/test",
            body=header_only.encode("utf-8"),
            request=request,
        )

        items = list(spider.parse(response))

        assert len(items) == 0
