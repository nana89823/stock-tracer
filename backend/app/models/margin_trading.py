from datetime import date

from sqlalchemy import BigInteger, Date, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class MarginTrading(Base):
    __tablename__ = "margin_trading"
    __table_args__ = (Index("ix_margin_trading_stock_date", "stock_id", "date"),)

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    stock_id: Mapped[str] = mapped_column(
        String(10), ForeignKey("stocks.stock_id"), primary_key=True
    )
    margin_buy: Mapped[int] = mapped_column(BigInteger)
    margin_sell: Mapped[int] = mapped_column(BigInteger)
    margin_cash_repay: Mapped[int] = mapped_column(BigInteger)
    margin_balance_prev: Mapped[int] = mapped_column(BigInteger)
    margin_balance: Mapped[int] = mapped_column(BigInteger)
    margin_limit: Mapped[int] = mapped_column(BigInteger)
    short_buy: Mapped[int] = mapped_column(BigInteger)
    short_sell: Mapped[int] = mapped_column(BigInteger)
    short_cash_repay: Mapped[int] = mapped_column(BigInteger)
    short_balance_prev: Mapped[int] = mapped_column(BigInteger)
    short_balance: Mapped[int] = mapped_column(BigInteger)
    short_limit: Mapped[int] = mapped_column(BigInteger)
    offset: Mapped[int] = mapped_column(BigInteger)
    note: Mapped[str] = mapped_column(String(20))
