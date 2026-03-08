from datetime import date

from pydantic import BaseModel, ConfigDict


class StockResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    stock_id: str
    stock_name: str
    market_type: str


class RawPriceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: date
    stock_id: str
    stock_name: str
    trade_volume: int
    trade_value: int
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    price_change: float
    transaction_count: int


class RawChipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: date
    stock_id: str
    stock_name: str
    foreign_buy: int
    foreign_sell: int
    foreign_net: int
    foreign_dealer_buy: int
    foreign_dealer_sell: int
    foreign_dealer_net: int
    trust_buy: int
    trust_sell: int
    trust_net: int
    dealer_net: int
    dealer_self_buy: int
    dealer_self_sell: int
    dealer_self_net: int
    dealer_hedge_buy: int
    dealer_hedge_sell: int
    dealer_hedge_net: int
    total_net: int


class MajorHoldersResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: date
    stock_id: str
    holding_level: int
    holder_count: int
    share_count: int
    holding_ratio: float


class MarginTradingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: date
    stock_id: str
    margin_buy: int
    margin_sell: int
    margin_cash_repay: int
    margin_balance_prev: int
    margin_balance: int
    margin_limit: int
    short_buy: int
    short_sell: int
    short_cash_repay: int
    short_balance_prev: int
    short_balance: int
    short_limit: int
    offset: int
    note: str


class BrokerTradingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: date
    stock_id: str
    broker_id: str
    broker_name: str
    price: float
    buy_volume: int
    sell_volume: int
