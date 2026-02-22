from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Index, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.job import Job
    from app.models.resume import Resume
    from app.models.user import User


class InterviewType(str, enum.Enum):
    ai = "ai"
    mock = "mock"


class InterviewStatus(str, enum.Enum):
    started = "started"
    completed = "completed"


class Interview(Base, TimestampMixin):
    __tablename__ = "interviews"
    __table_args__ = (
        Index("ix_interviews_candidate_created", "candidate_user_id", "created_at"),
        Index("ix_interviews_application", "application_id"),
        Index("ix_interviews_job", "job_id"),
        Index("ix_interviews_type_status", "type", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    candidate_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    hr_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)

    application_id: Mapped[int | None] = mapped_column(ForeignKey("applications.id"), nullable=True)
    job_id: Mapped[int | None] = mapped_column(ForeignKey("jobs.id"), nullable=True)
    resume_id: Mapped[int | None] = mapped_column(ForeignKey("resumes.id"), nullable=True, index=True)

    type: Mapped[InterviewType] = mapped_column(Enum(InterviewType, name="interview_type"), nullable=False, index=True)
    status: Mapped[InterviewStatus] = mapped_column(
        Enum(InterviewStatus, name="interview_status"),
        default=InterviewStatus.started,
        nullable=False,
        index=True,
    )

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    overall_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    report_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    transcript: Mapped[str] = mapped_column(Text, default="", nullable=False)
    recording_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    candidate: Mapped[User] = relationship("User", back_populates="interviews", foreign_keys=[candidate_user_id])
    hr_user: Mapped[User | None] = relationship(
        "User",
        back_populates="hr_interviews",
        foreign_keys=[hr_user_id],
    )

    application: Mapped[Application | None] = relationship("Application", back_populates="interviews")
    job: Mapped[Job | None] = relationship("Job", back_populates="interviews")
    resume: Mapped[Resume | None] = relationship("Resume", back_populates="interviews")
