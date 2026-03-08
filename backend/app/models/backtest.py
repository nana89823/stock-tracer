from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Backtest(Base):
    __tablename__ = "backtests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    strategy_id: Mapped[int] = mapped_column(Integer, ForeignKey("strategies.id"))
    stock_id: Mapped[str] = mapped_column(String(10), ForeignKey("stocks.stock_id"))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    initial_capital: Mapped[float] = mapped_column(Float, default=1000000.0)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    trades: Mapped[list["BacktestTrade"]] = relationship(
        back_populates="backtest", cascade="all, delete-orphan"
    )
    daily_returns: Mapped[list["BacktestDailyReturn"]] = relationship(
        back_populates="backtest", cascade="all, delete-orphan"
    )


class BacktestTrade(Base):
    __tablename__ = "backtest_trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    backtest_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("backtests.id", ondelete="CASCADE")
    )
    trade_date: Mapped[date] = mapped_column(Date)
    stock_id: Mapped[str] = mapped_column(String(10))
    direction: Mapped[str] = mapped_column(String(10))
    price: Mapped[float] = mapped_column(Float)
    quantity: Mapped[int] = mapped_column(Integer)
    commission: Mapped[float] = mapped_column(Float)
    tax: Mapped[float] = mapped_column(Float)
    realized_pnl: Mapped[float | None] = mapped_column(Float, nullable=True)

    backtest: Mapped["Backtest"] = relationship(back_populates="trades")


class BacktestDailyReturn(Base):
    __tablename__ = "backtest_daily_returns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    backtest_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("backtests.id", ondelete="CASCADE")
    )
    date: Mapped[date] = mapped_column(Date)
    position_value: Mapped[float] = mapped_column(Float)
    cash: Mapped[float] = mapped_column(Float)
    total_equity: Mapped[float] = mapped_column(Float)
    daily_return: Mapped[float | None] = mapped_column(Float, nullable=True)

    backtest: Mapped["Backtest"] = relationship(back_populates="daily_returns")
