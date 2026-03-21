from datetime import date, time

from sqlalchemy import BigInteger, Date, Float, ForeignKey, Index, String, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class IntradayTick(Base):
    __tablename__ = "intraday_ticks"
    __table_args__ = (Index("ix_intraday_ticks_stock_date", "stock_id", "date"),)

    stock_id: Mapped[str] = mapped_column(
        String(10), ForeignKey("stocks.stock_id"), primary_key=True
    )
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    tick_time: Mapped[time] = mapped_column(Time, primary_key=True)
    price: Mapped[float] = mapped_column(Float)
    price_change: Mapped[float] = mapped_column(Float)
    volume: Mapped[int] = mapped_column(BigInteger)
