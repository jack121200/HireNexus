from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_hr
from app.core.exceptions import APIError
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.chat import (
    ConversationsResponse,
    HrConversationEnsureRequest,
    MarkReadResponse,
    MessagesResponse,
    SendMessageRequest,
    SendMessageResponse,
)
from app.schemas.common import meta_from_page
from app.services.chat_service import (
    assert_user_in_conversation,
    ensure_conversation,
    get_conversation,
    list_conversations,
    list_messages,
    mark_conversation_read,
    other_user_id,
    serialize_conversation,
    serialize_message,
    send_message,
    unread_total,
)
from app.services.job_service import get_job
from app.services.notification_service import create_notification, get_unread_count, serialize_notification
from app.services.realtime import broadcast_conversation, broadcast_user


router = APIRouter(prefix="/api/hr/chat", tags=["hr-chat"])


@router.get("/conversations", response_model=ConversationsResponse)
def conversations(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db),
) -> ConversationsResponse:
    items, meta = list_conversations(db, current_user=current_user, page=page, page_size=page_size)
    return ConversationsResponse(items=items, meta=meta_from_page(meta), unread_total=unread_total(db, current_user=current_user))


@router.post("/conversations/ensure", response_model=SendMessageResponse)
def ensure(
    payload: HrConversationEnsureRequest,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db),
) -> SendMessageResponse:
    candidate = db.get(User, payload.candidate_user_id)
    if not candidate or candidate.role != UserRole.candidate:
        raise APIError(status_code=404, code="candidate_not_found", detail="Candidate not found")

    if payload.job_id:
        job = get_job(db, job_id=payload.job_id)
        if job.hr_user_id != current_user.id:
            raise APIError(status_code=403, code="job_forbidden", detail="Job does not belong to HR user")

    conversation = ensure_conversation(
        db,
        candidate_user_id=payload.candidate_user_id,
        hr_user_id=current_user.id,
        job_id=payload.job_id,
    )
    db.commit()
    conversation = get_conversation(db, conversation_id=conversation.id)
    return SendMessageResponse(message={"conversation": serialize_conversation(db, conversation=conversation, current_user=current_user)})


@router.get("/conversations/{conversation_id}/messages", response_model=MessagesResponse)
def messages(
    conversation_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db),
) -> MessagesResponse:
    conversation = get_conversation(db, conversation_id=conversation_id)
    assert_user_in_conversation(conversation=conversation, user=current_user)
    items, meta = list_messages(db, conversation=conversation, page=page, page_size=page_size)
    return MessagesResponse(conversation_id=conversation.id, items=items, meta=meta_from_page(meta))


@router.post("/conversations/{conversation_id}/messages", response_model=SendMessageResponse)
async def send(
    conversation_id: int,
    payload: SendMessageRequest,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db),
) -> SendMessageResponse:
    conversation = get_conversation(db, conversation_id=conversation_id)
    assert_user_in_conversation(conversation=conversation, user=current_user)

    message = send_message(db, conversation=conversation, sender=current_user, content=payload.content)

    receiver_id = other_user_id(conversation=conversation, current_user=current_user)
    chat_notification = create_notification(
        db,
        user_id=receiver_id,
        type="chat_message",
        title="New Message",
        body=f"{current_user.full_name} sent you a message",
        data={"conversation_id": conversation.id, "message_id": message.id},
    )

    db.commit()
    db.refresh(message)
    db.refresh(chat_notification)

    await broadcast_conversation(
        conversation_id=conversation.id,
        event="chat.message",
        data={"message": serialize_message(message)},
    )

    updated_conversation = get_conversation(db, conversation_id=conversation.id)
    await broadcast_user(
        user_id=current_user.id,
        event="chat.updated",
        data={
            "conversation": serialize_conversation(db, conversation=updated_conversation, current_user=current_user),
            "unread_total": unread_total(db, current_user=current_user),
        },
    )

    receiver_user = db.get(User, receiver_id)
    if receiver_user:
        await broadcast_user(
            user_id=receiver_id,
            event="chat.updated",
            data={
                "conversation": serialize_conversation(db, conversation=updated_conversation, current_user=receiver_user),
                "unread_total": unread_total(db, current_user=receiver_user),
            },
        )

        receiver_unread_notifications = get_unread_count(db, user_id=receiver_id)
        await broadcast_user(
            user_id=receiver_id,
            event="notification.created",
            data={
                "notification": serialize_notification(chat_notification),
                "unread_count": receiver_unread_notifications,
            },
        )

    return SendMessageResponse(message=serialize_message(message))


@router.post("/conversations/{conversation_id}/read", response_model=MarkReadResponse)
async def mark_read_route(
    conversation_id: int,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db),
) -> MarkReadResponse:
    conversation = get_conversation(db, conversation_id=conversation_id)
    count = mark_conversation_read(db, conversation=conversation, user=current_user)
    db.commit()

    await broadcast_user(
        user_id=current_user.id,
        event="chat.unread_total",
        data={"unread_total": unread_total(db, current_user=current_user)},
    )

    return MarkReadResponse(marked_count=count)