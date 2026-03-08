from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.auth.security import get_current_user
from app.cache import get_cache, set_cache
from app.database import get_db
from app.models.broker_trading import BrokerTrading
from app.models.major_holders import MajorHolders
from app.models.margin_trading import MarginTrading
from app.models.raw_chip import RawChip
from app.models.raw_price import RawPrice
from app.models.stock import Stock
from app.models.user import User
from app.schemas.stock import (
    BrokerTradingResponse,
    MajorHoldersResponse,
    MarginTradingResponse,
    RawChipResponse,
    RawPriceResponse,
    StockResponse,
)

router = APIRouter()


@router.get("/", response_model=list[StockResponse])
async def list_stocks(
    response: Response,
    q: str | None = None,
    skip: int = 0,
    limit: int = Query(default=20, le=100),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    cache_key = f"stocks:search:{q}:{skip}:{limit}"
    cached = await get_cache(cache_key)
    if cached is not None:
        response.headers["X-Total-Count"] = str(cached["total"])
        return cached["data"]

    base = select(Stock)
    if q:
        base = base.where(Stock.stock_id.contains(q) | Stock.stock_name.contains(q))

    # Total count
    count_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total = count_result.scalar_one()

    # Paginated results
    stmt = base.offset(skip).limit(limit)
    result = await db.execute(stmt)
    rows = result.scalars().all()

    response.headers["X-Total-Count"] = str(total)

    data = [StockResponse.model_validate(r).model_dump() for r in rows]
    await set_cache(cache_key, {"total": total, "data": data}, ttl=300)
    return rows


@router.get("/{stock_id}", response_model=StockResponse)
async def get_stock(
    stock_id: str,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    cache_key = f"stocks:info:{stock_id}"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    result = await db.execute(select(Stock).where(Stock.stock_id == stock_id))
    stock = result.scalar_one_or_none()
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")

    data = StockResponse.model_validate(stock).model_dump()
    await set_cache(cache_key, data, ttl=3600)
    return stock


@router.get("/{stock_id}/prices", response_model=list[RawPriceResponse])
async def get_prices(
    stock_id: str,
    start_date: date | None = None,
    end_date: date | None = None,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    cache_key = f"stocks:prices:{stock_id}:{start_date}:{end_date}"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    stmt = select(RawPrice).where(RawPrice.stock_id == stock_id)
    if start_date:
        stmt = stmt.where(RawPrice.date >= start_date)
    if end_date:
        stmt = stmt.where(RawPrice.date <= end_date)
    stmt = stmt.order_by(RawPrice.date)
    result = await db.execute(stmt)
    rows = result.scalars().all()

    data = [RawPriceResponse.model_validate(r).model_dump(mode="json") for r in rows]
    await set_cache(cache_key, data, ttl=1800)
    return rows


@router.get("/{stock_id}/chips", response_model=list[RawChipResponse])
async def get_chips(
    stock_id: str,
    start_date: date | None = None,
    end_date: date | None = None,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    cache_key = f"stocks:chips:{stock_id}:{start_date}:{end_date}"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    stmt = select(RawChip).where(RawChip.stock_id == stock_id)
    if start_date:
        stmt = stmt.where(RawChip.date >= start_date)
    if end_date:
        stmt = stmt.where(RawChip.date <= end_date)
    stmt = stmt.order_by(RawChip.date)
    result = await db.execute(stmt)
    rows = result.scalars().all()

    data = [RawChipResponse.model_validate(r).model_dump(mode="json") for r in rows]
    await set_cache(cache_key, data, ttl=1800)
    return rows


@router.get("/{stock_id}/holders", response_model=list[MajorHoldersResponse])
async def get_holders(
    stock_id: str,
    date_param: date | None = None,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    cache_key = f"stocks:holders:{stock_id}:{date_param}"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    stmt = select(MajorHolders).where(MajorHolders.stock_id == stock_id)
    if date_param:
        stmt = stmt.where(MajorHolders.date == date_param)
    stmt = stmt.order_by(MajorHolders.date, MajorHolders.holding_level)
    result = await db.execute(stmt)
    rows = result.scalars().all()

    data = [MajorHoldersResponse.model_validate(r).model_dump(mode="json") for r in rows]
    await set_cache(cache_key, data, ttl=3600)
    return rows


@router.get("/{stock_id}/margin", response_model=list[MarginTradingResponse])
async def get_margin_trading(
    stock_id: str,
    start_date: date | None = None,
    end_date: date | None = None,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    cache_key = f"stocks:margin:{stock_id}:{start_date}:{end_date}"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    stmt = select(MarginTrading).where(MarginTrading.stock_id == stock_id)
    if start_date:
        stmt = stmt.where(MarginTrading.date >= start_date)
    if end_date:
        stmt = stmt.where(MarginTrading.date <= end_date)
    stmt = stmt.order_by(MarginTrading.date)
    result = await db.execute(stmt)
    rows = result.scalars().all()

    data = [MarginTradingResponse.model_validate(r).model_dump(mode="json") for r in rows]
    await set_cache(cache_key, data, ttl=1800)
    return rows


@router.get("/{stock_id}/brokers", response_model=list[BrokerTradingResponse])
async def get_broker_trading(
    stock_id: str,
    start_date: date | None = None,
    end_date: date | None = None,
    broker_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    cache_key = f"stocks:brokers:{stock_id}:{start_date}:{end_date}:{broker_id}"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    stmt = select(BrokerTrading).where(BrokerTrading.stock_id == stock_id)
    if start_date:
        stmt = stmt.where(BrokerTrading.date >= start_date)
    if end_date:
        stmt = stmt.where(BrokerTrading.date <= end_date)
    if broker_id:
        stmt = stmt.where(BrokerTrading.broker_id == broker_id)
    stmt = stmt.order_by(BrokerTrading.date, BrokerTrading.broker_id)
    result = await db.execute(stmt)
    rows = result.scalars().all()

    data = [BrokerTradingResponse.model_validate(r).model_dump(mode="json") for r in rows]
    await set_cache(cache_key, data, ttl=1800)
    return rows
