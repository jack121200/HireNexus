from __future__ import annotations

from pydantic import BaseModel

from app.schemas.common import PaginationMeta


class NotificationsResponse(BaseModel):
    items: list[dict]
    meta: PaginationMeta
    unread_count: int


class NotificationMarkReadResponse(BaseModel):
    notification: dict
    unread_count: int


class NotificationUnreadCountResponse(BaseModel):
    unread_count: int