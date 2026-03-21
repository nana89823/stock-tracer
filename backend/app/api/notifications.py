import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import get_current_user
from app.cache import delete_cache, get_cache, set_cache
from app.database import get_db
from app.models.notification import Notification
from app.models.user import User
from app.schemas.alert import NotificationResponse, UnreadCountResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=list[NotificationResponse])
async def list_notifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/unread-count", response_model=UnreadCountResponse)
async def unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cache_key = f"notif:unread:{current_user.id}"
    cached = await get_cache(cache_key)
    if cached is not None:
        return UnreadCountResponse(count=cached)

    result = await db.execute(
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == current_user.id, Notification.is_read.is_(False))
    )
    count = result.scalar()
    await set_cache(cache_key, count, ttl=10)
    return UnreadCountResponse(count=count)


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification).where(Notification.id == notification_id)
    )
    notif = result.scalar_one_or_none()
    if not notif or notif.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="通知不存在")

    notif.is_read = True
    await db.commit()
    await db.refresh(notif)
    await delete_cache(f"notif:unread:{current_user.id}")
    return notif


@router.post("/read-all", status_code=204)
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        update(Notification)
        .where(Notification.user_id == current_user.id, Notification.is_read.is_(False))
        .values(is_read=True)
    )
    await db.commit()
    await delete_cache(f"notif:unread:{current_user.id}")
