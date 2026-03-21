import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import get_current_user
from app.database import get_db
from app.models.price_alert import PriceAlert
from app.models.stock import Stock
from app.models.user import User
from app.schemas.alert import AlertCreate, AlertUpdate, AlertResponse

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_ALERTS_PER_USER = 20


@router.get("/", response_model=list[AlertResponse])
async def list_alerts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PriceAlert, Stock.stock_name)
        .outerjoin(Stock, PriceAlert.stock_id == Stock.stock_id)
        .where(PriceAlert.user_id == current_user.id)
        .order_by(PriceAlert.created_at.desc())
    )
    rows = result.all()
    return [
        AlertResponse(
            id=alert.id,
            stock_id=alert.stock_id,
            stock_name=stock_name,
            condition_type=alert.condition_type,
            threshold=alert.threshold,
            is_active=alert.is_active,
            is_triggered=alert.is_triggered,
            created_at=alert.created_at,
            updated_at=alert.updated_at,
        )
        for alert, stock_name in rows
    ]


@router.post("/", response_model=AlertResponse, status_code=201)
async def create_alert(
    data: AlertCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Validate stock exists
    stock_result = await db.execute(
        select(Stock).where(Stock.stock_id == data.stock_id)
    )
    stock = stock_result.scalar_one_or_none()
    if not stock:
        raise HTTPException(status_code=404, detail="股票不存在")

    # Check limit
    count_result = await db.execute(
        select(func.count()).where(PriceAlert.user_id == current_user.id)
    )
    count = count_result.scalar()
    if count >= MAX_ALERTS_PER_USER:
        raise HTTPException(status_code=400, detail=f"最多只能設定 {MAX_ALERTS_PER_USER} 個提醒")

    alert = PriceAlert(
        user_id=current_user.id,
        stock_id=data.stock_id,
        condition_type=data.condition_type,
        threshold=data.threshold,
    )
    db.add(alert)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="提醒已存在")
    await db.refresh(alert)

    return AlertResponse(
        id=alert.id,
        stock_id=alert.stock_id,
        stock_name=stock.stock_name,
        condition_type=alert.condition_type,
        threshold=alert.threshold,
        is_active=alert.is_active,
        is_triggered=alert.is_triggered,
        created_at=alert.created_at,
        updated_at=alert.updated_at,
    )


@router.patch("/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: int,
    data: AlertUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PriceAlert).where(PriceAlert.id == alert_id)
    )
    alert = result.scalar_one_or_none()
    if not alert or alert.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="提醒不存在")

    if data.condition_type is not None:
        alert.condition_type = data.condition_type
    if data.threshold is not None:
        alert.threshold = data.threshold
    if data.is_active is not None:
        alert.is_active = data.is_active
        if data.is_active:
            alert.is_triggered = False  # Re-enable resets triggered

    await db.commit()
    await db.refresh(alert)

    stock_result = await db.execute(
        select(Stock.stock_name).where(Stock.stock_id == alert.stock_id)
    )
    stock_name = stock_result.scalar_one_or_none()

    return AlertResponse(
        id=alert.id,
        stock_id=alert.stock_id,
        stock_name=stock_name,
        condition_type=alert.condition_type,
        threshold=alert.threshold,
        is_active=alert.is_active,
        is_triggered=alert.is_triggered,
        created_at=alert.created_at,
        updated_at=alert.updated_at,
    )


@router.delete("/{alert_id}", status_code=204)
async def delete_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PriceAlert).where(PriceAlert.id == alert_id)
    )
    alert = result.scalar_one_or_none()
    if not alert or alert.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="提醒不存在")

    await db.delete(alert)
    await db.commit()
