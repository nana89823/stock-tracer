from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import get_current_user
from app.database import get_db
from app.models.raw_price import RawPrice
from app.models.stock import Stock
from app.models.user import User
from app.models.watchlist import Watchlist
from app.schemas.watchlist import (
    WatchlistAdd,
    WatchlistCheckResponse,
    WatchlistItemResponse,
)

router = APIRouter()

MAX_WATCHLIST_ITEMS = 50


@router.get("/", response_model=list[WatchlistItemResponse])
async def list_watchlist(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # 1. Get watchlist items with stock info
    result = await db.execute(
        select(Watchlist, Stock.stock_name, Stock.market_type)
        .join(Stock, Watchlist.stock_id == Stock.stock_id)
        .where(Watchlist.user_id == current_user.id)
        .order_by(Watchlist.sort_order, Watchlist.created_at.desc())
    )
    rows = result.all()

    if not rows:
        return []

    # 2. Batch fetch latest prices using window function
    stock_ids = [row[0].stock_id for row in rows]

    price_subq = (
        select(
            RawPrice.stock_id,
            RawPrice.close_price,
            RawPrice.price_change,
            func.row_number()
            .over(partition_by=RawPrice.stock_id, order_by=desc(RawPrice.date))
            .label("rn"),
        )
        .where(RawPrice.stock_id.in_(stock_ids))
        .subquery()
    )

    price_result = await db.execute(
        select(
            price_subq.c.stock_id,
            price_subq.c.close_price,
            price_subq.c.price_change,
        ).where(price_subq.c.rn == 1)
    )
    price_map = {r[0]: (r[1], r[2]) for r in price_result.all()}

    # 3. Build response
    items = []
    for watchlist_item, stock_name, market_type in rows:
        price_data = price_map.get(watchlist_item.stock_id)
        close_price = price_data[0] if price_data else None
        price_change_val = price_data[1] if price_data else None
        change_pct = None
        if (
            close_price is not None
            and price_change_val is not None
            and (close_price - price_change_val) != 0
        ):
            change_pct = round(
                price_change_val / (close_price - price_change_val) * 100, 2
            )

        items.append(
            WatchlistItemResponse(
                id=watchlist_item.id,
                stock_id=watchlist_item.stock_id,
                stock_name=stock_name,
                market_type=market_type,
                close_price=close_price,
                price_change=price_change_val,
                change_percent=change_pct,
                sort_order=watchlist_item.sort_order,
                created_at=watchlist_item.created_at,
            )
        )

    return items


@router.post("/", response_model=WatchlistItemResponse, status_code=status.HTTP_201_CREATED)
async def add_to_watchlist(
    payload: WatchlistAdd,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Validate stock exists
    stock_result = await db.execute(
        select(Stock).where(Stock.stock_id == payload.stock_id)
    )
    stock = stock_result.scalar_one_or_none()
    if not stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stock {payload.stock_id} not found",
        )

    # Check duplicate
    existing = await db.execute(
        select(Watchlist).where(
            Watchlist.user_id == current_user.id,
            Watchlist.stock_id == payload.stock_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Stock already in watchlist",
        )

    # Check 50 item limit
    count_result = await db.execute(
        select(func.count()).where(Watchlist.user_id == current_user.id)
    )
    count = count_result.scalar()
    if count >= MAX_WATCHLIST_ITEMS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Watchlist limit reached ({MAX_WATCHLIST_ITEMS} items max)",
        )

    # Create watchlist item
    item = Watchlist(
        user_id=current_user.id,
        stock_id=payload.stock_id,
        sort_order=count,  # append at the end
    )
    db.add(item)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Stock already in watchlist",
        )
    await db.refresh(item)

    # Fetch latest price for response
    price_result = await db.execute(
        select(RawPrice.close_price, RawPrice.price_change)
        .where(RawPrice.stock_id == payload.stock_id)
        .order_by(desc(RawPrice.date))
        .limit(1)
    )
    price_row = price_result.first()
    close_price = price_row[0] if price_row else None
    price_change_val = price_row[1] if price_row else None
    change_pct = None
    if close_price is not None and price_change_val is not None and (close_price - price_change_val) != 0:
        change_pct = round(
            price_change_val / (close_price - price_change_val) * 100, 2
        )

    return WatchlistItemResponse(
        id=item.id,
        stock_id=item.stock_id,
        stock_name=stock.stock_name,
        market_type=stock.market_type,
        close_price=close_price,
        price_change=price_change_val,
        change_percent=change_pct,
        sort_order=item.sort_order,
        created_at=item.created_at,
    )


@router.delete("/{stock_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_watchlist(
    stock_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        delete(Watchlist).where(
            Watchlist.user_id == current_user.id,
            Watchlist.stock_id == stock_id,
        )
    )
    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock not found in watchlist",
        )
    await db.commit()


@router.get("/check/{stock_id}", response_model=WatchlistCheckResponse)
async def check_watchlist(
    stock_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Watchlist.id).where(
            Watchlist.user_id == current_user.id,
            Watchlist.stock_id == stock_id,
        )
    )
    return WatchlistCheckResponse(is_watched=result.scalar_one_or_none() is not None)
