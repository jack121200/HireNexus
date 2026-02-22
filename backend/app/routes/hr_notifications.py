from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_hr
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import meta_from_page
from app.schemas.notification import (
    NotificationMarkReadResponse,
    NotificationUnreadCountResponse,
    NotificationsResponse,
)
from app.services.notification_service import (
    get_notifications_page,
    get_unread_count,
    mark_all_read,
    mark_read,
    serialize_notification,
)
from app.services.realtime import broadcast_user


router = APIRouter(prefix="/api/hr/notifications", tags=["hr-notifications"])


@router.get("", response_model=NotificationsResponse)
async def list_notifications(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=15, ge=1, le=50),
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db),
) -> NotificationsResponse:
    notifications, meta = get_notifications_page(db, user_id=current_user.id, page=page, page_size=page_size)
    unread = get_unread_count(db, user_id=current_user.id)
    return NotificationsResponse(
        items=[serialize_notification(n) for n in notifications],
        meta=meta_from_page(meta),
        unread_count=unread,
    )


@router.get("/unread-count", response_model=NotificationUnreadCountResponse)
async def unread_count(current_user: User = Depends(get_current_hr), db: Session = Depends(get_db)) -> NotificationUnreadCountResponse:
    return NotificationUnreadCountResponse(unread_count=get_unread_count(db, user_id=current_user.id))


@router.post("/{notification_id}/read", response_model=NotificationMarkReadResponse)
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db),
) -> NotificationMarkReadResponse:
    notification = mark_read(db, user_id=current_user.id, notification_id=notification_id)
    db.commit()
    db.refresh(notification)
    unread = get_unread_count(db, user_id=current_user.id)

    await broadcast_user(
        user_id=current_user.id,
        event="notifications.unread_count",
        data={"unread_count": unread},
    )

    return NotificationMarkReadResponse(notification=serialize_notification(notification), unread_count=unread)


@router.post("/mark-all-read", response_model=NotificationUnreadCountResponse)
async def mark_all(
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db),
) -> NotificationUnreadCountResponse:
    mark_all_read(db, user_id=current_user.id)
    db.commit()
    unread = get_unread_count(db, user_id=current_user.id)
    await broadcast_user(
        user_id=current_user.id,
        event="notifications.unread_count",
        data={"unread_count": unread},
    )
    return NotificationUnreadCountResponse(unread_count=unread)