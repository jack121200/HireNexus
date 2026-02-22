from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.core.exceptions import APIError
from app.models.notification import Notification
from app.services.pagination import paginate


def serialize_notification(notification: Notification) -> dict[str, Any]:
    return {
        "id": notification.id,
        "type": notification.type,
        "title": notification.title,
        "body": notification.body,
        "data": notification.data_json,
        "is_read": notification.is_read,
        "read_at": notification.read_at.isoformat() if notification.read_at else None,
        "created_at": notification.created_at.isoformat(),
    }


def create_notification(
    db: Session,
    *,
    user_id: int,
    type: str,
    title: str,
    body: str,
    data: dict[str, Any] | None = None,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        type=type,
        title=title,
        body=body,
        data_json=data or {},
        is_read=False,
    )
    db.add(notification)
    db.flush()
    return notification


def get_notifications_page(db: Session, *, user_id: int, page: int, page_size: int):
    stmt: Select = (
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
    )
    return paginate(db, stmt, page=page, page_size=page_size)


def get_unread_count(db: Session, *, user_id: int) -> int:
    stmt = select(func.count(Notification.id)).where(
        Notification.user_id == user_id,
        Notification.is_read.is_(False),
    )
    return int(db.scalar(stmt) or 0)


def mark_read(db: Session, *, user_id: int, notification_id: int) -> Notification:
    notification = db.get(Notification, notification_id)
    if not notification or notification.user_id != user_id:
        raise APIError(status_code=404, code="notification_not_found", detail="Notification not found")

    if not notification.is_read:
        notification.is_read = True
        notification.read_at = datetime.now(timezone.utc)
        db.add(notification)
        db.flush()
    return notification


def mark_all_read(db: Session, *, user_id: int) -> int:
    stmt = select(Notification).where(Notification.user_id == user_id, Notification.is_read.is_(False))
    notifications = db.execute(stmt).scalars().all()
    now = datetime.now(timezone.utc)
    for notification in notifications:
        notification.is_read = True
        notification.read_at = now
        db.add(notification)
    db.flush()
    return len(notifications)