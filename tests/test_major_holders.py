"""Tests for MajorHoldersSpider - 大戶持股分布爬蟲。"""

import pytest
from scrapy.http import TextResponse, Request

from stock_tracer.items import MajorHoldersItem
from stock_tracer.spiders.major_holders import MajorHoldersSpider


class TestMajorHoldersSpider:
    """Test suite for MajorHoldersSpider."""

    def test_spider_name(self):
        """Spider should have correct name."""
        spider = MajorHoldersSpider()
        assert spider.name == "major_holders"

    def test_start_urls(self):
        """Spider should have correct start URL."""
        spider = MajorHoldersSpider()
        assert len(spider.start_urls) == 1
        assert "opendata.tdcc.com.tw" in spider.start_urls[0]
        assert "id=1-5" in spider.start_urls[0]

    def test_parse_csv_returns_items(self, major_holders_csv):
        """Parse should return MajorHoldersItem from CSV response."""
        spider = MajorHoldersSpider()
        request = Request(url="https://opendata.tdcc.com.tw/test")
        response = TextResponse(
            url="https://opendata.tdcc.com.tw/test",
            body=major_holders_csv.encode("utf-8"),
            request=request,
        )

        items = list(spider.parse(response))

        assert len(items) == 7
        assert all(isinstance(item, MajorHoldersItem) for item in items)

    def test_parse_extracts_stock_id(self, major_holders_csv):
        """Parse should extract stock_id correctly."""
        spider = MajorHoldersSpider()
        request = Request(url="https://opendata.tdcc.com.tw/test")
        response = TextResponse(
            url="https://opendata.tdcc.com.tw/test",
            body=major_holders_csv.encode("utf-8"),
            request=request,
        )

        items = list(spider.parse(response))
        stock_ids = [item["stock_id"] for item in items]

        assert "2330" in stock_ids
        assert "2317" in stock_ids

    def test_parse_extracts_date(self, major_holders_csv):
        """Parse should extract date in ISO format."""
        spider = MajorHoldersSpider()
        request = Request(url="https://opendata.tdcc.com.tw/test")
        response = TextResponse(
            url="https://opendata.tdcc.com.tw/test",
            body=major_holders_csv.encode("utf-8"),
            request=request,
        )

        items = list(spider.parse(response))

        assert items[0]["date"] == "2026-01-23"

    def test_parse_extracts_holding_level(self, major_holders_csv):
        """Parse should extract holding level correctly."""
        spider = MajorHoldersSpider()
        request = Request(url="https://opendata.tdcc.com.tw/test")
        response = TextResponse(
            url="https://opendata.tdcc.com.tw/test",
            body=major_holders_csv.encode("utf-8"),
            request=request,
        )

        items = list(spider.parse(response))
        tsmc_items = [item for item in items if item["stock_id"] == "2330"]

        levels = [item["holding_level"] for item in tsmc_items]
        assert 1 in levels
        assert 15 in levels
        assert 17 in levels

    def test_parse_extracts_holder_count(self, major_holders_csv):
        """Parse should extract holder count correctly."""
        spider = MajorHoldersSpider()
        request = Request(url="https://opendata.tdcc.com.tw/test")
        response = TextResponse(
            url="https://opendata.tdcc.com.tw/test",
            body=major_holders_csv.encode("utf-8"),
            request=request,
        )

        items = list(spider.parse(response))
        tsmc_level1 = next(
            item for item in items
            if item["stock_id"] == "2330" and item["holding_level"] == 1
        )

        assert tsmc_level1["holder_count"] == 500000

    def test_parse_extracts_share_count(self, major_holders_csv):
        """Parse should extract share count correctly."""
        spider = MajorHoldersSpider()
        request = Request(url="https://opendata.tdcc.com.tw/test")
        response = TextResponse(
            url="https://opendata.tdcc.com.tw/test",
            body=major_holders_csv.encode("utf-8"),
            request=request,
        )

        items = list(spider.parse(response))
        tsmc_level17 = next(
            item for item in items
            if item["stock_id"] == "2330" and item["holding_level"] == 17
        )

        assert tsmc_level17["share_count"] == 10000000000

    def test_parse_extracts_holding_ratio(self, major_holders_csv):
        """Parse should extract holding ratio correctly."""
        spider = MajorHoldersSpider()
        request = Request(url="https://opendata.tdcc.com.tw/test")
        response = TextResponse(
            url="https://opendata.tdcc.com.tw/test",
            body=major_holders_csv.encode("utf-8"),
            request=request,
        )

        items = list(spider.parse(response))
        tsmc_level17 = next(
            item for item in items
            if item["stock_id"] == "2330" and item["holding_level"] == 17
        )

        assert tsmc_level17["holding_ratio"] == 38.46

    def test_parse_handles_empty_response(self):
        """Parse should handle empty CSV gracefully."""
        spider = MajorHoldersSpider()
        request = Request(url="https://opendata.tdcc.com.tw/test")
        response = TextResponse(
            url="https://opendata.tdcc.com.tw/test",
            body=b"",
            request=request,
        )

        items = list(spider.parse(response))

        assert len(items) == 0


class TestMajorHoldersCalculation:
    """Test suite for 400張以上大戶計算。"""

    def test_calculate_major_holders_ratio(self, major_holders_csv):
        """Should calculate 400張以上大戶比例 correctly.

        持股分級說明:
        - 級距 1-11: 1-400張
        - 級距 12-17: 400張以上 (大戶)

        15級: 400-600張
        16級: 600-800張
        17級: 800-1000張及以上
        """
        spider = MajorHoldersSpider()
        request = Request(url="https://opendata.tdcc.com.tw/test")
        response = TextResponse(
            url="https://opendata.tdcc.com.tw/test",
            body=major_holders_csv.encode("utf-8"),
            request=request,
        )

        items = list(spider.parse(response))
        tsmc_items = [item for item in items if item["stock_id"] == "2330"]

        # 400張以上為級距 12-17 (level >= 12)
        major_holders_ratio = sum(
            item["holding_ratio"]
            for item in tsmc_items
            if item["holding_level"] >= 12
        )

        # 15級: 19.23% + 16級: 38.46% + 17級: 38.46% = 96.15%
        assert major_holders_ratio == pytest.approx(96.15, rel=0.01)

    def test_calculate_major_holders_count(self, major_holders_csv):
        """Should calculate 400張以上大戶人數 correctly."""
        spider = MajorHoldersSpider()
        request = Request(url="https://opendata.tdcc.com.tw/test")
        response = TextResponse(
            url="https://opendata.tdcc.com.tw/test",
            body=major_holders_csv.encode("utf-8"),
            request=request,
        )

        items = list(spider.parse(response))
        tsmc_items = [item for item in items if item["stock_id"] == "2330"]

        major_holders_count = sum(
            item["holder_count"]
            for item in tsmc_items
            if item["holding_level"] >= 12
        )

        # 15級: 100 + 16級: 50 + 17級: 10 = 160人
        assert major_holders_count == 160
