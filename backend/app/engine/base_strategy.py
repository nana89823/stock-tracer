from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from enum import Enum


class SignalType(Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


@dataclass
class Signal:
    signal_type: SignalType
    stock_id: str
    date: date
    quantity: int = 1000  # shares, multiples of 1000
    reason: str = ""


@dataclass
class MarketData:
    prices: list[dict]
    chips: list[dict]
    holders: list[dict]
    margin: list[dict]


class BaseStrategy(ABC):
    def __init__(self, params: dict | None = None):
        self.params = params or {}

    @abstractmethod
    def on_data(self, current_date: date, data: MarketData) -> Signal:
        """Given market data up to current_date, return a signal."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def default_params(self) -> dict:
        pass
