from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, Float, ForeignKey, Index, Integer, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.interview import Interview
    from app.models.job import Job
    from app.models.resume import Resume
    from app.models.user import User


class ApplicationStatus(str, enum.Enum):
    applied = "applied"
    shortlisted = "shortlisted"
    rejected = "rejected"
    interview_completed = "interview_completed"


class Application(Base, TimestampMixin):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("candidate_user_id", "job_id", name="uq_applications_candidate_job"),
        Index("ix_applications_job_status", "job_id", "status"),
        Index("ix_applications_candidate_status", "candidate_user_id", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    candidate_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), nullable=False, index=True)
    resume_id: Mapped[int] = mapped_column(ForeignKey("resumes.id"), nullable=False, index=True)

    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, name="application_status"),
        default=ApplicationStatus.applied,
        nullable=False,
        index=True,
    )

    eligibility_percentage: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    skill_match_percentage: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    experience_match_percentage: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    education_match_percentage: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    semantic_similarity: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    keyword_overlap: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    missing_skills: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    eligibility_breakdown_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    application_details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    candidate: Mapped[User] = relationship("User", back_populates="applications")
    job: Mapped[Job] = relationship("Job", back_populates="applications")
    resume: Mapped[Resume] = relationship("Resume", back_populates="applications")
    interviews: Mapped[list[Interview]] = relationship("Interview", back_populates="application")
