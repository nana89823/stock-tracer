import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response, StreamingResponse
from sqlalchemy.orm import selectinload

from app.auth.security import get_current_user
from app.database import get_db
from app.engine.strategies import BUILTIN_STRATEGIES
from app.models.backtest import Backtest, BacktestDailyReturn
from app.models.strategy import Strategy
from app.models.user import User
from app.schemas.backtest import (
    BacktestCreate,
    BacktestDailyReturnResponse,
    BacktestListResponse,
    BacktestResponse,
    StrategyCreate,
    StrategyResponse,
)
from app.tasks.backtest_task import run_backtest_task

router = APIRouter()


async def _seed_builtin_strategies(db: AsyncSession) -> None:
    """Seed built-in strategies if they don't exist yet."""
    result = await db.execute(
        select(Strategy).where(Strategy.is_builtin == True)  # noqa: E712
    )
    existing = {s.strategy_type for s in result.scalars().all()}

    for strategy_type, info in BUILTIN_STRATEGIES.items():
        if strategy_type not in existing:
            db.add(Strategy(
                name=info["name"],
                description=info["description"],
                strategy_type=strategy_type,
                is_builtin=True,
                params=info["default_params"],
                created_by=None,
            ))

    await db.commit()


# --- Strategy endpoints ---


@router.get("/strategies/", response_model=list[StrategyResponse])
async def list_strategies(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    await _seed_builtin_strategies(db)
    result = await db.execute(select(Strategy).order_by(Strategy.id))
    return result.scalars().all()


@router.post("/strategies/", response_model=StrategyResponse, status_code=201)
async def create_strategy(
    payload: StrategyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.strategy_type not in BUILTIN_STRATEGIES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown strategy_type: {payload.strategy_type}. "
                   f"Available: {list(BUILTIN_STRATEGIES.keys())}",
        )

    # Validate params keys against strategy's default_params
    if payload.params:
        allowed_keys = set(BUILTIN_STRATEGIES[payload.strategy_type]["default_params"].keys())
        invalid_keys = set(payload.params.keys()) - allowed_keys
        if invalid_keys:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid params: {sorted(invalid_keys)}. "
                       f"Allowed: {sorted(allowed_keys)}",
            )

    strategy = Strategy(
        name=payload.name,
        description=payload.description,
        strategy_type=payload.strategy_type,
        is_builtin=False,
        params=payload.params,
        created_by=current_user.id,
    )
    db.add(strategy)
    await db.commit()
    await db.refresh(strategy)
    return strategy


# --- Backtest endpoints ---


@router.post("/", response_model=BacktestListResponse, status_code=201)
async def create_backtest(
    payload: BacktestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Validate strategy exists
    result = await db.execute(
        select(Strategy).where(Strategy.id == payload.strategy_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Strategy not found")

    if payload.start_date >= payload.end_date:
        raise HTTPException(status_code=400, detail="start_date must be before end_date")

    backtest = Backtest(
        strategy_id=payload.strategy_id,
        stock_id=payload.stock_id if payload.mode == "single" else None,
        start_date=payload.start_date,
        end_date=payload.end_date,
        initial_capital=payload.initial_capital,
        status="pending",
        created_by=current_user.id,
        mode=payload.mode,
        stock_ids=payload.stock_ids if payload.mode != "single" else None,
        risk_params=payload.risk_params,
    )
    db.add(backtest)
    await db.commit()
    await db.refresh(backtest)

    run_backtest_task.delay(backtest.id)

    return backtest


@router.get("/", response_model=list[BacktestListResponse])
async def list_backtests(
    response: Response,
    skip: int = 0,
    limit: int = Query(default=20, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    base = (
        select(Backtest)
        .where(Backtest.created_by == current_user.id)
    )

    # Total count
    count_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total = count_result.scalar_one()

    # Paginated results
    stmt = base.order_by(Backtest.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)

    response.headers["X-Total-Count"] = str(total)
    return result.scalars().all()


@router.get("/{backtest_id}", response_model=BacktestResponse)
async def get_backtest(
    backtest_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Backtest)
        .where(Backtest.id == backtest_id, Backtest.created_by == current_user.id)
        .options(selectinload(Backtest.trades), selectinload(Backtest.daily_returns))
    )
    backtest = result.scalar_one_or_none()
    if not backtest:
        raise HTTPException(status_code=404, detail="Backtest not found")

    # Build the base response data
    resp = BacktestResponse.model_validate(backtest)

    # For batch mode: extract per_stock_results from the JSONB result field
    if backtest.mode == "batch" and backtest.result:
        resp.per_stock_results = backtest.result.get("per_stock_results")

    # For portfolio mode: separate portfolio-level and per-stock daily returns
    if backtest.mode == "portfolio":
        portfolio_returns = []
        per_stock_returns: dict[str, list[BacktestDailyReturnResponse]] = {}

        for dr in backtest.daily_returns:
            dr_resp = BacktestDailyReturnResponse.model_validate(dr)
            if dr.stock_id is None:
                portfolio_returns.append(dr_resp)
            else:
                per_stock_returns.setdefault(dr.stock_id, []).append(dr_resp)

        resp.portfolio_daily_returns = portfolio_returns
        resp.per_stock_daily_returns = per_stock_returns if per_stock_returns else None

    return resp


@router.get("/{backtest_id}/export")
async def export_backtest_csv(
    backtest_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Backtest)
        .where(Backtest.id == backtest_id, Backtest.created_by == current_user.id)
        .options(selectinload(Backtest.trades))
    )
    backtest = result.scalar_one_or_none()
    if not backtest:
        raise HTTPException(status_code=404, detail="Backtest not found")

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "action", "stock_id", "price", "shares", "commission", "tax", "pnl", "reason"])

    for trade in sorted(backtest.trades, key=lambda t: t.trade_date):
        writer.writerow([
            trade.trade_date.isoformat(),
            trade.direction,
            trade.stock_id,
            trade.price,
            trade.quantity,
            trade.commission,
            trade.tax,
            trade.realized_pnl if trade.realized_pnl is not None else "",
            trade.reason,
        ])

    output.seek(0)
    filename = f"backtest_{backtest_id}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
