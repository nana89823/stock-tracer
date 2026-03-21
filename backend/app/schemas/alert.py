from datetime import datetime
from pydantic import BaseModel, field_validator
from typing import Literal


class AlertCreate(BaseModel):
    stock_id: str
    condition_type: Literal["above", "below"]
    threshold: float

    @field_validator("threshold")
    @classmethod
    def threshold_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("目標價必須大於 0")
        return v


class AlertUpdate(BaseModel):
    condition_type: Literal["above", "below"] | None = None
    threshold: float | None = None
    is_active: bool | None = None

    @field_validator("threshold")
    @classmethod
    def threshold_positive(cls, v: float | None) -> float | None:
        if v is not None and v <= 0:
            raise ValueError("目標價必須大於 0")
        return v


class AlertResponse(BaseModel):
    id: int
    stock_id: str
    stock_name: str | None = None
    condition_type: str
    threshold: float
    is_active: bool
    is_triggered: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class NotificationResponse(BaseModel):
    id: int
    alert_id: int | None
    title: str
    message: str
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UnreadCountResponse(BaseModel):
    count: int
