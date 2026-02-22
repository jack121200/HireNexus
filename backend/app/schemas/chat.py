from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.common import PaginationMeta


class ConversationEnsureRequest(BaseModel):
    hr_user_id: int = Field(gt=0)
    job_id: int | None = Field(default=None, gt=0)


class HrConversationEnsureRequest(BaseModel):
    candidate_user_id: int = Field(gt=0)
    job_id: int | None = Field(default=None, gt=0)


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=5000)


class ConversationsResponse(BaseModel):
    items: list[dict]
    meta: PaginationMeta
    unread_total: int


class MessagesResponse(BaseModel):
    conversation_id: int
    items: list[dict]
    meta: PaginationMeta


class SendMessageResponse(BaseModel):
    message: dict


class MarkReadResponse(BaseModel):
    marked_count: int
