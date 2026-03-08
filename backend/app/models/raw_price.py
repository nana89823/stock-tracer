from datetime import date

from sqlalchemy import BigInteger, Date, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class RawPrice(Base):
    __tablename__ = "raw_prices"
    __table_args__ = (Index("ix_raw_prices_stock_date", "stock_id", "date"),)

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    stock_id: Mapped[str] = mapped_column(
        String(10), ForeignKey("stocks.stock_id"), primary_key=True
    )
    stock_name: Mapped[str] = mapped_column(String(50))
    trade_volume: Mapped[int] = mapped_column(BigInteger)
    trade_value: Mapped[int] = mapped_column(BigInteger)
    open_price: Mapped[float] = mapped_column(Float)
    high_price: Mapped[float] = mapped_column(Float)
    low_price: Mapped[float] = mapped_column(Float)
    close_price: Mapped[float] = mapped_column(Float)
    price_change: Mapped[float] = mapped_column(Float)
    transaction_count: Mapped[int] = mapped_column(Integer)
