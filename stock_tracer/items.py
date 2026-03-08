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
    share_count = scrapy.Field()  # 張數 (原始股數/1000)
    holding_ratio = scrapy.Field()  # 占集保庫存數比例 (%)


class MarginTradingItem(scrapy.Item):
    """融資融券資料結構。"""

    date = scrapy.Field()  # 日期
    stock_id = scrapy.Field()  # 證券代號
    stock_name = scrapy.Field()  # 證券名稱 (for stock upsert, not in margin table)
    margin_buy = scrapy.Field()  # 融資買進
    margin_sell = scrapy.Field()  # 融資賣出
    margin_cash_repay = scrapy.Field()  # 融資現金償還
    margin_balance_prev = scrapy.Field()  # 融資前日餘額
    margin_balance = scrapy.Field()  # 融資今日餘額
    margin_limit = scrapy.Field()  # 融資限額
    short_buy = scrapy.Field()  # 融券買進
    short_sell = scrapy.Field()  # 融券賣出
    short_cash_repay = scrapy.Field()  # 融券現券償還
    short_balance_prev = scrapy.Field()  # 融券前日餘額
    short_balance = scrapy.Field()  # 融券今日餘額
    short_limit = scrapy.Field()  # 融券限額
    offset = scrapy.Field()  # 資券互抵
    note = scrapy.Field()  # 註記


class BrokerTradingItem(scrapy.Item):
    """分點券商進出資料結構。"""

    date = scrapy.Field()  # 日期
    stock_id = scrapy.Field()  # 證券代號
    broker_id = scrapy.Field()  # 券商代碼
    broker_name = scrapy.Field()  # 券商名稱
    price = scrapy.Field()  # 成交價
    buy_volume = scrapy.Field()  # 買進股數
    sell_volume = scrapy.Field()  # 賣出股數
