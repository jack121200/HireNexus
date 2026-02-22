#file name is interview.py
from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.common import PaginationMeta


class MockInterviewCreateRequest(BaseModel):
    role: str = Field(min_length=2, max_length=255)
    years_experience: float = Field(ge=0, le=50)
    resume_id: int | None = Field(default=None, gt=0)
    jd_text: str = Field(min_length=50)


class InterviewCompleteRequest(BaseModel):
    answers: list[str] = Field(default_factory=list)
    transcript: str = Field(default="")
    recording_url: str | None = None


class InterviewResponse(BaseModel):
    interview: dict


class InterviewQuestionsResponse(BaseModel):
    interview_id: int
    questions: list[dict]


class InterviewListResponse(BaseModel):
    items: list[dict]
    meta: PaginationMeta
