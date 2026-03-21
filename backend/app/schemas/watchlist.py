from datetime import datetime

from pydantic import BaseModel


class WatchlistAdd(BaseModel):
    stock_id: str


class WatchlistItemResponse(BaseModel):
    id: int
    stock_id: str
    stock_name: str
    market_type: str
    close_price: float | None = None
    price_change: float | None = None
    change_percent: float | None = None
    sort_order: int
    created_at: datetime

    model_config = {"from_attributes": True}


class WatchlistCheckResponse(BaseModel):
    is_watched: bool
