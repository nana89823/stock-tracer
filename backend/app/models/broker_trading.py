from datetime import date

from sqlalchemy import BigInteger, Date, Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class BrokerTrading(Base):
    __tablename__ = "broker_trading"
    __table_args__ = (Index("ix_broker_trading_stock_date", "stock_id", "date"),)

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    stock_id: Mapped[str] = mapped_column(
        String(10), ForeignKey("stocks.stock_id"), primary_key=True
    )
    broker_id: Mapped[str] = mapped_column(String(10), primary_key=True)
    broker_name: Mapped[str] = mapped_column(String(50))
    price: Mapped[float] = mapped_column(Float)
    buy_volume: Mapped[int] = mapped_column(BigInteger)
    sell_volume: Mapped[int] = mapped_column(BigInteger)
