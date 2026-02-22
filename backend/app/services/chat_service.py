from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import APIError
from app.models.conversation import Conversation
from app.models.job import Job
from app.models.message import Message
from app.models.user import User, UserRole
from app.services.pagination import paginate


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def serialize_message(message: Message) -> dict[str, Any]:
    return {
        "id": message.id,
        "conversation_id": message.conversation_id,
        "sender_user_id": message.sender_user_id,
        "content": message.content,
        "message_type": message.message_type,
        "is_read": message.is_read,
        "read_at": message.read_at.isoformat() if message.read_at else None,
        "created_at": message.created_at.isoformat(),
    }


def _unread_count_for_conversation(db: Session, *, conversation: Conversation, current_user: User) -> int:
    if current_user.role == UserRole.candidate:
        last_read_at = conversation.candidate_last_read_at
    else:
        last_read_at = conversation.hr_last_read_at

    conditions = [
        Message.conversation_id == conversation.id,
        Message.sender_user_id != current_user.id,
    ]
    if last_read_at:
        conditions.append(Message.created_at > last_read_at)

    stmt = select(func.count(Message.id)).where(and_(*conditions))
    return int(db.scalar(stmt) or 0)


def _last_message(db: Session, *, conversation_id: int) -> Message | None:
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc(), Message.id.desc())
        .limit(1)
    )
    return db.scalar(stmt)


def serialize_conversation(db: Session, *, conversation: Conversation, current_user: User) -> dict[str, Any]:
    other_user = conversation.hr if current_user.role == UserRole.candidate else conversation.candidate
    last_message = _last_message(db, conversation_id=conversation.id)
    unread_count = _unread_count_for_conversation(db, conversation=conversation, current_user=current_user)

    job_payload: dict[str, Any] | None = None
    if conversation.job:
        job_payload = {"id": conversation.job.id, "title": conversation.job.title}

    return {
        "id": conversation.id,
        "candidate_user_id": conversation.candidate_user_id,
        "hr_user_id": conversation.hr_user_id,
        "job": job_payload,
        "other_user": {
            "id": other_user.id if other_user else None,
            "full_name": other_user.full_name if other_user else "Unknown",
            "email": other_user.email if other_user else "",
        },
        "last_message": serialize_message(last_message) if last_message else None,
        "unread_count": unread_count,
        "updated_at": conversation.updated_at.isoformat(),
    }


def get_conversation(db: Session, *, conversation_id: int) -> Conversation:
    stmt = (
        select(Conversation)
        .options(
            selectinload(Conversation.candidate),
            selectinload(Conversation.hr),
            selectinload(Conversation.job),
        )
        .where(Conversation.id == conversation_id)
    )
    conversation = db.scalar(stmt)
    if not conversation:
        raise APIError(status_code=404, code="conversation_not_found", detail="Conversation not found")
    return conversation


def assert_user_in_conversation(*, conversation: Conversation, user: User) -> None:
    if user.id not in {conversation.candidate_user_id, conversation.hr_user_id}:
        raise APIError(status_code=403, code="conversation_forbidden", detail="Forbidden")


def ensure_conversation(
    db: Session,
    *,
    candidate_user_id: int,
    hr_user_id: int,
    job_id: int | None,
) -> Conversation:
    stmt: Select = select(Conversation).where(
        Conversation.candidate_user_id == candidate_user_id,
        Conversation.hr_user_id == hr_user_id,
        Conversation.job_id == job_id,
    )
    conversation = db.scalar(stmt)
    if conversation:
        return conversation

    conversation = Conversation(
        candidate_user_id=candidate_user_id,
        hr_user_id=hr_user_id,
        job_id=job_id,
        last_message_at=None,
        candidate_last_read_at=None,
        hr_last_read_at=None,
    )
    db.add(conversation)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        # Another transaction likely created the same conversation.
        return ensure_conversation(
            db,
            candidate_user_id=candidate_user_id,
            hr_user_id=hr_user_id,
            job_id=job_id,
        )
    return conversation


def list_conversations(db: Session, *, current_user: User, page: int, page_size: int):
    stmt = (
        select(Conversation)
        .options(
            selectinload(Conversation.candidate),
            selectinload(Conversation.hr),
            selectinload(Conversation.job),
        )
        .where(
            or_(
                Conversation.candidate_user_id == current_user.id,
                Conversation.hr_user_id == current_user.id,
            )
        )
        .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
    )
    conversations, meta = paginate(db, stmt, page=page, page_size=page_size)
    payload = [serialize_conversation(db, conversation=conv, current_user=current_user) for conv in conversations]
    return payload, meta


def list_messages(db: Session, *, conversation: Conversation, page: int, page_size: int):
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.asc(), Message.id.asc())
    )
    messages, meta = paginate(db, stmt, page=page, page_size=page_size)
    return [serialize_message(msg) for msg in messages], meta


def send_message(db: Session, *, conversation: Conversation, sender: User, content: str) -> Message:
    assert_user_in_conversation(conversation=conversation, user=sender)

    now = _utcnow()

    message = Message(
        conversation_id=conversation.id,
        sender_user_id=sender.id,
        content=content.strip(),
        message_type="text",
        is_read=False,
    )
    db.add(message)

    conversation.last_message_at = now
    conversation.updated_at = now
    if sender.role == UserRole.candidate:
        conversation.candidate_last_read_at = now
    else:
        conversation.hr_last_read_at = now
    db.add(conversation)

    db.flush()
    return message


def mark_conversation_read(db: Session, *, conversation: Conversation, user: User) -> int:
    assert_user_in_conversation(conversation=conversation, user=user)

    now = _utcnow()
    if user.role == UserRole.candidate:
        conversation.candidate_last_read_at = now
    else:
        conversation.hr_last_read_at = now
    db.add(conversation)

    stmt = select(Message).where(
        Message.conversation_id == conversation.id,
        Message.sender_user_id != user.id,
        Message.is_read.is_(False),
    )
    unread_messages = db.execute(stmt).scalars().all()
    for message in unread_messages:
        message.is_read = True
        message.read_at = now
        db.add(message)

    db.flush()
    return len(unread_messages)


def ensure_conversation_for_job(db: Session, *, candidate: User, job: Job) -> Conversation:
    if candidate.role != UserRole.candidate:
        raise APIError(status_code=403, code="candidate_required", detail="Candidate role required")
    return ensure_conversation(
        db,
        candidate_user_id=candidate.id,
        hr_user_id=job.hr_user_id,
        job_id=job.id,
    )


def other_user_id(*, conversation: Conversation, current_user: User) -> int:
    if current_user.id == conversation.candidate_user_id:
        return conversation.hr_user_id
    if current_user.id == conversation.hr_user_id:
        return conversation.candidate_user_id
    raise APIError(status_code=403, code="conversation_forbidden", detail="Forbidden")


def unread_total(db: Session, *, current_user: User) -> int:
    stmt = select(Conversation).where(
        or_(
            Conversation.candidate_user_id == current_user.id,
            Conversation.hr_user_id == current_user.id,
        )
    )
    conversations = db.execute(stmt).scalars().all()
    return sum(_unread_count_for_conversation(db, conversation=conv, current_user=current_user) for conv in conversations)
