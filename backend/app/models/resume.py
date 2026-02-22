from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.interview import Interview
    from app.models.user import User


class Resume(Base, TimestampMixin):
    __tablename__ = "resumes"
    __table_args__ = (
        Index("ix_resumes_user_created", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)

    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    extracted_skills: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    keywords: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    estimated_experience_years: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    education_level: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    user: Mapped[User] = relationship("User", back_populates="resumes")
    applications: Mapped[list[Application]] = relationship("Application", back_populates="resume")
    interviews: Mapped[list[Interview]] = relationship("Interview", back_populates="resume")