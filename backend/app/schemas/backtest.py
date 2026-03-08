from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


# Strategy schemas

class StrategyCreate(BaseModel):
    name: str
    description: str | None = None
    strategy_type: str
    params: dict | None = None


class StrategyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    strategy_type: str
    is_builtin: bool
    params: dict | None
    created_by: int | None
    created_at: datetime
    updated_at: datetime


# Backtest schemas

class BacktestCreate(BaseModel):
    strategy_id: int
    stock_id: str
    start_date: date
    end_date: date
    initial_capital: float = 1000000.0


class BacktestTradeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    backtest_id: int
    trade_date: date
    stock_id: str
    direction: str
    price: float
    quantity: int
    commission: float
    tax: float
    realized_pnl: float | None


class BacktestDailyReturnResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    backtest_id: int
    date: date
    position_value: float
    cash: float
    total_equity: float
    daily_return: float | None


class BacktestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    strategy_id: int
    stock_id: str
    start_date: date
    end_date: date
    initial_capital: float
    status: str
    error_message: str | None
    result: dict | None
    created_by: int
    created_at: datetime
    completed_at: datetime | None
    trades: list[BacktestTradeResponse] = []
    daily_returns: list[BacktestDailyReturnResponse] = []


class BacktestListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    strategy_id: int
    stock_id: str
    start_date: date
    end_date: date
    initial_capital: float
    status: str
    result: dict | None
    created_by: int
    created_at: datetime
    completed_at: datetime | None
