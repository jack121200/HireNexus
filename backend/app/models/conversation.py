from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.job import Job
    from app.models.message import Message
    from app.models.user import User


class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"
    __table_args__ = (
        UniqueConstraint("candidate_user_id", "hr_user_id", "job_id", name="uq_conversations_pair_job"),
        Index("ix_conversations_candidate_updated", "candidate_user_id", "updated_at"),
        Index("ix_conversations_hr_updated", "hr_user_id", "updated_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    candidate_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    hr_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    job_id: Mapped[int | None] = mapped_column(ForeignKey("jobs.id"), nullable=True, index=True)

    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    candidate_last_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    hr_last_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    candidate: Mapped[User] = relationship(
        "User", back_populates="conversations_as_candidate", foreign_keys=[candidate_user_id]
    )
    hr: Mapped[User] = relationship("User", back_populates="conversations_as_hr", foreign_keys=[hr_user_id])
    job: Mapped[Job | None] = relationship("Job", back_populates="conversations")

    messages: Mapped[list[Message]] = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at"
    )