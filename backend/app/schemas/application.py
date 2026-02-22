from __future__ import annotations

from pydantic import BaseModel, Field


class ApplyRequest(BaseModel):
    resume_id: int = Field(gt=0)
    details: dict | None = None


class ApplyResponse(BaseModel):
    application: dict
    interview_id: int
    conversation_id: int
    eligibility: dict


class ApplicationStatusUpdateRequest(BaseModel):
    status: str = Field(pattern="^(shortlisted|rejected)$")


class ApplicationStatusUpdateResponse(BaseModel):
    application: dict
