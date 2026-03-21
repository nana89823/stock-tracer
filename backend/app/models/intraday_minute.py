from datetime import date, time

from sqlalchemy import BigInteger, Date, Float, ForeignKey, Index, String, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class IntradayMinute(Base):
    __tablename__ = "intraday_minutes"
    __table_args__ = (Index("ix_intraday_minutes_stock_date", "stock_id", "date"),)

    stock_id: Mapped[str] = mapped_column(
        String(10), ForeignKey("stocks.stock_id"), primary_key=True
    )
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    minute_time: Mapped[time] = mapped_column(Time, primary_key=True)
    open_price: Mapped[float] = mapped_column(Float)
    high_price: Mapped[float] = mapped_column(Float)
    low_price: Mapped[float] = mapped_column(Float)
    close_price: Mapped[float] = mapped_column(Float)
    volume: Mapped[int] = mapped_column(BigInteger)
