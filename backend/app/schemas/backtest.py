from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


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

ALLOWED_RISK_PARAM_KEYS = {
    "stop_loss_pct",
    "take_profit_pct",
    "trailing_stop_pct",
    "position_size_pct",
    "allow_scale_in",
    "max_scale_in_times",
}


class BacktestCreate(BaseModel):
    strategy_id: int
    stock_id: str | None = None
    start_date: date
    end_date: date
    initial_capital: float = 1000000.0
    mode: Literal["single", "batch", "portfolio"] = "single"
    stock_ids: list[str] | None = None
    risk_params: dict | None = None

    @model_validator(mode="after")
    def validate_mode_stocks(self):
        if self.mode == "single":
            if not self.stock_id:
                raise ValueError("stock_id is required for single mode")
            # Ignore stock_ids in single mode
            self.stock_ids = None
        else:
            # batch or portfolio
            if not self.stock_ids or len(self.stock_ids) < 2:
                raise ValueError(
                    "stock_ids must contain at least 2 items for batch/portfolio mode"
                )
            if len(self.stock_ids) > 20:
                raise ValueError(
                    "stock_ids must contain at most 20 items"
                )
            for sid in self.stock_ids:
                if not isinstance(sid, str) or not sid.strip():
                    raise ValueError("Each stock_id must be a non-empty string")
            # Ignore stock_id in batch/portfolio mode
            self.stock_id = None
        return self

    @field_validator("risk_params")
    @classmethod
    def validate_risk_params(cls, v):
        if v is None:
            return v
        invalid_keys = set(v.keys()) - ALLOWED_RISK_PARAM_KEYS
        if invalid_keys:
            raise ValueError(
                f"Invalid risk_params keys: {sorted(invalid_keys)}. "
                f"Allowed: {sorted(ALLOWED_RISK_PARAM_KEYS)}"
            )
        # Validate numeric values > 0 when set
        for key in ("stop_loss_pct", "take_profit_pct", "trailing_stop_pct", "position_size_pct"):
            if key in v and v[key] is not None:
                if not isinstance(v[key], (int, float)) or v[key] <= 0:
                    raise ValueError(f"{key} must be a positive number")
        # Validate max_scale_in_times >= 0
        if "max_scale_in_times" in v and v["max_scale_in_times"] is not None:
            if not isinstance(v["max_scale_in_times"], int) or v["max_scale_in_times"] < 0:
                raise ValueError("max_scale_in_times must be a non-negative integer")
        # Validate allow_scale_in is bool
        if "allow_scale_in" in v and v["allow_scale_in"] is not None:
            if not isinstance(v["allow_scale_in"], bool):
                raise ValueError("allow_scale_in must be a boolean")
        return v


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
    reason: str = "strategy"


class BacktestDailyReturnResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    backtest_id: int
    date: date
    stock_id: str | None = None
    position_value: float
    cash: float
    total_equity: float
    daily_return: float | None


class BacktestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    strategy_id: int
    stock_id: str | None
    start_date: date
    end_date: date
    initial_capital: float
    status: str
    error_message: str | None
    result: dict | None
    created_by: int
    created_at: datetime
    completed_at: datetime | None
    mode: str = "single"
    stock_ids: list[str] | None = None
    risk_params: dict | None = None
    trades: list[BacktestTradeResponse] = []
    daily_returns: list[BacktestDailyReturnResponse] = []
    per_stock_results: dict | None = None
    portfolio_daily_returns: list[BacktestDailyReturnResponse] | None = None
    per_stock_daily_returns: dict[str, list[BacktestDailyReturnResponse]] | None = None


class BacktestListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    strategy_id: int
    stock_id: str | None
    start_date: date
    end_date: date
    initial_capital: float
    status: str
    result: dict | None
    created_by: int
    created_at: datetime
    completed_at: datetime | None
    mode: str = "single"
    stock_ids: list[str] | None = None
    risk_params: dict | None = None
