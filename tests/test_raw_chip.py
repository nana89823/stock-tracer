"""Tests for RawChipSpider - 三大法人買賣超爬蟲。"""

import json
from unittest.mock import MagicMock

import pytest
from scrapy.http import TextResponse, Request

from stock_tracer.items import RawChipItem
from stock_tracer.spiders.raw_chip import RawChipSpider


class TestRawChipSpider:
    """Test suite for RawChipSpider."""

    def test_spider_name(self):
        """Spider should have correct name."""
        spider = RawChipSpider()
        assert spider.name == "raw_chip"

    def test_start_urls(self):
        """Spider should have correct start URL."""
        spider = RawChipSpider()
        assert len(spider.start_urls) == 1
        assert "T86" in spider.start_urls[0]
        assert "response=json" in spider.start_urls[0]

    def test_parse_json_returns_items(self, raw_chip_json):
        """Parse should return RawChipItem from JSON response."""
        spider = RawChipSpider()
        request = Request(url="https://www.twse.com.tw/test")
        response = TextResponse(
            url="https://www.twse.com.tw/test",
            body=json.dumps(raw_chip_json).encode("utf-8"),
            request=request,
        )

        items = list(spider.parse(response))

        assert len(items) == 2
        assert all(isinstance(item, RawChipItem) for item in items)

    def test_parse_extracts_stock_id(self, raw_chip_json):
        """Parse should extract stock_id correctly."""
        spider = RawChipSpider()
        request = Request(url="https://www.twse.com.tw/test")
        response = TextResponse(
            url="https://www.twse.com.tw/test",
            body=json.dumps(raw_chip_json).encode("utf-8"),
            request=request,
        )

        items = list(spider.parse(response))

        assert items[0]["stock_id"] == "2330"
        assert items[1]["stock_id"] == "2317"

    def test_parse_extracts_date(self, raw_chip_json):
        """Parse should extract and convert date correctly."""
        spider = RawChipSpider()
        request = Request(url="https://www.twse.com.tw/test")
        response = TextResponse(
            url="https://www.twse.com.tw/test",
            body=json.dumps(raw_chip_json).encode("utf-8"),
            request=request,
        )

        items = list(spider.parse(response))

        assert items[0]["date"] == "2026-01-26"

    def test_parse_extracts_foreign_data(self, raw_chip_json):
        """Parse should extract foreign investor data correctly."""
        spider = RawChipSpider()
        request = Request(url="https://www.twse.com.tw/test")
        response = TextResponse(
            url="https://www.twse.com.tw/test",
            body=json.dumps(raw_chip_json).encode("utf-8"),
            request=request,
        )

        items = list(spider.parse(response))
        tsmc = items[0]

        assert tsmc["foreign_buy"] == 5000000
        assert tsmc["foreign_sell"] == 3000000
        assert tsmc["foreign_net"] == 2000000

    def test_parse_extracts_trust_data(self, raw_chip_json):
        """Parse should extract investment trust data correctly."""
        spider = RawChipSpider()
        request = Request(url="https://www.twse.com.tw/test")
        response = TextResponse(
            url="https://www.twse.com.tw/test",
            body=json.dumps(raw_chip_json).encode("utf-8"),
            request=request,
        )

        items = list(spider.parse(response))
        tsmc = items[0]

        assert tsmc["trust_buy"] == 500000
        assert tsmc["trust_sell"] == 200000
        assert tsmc["trust_net"] == 300000

    def test_parse_extracts_dealer_data(self, raw_chip_json):
        """Parse should extract dealer data correctly."""
        spider = RawChipSpider()
        request = Request(url="https://www.twse.com.tw/test")
        response = TextResponse(
            url="https://www.twse.com.tw/test",
            body=json.dumps(raw_chip_json).encode("utf-8"),
            request=request,
        )

        items = list(spider.parse(response))
        tsmc = items[0]

        assert tsmc["dealer_net"] == 150000
        assert tsmc["dealer_self_buy"] == 100000
        assert tsmc["dealer_hedge_net"] == 100000

    def test_parse_extracts_total_net(self, raw_chip_json):
        """Parse should extract total net correctly."""
        spider = RawChipSpider()
        request = Request(url="https://www.twse.com.tw/test")
        response = TextResponse(
            url="https://www.twse.com.tw/test",
            body=json.dumps(raw_chip_json).encode("utf-8"),
            request=request,
        )

        items = list(spider.parse(response))

        assert items[0]["total_net"] == 2500000
        assert items[1]["total_net"] == -500000

    def test_parse_handles_negative_numbers(self, raw_chip_json):
        """Parse should handle negative numbers correctly."""
        spider = RawChipSpider()
        request = Request(url="https://www.twse.com.tw/test")
        response = TextResponse(
            url="https://www.twse.com.tw/test",
            body=json.dumps(raw_chip_json).encode("utf-8"),
            request=request,
        )

        items = list(spider.parse(response))
        hon_hai = items[1]  # 2317 鴻海

        assert hon_hai["foreign_net"] == -500000
        assert hon_hai["dealer_net"] == -50000

    def test_parse_handles_error_status(self):
        """Parse should handle error response gracefully."""
        spider = RawChipSpider()
        error_response = {"stat": "ERROR", "message": "No data"}
        request = Request(url="https://www.twse.com.tw/test")
        response = TextResponse(
            url="https://www.twse.com.tw/test",
            body=json.dumps(error_response).encode("utf-8"),
            request=request,
        )

        items = list(spider.parse(response))

        assert len(items) == 0

    def test_parse_handles_empty_data(self):
        """Parse should handle empty data array."""
        spider = RawChipSpider()
        empty_response = {"stat": "OK", "date": "20260126", "data": []}
        request = Request(url="https://www.twse.com.tw/test")
        response = TextResponse(
            url="https://www.twse.com.tw/test",
            body=json.dumps(empty_response).encode("utf-8"),
            request=request,
        )

        items = list(spider.parse(response))

        assert len(items) == 0
