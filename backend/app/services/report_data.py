"""Data queries for daily email report sections."""

import logging
from datetime import date

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models import (
    MajorHolders,
    MarginTrading,
    Notification,
    RawChip,
    RawPrice,
    Watchlist,
)

logger = logging.getLogger(__name__)


def get_watchlist_prices(
    session: Session, user_id: int, target_date: date
) -> list[dict]:
    """Get closing prices for user's watchlist stocks."""
    stmt = (
        select(
            RawPrice.stock_id,
            RawPrice.stock_name,
            RawPrice.open_price,
            RawPrice.high_price,
            RawPrice.low_price,
            RawPrice.close_price,
            RawPrice.price_change,
            RawPrice.trade_volume,
        )
        .join(Watchlist, Watchlist.stock_id == RawPrice.stock_id)
        .where(Watchlist.user_id == user_id, RawPrice.date == target_date)
        .order_by(Watchlist.sort_order)
    )
    return [row._asdict() for row in session.execute(stmt).all()]


def get_watchlist_chips(
    session: Session, user_id: int, target_date: date
) -> list[dict]:
    """Get institutional investor data for user's watchlist stocks."""
    stmt = (
        select(
            RawChip.stock_id,
            RawChip.stock_name,
            RawChip.foreign_net,
            RawChip.trust_net,
            RawChip.dealer_net,
            RawChip.total_net,
        )
        .join(Watchlist, Watchlist.stock_id == RawChip.stock_id)
        .where(Watchlist.user_id == user_id, RawChip.date == target_date)
        .order_by(Watchlist.sort_order)
    )
    return [row._asdict() for row in session.execute(stmt).all()]


def get_watchlist_margin(
    session: Session, user_id: int, target_date: date
) -> list[dict]:
    """Get margin trading data for user's watchlist stocks."""
    stmt = (
        select(
            MarginTrading.stock_id,
            MarginTrading.margin_balance,
            MarginTrading.margin_balance_prev,
            MarginTrading.short_balance,
            MarginTrading.short_balance_prev,
            MarginTrading.offset,
        )
        .join(Watchlist, Watchlist.stock_id == MarginTrading.stock_id)
        .where(Watchlist.user_id == user_id, MarginTrading.date == target_date)
        .order_by(Watchlist.sort_order)
    )
    rows = session.execute(stmt).all()
    result = []
    for row in rows:
        d = row._asdict()
        d["margin_change"] = d["margin_balance"] - d["margin_balance_prev"]
        d["short_change"] = d["short_balance"] - d["short_balance_prev"]
        result.append(d)
    return result


def get_watchlist_holders(
    session: Session, user_id: int, target_date: date
) -> list[dict]:
    """Get major holders (>=400 shares) for user's watchlist.

    Uses the latest available date on or before target_date.
    """
    latest_date_stmt = select(func.max(MajorHolders.date)).where(
        MajorHolders.date <= target_date
    )
    latest_date = session.execute(latest_date_stmt).scalar()
    if not latest_date:
        return []

    prev_date_stmt = select(func.max(MajorHolders.date)).where(
        MajorHolders.date < latest_date
    )
    prev_date = session.execute(prev_date_stmt).scalar()

    wl_stmt = select(Watchlist.stock_id).where(Watchlist.user_id == user_id)
    watchlist_ids = [r[0] for r in session.execute(wl_stmt).all()]
    if not watchlist_ids:
        return []

    curr_stmt = (
        select(
            MajorHolders.stock_id,
            func.sum(MajorHolders.holding_ratio).label("ratio"),
            func.sum(MajorHolders.holder_count).label("count"),
        )
        .where(
            MajorHolders.date == latest_date,
            MajorHolders.stock_id.in_(watchlist_ids),
            MajorHolders.holding_level >= 12,
        )
        .group_by(MajorHolders.stock_id)
    )
    current = {
        r.stock_id: {"ratio": r.ratio, "count": r.count}
        for r in session.execute(curr_stmt).all()
    }

    prev = {}
    if prev_date:
        prev_stmt = (
            select(
                MajorHolders.stock_id,
                func.sum(MajorHolders.holding_ratio).label("ratio"),
                func.sum(MajorHolders.holder_count).label("count"),
            )
            .where(
                MajorHolders.date == prev_date,
                MajorHolders.stock_id.in_(watchlist_ids),
                MajorHolders.holding_level >= 12,
            )
            .group_by(MajorHolders.stock_id)
        )
        prev = {
            r.stock_id: {"ratio": r.ratio, "count": r.count}
            for r in session.execute(prev_stmt).all()
        }

    result = []
    for sid in watchlist_ids:
        if sid not in current:
            continue
        c = current[sid]
        p = prev.get(sid, {"ratio": 0, "count": 0})
        result.append(
            {
                "stock_id": sid,
                "holder_ratio": round(c["ratio"], 2),
                "holder_count": c["count"],
                "ratio_delta": round(c["ratio"] - p["ratio"], 2),
                "count_delta": c["count"] - p["count"],
                "data_date": latest_date.isoformat(),
            }
        )
    return result


def get_market_summary(session: Session, target_date: date) -> dict:
    """Get overall market statistics for the day."""
    up = case((RawPrice.price_change > 0, 1), else_=0)
    down = case((RawPrice.price_change < 0, 1), else_=0)
    flat = case((RawPrice.price_change == 0, 1), else_=0)
    price_stmt = select(
        func.sum(up).label("up_count"),
        func.sum(down).label("down_count"),
        func.sum(flat).label("flat_count"),
        func.sum(RawPrice.trade_volume).label("total_volume"),
    ).where(RawPrice.date == target_date)
    price_row = session.execute(price_stmt).one()

    chip_stmt = select(
        func.sum(RawChip.foreign_net).label("foreign_total"),
        func.sum(RawChip.trust_net).label("trust_total"),
        func.sum(RawChip.dealer_net).label("dealer_total"),
        func.sum(RawChip.total_net).label("inst_total"),
    ).where(RawChip.date == target_date)
    chip_row = session.execute(chip_stmt).one()

    return {
        "up_count": price_row.up_count or 0,
        "down_count": price_row.down_count or 0,
        "flat_count": price_row.flat_count or 0,
        "total_volume": price_row.total_volume or 0,
        "foreign_total": chip_row.foreign_total or 0,
        "trust_total": chip_row.trust_total or 0,
        "dealer_total": chip_row.dealer_total or 0,
        "inst_total": chip_row.inst_total or 0,
    }


def get_user_alerts(
    session: Session, user_id: int, target_date: date
) -> list[dict]:
    """Get alert notifications triggered today for the user."""
    stmt = (
        select(
            Notification.title,
            Notification.message,
            Notification.created_at,
        )
        .where(
            Notification.user_id == user_id,
            func.date(Notification.created_at) == target_date,
        )
        .order_by(Notification.created_at)
    )
    return [row._asdict() for row in session.execute(stmt).all()]
