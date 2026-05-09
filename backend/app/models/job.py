from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.company import Company
    from app.models.conversation import Conversation
    from app.models.interview import Interview
    from app.models.user import User


class Job(Base, TimestampMixin):
    __tablename__ = "jobs"
    __table_args__ = (
        Index("ix_jobs_hr_status", "hr_user_id", "status"),
        Index("ix_jobs_company_created", "company_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    hr_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    responsibilities: Mapped[str | None] = mapped_column(Text, nullable=True)

    required_skills: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    extracted_required_skills: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    preferred_skills: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False, server_default="'[]'")
    parsed_jd: Mapped[dict] = mapped_column(JSON, default=dict, nullable=True)

    minimum_experience_years: Mapped[float] = mapped_column(Float, default=0.0, nullable=False, index=True)
    education_requirement: Mapped[str | None] = mapped_column(String(255), nullable=True)
    employment_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="open", nullable=False, index=True)

    hr_user: Mapped[User] = relationship("User", back_populates="hr_jobs")
    company: Mapped[Company] = relationship("Company", back_populates="jobs")

    applications: Mapped[list[Application]] = relationship("Application", back_populates="job")
    interviews: Mapped[list[Interview]] = relationship("Interview", back_populates="job")
    conversations: Mapped[list[Conversation]] = relationship("Conversation", back_populates="job")