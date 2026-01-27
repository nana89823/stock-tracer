"""Item definitions for stock_tracer."""

import scrapy


class RawPriceItem(scrapy.Item):
    """個股成交價格資料結構。"""

    date = scrapy.Field()  # 日期
    stock_id = scrapy.Field()  # 證券代號
    stock_name = scrapy.Field()  # 證券名稱
    trade_volume = scrapy.Field()  # 成交股數
    trade_value = scrapy.Field()  # 成交金額
    open_price = scrapy.Field()  # 開盤價
    high_price = scrapy.Field()  # 最高價
    low_price = scrapy.Field()  # 最低價
    close_price = scrapy.Field()  # 收盤價
    price_change = scrapy.Field()  # 漲跌價差
    transaction_count = scrapy.Field()  # 成交筆數


class RawChipItem(scrapy.Item):
    """三大法人買賣超資料結構。"""

    date = scrapy.Field()  # 日期
    stock_id = scrapy.Field()  # 證券代號
    stock_name = scrapy.Field()  # 證券名稱
    foreign_buy = scrapy.Field()  # 外陸資買進股數(不含外資自營商)
    foreign_sell = scrapy.Field()  # 外陸資賣出股數(不含外資自營商)
    foreign_net = scrapy.Field()  # 外陸資買賣超股數(不含外資自營商)
    foreign_dealer_buy = scrapy.Field()  # 外資自營商買進股數
    foreign_dealer_sell = scrapy.Field()  # 外資自營商賣出股數
    foreign_dealer_net = scrapy.Field()  # 外資自營商買賣超股數
    trust_buy = scrapy.Field()  # 投信買進股數
    trust_sell = scrapy.Field()  # 投信賣出股數
    trust_net = scrapy.Field()  # 投信買賣超股數
    dealer_net = scrapy.Field()  # 自營商買賣超股數
    dealer_self_buy = scrapy.Field()  # 自營商買進股數(自行買賣)
    dealer_self_sell = scrapy.Field()  # 自營商賣出股數(自行買賣)
    dealer_self_net = scrapy.Field()  # 自營商買賣超股數(自行買賣)
    dealer_hedge_buy = scrapy.Field()  # 自營商買進股數(避險)
    dealer_hedge_sell = scrapy.Field()  # 自營商賣出股數(避險)
    dealer_hedge_net = scrapy.Field()  # 自營商買賣超股數(避險)
    total_net = scrapy.Field()  # 三大法人買賣超股數


class MajorHoldersItem(scrapy.Item):
    """大戶持股分布資料結構。"""

    date = scrapy.Field()  # 資料日期
    stock_id = scrapy.Field()  # 證券代號
    holding_level = scrapy.Field()  # 持股分級 (1-17)
    holder_count = scrapy.Field()  # 人數
    share_count = scrapy.Field()  # 股數/單位數
    holding_ratio = scrapy.Field()  # 占集保庫存數比例 (%)
