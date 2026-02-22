from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.company import Company
    from app.models.conversation import Conversation
    from app.models.interview import Interview
    from app.models.job import Job
    from app.models.message import Message
    from app.models.notification import Notification
    from app.models.resume import Resume


class UserRole(str, enum.Enum):
    candidate = "candidate"
    hr = "hr"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)

    company: Mapped[Company | None] = relationship("Company", back_populates="hr_users")

    resumes: Mapped[list[Resume]] = relationship("Resume", back_populates="user", cascade="all, delete-orphan")
    applications: Mapped[list[Application]] = relationship(
        "Application", back_populates="candidate", cascade="all, delete-orphan"
    )
    interviews: Mapped[list[Interview]] = relationship(
        "Interview",
        back_populates="candidate",
        foreign_keys="Interview.candidate_user_id",
    )
    hr_interviews: Mapped[list[Interview]] = relationship(
        "Interview",
        back_populates="hr_user",
        foreign_keys="Interview.hr_user_id",
    )
    notifications: Mapped[list[Notification]] = relationship(
        "Notification", back_populates="user", cascade="all, delete-orphan"
    )

    hr_jobs: Mapped[list[Job]] = relationship("Job", back_populates="hr_user")

    conversations_as_candidate: Mapped[list[Conversation]] = relationship(
        "Conversation",
        back_populates="candidate",
        foreign_keys="Conversation.candidate_user_id",
    )
    conversations_as_hr: Mapped[list[Conversation]] = relationship(
        "Conversation",
        back_populates="hr",
        foreign_keys="Conversation.hr_user_id",
    )

    messages_sent: Mapped[list[Message]] = relationship("Message", back_populates="sender")
