from __future__ import annotations

from pydantic import BaseModel, Field


class ResumeResponse(BaseModel):
    id: int
    file_name: str
    file_type: str
    is_primary: bool
    extracted_skills: list[str]
    estimated_experience_years: float
    education_level: str | None
    created_at: str


class ResumeDetailResponse(ResumeResponse):
    raw_text: str
    parsed: dict


class ResumeAnalysisRequest(BaseModel):
    jd_text: str = Field(min_length=20)
    required_skills: list[str] | None = None
    minimum_experience_years: float | None = Field(default=None, ge=0)
    education_requirement: str | None = None


class ResumeAnalysisResponse(BaseModel):
    resume_id: int
    eligibility: dict


class ResumeUploadResponse(BaseModel):
    resume: ResumeResponse