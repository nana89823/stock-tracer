from datetime import date

from sqlalchemy import BigInteger, Date, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class RawChip(Base):
    __tablename__ = "raw_chips"
    __table_args__ = (Index("ix_raw_chips_stock_date", "stock_id", "date"),)

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    stock_id: Mapped[str] = mapped_column(
        String(10), ForeignKey("stocks.stock_id"), primary_key=True
    )
    stock_name: Mapped[str] = mapped_column(String(50))
    foreign_buy: Mapped[int] = mapped_column(BigInteger)
    foreign_sell: Mapped[int] = mapped_column(BigInteger)
    foreign_net: Mapped[int] = mapped_column(BigInteger)
    foreign_dealer_buy: Mapped[int] = mapped_column(BigInteger)
    foreign_dealer_sell: Mapped[int] = mapped_column(BigInteger)
    foreign_dealer_net: Mapped[int] = mapped_column(BigInteger)
    trust_buy: Mapped[int] = mapped_column(BigInteger)
    trust_sell: Mapped[int] = mapped_column(BigInteger)
    trust_net: Mapped[int] = mapped_column(BigInteger)
    dealer_net: Mapped[int] = mapped_column(BigInteger)
    dealer_self_buy: Mapped[int] = mapped_column(BigInteger)
    dealer_self_sell: Mapped[int] = mapped_column(BigInteger)
    dealer_self_net: Mapped[int] = mapped_column(BigInteger)
    dealer_hedge_buy: Mapped[int] = mapped_column(BigInteger)
    dealer_hedge_sell: Mapped[int] = mapped_column(BigInteger)
    dealer_hedge_net: Mapped[int] = mapped_column(BigInteger)
    total_net: Mapped[int] = mapped_column(BigInteger)
