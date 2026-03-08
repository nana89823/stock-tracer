from datetime import date

from sqlalchemy import BigInteger, Date, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class MajorHolders(Base):
    __tablename__ = "major_holders"
    __table_args__ = (Index("ix_major_holders_stock_date", "stock_id", "date"),)

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    stock_id: Mapped[str] = mapped_column(
        String(10), ForeignKey("stocks.stock_id"), primary_key=True
    )
    holding_level: Mapped[int] = mapped_column(Integer, primary_key=True)
    holder_count: Mapped[int] = mapped_column(Integer)
    share_count: Mapped[int] = mapped_column(BigInteger)
    holding_ratio: Mapped[float] = mapped_column(Float)
